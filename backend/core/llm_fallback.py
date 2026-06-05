"""
LLM fallback classifier — uses Claude to classify changes that
pattern matching couldn't confidently identify.
"""

import json
import os
import anthropic
from core.mapping_engine import DetectedChange

_TAXONOMY_SUMMARY = None

def _get_taxonomy_summary() -> str:
    global _TAXONOMY_SUMMARY
    if _TAXONOMY_SUMMARY:
        return _TAXONOMY_SUMMARY

    from pathlib import Path
    with open(Path(__file__).parent.parent / "data" / "change_taxonomy.json") as f:
        taxonomy = json.load(f)

    lines = ["Code-detectable change types:"]
    for c in taxonomy["code_detectable"]:
        lines.append(f"- {c['id']}: {c['name']} — {c['example']}")

    _TAXONOMY_SUMMARY = "\n".join(lines)
    return _TAXONOMY_SUMMARY


def classify_with_llm(
    diff_excerpt: str,
    unmatched_files: list[str],
    api_key: str | None = None,
) -> list[DetectedChange]:
    """
    Use Claude to classify changes that pattern matching missed.
    Returns additional DetectedChange objects tagged source='llm'.
    """
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return []

    taxonomy = _get_taxonomy_summary()
    files_str = "\n".join(f"  - {f}" for f in unmatched_files[:20])

    prompt = f"""You are a security compliance analyst classifying git changes for ATO (Authority to Operate) impact analysis.

The following files were changed in a pull request but did not match standard detection patterns:
{files_str}

Here is an excerpt of the diff:
```
{diff_excerpt[:3000]}
```

Using the change taxonomy below, identify which change types (if any) apply to these changes.
Only classify if you are reasonably confident — do not force a classification.

{taxonomy}

Respond with a JSON array. Each element:
{{
  "change_type_id": "<taxonomy ID from above>",
  "change_type_name": "<name>",
  "confidence": "medium" or "low",
  "reasoning": "<one sentence explaining why>",
  "evidence": ["<specific file or pattern that led to classification>"]
}}

If no changes match, return an empty array [].
Respond with JSON only — no markdown, no explanation."""

    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        parsed = json.loads(message.content[0].text)
        results = []
        for item in parsed:
            results.append(DetectedChange(
                change_type_id=item["change_type_id"],
                change_type_name=item["change_type_name"],
                confidence=item.get("confidence", "low"),
                evidence=item.get("evidence", []),
                source="llm",
                llm_reasoning=item.get("reasoning"),
            ))
        return results
    except (json.JSONDecodeError, KeyError):
        return []
