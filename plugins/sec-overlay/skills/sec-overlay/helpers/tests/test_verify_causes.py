"""REQ-21: the verify verdict names why it reached its answer."""

from __future__ import annotations

import pytest

from sec_overlay import verify as verify_mod
from sec_overlay.evidence import VERIFICATION_VALUES
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.verify import VERIFY_CAUSES, verify_findings, verify_patch
from sec_overlay.workspace import Workspace, read_findings, write_findings

_DIFF = "--- a/app.py\n+++ b/app.py\n"


class _Hits:
    """Fake ``_file_has_hit``: pops the next result from ``results`` per call."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self._results.pop(0)


def _target(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")
    return str(repo)


def _patch_backend(monkeypatch, results, applied=True):
    hits = _Hits(results)
    monkeypatch.setattr(verify_mod, "_file_has_hit", hits)
    monkeypatch.setattr(verify_mod, "apply_patch", lambda repo, diff: applied)
    return hits


@pytest.mark.parametrize(
    ("results", "applied", "cause"),
    [
        ([None], True, "rule-no-match"),
        ([False], True, "rule-no-match"),
        ([True], False, "patch-not-applied"),
        ([True, None], True, "unconfirmed"),
        ([True, False], True, "verified-static"),
        ([True, True], True, "not-fixed"),
    ],
)
def test_verify_patch_returns_a_named_cause(tmp_path, monkeypatch, results, applied, cause):
    _patch_backend(monkeypatch, results, applied=applied)
    got = verify_patch(_target(tmp_path), _DIFF, "cfg", "app.py", "sqli")
    assert got == cause
    assert got in VERIFY_CAUSES


def test_every_cause_maps_to_a_legal_verification():
    mapping = verify_mod._CAUSE_TO_VERIFICATION
    assert set(mapping) == set(VERIFY_CAUSES)
    assert set(mapping.values()) <= VERIFICATION_VALUES


def _confirmed(id_="F-1"):
    return Finding(id=id_, rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=Severity.HIGH, file="app.py", line=1, message="m",
                   patch_diff=_DIFF)


@pytest.mark.parametrize(
    ("cause", "verification"),
    [
        ("verified-static", "verified-static"),
        ("not-fixed", "not-fixed"),
        ("patch-not-applied", "static-only"),
        ("rule-no-match", "static-only"),
        ("unconfirmed", "static-only"),
    ],
)
def test_verify_findings_records_the_cause(tmp_path, cause, verification):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_confirmed()])
    verify_findings(ws, "t", "c", verifier=lambda *a, **k: cause)
    out = read_findings(ws)[0]
    assert out.verification == verification
    assert {"event": f"verify:cause:{cause}"} in out.history


def test_an_unknown_cause_degrades_to_static_only(tmp_path):
    """A verifier that returns an unmapped string must never launder a clean verdict."""
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_confirmed()])
    verify_findings(ws, "t", "c", verifier=lambda *a, **k: "static-only")
    assert read_findings(ws)[0].verification == "static-only"
