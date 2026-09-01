"""Group 1 (RC-9) acceptance tests: no phase reads what no earlier phase writes.

Each test names the requirement it pins. The defects these cover all share one
shape — a reader whose input has no producer, so the stage ledger records work
that never happened.
"""

from __future__ import annotations

from sec_overlay.workspace import Workspace


def test_factcheck_phase_is_deleted() -> None:
    # REQ-42: the phase's only input (kb/verdicts.json) had no producing phase,
    # so every run recorded `factcheck: done` after doing nothing.
    from sec_overlay.driver import DETERMINISTIC_ACTIONS
    from sec_overlay.phases import PHASE_TABLE

    assert "factcheck" not in [p.name for p in PHASE_TABLE]
    assert "factcheck" not in DETERMINISTIC_ACTIONS


def test_no_verification_value_lacks_a_writer() -> None:
    # REQ-42: `fact-checked` was written only by the deleted factcheck stage.
    from sec_overlay.evidence import VERIFICATION_VALUES

    assert "fact-checked" not in VERIFICATION_VALUES


def test_the_factcheck_module_and_prompt_are_gone() -> None:
    # REQ-42: a deleted phase must leave no CLI-callable module and no prompt.
    import importlib.util
    from pathlib import Path

    assert importlib.util.find_spec("sec_overlay.factcheck") is None
    skill_root = Path(__file__).resolve().parents[2]
    assert not (skill_root / "agents" / "factcheck.md").exists()


def test_report_declares_the_redteam_plan_as_an_input(tmp_path) -> None:
    # REQ-40: the report named redteam-plan.md unconditionally while the phase
    # that writes it ran later. Declare it, so the driver gates on it.
    from sec_overlay.phases import PHASE_TABLE, missing_inputs

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    report = next(p for p in PHASE_TABLE if p.name == "report")
    assert missing_inputs(report, ws) == [ws.reports / "redteam-plan.md"]


def test_redteam_runs_before_report() -> None:
    # REQ-40: reversal of the prior invariant. redteam produced an artifact the
    # report links, so it must precede the report, not follow it.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("demote-noise") < names.index("redteam") < names.index("report")
    assert names.index("report") < names.index("selfscore") < names.index("artifact-gate")


def test_render_ndt_omits_the_redteam_pointer_when_no_plan_exists() -> None:
    # REQ-40: review mode renders a report with no redteam phase.
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.report import render_ndt

    f = Finding(
        id="F-1",
        rule_id="r",
        cls="xss",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message="m",
    )
    assert "redteam-plan.md" not in render_ndt(f, has_redteam_plan=False)


def test_only_the_report_cli_probes_for_the_redteam_plan() -> None:
    # REQ-40: the caller knows whether the plan exists; the filesystem does not.
    # The CLI entry point has no caller, so it is the single permitted probe site.
    import inspect

    from sec_overlay import report

    probe = 'redteam-plan.md").exists()'
    assert inspect.getsource(report).count(probe) == 1
    assert probe in inspect.getsource(report.main)
    assert probe not in inspect.getsource(report.write_report)
    assert probe not in inspect.getsource(report.write_finding_details)


def _confirmed_with_patch(fid: str):
    from sec_overlay.models import Finding, FindingStatus, Severity

    return Finding(
        id=fid,
        rule_id="r",
        cls="authz",
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file="a.py",
        line=1,
        message="m",
        patch_diff="--- a/a.py\n+++ b/a.py\n",
    )


def test_validate_fix_is_a_phase_between_patch_and_verify() -> None:
    # REQ-43: the prompt and score_fix both shipped with no caller, so
    # verify.py's `verify:conflict` branch was unreachable.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("patch") < names.index("validate-fix") < names.index("verify")
    vf = next(p for p in PHASE_TABLE if p.name == "validate-fix")
    assert vf.kind == "agent" and vf.prompt == "validate-fix.md"


def test_verify_declares_the_validate_fix_gate_as_an_input(tmp_path) -> None:
    # REQ-43: verify reads the gate file, so the driver must gate on it.
    from sec_overlay.phases import PHASE_TABLE, missing_inputs

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    verify = next(p for p in PHASE_TABLE if p.name == "verify")
    assert missing_inputs(verify, ws) == [ws.kb / "gates" / "validate-fix.json"]


def test_apply_fix_gates_records_the_verdict_without_setting_status(tmp_path) -> None:
    # REQ-43: scoring.py computes the verdict, never the LLM, and verify keeps
    # sole ownership of promotion.
    import json

    from sec_overlay.models import FindingStatus
    from sec_overlay.verify import apply_fix_gates
    from sec_overlay.workspace import read_findings, write_findings

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    write_findings(ws, [_confirmed_with_patch("F-1")])
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / "validate-fix.json").write_text(
        json.dumps(
            {
                "F-1": {
                    "root_cause": "pass",
                    "instance_coverage": "partial",
                    "no_new_vulnerabilities": "partial",
                    "best_practices": "pass",
                }
            }
        )
    )

    assert apply_fix_gates(ws) == 1
    f = read_findings(ws)[0]
    assert f.status is FindingStatus.CONFIRMED  # apply_fix_gates never promotes
    events = [h.get("event") for h in f.history]
    assert "validate-fix:partial" in events


def test_score_fix_has_a_non_test_caller() -> None:
    # REQ-43: score_fix shipped with no production caller.
    import inspect

    from sec_overlay import verify

    assert "score_fix" in inspect.getsource(verify)
