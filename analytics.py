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
        shared.append({"name": new["name"], "earlier_value": old["value"], "later_value": new["value"],
                       "earlier_unit": old.get("unit", ""), "later_unit": new.get("unit", ""),
                       "comparable_units": old.get("unit", "").casefold() == new.get("unit", "").casefold()})
    old_risks = {x["title"].casefold() for x in left.get("risks", [])}
    new_risks = {x["title"].casefold() for x in right.get("risks", [])}
    return {"shared_metrics": shared, "new_risks": sorted(new_risks-old_risks),
            "risks_no_longer_listed": sorted(old_risks-new_risks), "shared_risks": sorted(old_risks & new_risks)}
