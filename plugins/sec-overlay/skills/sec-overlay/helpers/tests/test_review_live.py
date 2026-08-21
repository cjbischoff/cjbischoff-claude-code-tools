"""Live-source tests: the review verb wired to real findings, end to end (03-06 Task 3)."""

import json
import subprocess

from sec_overlay import cli
from sec_overlay.cli import main, run_review
from sec_overlay.repo_memory import RepoMemory
from sec_overlay.review_agent import agent_label
from sec_overlay.workspace import record_agent_return

_BASE_SHA = "a" * 40
_HEAD_SHA = "b" * 40


def _sidecar_ws(root):
    """Resolve the sidecar workspace `run_review` writes to for `root`.

    Reads `subprocess.run` at call time so it sees whatever the test's
    `monkeypatch.setattr(subprocess, "run", ...)` installed — the same runner
    `run_review` resolves through its own `r = runner or subprocess.run` default.
    """
    return RepoMemory.for_target(root, runner=subprocess.run).workspace


def _diff_for(path: str) -> str:
    """One-hunk unified diff adding a line to `path` (mirrors test_review_tracer's fixture)."""
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1,2 +1,3 @@\n"
        " import os\n"
        "+os.system(cmd)\n"
        " print('hi')\n"
    )


def _new_file_text_from_diff(diff_text: str) -> str:
    """Reconstruct the new-side whole file from a single-hunk diff covering it end to end.

    Mirrors `diffhunks.parse_hunks`'s own line classification (context/added kept,
    deleted dropped) — the fixture diffs here always describe the file's full content,
    so this is the same "head text" `diffscope.file_text_at_ref` would return for real.
    """
    lines: list[str] = []
    in_hunk = False
    for raw in diff_text.splitlines():
        if raw.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("-"):
            continue
        lines.append(raw[1:] if raw else raw)
    return "\n".join(lines) + "\n"


def _fake_run_for(diffs: dict[str, str], head_texts: dict[str, str] | None = None):
    """Fake runner over an arbitrary set of changed files (path -> diff text).

    `head_texts` overrides the default whole-file text (reconstructed from `diffs`) that
    a `git show <ref>:<path>` call returns — needed only when a test's claimed line falls
    outside the diff-reconstructed content (e.g. line 999 of a much longer real file).

    Accepts (and ignores) `**kwargs`: the production runner default is
    `partial(subprocess.run, timeout=timeout)`, so a fake monkeypatched onto
    `subprocess.run` receives a `timeout` keyword it must tolerate (SCALE-02).
    """
    name_status = "".join(f"M\t{p}\n" for p in diffs)
    texts = head_texts or {}

    def fake(cmd, capture_output, text, check, **kwargs):
        class R:
            returncode = 0
            stdout = ""

        r = R()
        if "--verify" in cmd:
            r.stdout = f"{cmd[-1]}\n"
        elif "--name-status" in cmd:
            r.stdout = name_status
        elif "--unified=3" in cmd:
            r.stdout = diffs.get(cmd[-1], "")
        elif cmd[1] == "show":
            path = cmd[-1].split(":", 1)[1]
            r.stdout = texts.get(path, _new_file_text_from_diff(diffs.get(path, "")))
        else:
            r.stdout = ""
        return r

    return fake


def _record_return(root, path, *, base=_BASE_SHA, head=_HEAD_SHA, calls):
    """Record a review-file return envelope for `path` (production disk format)."""
    ws = _sidecar_ws(root)
    ws.ensure()
    envelope = json.dumps({"base": base, "head": head, "response": json.dumps(calls)})
    record_agent_return(ws, agent_label(path), envelope)


def _code_comment(path, line, message, defect_class="sqli"):
    return {"tool": "code_comment", "path": path, "line": line, "message": message,
            "defect_class": defect_class}


def test_prepare_writes_plan_and_prompt_per_file(tmp_path, monkeypatch):
    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path),
               "--prepare"])
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    plan = json.loads((ws.runs / "review_plan.json").read_text())
    assert len(plan) == 2
    assert {e["path"] for e in plan} == {"app.py", "other.py"}
    for entry in plan:
        assert entry["base"] == _BASE_SHA
        assert entry["head"] == _HEAD_SHA
        prompt_text = (ws.runs / "review_prompts" / f"{entry['agent_label']}.md").read_text()
        assert entry["path"] in prompt_text
        assert "{{" not in prompt_text


def test_recorded_return_produces_a_nonzero_finding_count(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["review_findings"]) == 1
    assert ledger["review_findings"][0]["path"] == "app.py"


