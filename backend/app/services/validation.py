from __future__ import annotations

import json
from difflib import unified_diff
from typing import Any, Dict

from pydantic import ValidationError

from ..core.exceptions import ProviderResponseError
from ..schemas.review import Category, CodeReviewResponse, Finding, Severity

_VALID_CATEGORIES = {c.value for c in Category}
_VALID_SEVERITIES = {s.value for s in Severity}


def extract_json(raw_text: str) -> Dict[str, Any] | None:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None
    # Models sometimes wrap JSON in ```json fences despite instructions; strip them.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:]
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _coerce_finding(raw: Any) -> Finding | None:
    if not isinstance(raw, dict):
        return None
    category = str(raw.get("category", "")).strip().lower()
    severity = str(raw.get("severity", "")).strip().lower()
    title = str(raw.get("title", "")).strip()
    description = str(raw.get("description", "")).strip()
    if category not in _VALID_CATEGORIES or not title or not description:
        return None
    if severity not in _VALID_SEVERITIES:
        severity = "medium"
    line = raw.get("line")
    try:
        line = int(line) if line is not None else None
        if line is not None and line < 1:
            line = None
    except (TypeError, ValueError):
        line = None
    return Finding(category=category, severity=severity, title=title, description=description, line=line)


def normalize_findings(payload: Dict[str, Any]) -> list[Finding]:
    raw_findings = payload.get("findings")
    if isinstance(raw_findings, list):
        coerced = [_coerce_finding(f) for f in raw_findings]
        return [f for f in coerced if f is not None]

    # Backward-compat: older prompt/model output might still use the four
    # flat string-array shape. Fold those into structured findings instead
    # of throwing the data away.
    legacy_map = {
        "bugs": Category.bug,
        "security_risks": Category.security,
        "performance_improvements": Category.performance,
        "code_quality_issues": Category.quality,
    }
    findings: list[Finding] = []
    for key, category in legacy_map.items():
        for item in payload.get(key, []) or []:
            text = str(item).strip()
            if text:
                findings.append(
                    Finding(category=category, severity=Severity.medium, title=text[:120], description=text)
                )
    return findings


def generate_code_diff(original_code: str, refactored_code: str, language: str) -> str:
    diff = unified_diff(
        original_code.strip().splitlines(),
        refactored_code.strip().splitlines(),
        fromfile=f"original.{language}",
        tofile=f"refactored.{language}",
        lineterm="",
    )
    result = "\n".join(diff)
    return result if result else "No meaningful code changes detected."


def parse_and_validate_response(raw_text: str, original_code: str, language: str) -> Dict[str, Any]:
    parsed = extract_json(raw_text)
    if not parsed:
        raise ProviderResponseError("Model response was not valid JSON.")

    findings = normalize_findings(parsed)
    refactored_code = str(parsed.get("refactored_code", "")).strip() or original_code.strip()
    diff = generate_code_diff(original_code, refactored_code, language)

    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "findings": findings,
        "refactored_code": refactored_code,
        "diff": diff,
        "explanation": str(parsed.get("explanation", "")).strip(),
        "confidence": confidence,
    }


def build_response(payload: Dict[str, Any], used_model: str) -> CodeReviewResponse:
    try:
        return CodeReviewResponse(used_model=used_model, **payload)
    except ValidationError as exc:
        raise ProviderResponseError(f"Final payload failed schema validation: {exc}") from exc
