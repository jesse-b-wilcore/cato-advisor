"""
Diff analyzer — classifies a raw git diff into detected change types
using pattern matching as the primary classifier with LLM fallback.
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass

from core.mapping_engine import DetectedChange

DATA = Path(__file__).parent.parent / "data"

with open(DATA / "change_taxonomy.json") as f:
    _TAXONOMY = json.load(f)

_CODE_CHANGES = _TAXONOMY["code_detectable"]


@dataclass
class DiffFile:
    path: str
    added_lines: list[str]
    removed_lines: list[str]
    is_new: bool
    is_deleted: bool


def _parse_diff(raw_diff: str) -> list[DiffFile]:
    """Parse a unified diff into a list of DiffFile objects."""
    files: list[DiffFile] = []
    current_file: DiffFile | None = None
    added: list[str] = []
    removed: list[str] = []

    for line in raw_diff.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                current_file.added_lines = added
                current_file.removed_lines = removed
                files.append(current_file)
            added, removed = [], []
            current_file = None

        elif line.startswith("+++ b/"):
            path = line[6:]
            is_new = False
            current_file = DiffFile(path=path, added_lines=[], removed_lines=[], is_new=is_new, is_deleted=False)

        elif line.startswith("new file mode"):
            if current_file:
                current_file.is_new = True

        elif line.startswith("deleted file mode"):
            if current_file:
                current_file.is_deleted = True

        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])

        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])

    if current_file:
        current_file.added_lines = added
        current_file.removed_lines = removed
        files.append(current_file)

    return files


def _filename_matches(path: str, patterns: list[str]) -> bool:
    """Check if a file path matches any of the given glob-like patterns."""
    filename = Path(path).name
    for pattern in patterns:
        # Handle directory prefix patterns like ".github/workflows/*.yml"
        if "/" in pattern:
            if re.search(pattern.replace(".", r"\.").replace("*", ".*"), path):
                return True
        else:
            clean = pattern.replace("*.", "").replace(".*", "").replace("*", "")
            if clean.lower() in filename.lower() or filename == pattern:
                return True
            if pattern.endswith(".*") and filename.startswith(pattern[:-2]):
                return True
    return False


def _content_matches(lines: list[str], patterns: list[str]) -> list[str]:
    """Return the content patterns found in the given lines."""
    found = []
    joined = "\n".join(lines)
    for pattern in patterns:
        if pattern.lower() in joined.lower():
            found.append(pattern)
    return found


def _classify_change(change_def: dict, files: list[DiffFile]) -> tuple[str, list[str]]:
    """
    Returns (confidence, evidence_list) for a change type against a set of files.
    confidence: 'high' | 'medium' | 'low' | 'none'
    """
    patterns = change_def.get("detection_patterns", {})
    file_patterns = patterns.get("file_patterns", [])
    content_patterns = patterns.get("content_patterns", [])

    matched_files: list[str] = []
    matched_content: list[str] = []

    for f in files:
        if _filename_matches(f.path, file_patterns):
            matched_files.append(f.path)
            if content_patterns:
                found = _content_matches(f.added_lines + f.removed_lines, content_patterns)
                matched_content.extend(found)

    if matched_files and matched_content:
        confidence = "high"
        evidence = [f"File match: {p}" for p in matched_files[:3]] + \
                   [f"Pattern match: `{p}`" for p in matched_content[:3]]
    elif matched_files:
        confidence = "medium"
        evidence = [f"File match: {p}" for p in matched_files[:3]]
    else:
        # Content-only match (no file path match)
        all_lines = []
        for f in files:
            all_lines.extend(f.added_lines)
        found = _content_matches(all_lines, content_patterns)
        if found:
            confidence = "low"
            evidence = [f"Content pattern: `{p}`" for p in found[:3]]
        else:
            return "none", []

    return confidence, evidence


def analyze_diff(raw_diff: str) -> list[DetectedChange]:
    """
    Main entry point. Parse the diff and classify all detectable change types.
    Returns a list of DetectedChange objects with confidence >= low.
    """
    if not raw_diff or not raw_diff.strip():
        return []

    files = _parse_diff(raw_diff)
    if not files:
        return []

    results: list[DetectedChange] = []
    unmatched_files: list[str] = []

    for change_def in _CODE_CHANGES:
        confidence, evidence = _classify_change(change_def, files)
        if confidence != "none":
            results.append(DetectedChange(
                change_type_id=change_def["id"],
                change_type_name=change_def["name"],
                confidence=confidence,
                evidence=evidence,
                source="pattern_match",
            ))

    # Collect files that didn't confidently match anything for LLM fallback
    matched_file_paths = set()
    for change in results:
        if change.confidence == "high":
            for ev in change.evidence:
                if ev.startswith("File match:"):
                    matched_file_paths.add(ev.replace("File match: ", "").strip())

    for f in files:
        if f.path not in matched_file_paths:
            unmatched_files.append(f.path)

    return results, unmatched_files


def get_diff_stats(raw_diff: str) -> dict:
    """Return basic stats about a diff for validation and display."""
    files = _parse_diff(raw_diff)
    total_added = sum(len(f.added_lines) for f in files)
    total_removed = sum(len(f.removed_lines) for f in files)
    return {
        "file_count": len(files),
        "lines_added": total_added,
        "lines_removed": total_removed,
        "files": [f.path for f in files],
        "new_files": [f.path for f in files if f.is_new],
        "deleted_files": [f.path for f in files if f.is_deleted],
    }
