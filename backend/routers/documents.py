"""
UC3 — Document Generation
POST /api/documents/sia              — generate SIA from an analysis ID
GET  /api/documents/sia/{id}/docx    — download SIA as DOCX
GET  /api/documents/sia/{id}/pdf     — download SIA as PDF (weasyprint)
GET  /api/documents/sia/{id}         — get SIA JSON for UI display
POST /api/documents/scn              — generate SCN for adaptive/transformative changes
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from core.mapping_engine import run_mapping, DetectedChange, MappingResult
from core.sia_generator import generate_sia_content, build_sia_docx, SIADocument

router = APIRouter()

_sia_store: dict[str, SIADocument] = {}
_analysis_store_ref = None  # set at startup by main.py if needed


class SIARequest(BaseModel):
    analysis_id: Optional[str] = None
    # Or supply mapping data directly (for manual intake)
    detected_changes: Optional[list[dict]] = None
    system_name: Optional[str] = "[System Name]"
    change_reference: Optional[str] = None


@router.post("/sia")
async def generate_sia(req: SIARequest):
    """UC3-001: Generate a draft SIA from a prior analysis or inline change data."""
    from routers.analysis import _store as analysis_store

    if req.analysis_id:
        stored = analysis_store.get(req.analysis_id)
        if not stored:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        detected_changes = [
            DetectedChange(
                change_type_id=c["change_type_id"],
                change_type_name=c["change_type_name"],
                confidence=c["confidence"],
                evidence=c["evidence"],
                source=c["source"],
                llm_reasoning=c.get("llm_reasoning"),
            )
            for c in stored["detected_changes"]
        ]
        system_name = req.system_name or stored.get("system_name", "[System Name]")
        change_ref = req.change_reference or stored.get("change_reference", req.analysis_id[:8].upper())

    elif req.detected_changes:
        detected_changes = [
            DetectedChange(
                change_type_id=c["change_type_id"],
                change_type_name=c["change_type_name"],
                confidence=c.get("confidence", "medium"),
                evidence=c.get("evidence", []),
                source=c.get("source", "manual"),
            )
            for c in req.detected_changes
        ]
        system_name = req.system_name or "[System Name]"
        change_ref = req.change_reference or str(uuid.uuid4())[:8].upper()
    else:
        raise HTTPException(status_code=400, detail="Provide either analysis_id or detected_changes.")

    mapping = run_mapping(detected_changes)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    sia = generate_sia_content(mapping, system_name, change_ref, api_key)

    sia_id = str(uuid.uuid4())
    _sia_store[sia_id] = sia

    return {
        "sia_id": sia_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_name": sia.system_name,
        "change_reference": sia.change_reference,
        "tier": sia.tier,
        "tier_color": sia.tier_color,
        "risk_level": sia.risk_level,
        "ao_action_required": sia.ao_action_required,
        "change_description": sia.change_description,
        "system_impact_summary": sia.system_impact_summary,
        "affected_controls_analysis": sia.affected_controls_analysis,
        "affected_artifacts": sia.affected_artifacts,
        "risk_determination": sia.risk_determination,
        "recommended_actions": sia.recommended_actions,
    }


@router.get("/sia/{sia_id}")
def get_sia(sia_id: str):
    sia = _sia_store.get(sia_id)
    if not sia:
        raise HTTPException(status_code=404, detail="SIA not found.")
    return {
        "sia_id": sia_id,
        "system_name": sia.system_name,
        "change_reference": sia.change_reference,
        "tier": sia.tier,
        "tier_color": sia.tier_color,
        "risk_level": sia.risk_level,
        "ao_action_required": sia.ao_action_required,
        "change_description": sia.change_description,
        "system_impact_summary": sia.system_impact_summary,
        "affected_controls_analysis": sia.affected_controls_analysis,
        "affected_artifacts": sia.affected_artifacts,
        "risk_determination": sia.risk_determination,
        "recommended_actions": sia.recommended_actions,
    }


@router.get("/sia/{sia_id}/docx")
def download_sia_docx(sia_id: str):
    """UC3-003: Download SIA as DOCX."""
    sia = _sia_store.get(sia_id)
    if not sia:
        raise HTTPException(status_code=404, detail="SIA not found.")

    docx_bytes = build_sia_docx(sia)
    filename = f"SIA-{sia.system_name.replace(' ', '_')}-{sia.change_reference}-{sia.prepared_date.replace(' ', '_')}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