def test_profile_split_null_dereference_security_excludes_general_includes(tmp_path, monkeypatch):
    # Two independent targets, not two calls against one target: SCALE-03's resume-identity
    # gate now rejects a profile change on an existing manifest, so this profile-split
    # comparison needs its own workspace per profile rather than resuming one.
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    target_security = tmp_path / "security"
    target_general = tmp_path / "general"
    _record_return(str(target_security), "app.py",
                    calls=[_code_comment("app.py", 2, "possible nil deref", "null-dereference")])
    _record_return(str(target_general), "app.py",
                    calls=[_code_comment("app.py", 2, "possible nil deref", "null-dereference")])

    rc_security = run_review(_BASE_SHA, _HEAD_SHA, str(target_security), profile="security")
    assert rc_security == 0
    ledger_security = json.loads(
        (_sidecar_ws(target_security).artifacts / "review_ledger.json").read_text()
    )
    assert ledger_security["review_findings"] == []

    rc_general = run_review(_BASE_SHA, _HEAD_SHA, str(target_general), profile="general")
    assert rc_general == 0
    ledger_general = json.loads(
        (_sidecar_ws(target_general).artifacts / "review_ledger.json").read_text()
    )
    assert len(ledger_general["review_findings"]) == 1
    assert ledger_general["review_findings"][0]["defect_class"] == "null-dereference"


def test_run_review_scopes_git_calls_to_root_not_process_cwd(tmp_path):
    """Regression (Phase 5 tracer, D-05-01-01): a real, uninjected runner must run every
    git diff/rev-parse call against `--root`, not wherever the CLI process's cwd happens
    to be. Uses a real subprocess-backed git repo deliberately unrelated to pytest's own
    cwd (this plugin's helpers/ checkout) — pre-fix, `resolve_ref_sha`/`changed_file_records`
    ran unscoped, silently reading pytest's cwd repo and reporting zero changed files.
    """
    repo = tmp_path / "target-repo"
    repo.mkdir()

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

    def git_out(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (repo / "app.py").write_text("print('hi')\n")
    git("add", "app.py")
    git("commit", "-q", "-m", "base")
    base_sha = git_out("rev-parse", "HEAD")
    (repo / "app.py").write_text("print('hi')\nprint('bye')\n")
    git("add", "app.py")
    git("commit", "-q", "-m", "head")
    head_sha = git_out("rev-parse", "HEAD")

    # No `runner=` injected: exercises the real `partial(subprocess.run, ...)` path.
    rc = run_review(base_sha, head_sha, str(repo), prepare=True)
    assert rc == 0

    ws = _sidecar_ws(str(repo))
    plan = json.loads((ws.runs / "review_plan.json").read_text())
    assert {e["path"] for e in plan} == {"app.py"}


def test_finding_outside_every_hunk_dropped_as_outside_diff(tmp_path, monkeypatch):
    # A real head file with 999 lines, a unique marker at line 999 — far outside the
    # 3-line diff hunk `_diff_for` describes, so the position gate's whole-file rung
    # relocates it there and then drops it for falling outside every hunk.
    head_text = "\n".join([f"line {i}" for i in range(1, 999)] + ["unique marker line"]) + "\n"
    monkeypatch.setattr(
        subprocess, "run",
        _fake_run_for({"app.py": _diff_for("app.py")}, head_texts={"app.py": head_text}),
    )
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 999, "unreachable line", "sqli")])
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_findings"] == []
    assert any(d["reason"] == "outside-diff" for d in ledger["dropped"])


def test_reflection_retraction_removes_a_live_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])

    from sec_overlay.reflection import RETRACTED_REASON, ReflectionRetraction

    def fake_apply_verdict(findings, verdict, *, path):
        retraction = ReflectionRetraction(path, 2, findings[0].rule_id, RETRACTED_REASON, "sanitized upstream")
        return [], [retraction]

    monkeypatch.setattr(cli, "apply_verdict", fake_apply_verdict)
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_findings"] == []
    assert len(ledger["reflection_retractions"]) == 1
    assert ledger["reflection_retractions"][0]["reason"] == RETRACTED_REASON


def test_reflection_failure_for_one_file_leaves_other_files_unaffected(tmp_path, monkeypatch):
    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    _record_return(str(tmp_path), "other.py",
                    calls=[_code_comment("other.py", 2, "sql injection", "sqli")])

    def fake_apply_verdict(findings, verdict, *, path):
        if path == "app.py":
            raise RuntimeError("boom")
        return findings, []

    monkeypatch.setattr(cli, "apply_verdict", fake_apply_verdict)
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["reflection_skipped"]) == 1
    assert ledger["reflection_skipped"][0]["path"] == "app.py"
    assert {rf["path"] for rf in ledger["review_findings"]} == {"app.py", "other.py"}


