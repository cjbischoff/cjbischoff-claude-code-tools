"""Tests for the scan CLI's run_scan wiring."""

import json

from sec_overlay.cli import run_scan
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
