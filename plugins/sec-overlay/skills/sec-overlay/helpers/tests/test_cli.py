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
    """Fake ``runner`` answering rev-parse/name-status/unified diff for ``paths``.

    Accepts (and ignores) ``**kwargs`` because the production runner default
    is ``partial(subprocess.run, timeout=timeout)`` — any fake monkeypatched
    onto ``subprocess.run`` receives a ``timeout`` keyword it must tolerate
    (SCALE-02).
    """

    def runner(cmd, capture_output, text, check, **kwargs):
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


# --- run_review: review_comments.json's embedded seal matches on-disk (OUT-01) -----------


def test_review_comments_embedded_manifest_seal_matches_on_disk_after_complete_run(tmp_path):
    from sec_overlay import cli
    from sec_overlay.repo_memory import RepoMemory

    runner = _make_review_runner(["a.py"])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    on_disk_seal = json.loads((ws.artifacts / "coverage_manifest.json").read_text())["seal"]
    comments_json = json.loads((ws.artifacts / "review_comments.json").read_text())
    embedded_seal = comments_json["coverage_manifest"]["seal"]

    assert embedded_seal is not None
    assert embedded_seal == on_disk_seal == "complete"


def test_review_comments_embedded_manifest_seal_is_partial_after_partial_run(
    tmp_path, monkeypatch
):
    from sec_overlay import cli
    from sec_overlay.repo_memory import RepoMemory

    runner = _make_review_runner(["a.py", "b.py"])
    monkeypatch.setattr(cli, "parse_hunks", _failing_parse_hunks(["b.py"]))
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 3

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    on_disk_seal = json.loads((ws.artifacts / "coverage_manifest.json").read_text())["seal"]
    comments_json = json.loads((ws.artifacts / "review_comments.json").read_text())
    embedded_seal = comments_json["coverage_manifest"]["seal"]

    assert embedded_seal == on_disk_seal == "partial"


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


# --- run_review: bounded ThreadPoolExecutor for per-file git fetch loops (SCALE-02) -------


def test_review_fetches_files_concurrently_bounded_by_max_git_procs(tmp_path):
    """A serial per-file fetch loop takes ``len(paths) * SLEEP``; a pool sized to
    fit every file collapses that to roughly one ``SLEEP`` regardless of file count."""
    import time

    from sec_overlay import cli

    paths = ["a.py", "b.py", "c.py"]
    sleep_seconds = 0.05

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and ("--unified=3" in cmd or "--unified=0" in cmd):
            time.sleep(sleep_seconds)
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    start = time.monotonic()
    rc = cli.run_review(
        "main", "develop", str(tmp_path), runner=runner, max_git_procs=len(paths)
    )
    elapsed = time.monotonic() - start
    assert rc == 0
    assert elapsed < len(paths) * sleep_seconds


def test_review_manifest_entries_preserve_file_order_despite_uneven_fetch_delay(tmp_path):
    """Manifest mutation order must stay file order, not fetch-completion order —
    the consuming thread applies ``manifest.add``/``start``/... in ``selection.reviewable``
    order regardless of which worker's git call returns first."""
    import json
    import time

    from sec_overlay import cli
    from sec_overlay.repo_memory import RepoMemory

    paths = ["a.py", "b.py", "c.py"]
    # a.py's fetch is the slowest, so a completion-ordered consumer would place it last.
    delays = {"a.py": 0.06, "b.py": 0.0, "c.py": 0.0}

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            path = cmd[-1]
            time.sleep(delays.get(path, 0.0))
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner, max_git_procs=3)
    assert rc == 0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    manifest_json = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    assert [f["path"] for f in manifest_json["files"]] == paths


def test_review_zero_reviewable_files_needs_no_worker_pool(tmp_path, monkeypatch):
    """An empty diff must not construct a ``ThreadPoolExecutor`` at all."""
    from sec_overlay import cli

    def _forbidden(*args, **kwargs):
        raise AssertionError("ThreadPoolExecutor must not be constructed for zero files")

    monkeypatch.setattr(cli, "ThreadPoolExecutor", _forbidden)
    runner = _make_review_runner([])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc == 0


