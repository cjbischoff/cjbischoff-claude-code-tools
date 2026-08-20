"""Tests for the scan CLI's run_scan wiring."""

import json

import pytest

from sec_overlay.cli import run_scan
from sec_overlay.phase_gate import DroppedFinding
from sec_overlay.positioning import PositionResult
from sec_overlay.repo_memory import RepoMemory
from sec_overlay.report import DROPPED_FINDINGS_HEADING, POSITION_REVIEW_HEADING
from sec_overlay.workspace import Workspace


def test_run_scan_writes_findings_json_to_reports_dir(tmp_path, monkeypatch):
    from sec_overlay import cli

    monkeypatch.setattr(cli, "run_semgrep", lambda *a, **k: [])
    ws = Workspace(tmp_path / "w", reports_dir=tmp_path / "R")
    run_scan("t", ws, "cfg", sha="deadbeef")
    assert (tmp_path / "R" / "report.sarif").exists()
    assert (tmp_path / "R" / "report.md").exists()
    fj = tmp_path / "R" / "findings.json"
    assert fj.exists() and json.loads(fj.read_text()) == []


def test_scan_defaults_to_repo_memory(tmp_path, monkeypatch):
    from sec_overlay import cli
    monkeypatch.setenv("SEC_OVERLAY_HOME", str(tmp_path / "mem"))
    target = tmp_path / "repo"; (target / "a.py").parent.mkdir(parents=True, exist_ok=True)
    (target / "a.py").write_text("x=1\n")
    monkeypatch.setattr(cli, "run_semgrep", lambda *a, **k: [])
    rc = cli.main(["scan", "--target", str(target), "--config", "rules/smoke.yaml"])
    assert rc == 0
    # memory folder created under SEC_OVERLAY_HOME with a seeded MEMORY.md + state
    # (the home also holds a .gitignore sidecar; select the repo-slug dir explicitly)
    slugs = [p for p in (tmp_path / "mem").iterdir() if p.is_dir()]
    assert slugs and (slugs[0] / "MEMORY.md").exists()
    assert (slugs[0] / "findings").is_dir()


def test_review_rejects_leading_dash_base_ref_with_exit_2(tmp_path, capsys):
    from sec_overlay import cli

    rc = cli.main(["review", "--base=-x", "--head", "HEAD", "--root", str(tmp_path)])
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert err.count("\n") == 0
    assert "-x" in err


def test_review_rejects_empty_base_ref_with_exit_2(tmp_path, capsys):
    from sec_overlay import cli

    rc = cli.main(["review", "--base", "", "--head", "HEAD", "--root", str(tmp_path)])
    assert rc == 2


def test_memory_command_status_and_learn(tmp_path, monkeypatch, capsys):
    from sec_overlay import cli
    monkeypatch.setenv("SEC_OVERLAY_HOME", str(tmp_path / "mem"))
    target = tmp_path / "repo"; target.mkdir()
    assert cli.main(["memory", "--target", str(target)]) == 0
    assert "status:" in capsys.readouterr().out
    assert cli.main(["memory", "--target", str(target), "--learn", "found X", "--tag", "note"]) == 0
    slug = next(p for p in (tmp_path / "mem").iterdir() if p.is_dir())
    assert "found X" in (slug / "MEMORY.md").read_text()


# --- run_review: seal -> exit code wiring (D-15) -----------------------------------------


class _FakeResult:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def _make_review_runner(paths):
    """Fake ``runner`` answering rev-parse/name-status/unified diff for ``paths``."""

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    return runner


def _failing_parse_hunks(fail_paths):
    """Fake ``parse_hunks`` raising for any diff text naming a path in ``fail_paths``."""
    from sec_overlay.diffhunks import parse_hunks as real_parse_hunks

    def fake(diff_text):
        for p in fail_paths:
            if p in diff_text:
                raise ValueError(f"parse failed: {p}")
        return real_parse_hunks(diff_text)

    return fake


def test_review_exit_2_on_unresolvable_but_valid_ref(tmp_path, capsys):
    # Regression (CR-02): a syntactically valid but nonexistent ref must exit 2,
    # not silently proceed with an empty SHA.
    from sec_overlay import cli

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult("", returncode=128)
        return _FakeResult("")

    rc = cli.run_review("nonexistent-ref", "HEAD", str(tmp_path), runner=runner)
    assert rc == 2
    assert "nonexistent-ref" in capsys.readouterr().err


