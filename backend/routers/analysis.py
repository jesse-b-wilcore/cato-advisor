"""
UC1 — PR Diff Analyzer
POST /api/analysis/diff        — analyze a raw diff
POST /api/analysis/pr-url      — fetch a PR and analyze its diff
GET  /api/analysis/{id}        — retrieve a stored analysis result
"""

import os
import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.diff_analyzer import analyze_diff, get_diff_stats
from core.llm_fallback import classify_with_llm
from core.mapping_engine import run_mapping, MappingResult, DetectedChange
from core.sia_generator import generate_sia_content

router = APIRouter()

# In-memory store for the prototype (replace with DB in production)
_store: dict[str, dict] = {}


class DiffRequest(BaseModel):
    diff_text: str
    system_name: Optional[str] = "[System Name]"
    change_reference: Optional[str] = None
    use_llm_fallback: Optional[bool] = True


class PRUrlRequest(BaseModel):
    pr_url: str
    github_token: Optional[str] = None
    system_name: Optional[str] = "[System Name]"


def _mapping_to_dict(result: MappingResult) -> dict:
    return {
        "detected_changes": [
            {
                "change_type_id": c.change_type_id,
                "change_type_name": c.change_type_name,
                "confidence": c.confidence,
                "evidence": c.evidence,
                "source": c.source,
                "llm_reasoning": c.llm_reasoning,
            }
            for c in result.detected_changes
        ],
        "affected_artifacts": [
            {
                "id": a.id,
                "name": a.name,
                "phase": a.phase,
                "owner": a.owner,
                "urgency": a.urgency,
                "triggered_by": a.triggered_by,
            }
            for a in result.affected_artifacts
        ],
        "affected_controls": [
            {
                "id": c.id,
                "family": c.family,
                "title": c.title,
                "impact": c.impact,
                "triggered_by": c.triggered_by,
            }
            for c in result.affected_controls
        ],
        "tier": result.tier,
        "recommended_actions": result.recommended_actions,
        "total_artifact_count": result.total_artifact_count,
        "total_control_count": result.total_control_count,
    }


@router.post("/diff")
async def analyze_diff_endpoint(req: DiffRequest):
    if not req.diff_text or not req.diff_text.strip():
        raise HTTPException(status_code=400, detail="Diff text is empty or unparseable.")

    lines = req.diff_text.splitlines()
    if len(lines) > 5000:
        raise HTTPException(status_code=400, detail="Diff exceeds 5,000 line limit for this prototype.")

    # Stats for display
    stats = get_diff_stats(req.diff_text)

    # Pattern matching
    pattern_changes, unmatched_files = analyze_diff(req.diff_text)

    # LLM fallback for unmatched files
    llm_changes: list[DetectedChange] = []
    if req.use_llm_fallback and unmatched_files:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key:
            llm_changes = classify_with_llm(req.diff_text, unmatched_files, api_key)

    all_changes = pattern_changes + llm_changes

    if not all_changes:
        analysis_id = str(uuid.uuid4())
        result = {
            "id": analysis_id,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "system_name": req.system_name,
            "change_reference": req.change_reference or analysis_id[:8].upper(),
            "diff_stats": stats,
            "detected_changes": [],
            "affected_artifacts": [],
            "affected_controls": [],
            "tier": {"id": "ROUTINE", "name": "Routine Recurring", "color": "green", "ao_action": "None"},
            "recommended_actions": ["No significant changes detected. Routine monitoring continues."],
            "total_artifact_count": 0,
            "total_control_count": 0,
        }
        _store[analysis_id] = result
        return result

    # Run the mapping engine
    mapping = run_mapping(all_changes)
    analysis_id = str(uuid.uuid4())
    change_ref = req.change_reference or analysis_id[:8].upper()

    result = {
        "id": analysis_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "system_name": req.system_name,
        "change_reference": change_ref,
        "diff_stats": stats,
        **_mapping_to_dict(mapping),
    }
    _store[analysis_id] = result
    return result


@router.post("/pr-url")
async def analyze_pr_url(req: PRUrlRequest):
    """Fetch a GitHub PR diff and analyze it."""
    # Parse GitHub PR URL: https://github.com/{owner}/{repo}/pull/{number}
    import re
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", req.pr_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL format. Expected: https://github.com/{owner}/{repo}/pull/{number}")

    owner, repo, pr_number = match.groups()
    headers = {"Accept": "application/vnd.github.v3.diff"}
    if req.github_token:
        headers["Authorization"] = f"Bearer {req.github_token}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={**headers, "Accept": "application/vnd.github.v3.diff"},
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"GitHub API error: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Failed to reach GitHub API: {str(e)}")

    diff_text = response.text
    change_ref = f"{owner}/{repo}#PR{pr_number}"

    return await analyze_diff_endpoint(DiffRequest(
        diff_text=diff_text,
        system_name=req.system_name,
        change_reference=change_ref,
    ))


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str):
    if analysis_id not in _store:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return _store[analysis_id]


@router.get("/")
def list_analyses():
    return [
        {"id": k, "analyzed_at": v["analyzed_at"], "change_reference": v.get("change_reference"),
         "tier": v.get("tier", {}).get("name"), "artifact_count": v.get("total_artifact_count")}
        for k, v in sorted(_store.items(), key=lambda x: x[1]["analyzed_at"], reverse=True)
    ]
