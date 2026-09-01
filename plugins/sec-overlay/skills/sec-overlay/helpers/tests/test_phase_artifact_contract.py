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