def test_review_excludes_oversized_diff_via_wired_diff_line_counts(tmp_path, monkeypatch):
    # Regression (CR-03): run_review must compute diff_line_counts/binary_paths and pass
    # them into partition(), or an oversized/binary file silently stays "reviewable".
    from sec_overlay import cli
    from sec_overlay.file_select import partition as real_partition

    captured = {}

    def spy_partition(records, **kwargs):
        selection = real_partition(records, **kwargs)
        captured["selection"] = selection
        return selection

    monkeypatch.setattr(cli, "partition", spy_partition)

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("M\tbig.py\n")
        if cmd[1] == "diff" and "--unified=0" in cmd:
            return _FakeResult("\n".join(f"+line{i}" for i in range(5001)))
        return _FakeResult("")

    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0
    selection = captured["selection"]
    assert selection.reviewable == []
    assert any(e.path == "big.py" and e.reason == "too-large" for e in selection.excluded)


def test_review_exit_0_on_complete_seal_with_no_drops(tmp_path):
    from sec_overlay import cli

    runner = _make_review_runner(["a.py"])
    assert cli.run_review("main", "develop", str(tmp_path), runner=runner) == 0


def test_review_exit_3_on_partial_seal(tmp_path, monkeypatch):
    from sec_overlay import cli

    runner = _make_review_runner(["a.py", "b.py"])
    monkeypatch.setattr(cli, "parse_hunks", _failing_parse_hunks(["b.py"]))
    assert cli.run_review("main", "develop", str(tmp_path), runner=runner) == 3


def test_review_partial_seal_prints_unfinished_file_name_state_and_note(
    tmp_path, monkeypatch, capsys
):
    from sec_overlay import cli

    runner = _make_review_runner(["a.py", "b.py"])
    monkeypatch.setattr(cli, "parse_hunks", _failing_parse_hunks(["b.py"]))
    cli.run_review("main", "develop", str(tmp_path), runner=runner)
    out = capsys.readouterr().out
    assert "b.py" in out
    assert "failed" in out
    assert "parse failed: b.py" in out


def test_review_partial_seal_with_three_failures_prints_three_unfinished_lines(
    tmp_path, monkeypatch, capsys
):
    from sec_overlay import cli

    paths = ["a.py", "b.py", "c.py"]
    runner = _make_review_runner(paths)
    monkeypatch.setattr(cli, "parse_hunks", _failing_parse_hunks(paths))
    cli.run_review("main", "develop", str(tmp_path), runner=runner)
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "unfinished" in ln]
    assert len(lines) == 3
    for p in paths:
        assert any(p in ln for ln in lines)


def test_review_complete_seal_prints_no_unfinished_lines(tmp_path, capsys):
    from sec_overlay import cli

    runner = _make_review_runner(["a.py"])
    cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert "unfinished" not in capsys.readouterr().out


def test_review_zero_reviewable_files_returns_exit_0_with_no_unfinished_line(tmp_path, capsys):
    from sec_overlay import cli

    runner = _make_review_runner([])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0
    assert "unfinished" not in capsys.readouterr().out


def test_review_exit_3_via_main_entrypoint_on_partial_seal(tmp_path, monkeypatch):
    from sec_overlay import cli
    from sec_overlay.diffscope import ChangedFile

    monkeypatch.setattr(cli, "resolve_ref_sha", lambda ref, runner=None: f"sha-{ref}")
    monkeypatch.setattr(
        cli, "changed_file_records",
        lambda base, head, runner=None: [ChangedFile(path="a.py", status="M")],
    )
    monkeypatch.setattr(cli, "file_diff_text", lambda *a, **k: "a.py")
    monkeypatch.setattr(cli, "parse_hunks", _failing_parse_hunks(["a.py"]))
    rc = cli.main(["review", "--base", "main", "--head", "develop", "--root", str(tmp_path)])
    assert rc == 3


# --- run_review: gate output wired into report.md + review_ledger.json (T-02-15/18) -----


def test_review_writes_ledger_and_report_with_zero_drops_and_declines(tmp_path):
    # No finding source is wired into review mode yet, so the real gate runs against an
    # empty finding list — both outputs must still be emitted (T-02-15's "absent" vs "none").
    from sec_overlay import cli

    runner = _make_review_runner(["a.py"])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["dropped"] == []
    assert ledger["position_reviews"] == []

    md = ws.report_path.read_text()
    assert f"{DROPPED_FINDINGS_HEADING}\n\nNo finding was dropped." in md
    assert f"{POSITION_REVIEW_HEADING}\n\nNo finding required position review." in md


