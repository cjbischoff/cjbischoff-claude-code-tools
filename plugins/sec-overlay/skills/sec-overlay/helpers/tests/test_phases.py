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


def test_phase_table_contains_redteam_and_postflight():
    # D-01: redteam/postflight are documented in the maintainer manual but were
    # absent from PHASE_TABLE, so run.drive()/run.advance() silently skipped them.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert "redteam" in names
    assert "postflight" in names


def test_redteam_precedes_the_artifact_gate():
    # Correction to the rough pattern draft: redteam must sit before
    # artifact-gate (artifact_gate.run_artifact_gate hard-requires
    # redteam-plan.md to exist), not after artifact-review.
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("selfscore") < names.index("redteam") < names.index("artifact-gate")
    rt = next(p for p in PHASE_TABLE if p.name == "redteam")
    assert rt.kind == "agent" and rt.prompt == "redteam.md"


def test_postflight_is_the_final_phase():
    from sec_overlay.phases import PHASE_TABLE

    assert PHASE_TABLE[-1].name == "postflight"
    pf = PHASE_TABLE[-1]
    assert pf.kind == "deterministic" and pf.prompt is None


def test_original_phase_order_is_preserved():
    # Inserting redteam/postflight must not reorder any pre-existing phase.
    from sec_overlay.phases import PHASE_TABLE

    original_order = [
        "recon", "architecture", "arch-gate", "threat_model", "tm-gate", "prefilter",
        "investigate", "findings-gate", "dedupe", "critic", "judge", "validate", "trace",
        "factcheck", "calibrate", "patch", "verify", "demote-noise", "report", "selfscore",
        "artifact-gate", "artifact-review",
    ]
    names = [p.name for p in PHASE_TABLE]
    filtered = [n for n in names if n in original_order]
    assert filtered == original_order


def test_missing_inputs_reports_absent_artifacts_for_the_new_phases(tmp_path):
    from sec_overlay.phases import PHASE_TABLE, missing_inputs

    ws = Workspace(tmp_path / "w")  # deliberately not ensure()d — inputs absent
    redteam = next(p for p in PHASE_TABLE if p.name == "redteam")
    postflight = next(p for p in PHASE_TABLE if p.name == "postflight")
    assert missing_inputs(redteam, ws) == [ws.findings_dir]
    assert missing_inputs(postflight, ws) == [ws.kb / "gates" / "artifact-review.json"]


def test_outputs_present_tracks_the_postflight_artifact(tmp_path):
    from sec_overlay.phases import PHASE_TABLE, outputs_present

    ws = Workspace(tmp_path / "w")
    ws.ensure()
    postflight = next(p for p in PHASE_TABLE if p.name == "postflight")
    assert outputs_present(postflight, ws) is False

    (ws.kb / "prior_context.json").write_text("{}")
    assert outputs_present(postflight, ws) is True
