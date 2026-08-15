import pytest

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
