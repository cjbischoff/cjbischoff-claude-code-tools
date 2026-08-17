"""Tests for the deterministic patch-application check."""

from sec_overlay.patch_status import PatchStatus, check_patch_applied, not_applied_caution


class _Runner:
    """Fake subprocess.run: pops the next returncode from ``returncodes`` per call."""

    def __init__(self, returncodes):
        self._returncodes = returncodes
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        rc = self._returncodes.pop(0)
        return type("R", (), {"returncode": rc})()


def _runner(returncodes):
    return _Runner(returncodes)


def test_check_patch_applied_reverse_succeeds_means_applied():
    runner = _runner([0])  # reverse check succeeds
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.APPLIED
    assert len(runner.calls) == 1


def test_check_patch_applied_forward_succeeds_means_not_applied():
    runner = _runner([1, 0])  # reverse fails, forward succeeds
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.NOT_APPLIED
    assert len(runner.calls) == 2


def test_check_patch_applied_neither_succeeds_means_unknown():
    runner = _runner([1, 1])  # both fail
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.UNKNOWN
    assert len(runner.calls) == 2


def test_check_patch_applied_empty_diff_short_circuits():
    runner = _runner([])
    assert check_patch_applied("/tgt", "", runner=runner) is PatchStatus.UNKNOWN
    assert check_patch_applied("/tgt", "   ", runner=runner) is PatchStatus.UNKNOWN
    assert runner.calls == []  # never invoked


def test_not_applied_caution_none_for_applied():
    assert not_applied_caution(PatchStatus.APPLIED) is None


def test_not_applied_caution_present_for_not_applied():
    text = not_applied_caution(PatchStatus.NOT_APPLIED)
    assert text is not None and "Caution" in text


def test_not_applied_caution_present_for_unknown():
    text = not_applied_caution(PatchStatus.UNKNOWN)
    assert text is not None and "Caution" in text