def test_review_defaults_to_repo_memory(tmp_path, monkeypatch):
    # Regression (DIFF-04): run_review must resolve its workspace through
    # RepoMemory.for_target, the same sidecar convention scan/audit use, not a bare
    # Workspace(root) on the reviewed repo's tracked tree.
    import subprocess

    from sec_overlay import cli

    monkeypatch.setenv("SEC_OVERLAY_HOME", str(tmp_path / "mem"))
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(subprocess, "run", _make_review_runner(["a.py"]))

    rc = cli.main(["review", "--base", "main", "--head", "develop", "--root", str(target)])
    assert rc == 0

    mem_base = tmp_path / "mem"
    slugs = [p for p in mem_base.iterdir() if p.is_dir()]
    assert len(slugs) == 1
    assert (slugs[0] / "artifacts" / "coverage_manifest.json").exists()

    assert not (target / "artifacts").exists()
    assert not (target / "report.md").exists()


def test_review_ledger_drop_count_matches_markdown_drop_rows(tmp_path, monkeypatch):
    # T-02-18 invariant: the markdown drop-row count must equal the ledger drop count —
    # both come from the same gate output via write_report, so they cannot disagree.
    from sec_overlay import cli

    dropped = [
        DroppedFinding(path="a.py", line=9, rule_id="R1", reason="outside-diff"),
        DroppedFinding(path="b.py", line=2, rule_id="R2", reason="outside-diff"),
    ]
    declines = [
        PositionResult("needs-position-review", None, None, "no-hunk-match", "c.py", 3, "snip"),
    ]
    monkeypatch.setattr(
        cli,
        "review_position_gate",
        lambda findings, hunks_by_path, file_text_by_path=None: ([], dropped, declines),
    )
    runner = _make_review_runner(["a.py"])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["dropped"]) == len(dropped)
    assert len(ledger["position_reviews"]) == len(declines)

    md = ws.report_path.read_text()
    drop_section = md.split(DROPPED_FINDINGS_HEADING, 1)[1].split("## ", 1)[0]
    drop_rows = [
        line for line in drop_section.splitlines()
        if line.startswith("|") and "Path" not in line and "---" not in line
    ]
    assert len(drop_rows) == len(ledger["dropped"])


# --- run_review: bounded --concurrency / --timeout / --max-git-procs (SCALE-02) ---------


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--concurrency", 1),
        ("--concurrency", 128),
        ("--timeout", 1),
        ("--timeout", 3600),
        ("--max-git-procs", 1),
        ("--max-git-procs", 128),
    ],
)
def test_review_accepts_flag_at_1_and_at_its_own_ceiling(tmp_path, monkeypatch, flag, value):
    import subprocess

    from sec_overlay import cli

    monkeypatch.setattr(subprocess, "run", _make_review_runner([]))
    target = tmp_path / "repo"
    target.mkdir()
    rc = cli.main(
        ["review", "--base", "main", "--head", "develop", "--root", str(target), flag, str(value)]
    )
    assert rc == 0


@pytest.mark.parametrize(
    "flag,ceiling,invalid",
    [
        ("--concurrency", 128, 0),
        ("--concurrency", 128, -1),
        ("--concurrency", 128, 129),
        ("--timeout", 3600, 0),
        ("--timeout", 3600, -1),
        ("--timeout", 3600, 3601),
        ("--max-git-procs", 128, 0),
        ("--max-git-procs", 128, -1),
        ("--max-git-procs", 128, 129),
    ],
)
def test_review_rejects_flag_out_of_range_naming_flag_and_range(
    tmp_path, capsys, flag, ceiling, invalid
):
    from sec_overlay import cli

    rc = cli.main(
        [
            "review",
            "--base", "main",
            "--head", "develop",
            "--root", str(tmp_path),
            f"{flag}={invalid}",
        ]
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert flag in err
    assert f"1 and {ceiling}" in err


def test_review_rejects_non_integer_flag_value_via_argparse(tmp_path, capsys):
    from sec_overlay import cli

    with pytest.raises(SystemExit):
        cli.main(
            [
                "review",
                "--base", "main",
                "--head", "develop",
                "--root", str(tmp_path),
                "--concurrency=nope",
            ]
        )


def test_review_default_bounds_are_8_600_and_16(tmp_path, monkeypatch):
    from sec_overlay import cli

    captured = {}
    real_run_review = cli.run_review

    def spy(*args, **kwargs):
        captured["concurrency"] = kwargs.get("concurrency")
        captured["timeout"] = kwargs.get("timeout")
        captured["max_git_procs"] = kwargs.get("max_git_procs")
        return real_run_review(*args, **kwargs)

    monkeypatch.setattr(cli, "run_review", spy)
    import subprocess

    monkeypatch.setattr(subprocess, "run", _make_review_runner([]))
    target = tmp_path / "repo"
    target.mkdir()
    rc = cli.main(["review", "--base", "main", "--head", "develop", "--root", str(target)])
    assert rc == 0
    assert captured == {"concurrency": 8, "timeout": 600, "max_git_procs": 16}
