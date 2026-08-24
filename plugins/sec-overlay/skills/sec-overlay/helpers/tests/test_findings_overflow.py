"""REQ-27: an unknown finding key survives a load-and-save round trip."""

from __future__ import annotations

import json

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, read_findings, write_findings


def _ws(tmp_path):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    return ws


def _raw(**extra):
    f = Finding(id="F-1", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="app.py", line=1, message="m")
    raw = f.to_dict()
    raw.update(extra)
    return raw


def _round_trip(ws, raw):
    (ws.findings_dir / "F-1.json").write_text(json.dumps(raw, indent=2))
    write_findings(ws, read_findings(ws))
    return json.loads((ws.findings_dir / "F-1.json").read_text())


def test_an_unknown_key_survives_a_round_trip(tmp_path):
    out = _round_trip(_ws(tmp_path), _raw(proof_of_exploit={"scope": "entrypoint"}))
    assert out["proof_of_exploit"] == {"scope": "entrypoint"}


def test_a_round_trip_preserves_the_known_fields(tmp_path):
    out = _round_trip(_ws(tmp_path), _raw(proof_of_exploit={"scope": "slice"}))
    assert out["id"] == "F-1"
    assert out["cls"] == "sqli"
    assert out["status"] == "confirmed"


def test_the_merge_is_deterministic(tmp_path):
    """Two insertion orders of the same unknown keys must produce identical bytes."""
    a = _ws(tmp_path / "a")
    b = _ws(tmp_path / "b")
    (a.findings_dir / "F-1.json").write_text(json.dumps(_raw(zeta=1, alpha=2), indent=2))
    (b.findings_dir / "F-1.json").write_text(json.dumps(_raw(alpha=2, zeta=1), indent=2))
    write_findings(a, read_findings(a))
    write_findings(b, read_findings(b))
    assert (a.findings_dir / "F-1.json").read_text() == (b.findings_dir / "F-1.json").read_text()


def test_a_finding_with_no_unknown_key_is_unchanged(tmp_path):
    ws = _ws(tmp_path)
    raw = _raw()
    out = _round_trip(ws, raw)
    assert out == raw


def test_a_warning_names_the_preserved_keys(tmp_path, capsys):
    ws = _ws(tmp_path)
    (ws.findings_dir / "F-1.json").write_text(json.dumps(_raw(proof_of_exploit=1)))
    read_findings(ws)
    assert "proof_of_exploit" in capsys.readouterr().err
