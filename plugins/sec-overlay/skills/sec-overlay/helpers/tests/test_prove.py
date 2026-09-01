"""REQ-30: the opt-in proof-by-execution lane."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from sec_overlay import evidence, prove
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


def _ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    return ws


def _profile(ws: Workspace, options: dict | None = None) -> None:
    payload: dict = {"languages": ["go"]}
    if options is not None:
        payload["scan_options"] = options
    (ws.kb / "scan-profile.json").write_text(json.dumps(payload))


def _finding(cls: str = "ssrf") -> Finding:
    return Finding(
        id="F-0100", rule_id="r", cls=cls, status=FindingStatus.RAW,
        severity=Severity.HIGH, file="app.go", line=12, message="m",
        evidence_sources=["semgrep:r"], runtime_disposition="needs-runtime",
    )


def _proposal(scope: str = "entrypoint", toolchain: str = "opa") -> dict:
    return {
        "finding_id": "F-0100",
        "command": "opa eval -d policy.rego 'data.x'",
        "exit_code": 0,
        "oracle": "loopback-collector",
        "oracle_result": "observed",
        "toolchain": toolchain,
        "resolved_version": "1.4.2",
        "scope": scope,
    }


def _stage(tmp_path: Path, *, cls: str = "ssrf", scope: str = "entrypoint",
           toolchain: str = "opa") -> Workspace:
    ws = _ws(tmp_path)
    _profile(ws, {"prove_findings": True})
    write_findings(ws, [_finding(cls)])
    (ws.kb / "prove.json").write_text(
        json.dumps({"enabled": True, "proofs": [_proposal(scope, toolchain)]})
    )
    return ws


def _read(ws: Workspace) -> dict:
    return json.loads((ws.findings_dir / "F-0100.json").read_text())


def _which(name: str) -> str | None:
    return "/usr/local/bin/opa" if name == "opa" else None


def test_prove_enabled_is_false_without_a_scan_profile(tmp_path: Path) -> None:
    assert prove.prove_enabled(_ws(tmp_path)) is False


def test_prove_enabled_is_false_when_the_key_is_absent(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _profile(ws, {})
    assert prove.prove_enabled(ws) is False


def test_prove_enabled_is_true_only_when_the_key_is_true(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _profile(ws, {"prove_findings": True})
    assert prove.prove_enabled(ws) is True


def test_run_prove_is_a_no_op_when_the_lane_is_off(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    _profile(ws, {})
    write_findings(ws, [_finding()])
    result = prove.run_prove(ws, "tgt", which=_which)
    assert result["enabled"] is False
    assert _read(ws)["evidence_sources"] == ["semgrep:r"]


def test_the_reproduction_receipt_is_recognised(tmp_path: Path) -> None:
    assert prove.is_reproduction_receipt(prove.REPRODUCTION_RECEIPT) is True
    assert prove.is_reproduction_receipt("semgrep:x") is False


def test_evidence_does_not_treat_reproduction_as_a_tool_receipt() -> None:
    assert evidence.is_tool_receipt("reproduction") is False


def test_an_entrypoint_proof_promotes_an_ssrf_finding(tmp_path: Path) -> None:
    ws = _stage(tmp_path)
    prove.run_prove(ws, "tgt", which=_which)
    data = _read(ws)
    assert data["status"] == "confirmed"
    assert prove.REPRODUCTION_RECEIPT in data["evidence_sources"]


def test_a_slice_proof_does_not_promote(tmp_path: Path) -> None:
    ws = _stage(tmp_path, scope="slice")
    prove.run_prove(ws, "tgt", which=_which)
    data = _read(ws)
    assert data["status"] == "raw"
    assert data["runtime_disposition"] == "needs-runtime"


def test_a_slice_proof_records_the_slice_degradation(tmp_path: Path) -> None:
    ws = _stage(tmp_path, scope="slice")
    result = prove.run_prove(ws, "tgt", which=_which)
    assert "prove: slice-unbuildable" in [d["reason"] for d in result["degraded"]]


def test_a_harness_only_class_never_promotes(tmp_path: Path) -> None:
    ws = _stage(tmp_path, cls="sqli")
    result = prove.run_prove(ws, "tgt", which=_which)
    assert result["promoted"] == []
    assert _read(ws)["status"] == "raw"


def test_a_missing_toolchain_degrades_and_promotes_nothing(tmp_path: Path) -> None:
    ws = _stage(tmp_path, toolchain="absent-tool")
    result = prove.run_prove(ws, "tgt", which=_which)
    assert "prove: toolchain-absent" in [d["reason"] for d in result["degraded"]]
    assert result["promoted"] == []


def test_the_gate_accepts_a_reproduction_only_confirmed_finding(tmp_path: Path) -> None:
    from sec_overlay.findings_gate import validate_findings

    ws = _ws(tmp_path)
    f = _finding()
    f.status = FindingStatus.CONFIRMED
    f.evidence_sources = [prove.REPRODUCTION_RECEIPT]
    f.impact = "the proof drove the entrypoint and the collector observed the request"
    write_findings(ws, [f])
    assert validate_findings(ws) == []


def test_the_loopback_collector_reports_the_observed_path() -> None:
    with prove.loopback_collector() as collector:
        urllib.request.urlopen(collector.url + "/hit", timeout=5).read()
    assert "/hit" in collector.paths


def test_the_phase_table_places_prove_directly_before_the_artifact_gate() -> None:
    # REQ-40 moved redteam ahead of report, so redteam and prove are no longer
    # adjacent; prove still sits directly before artifact-gate.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("redteam") < names.index("prove")
    assert names.index("prove") + 1 == names.index("artifact-gate")
    spec = PHASE_TABLE[names.index("prove")]
    assert (spec.kind, spec.prompt) == ("agent", "prove.md")


def test_the_workspace_carries_a_repro_directory(tmp_path: Path) -> None:
    ws = _ws(tmp_path)
    assert ws.repro == ws.root / "repro"
    assert ws.repro.is_dir()


def test_the_finding_schema_declares_the_reproduction_object() -> None:
    schema = json.loads(
        (Path(__file__).parents[2] / "references" / "finding.schema.json").read_text()
    )
    repro = schema["properties"]["reproduction"]
    assert set(repro["properties"]) == {
        "command", "exit_code", "oracle", "oracle_result",
        "toolchain", "resolved_version", "scope",
    }


def test_the_evidence_partition_still_holds() -> None:
    import importlib

    assert importlib.import_module("sec_overlay.evidence") is evidence


def test_the_driver_skips_the_prove_phase_when_the_lane_is_off(tmp_path: Path) -> None:
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.phases import PHASE_TABLE
    from sec_overlay.state import begin_pass, load_state

    ws = _ws(tmp_path)
    begin_pass(ws, "sha1")
    spec = next(p for p in PHASE_TABLE if p.name == "prove")
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")
    assert run_audit(ctx, table=(spec,)) == "AUDIT COMPLETE"
    assert load_state(ws).stages.get("prove") == "done"


def test_the_driver_dispatches_the_prove_phase_when_the_lane_is_on(tmp_path: Path) -> None:
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.phases import PHASE_TABLE
    from sec_overlay.state import begin_pass

    ws = _ws(tmp_path)
    _profile(ws, {"prove_findings": True})
    begin_pass(ws, "sha1")
    spec = next(p for p in PHASE_TABLE if p.name == "prove")
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")
    assert "agents/prove.md" in run_audit(ctx, table=(spec,))


def test_preflight_reports_the_prove_lane_toolchains(tmp_path: Path) -> None:
    from sec_overlay.preflight import preflight_report

    report = preflight_report(tmp_path, which=_which)
    assert set(report["prove_toolchains"]) == set(prove.PROVE_TOOLCHAINS)
    assert report["prove_toolchains"]["opa"] is True