def test_finding_on_an_unreflected_path_survives(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])

    from sec_overlay.models import Finding, FindingStatus, Severity

    ghost = Finding(
        id="ghost-1", rule_id="review:sqli", cls="sqli", status=FindingStatus.RAW,
        severity=Severity.MEDIUM, file="ghost.py", line=1, message="orphaned finding",
    )
    real_gate = cli.review_position_gate

    def fake_gate(findings, hunks_by_path, file_text_by_path):
        kept, dropped, declines = real_gate(findings, hunks_by_path, file_text_by_path)
        return [*kept, ghost], dropped, declines

    monkeypatch.setattr(cli, "review_position_gate", fake_gate)
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert any(rf["path"] == "ghost.py" for rf in ledger["review_findings"])


def test_thread_safety_finding_ships_needs_deployment_testing_end_to_end(tmp_path, monkeypatch):
    """Composed proof (03-07): Task 1's ledger wiring + Task 2's disposition ladder together."""
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "unsynchronized shared counter", "thread-safety")])
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="general")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["review_findings"]) == 1
    assert ledger["review_findings"][0]["disposition"] == "needs-deployment-testing"
    assert ledger["review_findings"][0]["defect_class"] == "thread-safety"


def test_file_with_no_recorded_return_is_skipped_and_run_still_exits_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_findings"] == []
    assert len(ledger["review_source_skipped"]) == 1
    assert ledger["review_source_skipped"][0]["path"] == "app.py"


def test_stale_base_head_return_is_refused_and_ledgered(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py", base="c" * 40, head="d" * 40,
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_findings"] == []
    assert len(ledger["review_source_skipped"]) == 1


def test_unparseable_return_skips_one_file_leaves_others_intact(tmp_path, monkeypatch):
    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    ws = _sidecar_ws(str(tmp_path))
    ws.ensure()
    envelope = json.dumps({"base": _BASE_SHA, "head": _HEAD_SHA, "response": "not-json"})
    record_agent_return(ws, agent_label("other.py"), envelope)

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["review_source_skipped"]) == 1
    assert ledger["review_source_skipped"][0]["path"] == "other.py"
    assert len(ledger["review_findings"]) == 1
    assert ledger["review_findings"][0]["path"] == "app.py"


def test_zero_skips_still_renders_review_source_skipped_heading(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_source_skipped"] == []
    report_text = ws.report_path.read_text()
    assert "## Review source skipped" in report_text
    assert "No file's review source was skipped." in report_text


def test_exit_codes_unchanged_invalid_ref_partial_seal_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))

    rc_invalid = run_review("-rf", _HEAD_SHA, str(tmp_path), profile="security")
    assert rc_invalid == 2

    def failing_diff(cmd, capture_output, text, check, **kwargs):
        if "--unified=3" in cmd:
            raise RuntimeError("boom")
        return _fake_run_for({"app.py": _diff_for("app.py")})(
            cmd, capture_output, text, check, **kwargs
        )

    monkeypatch.setattr(subprocess, "run", failing_diff)
    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    rc_partial = run_review(_BASE_SHA, _HEAD_SHA, str(partial_root), profile="security")
    assert rc_partial == 3

    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    complete_root = tmp_path / "complete"
    complete_root.mkdir()
    rc_complete = run_review(_BASE_SHA, _HEAD_SHA, str(complete_root), profile="security")
    assert rc_complete == 0


# --- WR-01: --root existence guard (06-01) -----------------------------------------------


def test_run_review_rejects_a_nonexistent_root_with_exit_2(tmp_path, capsys):
    """WR-01: a missing `--root` must exit 2 with one stderr line, never raise."""
    missing = tmp_path / "does-not-exist"
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(missing), profile="security")
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err
    assert str(missing) in err


def test_run_review_rejects_an_empty_root_with_exit_2(tmp_path, capsys):
    """WR-01: an empty `--root` string exits 2 through the same guard."""
    rc = run_review(_BASE_SHA, _HEAD_SHA, "", profile="security")
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err


def test_run_review_rejects_a_file_as_root_with_exit_2(tmp_path, capsys):
    """WR-01: a regular file (wrong type, not missing) exits 2 through the same guard."""
    a_file = tmp_path / "not-a-directory.txt"
    a_file.write_text("x")
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(a_file), profile="security")
    assert rc == 2
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err
    assert str(a_file) in err
