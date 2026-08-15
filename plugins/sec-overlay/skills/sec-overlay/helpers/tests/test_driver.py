import pytest

from sec_overlay.campaign import record_stage
from sec_overlay.workspace import Workspace


def _ctx(tmp_path):
    from sec_overlay.driver import AuditContext

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    return AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="deadbeef")


def test_run_deterministic_halts_on_missing_input(tmp_path):
    from sec_overlay.driver import PhaseHalt, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    spec = PhaseSpec(
        name="needs-profile",
        kind="deterministic",
        inputs=(lambda w: w.kb / "scan-profile.json",),
        outputs=(),
    )
    with pytest.raises(PhaseHalt) as exc:
        run_deterministic_phase(spec, ctx)
    assert "scan-profile.json" in str(exc.value)


def test_run_deterministic_halts_when_output_absent(tmp_path):
    from sec_overlay.driver import DETERMINISTIC_ACTIONS, PhaseHalt, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    DETERMINISTIC_ACTIONS["noop-phase"] = lambda c: None  # produces nothing
    spec = PhaseSpec(
        name="noop-phase",
        kind="deterministic",
        inputs=(),
        outputs=(lambda w: w.report_path,),
    )
    with pytest.raises(PhaseHalt) as exc:
        run_deterministic_phase(spec, ctx)
    assert "did not produce" in str(exc.value)


def test_run_deterministic_records_stage_on_success(tmp_path):
    from sec_overlay.driver import DETERMINISTIC_ACTIONS, run_deterministic_phase
    from sec_overlay.phases import PhaseSpec
    from sec_overlay.state import load_state

    ctx = _ctx(tmp_path)

    def _make_report(c):
        c.ws.report_path.write_text("# report")

    DETERMINISTIC_ACTIONS["make-report"] = _make_report
    spec = PhaseSpec(
        name="make-report",
        kind="deterministic",
        inputs=(),
        outputs=(lambda w: w.report_path,),
    )
    run_deterministic_phase(spec, ctx)
    assert load_state(ctx.ws).stages.get("make-report") == "done"


def test_render_dispatch_names_prompt_and_tokens(tmp_path):
    from sec_overlay.driver import render_dispatch
    from sec_overlay.phases import PhaseSpec

    ctx = _ctx(tmp_path)
    spec = PhaseSpec(
        name="recon",
        kind="agent",
        inputs=(),
        outputs=(lambda w: w.kb / "scan-profile.json",),
        prompt="recon.md",
    )
    out = render_dispatch(spec, ctx)
    assert "agents/recon.md" in out
    assert ctx.target in out
    assert str(ctx.ws.root) in out
    assert "deadbeef" in out


def test_run_audit_runs_deterministic_then_halts_at_agent(tmp_path, monkeypatch):
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.state import begin_pass

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    begin_pass(ws, "sha1")
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")

    # First actionable phase is 'recon' (agent) — no scan-profile yet, so the
    # driver must print recon's dispatch and stop.
    out = run_audit(ctx)
    assert "NEXT AGENT PHASE: recon" in out
    assert "agents/recon.md" in out


def test_run_audit_advances_past_completed_agent_phase(tmp_path):
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.state import begin_pass

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    begin_pass(ws, "sha1")
    # Simulate recon having produced its output.
    (ws.kb / "scan-profile.json").write_text('{"languages": []}')
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")

    out = run_audit(ctx)
    # recon's output exists -> recon recorded, next agent phase is architecture.
    from sec_overlay.state import load_state

    assert load_state(ws).stages.get("recon") == "done"
    assert "NEXT AGENT PHASE: architecture" in out


def test_run_audit_does_not_skip_agent_phase_with_findings_dir_io(tmp_path):
    """critic shares its findings_dir path as both input and output with its
    siblings — auto-advance must not mistake the dir's mere presence for
    'critic already ran' and skip straight past a precision-gate stage."""
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.state import begin_pass, load_state

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    begin_pass(ws, "sha1")
    for stage in (
        "recon",
        "architecture",
        "threat_model",
        "prefilter",
        "investigate",
        "findings-gate",
        "dedupe",
    ):
        record_stage(ws, stage)
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    ctx = AuditContext(ws=ws, target=str(tmp_path / "t"), config="cfg", sha="sha1")

    out = run_audit(ctx)
    assert "NEXT AGENT PHASE: critic" in out
    assert load_state(ws).stages.get("critic") != "done"