# --- run_review: per-unit --timeout fails every member of a slow unit (SCALE-02) ----------


def test_review_unit_timeout_fails_every_member_with_timeout_note(tmp_path):
    """A ReviewUnit whose fetch work exceeds ``--timeout`` fails every one of its
    member files with the timeout note, sealing the manifest partial (rc == 3).

    Three, not two, members — a timed-out unit that fails only its first
    member (or only itself) leaves the rest unfinished, and ``seal()`` raises
    on unfinished entries instead of returning partial (the plan's named
    regression risk)."""
    import time

    from sec_overlay import cli

    # en.json / fr.json / de.json group into one ReviewUnit via bundle.py's
    # same-directory locale-sibling rule (three members, one unit).
    paths = ["locales/en.json", "locales/fr.json", "locales/de.json"]

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            time.sleep(1.2)
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner, timeout=1)
    assert rc == 3

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    manifest_json = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    failed = {f["path"]: f["note"] for f in manifest_json["files"] if f["state"] == "failed"}
    assert failed == {p: cli.TIMEOUT_NOTE for p in paths}
    assert manifest_json["seal"] == "partial"


def test_review_unit_within_timeout_finishes_normally(tmp_path):
    """A unit whose fetch work stays under ``--timeout`` seals complete, not partial."""
    from sec_overlay import cli

    runner = _make_review_runner(["a.py", "test_a.py"])
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner, timeout=5)
    assert rc == 0


# --- run_review: wall-clock bound on a hung unit fetch (SCALE-02) ------------------------


def test_review_returns_before_hung_unit_fetch_completes(tmp_path):
    """A unit whose fetch work sleeps well past ``--timeout`` must not hold
    ``run_review`` open until every member finishes fetching. Pre-fix reproduction
    (04-VERIFICATION.md SCALE-02): 4.20s wall clock for a declared ``timeout=1``,
    because ``with ThreadPoolExecutor(...) as ex:`` blocks on exit until the
    abandoned worker finishes, even after ``future.result(timeout=...)`` already
    raised."""
    import time

    from sec_overlay import cli

    paths = ["locales/en.json", "locales/fr.json", "locales/de.json"]

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            time.sleep(1.2)
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    start = time.monotonic()
    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner, timeout=1)
    elapsed = time.monotonic() - start
    assert rc == 3
    # Roughly twice the declared timeout, not the ~4.2s full-fetch pre-fix wait.
    assert elapsed < 2.0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    manifest_json = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    failed = {f["path"]: f["note"] for f in manifest_json["files"] if f["state"] == "failed"}
    assert failed == {p: cli.TIMEOUT_NOTE for p in paths}
    assert manifest_json["seal"] == "partial"


def test_review_abandoned_unit_fetch_stops_at_the_unit_deadline(tmp_path):
    """Once a timed-out unit's own fetch deadline passes, the abandoned worker
    stops fetching its remaining members instead of continuing pointless work
    (SCALE-02) -- the recorded call count stays below a full unit fetch's count."""
    import time

    from sec_overlay import cli

    paths = ["locales/en.json", "locales/fr.json", "locales/de.json"]
    calls: list[str] = []

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and "--unified=3" in cmd:
            calls.append(cmd[-1])
            time.sleep(0.6)
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    rc = cli.run_review("main", "develop", str(tmp_path), runner=runner, timeout=1)
    assert rc == 3
    # Let the abandoned worker thread reach (and stop at) its own deadline
    # before reading the call count it recorded.
    time.sleep(0.8)
    assert len(calls) < len(paths)


