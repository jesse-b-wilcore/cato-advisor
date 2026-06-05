"""
Core mapping engine — the heart of the product.
Given a list of classified changes, returns affected artifacts,
affected NIST controls, the FedRAMP tier, and recommended actions.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

DATA = Path(__file__).parent.parent / "data"

def _load(filename: str) -> dict | list:
    with open(DATA / filename) as f:
        return json.load(f)

_ARTIFACTS: dict[str, dict]   = {a["id"]: a for a in _load("artifacts.json")}
_TAXONOMY:  dict               = _load("change_taxonomy.json")
_TIERS:     dict               = _load("tiers.json")

_CODE_MAP: dict[str, dict] = {c["id"]: c for c in _TAXONOMY["code_detectable"]}
_MANUAL_MAP: dict[str, dict] = {c["id"]: c for c in _TAXONOMY["manual"]}
_TIER_MAP: dict[str, dict] = {t["id"]: t for t in _TIERS["tiers"]}
_TIER_PRECEDENCE: list[str] = _TIERS["tier_precedence"]

# Map change type ID → tier ID
_CHANGE_TIER: dict[str, str] = {}
for tier in _TIERS["tiers"]:
    for ct in tier.get("change_types", []):
        _CHANGE_TIER[ct] = tier["id"]


@dataclass
class DetectedChange:
    change_type_id: str
    change_type_name: str
    confidence: str          # high / medium / low
    evidence: list[str]      # file paths / matched patterns
    source: str              # pattern_match / llm
    llm_reasoning: Optional[str] = None


@dataclass
class AffectedArtifact:
    id: str
    name: str
    phase: str
    owner: str
    urgency: str             # immediate / review
    triggered_by: list[str]  # change type IDs


@dataclass
class AffectedControl:
    id: str
    family: str
    title: str
    impact: str              # direct / potential
    triggered_by: list[str]


@dataclass
class MappingResult:
    detected_changes: list[DetectedChange]
    affected_artifacts: list[AffectedArtifact]
    affected_controls: list[AffectedControl]
    tier: dict
    recommended_actions: list[str]
    total_artifact_count: int
    total_control_count: int


# NIST 800-53 control family + title lookup (abbreviated — full list in prod)
CONTROL_META: dict[str, dict] = {
    "AC-2":  {"family": "AC", "title": "Account Management"},
    "AC-3":  {"family": "AC", "title": "Access Enforcement"},
    "AC-4":  {"family": "AC", "title": "Information Flow Enforcement"},
    "AC-6":  {"family": "AC", "title": "Least Privilege"},
    "AU-2":  {"family": "AU", "title": "Event Logging"},
    "AU-3":  {"family": "AU", "title": "Content of Audit Records"},
    "AU-6":  {"family": "AU", "title": "Audit Record Review, Analysis, and Reporting"},
    "AU-12": {"family": "AU", "title": "Audit Record Generation"},
    "CA-3":  {"family": "CA", "title": "Information Exchange"},
    "CA-6":  {"family": "CA", "title": "Authorization"},
    "CM-2":  {"family": "CM", "title": "Baseline Configuration"},
    "CM-3":  {"family": "CM", "title": "Configuration Change Control"},
    "CM-4":  {"family": "CM", "title": "Impact Analyses"},
    "CM-6":  {"family": "CM", "title": "Configuration Settings"},
    "CM-7":  {"family": "CM", "title": "Least Functionality"},
    "CP-4":  {"family": "CP", "title": "Contingency Plan Testing"},
    "CP-9":  {"family": "CP", "title": "System Backup"},
    "CP-10": {"family": "CP", "title": "System Recovery and Reconstitution"},
    "IA-2":  {"family": "IA", "title": "Identification and Authentication (Organizational Users)"},
    "IA-5":  {"family": "IA", "title": "Authenticator Management"},
    "IA-8":  {"family": "IA", "title": "Identification and Authentication (Non-Organizational Users)"},
    "IR-3":  {"family": "IR", "title": "Incident Response Testing"},
    "MP-6":  {"family": "MP", "title": "Media Sanitization"},
    "PT-2":  {"family": "PT", "title": "Authority to Process Personally Identifiable Information"},
    "RA-5":  {"family": "RA", "title": "Vulnerability Monitoring and Scanning"},
    "SA-9":  {"family": "SA", "title": "External System Services"},
    "SA-10": {"family": "SA", "title": "Developer Configuration Management"},
    "SA-11": {"family": "SA", "title": "Developer Testing and Evaluation"},
    "SC-7":  {"family": "SC", "title": "Boundary Protection"},
    "SC-8":  {"family": "SC", "title": "Transmission Confidentiality and Integrity"},
    "SC-12": {"family": "SC", "title": "Cryptographic Key Establishment and Management"},
    "SC-13": {"family": "SC", "title": "Cryptographic Protection"},
    "SC-28": {"family": "SC", "title": "Protection of Information at Rest"},
    "SI-2":  {"family": "SI", "title": "Flaw Remediation"},
    "SI-12": {"family": "SI", "title": "Information Management and Retention"},
    "SR-3":  {"family": "SR", "title": "Supply Chain Controls and Processes"},
}

# Artifact urgency — "immediate" if the artifact is directly in the change's primary list
IMMEDIATE_ARTIFACTS = {"A11", "A32", "A48", "A2", "A36", "A41"}


def _get_tier_for_changes(change_type_ids: list[str]) -> dict:
    """Return the highest-precedence tier across all detected change types."""
    found_tiers = set()
    for ct_id in change_type_ids:
        tier_id = _CHANGE_TIER.get(ct_id, "ROUTINE")
        found_tiers.add(tier_id)

    for tier_id in _TIER_PRECEDENCE:
        if tier_id in found_tiers:
            return _TIER_MAP[tier_id]

    return _TIER_MAP["ROUTINE"]


def _build_recommended_actions(
    tier: dict,
    artifact_ids: set[str],
    control_ids: set[str],
    changes: list[DetectedChange],
) -> list[str]:
    actions = []

    if tier["id"] in ("TRANSFORMATIVE", "IMPACT_CATEGORIZATION"):
        actions.append(f"Generate and submit a Significant Change Notification (SCN) to the AO — tier is {tier['name']}")
    if tier["id"] == "IMPACT_CATEGORIZATION":
        actions.append("Escalate to ISSM immediately — potential impact categorization change")
        actions.append("Block deployment until full re-assessment is complete")

    if "A11" in artifact_ids:
        affected_control_list = ", ".join(sorted(control_ids)[:6])
        actions.append(f"Update SSP control descriptions for: {affected_control_list}")

    if "A32" in artifact_ids:
        actions.append("Draft or update ISA for any new external system connections")

    if "A2" in artifact_ids:
        actions.append("Update Authorization Boundary Diagram to reflect architecture changes")

    if "A30" in artifact_ids:
        actions.append("Update Supply Chain Risk Management Plan with new dependency information")

    if tier["id"] != "ROUTINE":
        actions.append("Generate draft Security Impact Analysis (SIA) document")

    for change in changes:
        if change.change_type_id == "DB_SCHEMA_CHANGE":
            actions.append("Review PIA/PTA — database schema change may affect PII handling (A6, A7)")
        if change.change_type_id == "NEW_EXTERNAL_API":
            actions.append("Complete ISA with new external service before production deployment (A32)")
        if change.change_type_id == "AUTH_CHANGE":
            actions.append("Update IA-2 and IA-5 SSP narratives with new authentication mechanism details")

    return actions


def run_mapping(detected_changes: list[DetectedChange]) -> MappingResult:
    """
    Core mapping function. Takes detected changes and returns full impact analysis.
    """
    change_type_ids = [c.change_type_id for c in detected_changes]

    # Aggregate artifacts
    artifact_trigger_map: dict[str, list[str]] = {}
    for change in detected_changes:
        definition = _CODE_MAP.get(change.change_type_id) or _MANUAL_MAP.get(change.change_type_id)
        if not definition:
            continue
        for art_id in definition.get("artifacts", []):
            if art_id not in artifact_trigger_map:
                artifact_trigger_map[art_id] = []
            artifact_trigger_map[art_id].append(change.change_type_id)

    affected_artifacts = []
    for art_id, triggers in artifact_trigger_map.items():
        artifact = _ARTIFACTS.get(art_id)
        if not artifact:
            continue
        affected_artifacts.append(AffectedArtifact(
            id=art_id,
            name=artifact["name"],
            phase=artifact["phase"],
            owner=artifact["owner"],
            urgency="immediate" if art_id in IMMEDIATE_ARTIFACTS else "review",
            triggered_by=triggers,
        ))
    affected_artifacts.sort(key=lambda a: (0 if a.urgency == "immediate" else 1, a.id))

    # Aggregate controls
    control_trigger_map: dict[str, list[str]] = {}
    for change in detected_changes:
        definition = _CODE_MAP.get(change.change_type_id) or _MANUAL_MAP.get(change.change_type_id)
        if not definition:
            continue
        for ctrl_id in definition.get("controls", []):
            if ctrl_id not in control_trigger_map:
                control_trigger_map[ctrl_id] = []
            control_trigger_map[ctrl_id].append(change.change_type_id)

    affected_controls = []
    for ctrl_id, triggers in control_trigger_map.items():
        meta = CONTROL_META.get(ctrl_id, {"family": ctrl_id[:2], "title": ctrl_id})
        affected_controls.append(AffectedControl(
            id=ctrl_id,
            family=meta["family"],
            title=meta["title"],
            impact="direct",
            triggered_by=triggers,
        ))
    affected_controls.sort(key=lambda c: c.id)

    tier = _get_tier_for_changes(change_type_ids)
    artifact_ids = set(artifact_trigger_map.keys())
    control_ids = {c.id for c in affected_controls}

    recommended_actions = _build_recommended_actions(tier, artifact_ids, control_ids, detected_changes)

    return MappingResult(
        detected_changes=detected_changes,
        affected_artifacts=affected_artifacts,
        affected_controls=affected_controls,
        tier=tier,
        recommended_actions=recommended_actions,
        total_artifact_count=len(affected_artifacts),
        total_control_count=len(affected_controls),
    )
