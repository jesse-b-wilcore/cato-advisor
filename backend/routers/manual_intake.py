"""
UC2 — Manual Change Intake
GET  /api/intake/types              — list all 12 manual change types
POST /api/intake/classify           — classify free-text description with AI
POST /api/intake/submit             — submit a structured manual change form
GET  /api/intake/history            — unified change history (code + manual)
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import anthropic

from core.mapping_engine import run_mapping, DetectedChange

router = APIRouter()

_manual_changes_store: list[dict] = []

# Load manual change taxonomy
from pathlib import Path
with open(Path(__file__).parent.parent / "data" / "change_taxonomy.json") as f:
    _MANUAL_TYPES = {c["id"]: c for c in json.load(f)["manual"]}


class ClassifyRequest(BaseModel):
    description: str


class ManualChangeSubmission(BaseModel):
    change_type_id: str
    form_data: dict[str, Any]
    system_name: Optional[str] = "[System Name]"
    submitted_by: Optional[str] = "ISSO"


@router.get("/types")
def get_manual_change_types():
    """Return all 12 manual change types for the form selector."""
    return [
        {
            "id": v["id"],
            "name": v["name"],
            "example": v["example"],
            "why_not_code": v["why_not_code"],
            "form_fields": v.get("form_fields", []),
            "artifacts": v["artifacts"],
            "controls": v["controls"],
        }
        for v in _MANUAL_TYPES.values()
    ]


@router.post("/classify")
def classify_free_text(req: ClassifyRequest):
    """
    UC2-002: Use Claude to classify a free-text change description
    into one of the 12 manual change types.
    """
    if not req.description.strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty.")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI classification requires ANTHROPIC_API_KEY.")

    types_summary = "\n".join(
        f"- {v['id']}: {v['name']} — Example: {v['example']}"
        for v in _MANUAL_TYPES.values()
    )

    prompt = f"""You are a federal security compliance analyst. A user has described a system change in plain English.
Classify it into one of these 12 non-code change types:

{types_summary}

User description: "{req.description}"

Respond with JSON only:
{{
  "change_type_id": "<one of the IDs above>",
  "change_type_name": "<name>",
  "confidence": "high|medium|low",
  "reasoning": "<one sentence explaining the classification>",
  "extracted_fields": {{
    "<field_name>": "<extracted value from the description if present>"
  }}
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system="You are a compliance classification assistant. Respond with valid JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        result = json.loads(message.content[0].text)
        change_type = _MANUAL_TYPES.get(result.get("change_type_id", ""))
        if change_type:
            result["form_fields"] = change_type.get("form_fields", [])
            result["artifacts"] = change_type.get("artifacts", [])
            result["controls"] = change_type.get("controls", [])
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI classification returned invalid response.")


@router.post("/submit")
def submit_manual_change(req: ManualChangeSubmission):
    """
    UC2-003/004: Submit a manual change form and run it through the mapping engine.
    """
    change_type = _MANUAL_TYPES.get(req.change_type_id)
    if not change_type:
        raise HTTPException(status_code=400, detail=f"Unknown change type: {req.change_type_id}")

    # Validate required fields
    required = change_type.get("form_fields", [])
    missing = [f for f in required if not req.form_data.get(f)]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required fields: {', '.join(missing)}")

    # Run through mapping engine
    detected = [DetectedChange(
        change_type_id=req.change_type_id,
        change_type_name=change_type["name"],
        confidence="high",
        evidence=[f"{k}: {v}" for k, v in req.form_data.items() if v][:5],
        source="manual",
    )]

    mapping = run_mapping(detected)
    change_id = str(uuid.uuid4())

    record = {
        "id": change_id,
        "source": "manual",
        "change_type_id": req.change_type_id,
        "change_type_name": change_type["name"],
        "form_data": req.form_data,
        "system_name": req.system_name,
        "submitted_by": req.submitted_by,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "tier": mapping.tier,
        "affected_artifacts": [{"id": a.id, "name": a.name, "urgency": a.urgency} for a in mapping.affected_artifacts],
        "affected_controls": [{"id": c.id, "title": c.title} for c in mapping.affected_controls],
        "recommended_actions": mapping.recommended_actions,
        "total_artifact_count": mapping.total_artifact_count,
        "total_control_count": mapping.total_control_count,
    }
    _manual_changes_store.append(record)
    return record


@router.get("/history")
def get_change_history():
    """UC2-005: Return unified change history (manual changes for now; code changes added by analysis router)."""
    return sorted(_manual_changes_store, key=lambda x: x["submitted_at"], reverse=True)
