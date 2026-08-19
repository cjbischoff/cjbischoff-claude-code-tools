"""Tests for git diff scoping helpers."""

import pytest

from sec_overlay.diffscope import (
    binary_paths,
    changed_file_records,
    changed_files,
    file_diff_line_count,
    head_sha,
    resolve_ref_sha,
    validate_ref,
)


def test_changed_files_parses_name_only(monkeypatch):
    class R:
        stdout = "app.py\nsrc/db.py\n"
        returncode = 0

    def fake_run(cmd, capture_output, text, check):
        assert cmd[:3] == ["git", "diff", "--name-only"]
        return R()

    assert changed_files("sha1", "HEAD", runner=fake_run) == ["app.py", "src/db.py"]


def test_head_sha_strips(monkeypatch):
    class R:
        stdout = "abc1234\n"
        returncode = 0

    assert head_sha(runner=lambda *a, **k: R()) == "abc1234"


@pytest.mark.parametrize(
    "ref",
    [
        "a" * 40,
        "HEAD",
        "main",
        "v1.2.3",
        "feature/x-y",
        "a",
        "HEAD~1",
    ],
)
def test_validate_ref_accepts_allowlisted_refs(ref):
    assert validate_ref(ref) == ref


def test_resolve_ref_sha_strips_stdout_on_success():
    class R:
        stdout = "abc1234\n"
        returncode = 0

    assert resolve_ref_sha("main", runner=lambda *a, **k: R()) == "abc1234"


def test_resolve_ref_sha_raises_on_nonzero_returncode():
    # Regression (CR-02): a syntactically valid but nonexistent ref makes
    # `git rev-parse --verify` exit non-zero with empty stdout — this must raise,
    # not silently resolve to "".
    class R:
        stdout = ""
        returncode = 128

    with pytest.raises(ValueError, match="does-not-exist-branch"):
        resolve_ref_sha("does-not-exist-branch", runner=lambda *a, **k: R())


def test_validate_ref_rejects_empty_string():
    with pytest.raises(ValueError, match=r"''"):
        validate_ref("")


def test_validate_ref_rejects_leading_dash_even_with_allowlisted_rest():
    with pytest.raises(ValueError, match="-oProxyCommand"):
        validate_ref("-oProxyCommand=x")


@pytest.mark.parametrize("ref", ["a b", "a;b", "a`b", "a$b"])
def test_validate_ref_rejects_shell_metacharacters(ref):
    with pytest.raises(ValueError):
        validate_ref(ref)


def test_changed_file_records_empty_diff_returns_empty_list():
    def fake_run(cmd, capture_output, text, check):
        class R:
            stdout = ""
            returncode = 0

        return R()

    assert changed_file_records("a" * 40, "b" * 40, runner=fake_run) == []


def test_changed_file_records_preserves_git_emitted_order():
    def fake_run(cmd, capture_output, text, check):
        class R:
            stdout = "M\tb.py\nA\ta.py\nD\tc.py\n"
            returncode = 0

        return R()

    records = changed_file_records("base", "head", runner=fake_run)
    assert [r.path for r in records] == ["b.py", "a.py", "c.py"]
    assert [r.status for r in records] == ["M", "A", "D"]


def test_changed_file_records_rename_carries_both_paths():
    def fake_run(cmd, capture_output, text, check):
        class R:
            stdout = "R100\told/name.py\tnew/name.py\n"
            returncode = 0

        return R()

    records = changed_file_records("base", "head", runner=fake_run)
    assert len(records) == 1
    assert records[0].status == "R"
    assert records[0].path == "new/name.py"
    assert records[0].old_path == "old/name.py"


def test_changed_file_records_copy_carries_both_paths():
    def fake_run(cmd, capture_output, text, check):
        class R:
            stdout = "C75\tsrc.py\tdst.py\n"
            returncode = 0

        return R()

    records = changed_file_records("base", "head", runner=fake_run)
    assert records[0].status == "C"
    assert records[0].path == "dst.py"
    assert records[0].old_path == "src.py"


def test_file_diff_line_count_counts_diff_body_lines():
    def fake_run(cmd, capture_output, text, check):
        assert cmd[:3] == ["git", "diff", "--unified=0"]

        class R:
            stdout = "diff --git a/x b/x\n@@ -1 +1 @@\n-old\n+new\n"
            returncode = 0

        return R()

    assert file_diff_line_count("x", "base", "head", runner=fake_run) == 4


def test_binary_paths_reads_numstat_dash_markers():
    def fake_run(cmd, capture_output, text, check):
        assert cmd[:3] == ["git", "diff", "--numstat"]

        class R:
            stdout = "3\t1\ttext.py\n-\t-\timage.png\n"
            returncode = 0

        return R()

    assert binary_paths("base", "head", runner=fake_run) == frozenset({"image.png"})


def test_rev_parse_precedes_diff_and_diff_never_sees_a_raw_ref(tmp_path):
    from sec_overlay.cli import run_review

    class OrderRunner:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, cmd, capture_output, text, check):
            self.calls.append(list(cmd))

            class R:
                returncode = 0
                stdout = ""

            r = R()
            r.stdout = f"sha-for-{cmd[-1]}\n" if "--verify" in cmd else ""
            return r

    runner = OrderRunner()
    run_review("main", "develop", str(tmp_path), runner=runner)

    diff_indexes = [i for i, c in enumerate(runner.calls) if c[1] == "diff"]
    rev_parse_indexes = [i for i, c in enumerate(runner.calls) if c[1] == "rev-parse"]
    assert rev_parse_indexes and diff_indexes
    assert max(rev_parse_indexes[:2]) < min(diff_indexes)
    for i in diff_indexes:
        assert "main" not in runner.calls[i]
        assert "develop" not in runner.calls[i]
