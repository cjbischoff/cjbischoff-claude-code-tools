"""Tests for the constraint enforcers of Group 3 (REQ-49 through REQ-52)."""

import json
from pathlib import Path

from sec_overlay.schema import validate

SKILL = Path(__file__).resolve().parents[2]
SCHEMA = SKILL / "references" / "finding.schema.json"
GOLDEN = SKILL / "helpers" / "fixtures" / "golden_raw_finding.json"


def test_additional_properties_false_rejects_an_unknown_key():
    """REQ-49: a closed object reports every key no property declares."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"a": {"type": "string"}},
    }
    errors = validate({"a": "x", "b": 1}, schema)
    assert any("b" in e and "unknown field" in e for e in errors)


def test_additional_properties_false_accepts_a_declared_key():
    """REQ-49: closing the object must not reject a declared key."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"a": {"type": "string"}},
    }
    assert validate({"a": "x"}, schema) == []


def test_additional_properties_dict_form_stays_permissive():
    """REQ-49: only the boolean-false form closes an object (ruling R-3)."""
    schema = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "properties": {"a": {"type": "string"}},
    }
    assert validate({"a": "x", "b": 1}, schema) == []


def test_finding_schema_closes_the_object():
    """REQ-49: the finding schema declares itself closed."""
    assert json.loads(SCHEMA.read_text())["additionalProperties"] is False


def test_render_stale_is_rejected_by_the_finding_schema():
    """REQ-49: the key the deleted lever wrote no longer validates."""
    data = json.loads(GOLDEN.read_text())
    data["render_stale"] = True
    errors = validate(data, json.loads(SCHEMA.read_text()))
    assert any("render_stale" in e for e in errors)


def test_no_prompt_offers_a_render_stale_lever():
    """REQ-49: no agent prompt instructs an agent to write a rejected key."""
    for path in sorted((SKILL / "agents").glob("*.md")):
        assert "render_stale" not in path.read_text(), f"{path.name} still offers render_stale"


def test_artifact_review_verdict_vocabulary_drops_the_rerender_path():
    """REQ-49: the unreachable re-render verdict and its id list are gone."""
    text = (SKILL / "agents" / "artifact-review.md").read_text()
    assert '"verdict": "clean" | "downgrades"' in text
    assert "forced_rerender" not in text
