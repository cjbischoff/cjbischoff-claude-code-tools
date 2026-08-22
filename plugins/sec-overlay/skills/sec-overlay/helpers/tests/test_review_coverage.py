"""Tests for the coverage-manifest state machine and its terminal seal (D-03, D-04)."""

from __future__ import annotations

import json

import pytest

from sec_overlay.review_coverage import (
    MANIFEST_VERSION,
    SEALS,
    STATES,
    CoverageManifest,
    CoverageTransitionError,
    ResumeIdentityError,
    check_resume_identity,
)


def _manifest(tmp_path):
    return CoverageManifest("base123", "head456", tmp_path / "manifest.json")


def test_add_puts_a_path_at_pending_and_appends_it_to_entry_order(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.add("b.py")
    assert [entry.path for entry in manifest.entries()] == ["a.py", "b.py"]
    assert manifest.entries()[0].state == "pending"


def test_add_for_an_already_present_path_raises_rather_than_resetting_state(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    with pytest.raises(CoverageTransitionError):
        manifest.add("a.py")
    assert manifest.entries()[0].state == "in_review"


def test_start_moves_pending_to_in_review(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    assert manifest.entries()[0].state == "in_review"


def test_finish_moves_in_review_to_done(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    assert manifest.entries()[0].state == "done"


def test_fail_moves_pending_or_in_review_to_failed_and_stores_the_note(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.fail("a.py", note="binary")
    assert manifest.entries()[0].state == "failed"
    assert manifest.entries()[0].note == "binary"


def test_finish_on_a_pending_path_raises(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    with pytest.raises(CoverageTransitionError, match="a.py"):
        manifest.finish("a.py")


def test_finish_on_a_failed_path_raises(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.fail("a.py")
    with pytest.raises(CoverageTransitionError, match="a.py"):
        manifest.finish("a.py")


def test_start_on_a_done_path_raises(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    with pytest.raises(CoverageTransitionError, match="a.py"):
        manifest.start("a.py")


def test_seal_with_every_entry_done_returns_complete(tmp_path):
    manifest = _manifest(tmp_path)
    for path in ("a.py", "b.py"):
        manifest.add(path)
        manifest.start(path)
        manifest.finish(path)
    assert manifest.seal() == "complete"


def test_seal_with_one_done_and_one_failed_returns_partial(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    manifest.add("b.py")
    manifest.fail("b.py", note="too-large")
    assert manifest.seal() == "partial"


def test_seal_with_a_pending_entry_raises_and_names_the_path(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    with pytest.raises(CoverageTransitionError, match="a.py"):
        manifest.seal()


def test_seal_with_an_in_review_entry_raises_and_names_the_path(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    with pytest.raises(CoverageTransitionError, match="a.py"):
        manifest.seal()


def test_seal_on_an_empty_manifest_raises(tmp_path):
    manifest = _manifest(tmp_path)
    with pytest.raises(CoverageTransitionError):
        manifest.seal()


def test_single_entry_manifest_seals_complete_when_done(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    assert manifest.seal() == "complete"


def test_single_entry_manifest_seals_partial_when_failed(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.fail("a.py")
    assert manifest.seal() == "partial"


def test_failed_entries_after_a_partial_seal_returns_every_failed_entry_with_its_note(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    manifest.add("b.py")
    manifest.fail("b.py", note="binary")
    manifest.add("c.py")
    manifest.fail("c.py", note="too-large")
    manifest.seal()
    failed = {entry.path: entry.note for entry in manifest.failed_entries()}
    assert failed == {"b.py": "binary", "c.py": "too-large"}


def test_written_json_preserves_first_seen_path_order_after_interleaved_transitions(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("c.py")
    manifest.add("a.py")
    manifest.add("b.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    manifest.fail("c.py")
    manifest.start("b.py")
    manifest.finish("b.py")
    data = json.loads(manifest.path.read_text())
    assert [entry["path"] for entry in data["files"]] == ["c.py", "a.py", "b.py"]


def test_load_round_trips_shas_states_notes_seal_and_order(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("c.py")
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    manifest.fail("c.py", note="binary")
    manifest.seal()

    loaded = CoverageManifest.load(manifest.path)
    assert loaded.base_sha == "base123"
    assert loaded.head_sha == "head456"
    assert loaded.seal() == "partial"
    assert [entry.path for entry in loaded.entries()] == ["c.py", "a.py"]
    assert [entry.state for entry in loaded.entries()] == ["failed", "done"]
    assert loaded.entries()[0].note == "binary"


def test_reading_the_manifest_after_each_transition_always_yields_parseable_json(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    json.loads(manifest.path.read_text())
    manifest.start("a.py")
    json.loads(manifest.path.read_text())
    manifest.finish("a.py")
    json.loads(manifest.path.read_text())
    manifest.seal()
    json.loads(manifest.path.read_text())


def test_manifest_version_constant_is_written_to_the_json(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    data = json.loads(manifest.path.read_text())
    assert data["version"] == MANIFEST_VERSION


def test_states_and_seals_are_the_expected_closed_sets():
    assert STATES == {"pending", "in_review", "done", "failed"}
    assert SEALS == {"complete", "partial"}


def test_three_path_lifecycle_with_one_failed_seals_partial_and_names_the_failed_path(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    manifest.start("a.py")
    manifest.finish("a.py")
    manifest.add("b.py")
    manifest.fail("b.py", note="binary")
    manifest.add("c.py")
    manifest.start("c.py")
    manifest.finish("c.py")
    assert manifest.seal() == "partial"
    failed = {entry.path: entry.note for entry in manifest.failed_entries()}
    assert failed == {"b.py": "binary"}


def test_three_path_lifecycle_all_done_seals_complete(tmp_path):
    manifest = _manifest(tmp_path)
    for path in ("a.py", "b.py", "c.py"):
        manifest.add(path)
        manifest.start(path)
        manifest.finish(path)
    assert manifest.seal() == "complete"
    assert manifest.failed_entries() == []


# --- SCALE-03: model/profile identity persisted on the manifest, and a resumed
# run's identity checked before any write (04-03) ---


def test_manifest_version_constant_is_now_2():
    assert MANIFEST_VERSION == 2


def test_to_dict_carries_model_and_profile_when_supplied(tmp_path):
    manifest = CoverageManifest(
        "base123", "head456", tmp_path / "manifest.json", model="opus", profile="security"
    )
    manifest.add("a.py")
    data = json.loads(manifest.path.read_text())
    assert data["model"] == "opus"
    assert data["profile"] == "security"


def test_to_dict_carries_none_identity_when_not_supplied(tmp_path):
    manifest = _manifest(tmp_path)
    manifest.add("a.py")
    data = json.loads(manifest.path.read_text())
    assert data["model"] is None
    assert data["profile"] is None


def test_load_round_trips_model_and_profile(tmp_path):
    manifest = CoverageManifest(
        "base123", "head456", tmp_path / "manifest.json", model="opus", profile="security"
    )
    manifest.add("a.py")
    loaded = CoverageManifest.load(manifest.path)
    assert loaded.model == "opus"
    assert loaded.profile == "security"


def test_load_a_version_1_manifest_with_no_identity_keys_still_loads(tmp_path):
    # A real version-1 manifest predates the model/profile keys entirely.
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "base_sha": "base123",
                "head_sha": "head456",
                "seal": None,
                "files": [{"path": "a.py", "state": "pending", "note": None}],
            }
        )
    )
    loaded = CoverageManifest.load(path)
    assert loaded.version == 1
    assert loaded.model is None
    assert loaded.profile is None
    assert loaded.base_sha == "base123"
    assert loaded.head_sha == "head456"


def test_resume_identity_error_extends_runtime_error():
    assert issubclass(ResumeIdentityError, RuntimeError)


def test_check_resume_identity_passes_when_model_and_profile_match(tmp_path):
    prior = CoverageManifest(
        "base123", "head456", tmp_path / "manifest.json", model="opus", profile="security"
    )
    check_resume_identity(prior, model="opus", profile="security")


def test_check_resume_identity_permits_any_value_when_prior_has_no_recorded_identity(tmp_path):
    prior = _manifest(tmp_path)  # model=None, profile=None: no identity recorded
    check_resume_identity(prior, model="opus", profile="strict")


def test_check_resume_identity_raises_on_model_mismatch_naming_both_values(tmp_path):
    prior = CoverageManifest(
        "base123", "head456", tmp_path / "manifest.json", model="opus", profile="security"
    )
    with pytest.raises(ResumeIdentityError) as exc_info:
        check_resume_identity(prior, model="sonnet", profile="security")
    assert "opus" in str(exc_info.value)
    assert "sonnet" in str(exc_info.value)


def test_check_resume_identity_raises_on_profile_mismatch_naming_both_values(tmp_path):
    prior = CoverageManifest(
        "base123", "head456", tmp_path / "manifest.json", model="opus", profile="security"
    )
    with pytest.raises(ResumeIdentityError) as exc_info:
        check_resume_identity(prior, model="opus", profile="strict")
    assert "security" in str(exc_info.value)
    assert "strict" in str(exc_info.value)


def test_a_rejected_resume_leaves_the_manifest_byte_identical_and_writes_no_new_file(tmp_path):
    """Load-bearing: the identity gate runs before any write, resumed or not."""
    from sec_overlay import cli
    from sec_overlay.repo_memory import RepoMemory

    target = tmp_path / "repo"
    target.mkdir()

    def runner(cmd, capture_output, text, check):
        class R:
            returncode = 0
            stdout = ""

        r = R()
        if "--verify" in cmd:
            r.stdout = f"{cmd[-1]}\n"
        elif "--name-status" in cmd:
            r.stdout = "M\ta.py\n"
        elif "--unified=3" in cmd:
            r.stdout = (
                "diff --git a/a.py b/a.py\n"
                "index 1111111..2222222 100644\n"
                "--- a/a.py\n"
                "+++ b/a.py\n"
                "@@ -1,1 +1,2 @@\n"
                " x = 1\n"
                "+y = 2\n"
            )
        return r

    base_sha = "a" * 40
    head_sha = "b" * 40
    rc1 = cli.run_review(
        base_sha, head_sha, str(target), runner=runner, model="model-a", profile="security"
    )
    assert rc1 == 0

    ws = RepoMemory.for_target(str(target), runner=runner).workspace
    manifest_path = ws.artifacts / "coverage_manifest.json"
    before_bytes = manifest_path.read_bytes()
    before_files = sorted(str(p.relative_to(ws.root)) for p in ws.root.rglob("*") if p.is_file())

    rc2 = cli.run_review(
        base_sha, head_sha, str(target), runner=runner, model="model-b", profile="security"
    )
    assert rc2 == 2

    after_bytes = manifest_path.read_bytes()
    after_files = sorted(str(p.relative_to(ws.root)) for p in ws.root.rglob("*") if p.is_file())
    assert after_bytes == before_bytes
    assert after_files == before_files