def test_review_production_git_calls_carry_subprocess_timeout(tmp_path, monkeypatch):
    """With no injected runner, every real ``subprocess.run`` call the review
    path makes carries a ``timeout`` equal to the declared ``--timeout``, so a
    hung git child is killed rather than orphaned (SCALE-02)."""
    from sec_overlay import cli

    captured_timeouts: list[object] = []

    def fake_run(cmd, capture_output=True, text=True, check=False, **kwargs):
        captured_timeouts.append(kwargs.get("timeout"))
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("M\ta.py\n")
        if cmd[1] == "diff" and "--unified=3" in cmd:
            return _FakeResult("diff --git a/a.py b/a.py\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    import subprocess

    monkeypatch.setattr(subprocess, "run", fake_run)
    rc = cli.run_review("main", "develop", str(tmp_path), timeout=42)
    assert rc == 0
    assert captured_timeouts
    assert all(t == 42 for t in captured_timeouts)


# --- run_review: resumed run reads at the sealed SHAs, not fresh refs (SCALE-03) ---------


def test_review_resume_reads_at_persisted_head_sha_despite_moved_head(tmp_path):
    """A resumed run reads diffs at the SHA the prior run sealed, not at a freshly
    resolved (possibly moved) ref — the prior run's ``develop`` may have advanced."""
    from sec_overlay import cli

    runner = _make_review_runner(["a.py"])
    rc1 = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc1 == 0

    ws = RepoMemory.for_target(str(tmp_path), runner=runner).workspace
    prior = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    assert prior["head_sha"] == "sha-develop"

    captured = {}

    def moved_runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            ref = cmd[-1]
            if ref == "develop":
                # The branch moved since the prior run — a resumed read must
                # never land on this value.
                return _FakeResult("sha-develop-MOVED\n")
            return _FakeResult(f"{ref}\n" if ref.startswith("sha-") else f"sha-{ref}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            captured["diff_refs"] = (cmd[3], cmd[4])
            return _FakeResult("M\ta.py\n")
        if cmd[1] == "diff" and "--unified=3" in cmd:
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    rc2 = cli.run_review("main", "develop", str(tmp_path), runner=moved_runner)
    assert rc2 == 0
    assert captured["diff_refs"] == ("sha-main", "sha-develop")


def test_review_resume_with_unresolvable_persisted_sha_fails_loudly(tmp_path, capsys):
    """T-04-12: a persisted SHA that no longer resolves (rewritten/collected) fails
    the resumed run rather than silently reading a different tree as an empty diff."""
    from sec_overlay import cli

    runner = _make_review_runner(["a.py"])
    rc1 = cli.run_review("main", "develop", str(tmp_path), runner=runner)
    assert rc1 == 0

    def gc_runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            ref = cmd[-1]
            if ref == "sha-develop":
                # The prior run's sealed head SHA has since been GC'd/rewritten.
                return _FakeResult("", returncode=128)
            return _FakeResult(f"{ref}\n")
        return _FakeResult("")

    rc2 = cli.run_review("main", "develop", str(tmp_path), runner=gc_runner)
    assert rc2 == 2
    assert "sha-develop" in capsys.readouterr().err


# --- review CLI surface: --model flag forwarding + resume rejection (SCALE-03) -----------


def test_review_accepts_model_flag_and_forwards_it_to_run_review(tmp_path, monkeypatch):
    from sec_overlay import cli

    captured = {}
    real_run_review = cli.run_review

    def spy(*args, **kwargs):
        captured["model"] = kwargs.get("model")
        return real_run_review(*args, **kwargs)

    monkeypatch.setattr(cli, "run_review", spy)
    import subprocess

    monkeypatch.setattr(subprocess, "run", _make_review_runner([]))
    target = tmp_path / "repo"
    target.mkdir()
    rc = cli.main(
        [
            "review", "--base", "main", "--head", "develop", "--root", str(target),
            "--model", "opus",
        ]
    )
    assert rc == 0
    assert captured["model"] == "opus"


def test_review_resume_with_changed_model_exits_2_via_main_entrypoint(
    tmp_path, monkeypatch, capsys
):
    from sec_overlay import cli

    import subprocess

    monkeypatch.setattr(subprocess, "run", _make_review_runner(["a.py"]))

    rc1 = cli.main(
        [
            "review", "--base", "main", "--head", "develop", "--root", str(tmp_path),
            "--model", "opus",
        ]
    )
    assert rc1 == 0

    rc2 = cli.main(
        [
            "review", "--base", "main", "--head", "develop", "--root", str(tmp_path),
            "--model", "sonnet",
        ]
    )
    assert rc2 == 2
    err = capsys.readouterr().err
    assert "opus" in err
    assert "sonnet" in err
