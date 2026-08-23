"""Tests for the consolidated review_result.json artifact (REQ-P7)."""

import json

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.positioning import PositionResult
from sec_overlay.reflection import ReflectionRetraction, ReflectionSkip
from sec_overlay.review_coverage import CoverageManifest
from sec_overlay.review_findings import ReviewFinding
from sec_overlay.review_result import RESULT_FILENAME, RESULT_KEYS, write_review_result
from sec_overlay.workspace import Workspace

_BASE = "a" * 40
_HEAD = "b" * 40


def _manifest(tmp_path, *, seal=True):
    manifest = CoverageManifest(_BASE, _HEAD, tmp_path / "coverage_manifest.json")
    manifest.add("app.py")
    manifest.start("app.py")
    manifest.finish("app.py")
    if seal:
        manifest.seal()
    return manifest


def _review_finding(file="app.py", line=18):
    finding = Finding(
        id="F-0001",
        rule_id="review.sqli",
        cls="sqli",
        status=FindingStatus.RAW,
        severity=Severity.HIGH,
        file=file,
        line=line,
        message="possible SQLi",
        evidence="cursor.execute(query)",
    )
    return ReviewFinding(finding=finding, defect_class="sqli", disposition="reported", profile="general")


def _write(tmp_path, **overrides):
    ws = Workspace(tmp_path)
    kwargs = {
        "findings": [],
        "dropped": [],
        "declines": [],
        "retractions": [],
        "skips": [],
        "manifest": _manifest(tmp_path),
        "budget_exceeded": False,
        "tokens": {},
        "base": _BASE,
        "head": _HEAD,
        "model": "claude-sonnet",
        "profile": "general",
        "tier": "assured",
    }
    kwargs.update(overrides)
    path = write_review_result(ws, **kwargs)
    return path, json.loads(path.read_text())


def test_writes_to_artifacts_dir(tmp_path):
    ws = Workspace(tmp_path)
    path = write_review_result(
        ws,
        findings=[],
        dropped=[],
        declines=[],
        retractions=[],
        skips=[],
        manifest=_manifest(tmp_path),
        budget_exceeded=False,
        tokens={},
        base=_BASE,
        head=_HEAD,
        model=None,
        profile="general",
        tier=None,
    )
    assert path == ws.artifacts / RESULT_FILENAME


def test_zero_finding_run_has_full_key_set(tmp_path):
    _path, payload = _write(tmp_path)
    assert set(payload.keys()) == RESULT_KEYS
    assert payload["findings"] == []
    assert payload["dropped"] == []
    assert payload["declined"] == []
    assert payload["retractions"] == []
    assert payload["skips"] == []
    assert payload["budget_exceeded"] is False
    assert payload["base"] == _BASE
    assert payload["head"] == _HEAD
    assert payload["status"] == "complete"
    assert payload["coverage_manifest"]["seal"] == "complete"


def test_populated_run_has_full_key_set(tmp_path):
    _path, payload = _write(
        tmp_path,
        findings=[_review_finding()],
        dropped=[{"path": "b.py", "line": 3, "reason": "profile"}],
        declines=[
            PositionResult(
                decision="exact",
                path="app.py",
                line=10,
                reason=None,
                claimed_path="app.py",
                claimed_line=10,
                snippet="x",
            )
        ],
        retractions=[
            ReflectionRetraction(
                path="app.py", line=18, rule_id="review.sqli", reason="fp", analysis="why"
            )
        ],
        skips=[ReflectionSkip(path="c.py", reason="reflection-skipped", error="boom")],
        budget_exceeded=True,
        tokens={"review": 1234, "plan": 56},
        tier="fast",
    )
    assert set(payload.keys()) == RESULT_KEYS
    assert payload["budget_exceeded"] is True
    assert payload["tokens"] == {"review": 1234, "plan": 56}
    assert payload["tier"] == "fast"


def test_finding_record_has_documented_fields(tmp_path):
    _path, payload = _write(tmp_path, findings=[_review_finding()])
    record = payload["findings"][0]
    assert set(record.keys()) == {
        "id",
        "path",
        "line",
        "severity",
        "rule_id",
        "profile",
        "disposition",
    }
    assert record["id"] == "F-0001"
    assert record["path"] == "app.py"
    assert record["line"] == 18
    assert record["severity"] == "high"
    assert record["rule_id"] == "review.sqli"
    assert record["profile"] == "general"
    assert record["disposition"] == "reported"


def test_dataclass_declines_and_skips_serialize_to_dicts(tmp_path):
    _path, payload = _write(
        tmp_path,
        skips=[ReflectionSkip(path="c.py", reason="reflection-skipped", error="boom")],
    )
    assert payload["skips"][0] == {"path": "c.py", "reason": "reflection-skipped", "error": "boom"}
