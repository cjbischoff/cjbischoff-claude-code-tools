from sec_overlay.models import CampaignState
from sec_overlay.workspace import Workspace


def test_next_actionable_skips_recorded_phases():
    from sec_overlay.phases import PHASE_TABLE, next_actionable_phase

    state = CampaignState(pass_number=1, active_sha="s")
    phase = next_actionable_phase(PHASE_TABLE, state)
    assert phase is not None and phase.name == PHASE_TABLE[0].name

    state.stages[PHASE_TABLE[0].name] = "done"
    phase = next_actionable_phase(PHASE_TABLE, state)
    assert phase is not None and phase.name == PHASE_TABLE[1].name


def test_all_recorded_returns_none():
    from sec_overlay.phases import PHASE_TABLE, next_actionable_phase

    state = CampaignState(pass_number=1, active_sha="s")
    for p in PHASE_TABLE:
        state.stages[p.name] = "done"
    assert next_actionable_phase(PHASE_TABLE, state) is None


def test_missing_inputs_reports_absent_artifact(tmp_path):
    from sec_overlay.phases import PhaseSpec, missing_inputs, outputs_present

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    spec = PhaseSpec(
        name="x",
        kind="deterministic",
        inputs=(lambda w: w.kb / "scan-profile.json",),
        outputs=(lambda w: w.findings_dir / "done.flag",),
    )
    assert missing_inputs(spec, ws) == [ws.kb / "scan-profile.json"]
    assert outputs_present(spec, ws) is False

    (ws.kb / "scan-profile.json").write_text("{}")
    (ws.findings_dir / "done.flag").write_text("x")
    assert missing_inputs(spec, ws) == []
    assert outputs_present(spec, ws) is True


def test_first_phase_is_prefilter_and_investigate_precedes_findings_gate():
    # ISSUE-044: findings-gate runs right after investigate.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert "investigate" in names and "findings-gate" in names
    assert names.index("findings-gate") == names.index("investigate") + 1
    # ISSUE-007: noise/dedupe collapse before report.
    assert names.index("dedupe") < names.index("report")
    assert names.index("demote-noise") < names.index("report")
    # ISSUE-045: trace is a required phase.
    assert "trace" in names
    # ISSUE-047: factcheck applies the validate phase's verdict artifact.
    assert names.index("trace") < names.index("factcheck") < names.index("calibrate")


def test_artifact_phases_follow_selfscore():
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("artifact-gate") > names.index("selfscore")
    assert names.index("artifact-review") > names.index("artifact-gate")
    ar = next(p for p in PHASE_TABLE if p.name == "artifact-review")
    assert ar.kind == "agent" and ar.prompt == "artifact-review.md"


def test_arch_tm_gate_rows():
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("arch-gate") == names.index("architecture") + 1
    assert names.index("tm-gate") == names.index("threat_model") + 1
    for n in ("arch-gate", "tm-gate"):
        assert next(p for p in PHASE_TABLE if p.name == n).kind == "deterministic"
