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


def test_mechanical_set_is_derived_from_the_two_tiers():
    """REQ-51: the tiers are the single source; no literal can drift from them."""
    from sec_overlay import evidence

    assert evidence._MECHANICAL == evidence.TIER1_RECEIPTS | evidence.TIER2_RECEIPTS


def test_unknown_receipts_reports_an_undeclared_prefix():
    """REQ-51: a typo or an undeclared tool is an error, not a silent tier drop."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["semgrp:a.py:1"]) == ["semgrp:a.py:1"]


def test_unknown_receipts_passes_a_declared_prefix():
    """REQ-51: both tiers stay clean."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["semgrep:a.py:1", "ripgrep:b.py:2"]) == []


def test_unknown_receipts_passes_an_llm_claim():
    """REQ-51: an llm-namespaced source claims no receipt, so it is not an offender."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["llm-claimed:reasoning", "llm-corroborated"]) == []


def test_unknown_receipts_passes_the_reproduction_receipt():
    """REQ-51: prove.py's reproduction receipt names no tier prefix but is a real receipt."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["reproduction", "reproduction:pytest"]) == []


def test_gate_rejects_a_finding_with_an_undeclared_receipt_prefix(tmp_path):
    """REQ-51: the gate reports the offender instead of dropping its tier."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = Finding(id="F-0002", rule_id="r", cls="sqli", status=FindingStatus.RAW,
                severity=Severity.HIGH, file="app.py", line=18, message="m",
                dataflow=["a -> b"], evidence="e")
    f.evidence_sources = ["semgrp:app.py:18"]
    write_findings(ws, [f])
    errors = validate_findings(ws)
    assert any("semgrp:app.py:18" in e and "closed set" in e for e in errors)


def test_gate_passes_a_finding_confirmed_solely_by_reproduction(tmp_path):
    """REQ-51: the reproduction receipt must not trip the new unknown-receipt check."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = Finding(id="F-0003", rule_id="r", cls="ssrf", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="app.py", line=18, message="m",
                dataflow=["a -> b"], evidence="e", impact="egress to attacker-controlled host")
    f.evidence_sources = ["reproduction"]
    write_findings(ws, [f])
    assert validate_findings(ws) == []


def _external_boundary_finding():
    from sec_overlay.models import Finding, FindingStatus, Severity

    f = Finding(id="F-0002", rule_id="r", cls="sqli", status=FindingStatus.RAW,
                severity=Severity.HIGH, file="app.py", line=18, message="m",
                dataflow=["a -> b"], evidence="e")
    f.reachability = {"blocker": "external-boundary", "chain": ["app.py:18"]}
    return f


def test_external_boundary_is_in_the_blocker_taxonomy():
    """REQ-52: the value agents are told to write is a declared blocker."""
    from sec_overlay.reachability import BLOCKERS

    assert "external-boundary" in BLOCKERS


def test_blocker_of_no_longer_coerces_external_boundary():
    """REQ-52: an undeclared value was silently rewritten to 'other'."""
    from sec_overlay.reachability import blocker_of

    f = _external_boundary_finding()
    f.reachability["reachable"] = False
    assert blocker_of(f) == "external-boundary"


def test_trace_prompt_declares_external_boundary_in_the_taxonomy():
    """REQ-52: the prose taxonomy and the code taxonomy agree."""
    text = (SKILL / "agents" / "trace.md").read_text()
    assert "`external-boundary`" in text.split("3. Decide reachability:")[1].split("4. Write")[0]


def test_gate_rejects_external_boundary_without_an_open_question(tmp_path):
    """REQ-52: the prose asked for the entry; the gate now requires it."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_external_boundary_finding()])
    errors = validate_findings(ws)
    assert any("external-boundary" in e and "open_questions" in e for e in errors)


def test_gate_rejects_an_incomplete_open_question(tmp_path):
    """REQ-52: an entry missing who to ask settles nothing."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = _external_boundary_finding()
    f.open_questions = [{"question": "does policy X apply?", "why_it_matters": "gates the sink"}]
    write_findings(ws, [f])
    errors = validate_findings(ws)
    assert any("external-boundary" in e and "open_questions" in e for e in errors)


def test_gate_accepts_external_boundary_with_a_full_open_question(tmp_path):
    """REQ-52: a complete entry passes."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = _external_boundary_finding()
    f.open_questions = [{
        "question": "does @lume/account-portal-core check ownership?",
        "why_it_matters": "it is the only control between the route and the sink",
        "who_to_ask_or_check": "ask the platform team or read the published package",
    }]
    write_findings(ws, [f])
    assert validate_findings(ws) == []
