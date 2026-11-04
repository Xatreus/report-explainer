"""Structured extraction helpers and report comparison utilities."""
from __future__ import annotations
import json
import re
from typing import Any

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "entities": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "type": {"type": "string"}, "source_id": {"type": "string"}},
            "required": ["name", "type", "source_id"], "additionalProperties": False}},
        "metrics": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "value": {"type": "number"}, "unit": {"type": "string"},
            "period": {"type": "string"}, "source_id": {"type": "string"}},
            "required": ["name", "value", "unit", "period", "source_id"], "additionalProperties": False}},
        "risks": {"type": "array", "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "severity": {"type": "string"}, "description": {"type": "string"},
            "source_id": {"type": "string"}},
            "required": ["title", "severity", "description", "source_id"], "additionalProperties": False}},
        "actions": {"type": "array", "items": {"type": "object", "properties": {
            "action": {"type": "string"}, "owner": {"type": "string"}, "due_date": {"type": "string"},
            "source_id": {"type": "string"}},
            "required": ["action", "owner", "due_date", "source_id"], "additionalProperties": False}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "entities", "metrics", "risks", "actions", "limitations"],
    "additionalProperties": False,
}

def parse_json_object(content: str) -> dict[str, Any]:
    """Parse JSON from a model response, including fenced JSON."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", content.strip())
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object from the model.")
    return value

def compare_report_analyses(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare extracted report analyses without inventing numeric deltas."""
    old_metrics = {x["name"].casefold(): x for x in left.get("metrics", [])}
    new_metrics = {x["name"].casefold(): x for x in right.get("metrics", [])}
    shared = []
    for key in sorted(old_metrics.keys() & new_metrics.keys()):
        old, new = old_metrics[key], new_metrics[key]
        shared.append(compare_metric_values(old, new))
    old_risks = {x["title"].casefold() for x in left.get("risks", [])}
    new_risks = {x["title"].casefold() for x in right.get("risks", [])}
    return {"shared_metrics": shared, "new_risks": sorted(new_risks-old_risks),
            "risks_no_longer_listed": sorted(old_risks-new_risks), "shared_risks": sorted(old_risks & new_risks)}


def _metric_base_value(value: float, unit: str) -> tuple[str, float] | None:
    """Normalize common scale units without inventing currency exchange rates."""
    normalized = re.sub(r"\s+", "", unit.casefold()).replace("dollars", "usd").replace("$", "usd")
    scales = {
        "": ("number", 1.0), "unit": ("number", 1.0), "units": ("number", 1.0),
        "%": ("percent", 1.0), "percent": ("percent", 1.0), "percentage": ("percent", 1.0),
        "usd": ("usd", 1.0), "us$": ("usd", 1.0), "k usd": ("usd", 1_000.0),
        "thousandusd": ("usd", 1_000.0), "millionusd": ("usd", 1_000_000.0),
        "billionusd": ("usd", 1_000_000_000.0),
        "eur": ("eur", 1.0), "thousandeur": ("eur", 1_000.0),
        "millioneur": ("eur", 1_000_000.0),
        "gb": ("bytes", 1_000_000_000.0), "mb": ("bytes", 1_000_000.0),
        "kb": ("bytes", 1_000.0), "bytes": ("bytes", 1.0),
        "ms": ("milliseconds", 1.0), "s": ("milliseconds", 1_000.0),
        "seconds": ("milliseconds", 1_000.0), "minutes": ("milliseconds", 60_000.0),
    }
    entry = scales.get(normalized)
    return (entry[0], float(value) * entry[1]) if entry else None


def compare_metric_values(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare same-name metrics after safe scale normalization; never FX-convert."""
    old_unit, new_unit = str(left.get("unit", "")), str(right.get("unit", ""))
    old = _metric_base_value(float(left["value"]), old_unit)
    new = _metric_base_value(float(right["value"]), new_unit)
    result = {
        "name": right.get("name", left.get("name", "Metric")),
        "earlier_value": left.get("value"), "earlier_unit": old_unit,
        "later_value": right.get("value"), "later_unit": new_unit,
        "comparable": bool(old and new and old[0] == new[0]),
        "normalized_unit": old[0] if old and new and old[0] == new[0] else None,
    }
    if result["comparable"]:
        result["earlier_normalized"] = old[1]
        result["later_normalized"] = new[1]
        result["absolute_change"] = new[1] - old[1]
        result["percentage_change"] = ((new[1] - old[1]) / abs(old[1]) * 100) if old[1] else None
    return result


def _risk_similarity(left: str, right: str) -> float:
    """Token Jaccard similarity with a conservative phrase similarity fallback."""
    from difflib import SequenceMatcher
    tokens_left = set(re.findall(r"[a-z0-9]+", left.casefold()))
    tokens_right = set(re.findall(r"[a-z0-9]+", right.casefold()))
    if not tokens_left or not tokens_right:
        return 0.0
    jaccard = len(tokens_left & tokens_right) / len(tokens_left | tokens_right)
    sequence = SequenceMatcher(None, left.casefold(), right.casefold()).ratio()
    return max(jaccard, sequence * 0.85)


def match_semantic_risks(left_risks: list[dict[str, Any]], right_risks: list[dict[str, Any]],
                         threshold: float = 0.55) -> dict[str, Any]:
    """Match similarly worded risk labels across reports; output scores for human review."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    candidates = []
    for old in left_risks:
        for new in right_risks:
            score = _risk_similarity(str(old.get("title", "")), str(new.get("title", "")))
            if score >= threshold:
                candidates.append((score, old, new))
    candidates.sort(key=lambda item: item[0], reverse=True)
    used_old, used_new, matches = set(), set(), []
    for score, old, new in candidates:
        old_key, new_key = str(old.get("title", "")), str(new.get("title", ""))
        if old_key in used_old or new_key in used_new:
            continue
        used_old.add(old_key); used_new.add(new_key)
        matches.append({"earlier_risk": old_key, "later_risk": new_key, "similarity": round(score, 3),
                        "review_required": True})
    return {
        "matches": matches,
        "new_risks": [r for r in right_risks if str(r.get("title", "")) not in used_new],
        "unmatched_earlier_risks": [r for r in left_risks if str(r.get("title", "")) not in used_old],
        "note": "Similarity is heuristic; matches require human review and do not prove equivalent risk."
    }
