"""Live-source tests: the review verb wired to real findings, end to end (03-06 Task 3)."""

import json
import subprocess
from functools import partial

from sec_overlay import cli
from sec_overlay.cli import main, run_review
from sec_overlay.reflection import REFUSED_REASON, RETRACTED_REASON, reflection_label
from sec_overlay.repo_memory import RepoMemory
from sec_overlay.review_agent import _stable_finding_id, agent_label
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


def _record_verdict(root, path, verdict, *, base=_BASE_SHA, head=_HEAD_SHA):
    """Record a review-filter verdict envelope for `path` (production disk format)."""
    ws = _sidecar_ws(root)
    ws.ensure()
    envelope = json.dumps({"base": base, "head": head, "verdict": verdict})
    record_agent_return(ws, reflection_label(path), envelope)


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


def test_reflection_failure_for_one_file_leaves_other_files_unaffected(tmp_path, monkeypatch):
    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    _record_return(str(tmp_path), "other.py",
                    calls=[_code_comment("other.py", 2, "sql injection", "sqli")])
    # app.py's verdict is unreadable (invalid JSON) → reflection skip; other.py
    # records a valid empty verdict (retract nothing) → its finding survives.
    ws = _sidecar_ws(tmp_path)
    ws.ensure()
    record_agent_return(ws, reflection_label("app.py"), "not-json")
    _record_verdict(str(tmp_path), "other.py", {})

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["reflection_skipped"]) == 1
    assert ledger["reflection_skipped"][0]["path"] == "app.py"
    assert {rf["path"] for rf in ledger["review_findings"]} == {"app.py", "other.py"}


def test_recorded_verdict_retracts_a_nonprotected_finding_end_to_end(tmp_path, monkeypatch):
    """Task 9 (REQ-P6): a recorded review-filter verdict retracts a live finding
    through `run_review` with no monkeypatch of `apply_verdict` — the real
    recorded-verdict source drives the retraction."""
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    fid = _stable_finding_id("review", "app.py", 2, "sqli")
    _record_verdict(str(tmp_path), "app.py", {fid: "sanitized upstream"})

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert ledger["review_findings"] == []
    assert len(ledger["reflection_retractions"]) == 1
    assert ledger["reflection_retractions"][0]["reason"] == RETRACTED_REASON


def test_recorded_verdict_refuses_a_protected_class_finding_end_to_end(tmp_path, monkeypatch):
    """Task 9 (REQ-P6): a verdict naming a protected-class finding is refused —
    the finding stays kept and the refusal is ledgered, never silently dropped."""
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "unsynchronized shared state", "concurrency")])
    fid = _stable_finding_id("review", "app.py", 2, "concurrency")
    _record_verdict(str(tmp_path), "app.py", {fid: "looks harmless"})

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["review_findings"]) == 1
    assert ledger["review_findings"][0]["id"] == fid
    assert ledger["review_findings"][0]["rule_id"] == "review.concurrency"
    assert len(ledger["reflection_retractions"]) == 1
    assert ledger["reflection_retractions"][0]["reason"] == REFUSED_REASON


def test_missing_verdict_records_a_reflection_skip_not_a_silent_keep(tmp_path, monkeypatch):
    """Task 9 (REQ-P6): a reviewable file with findings but no recorded verdict
    fails open — the finding survives AND a reflection_skipped entry is ledgered
    (never a silent keep-all)."""
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security")
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    ledger = json.loads((ws.artifacts / "review_ledger.json").read_text())
    assert len(ledger["review_findings"]) == 1
    assert len(ledger["reflection_skipped"]) == 1
    assert ledger["reflection_skipped"][0]["path"] == "app.py"


def test_prepare_reflection_writes_a_filter_prompt_per_file_with_findings(tmp_path, monkeypatch):
    """Task 9 (REQ-P6): `--prepare-reflection` renders a review-filter prompt for
    each file with post-profile kept findings into runs/reflection_prompts/."""
    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])

    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path),
               "--prepare-reflection"])
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    plan = json.loads((ws.runs / "reflection_plan.json").read_text())
    assert {e["path"] for e in plan} == {"app.py"}
    for entry in plan:
        prompt_text = (ws.runs / "reflection_prompts" / f"{entry['agent_label']}.md").read_text()
        assert "{{" not in prompt_text


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


def _git_spy(monkeypatch):
    """Install a recording spy over `subprocess.run` and return its call list.

    `run_review` resolves its runner as `runner or subprocess.run`, so with no
    injected runner every git call lands here. The spy raises so a guard that
    fires late fails loudly; an empty call list proves the guard ran first.
    """
    calls: list = []

    def spy(*args, **kwargs):
        calls.append(args)
        raise AssertionError("WR-01: git ran before the --root guard")

    monkeypatch.setattr(subprocess, "run", spy)
    return calls


def test_run_review_rejects_a_nonexistent_root_with_exit_2(tmp_path, capsys, monkeypatch):
    """WR-01: a missing `--root` must exit 2 with one stderr line, never raise."""
    git_calls = _git_spy(monkeypatch)
    missing = tmp_path / "does-not-exist"
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(missing), profile="security")
    assert rc == 2
    assert git_calls == []
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err
    assert str(missing) in err


def test_run_review_rejects_an_empty_root_with_exit_2(tmp_path, capsys, monkeypatch):
    """WR-01: an empty `--root` string exits 2 through the same guard."""
    git_calls = _git_spy(monkeypatch)
    rc = run_review(_BASE_SHA, _HEAD_SHA, "", profile="security")
    assert rc == 2
    assert git_calls == []
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err


def test_run_review_rejects_a_file_as_root_with_exit_2(tmp_path, capsys, monkeypatch):
    """WR-01: a regular file (wrong type, not missing) exits 2 through the same guard."""
    git_calls = _git_spy(monkeypatch)
    a_file = tmp_path / "not-a-directory.txt"
    a_file.write_text("x")
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(a_file), profile="security")
    assert rc == 2
    assert git_calls == []
    err = capsys.readouterr().err.strip()
    assert err.startswith("error:")
    assert "--root" in err
    assert str(a_file) in err


# --- D-03: --workspace override (06-01) --------------------------------------------------


def test_run_review_uses_the_workspace_override_when_supplied(tmp_path):
    """An explicit `workspace=` writes artifacts there, not the --root sidecar."""
    target = tmp_path / "repo"
    target.mkdir()
    custom_ws = tmp_path / "custom-workspace"
    runner = _fake_run_for({"app.py": _diff_for("app.py")})

    rc = run_review(
        _BASE_SHA, _HEAD_SHA, str(target), runner=runner, workspace=str(custom_ws), profile="security"
    )
    assert rc == 0
    assert (custom_ws / "artifacts" / "coverage_manifest.json").is_file()
    # The per-repo sidecar under --root must stay untouched by the override.
    assert not _sidecar_ws(str(target)).artifacts.exists()


def test_run_review_falls_back_to_the_repo_sidecar_when_workspace_is_absent(tmp_path):
    """No `workspace=` keeps the existing per-repo sidecar resolution (regression guard)."""
    target = tmp_path / "repo"
    target.mkdir()
    runner = _fake_run_for({"app.py": _diff_for("app.py")})

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(target), runner=runner, profile="security")
    assert rc == 0
    assert (_sidecar_ws(str(target)).artifacts / "coverage_manifest.json").is_file()


def test_tiny_token_budget_seals_partial_marks_skips_and_exits_zero(tmp_path, monkeypatch):
    """Task 12 (REQ-P4/D4/D5): a budget that admits the first file but not the second
    seals `partial`, fails the over-budget file with note `skipped(budget)`, sets the
    manifest `budget_exceeded` flag, yet exits 0 (a budget stop with coverage is not a
    run failure)."""
    from sec_overlay.review_budget import BUDGET_SKIP_NOTE, estimate_review_cost

    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    _record_return(str(tmp_path), "other.py",
                    calls=[_code_comment("other.py", 2, "sql injection", "sqli")])

    # Admit exactly one file: budget between one and two file-costs, and high
    # enough that each single file clears the P4a fraction cap (0.8 * budget).
    one_cost = estimate_review_cost(_diff_for("app.py"))
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security",
                    token_budget=2 * one_cost - 1)
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    manifest = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    assert manifest["seal"] == "partial"
    assert manifest["budget_exceeded"] is True
    skipped = [f for f in manifest["files"] if f["note"] == BUDGET_SKIP_NOTE]
    assert len(skipped) == 1
    assert skipped[0]["state"] == "failed"


def test_zero_token_budget_reviews_every_file(tmp_path, monkeypatch):
    """Task 12: budget 0 means unlimited — every file completes, seal stays complete."""
    diffs = {"app.py": _diff_for("app.py"), "other.py": _diff_for("other.py")}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])
    _record_return(str(tmp_path), "other.py",
                    calls=[_code_comment("other.py", 2, "sql injection", "sqli")])

    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security", token_budget=0)
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    manifest = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    assert manifest["seal"] == "complete"
    assert manifest["budget_exceeded"] is False


def test_prepare_records_per_file_token_estimate(tmp_path, monkeypatch):
    """Task 12 (D10): the prepare plan carries a per-file `token_estimate`."""
    from sec_overlay.review_budget import estimate_review_cost

    monkeypatch.setattr(subprocess, "run", _fake_run_for({"app.py": _diff_for("app.py")}))
    rc = main(["review", "--base", _BASE_SHA, "--head", _HEAD_SHA, "--root", str(tmp_path),
               "--prepare"])
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    plan = json.loads((ws.runs / "review_plan.json").read_text())
    assert plan[0]["token_estimate"] == estimate_review_cost(_diff_for("app.py"))


def test_file_over_token_fraction_cap_excluded_not_reviewed(tmp_path, monkeypatch):
    """Task 12 (REQ-P4a): a file whose estimate alone exceeds 0.8 * budget is excluded
    before review — it never enters the coverage manifest — while a normal file under the
    cap is still reviewed and the seal stays complete."""
    big_body = "x" * 40000
    big_diff = (
        "diff --git a/big.py b/big.py\n"
        "index 1111111..2222222 100644\n"
        "--- a/big.py\n+++ b/big.py\n"
        "@@ -1,1 +1,2 @@\n import os\n+" + big_body + "\n"
    )
    diffs = {"app.py": _diff_for("app.py"), "big.py": big_diff}
    monkeypatch.setattr(subprocess, "run", _fake_run_for(diffs))
    _record_return(str(tmp_path), "app.py",
                    calls=[_code_comment("app.py", 2, "sql injection", "sqli")])

    # budget high enough that app.py clears 0.8*budget but big.py does not.
    rc = run_review(_BASE_SHA, _HEAD_SHA, str(tmp_path), profile="security",
                    token_budget=100000)
    assert rc == 0

    ws = _sidecar_ws(tmp_path)
    manifest = json.loads((ws.artifacts / "coverage_manifest.json").read_text())
    paths = [f["path"] for f in manifest["files"]]
    assert "app.py" in paths
    assert "big.py" not in paths
    assert manifest["seal"] == "complete"


def test_review_workspace_override_permits_a_second_profile_without_weakening_the_resume_guard(
    tmp_path,
):
    """A `workspace=` override must not bypass the SCALE-03 resume-identity guard."""
    target = tmp_path / "repo"
    target.mkdir()
    custom_ws = tmp_path / "custom-workspace"
    runner = _fake_run_for({"app.py": _diff_for("app.py")})

    rc1 = run_review(
        _BASE_SHA,
        _HEAD_SHA,
        str(target),
        runner=runner,
        workspace=str(custom_ws),
        model="model-a",
        profile="security",
    )
    assert rc1 == 0

    rc2 = run_review(
        _BASE_SHA,
        _HEAD_SHA,
        str(target),
        runner=runner,
        workspace=str(custom_ws),
        model="model-b",
        profile="security",
    )
    assert rc2 == 2


def _two_commit_repo(repo):
    """Build a real repo with two commits changing app.py; return (base_sha, head_sha)."""
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
    return base_sha, head_sha


def test_commit_mode_diffs_parent_to_commit(tmp_path):
    """`--commit <sha>` resolves base=sha^ and head=sha — the plan entry pins the
    parent and the commit SHAs, so the review scopes to exactly that commit."""
    repo = tmp_path / "repo"
    base_sha, head_sha = _two_commit_repo(repo)

    rc = main(["review", "--commit", head_sha, "--root", str(repo), "--prepare"])
    assert rc == 0

    ws = _sidecar_ws(str(repo))
    plan = json.loads((ws.runs / "review_plan.json").read_text())
    assert [e["path"] for e in plan] == ["app.py"]
    assert plan[0]["base"] == base_sha
    assert plan[0]["head"] == head_sha


def test_commit_with_base_exits_2(tmp_path):
    """`--commit` and `--base` are mutually exclusive: supplying both exits 2."""
    repo = tmp_path / "repo"
    _base_sha, head_sha = _two_commit_repo(repo)

    rc = main(
        ["review", "--commit", head_sha, "--base", head_sha, "--root", str(repo), "--prepare"]
    )
    assert rc == 2


def test_workspace_dirty_lists_uncommitted_changes(tmp_path):
    """`--workspace-dirty` scopes the review to the working tree: a staged
    modification, an unstaged modification, and an untracked file all appear."""
    repo = tmp_path / "repo"
    _two_commit_repo(repo)

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)

    (repo / "app.py").write_text("print('hi')\nprint('bye')\nprint('dirty')\n")
    git("add", "app.py")  # staged modification
    (repo / "new.py").write_text("x = 1\n")  # untracked

    rc = main(["review", "--workspace-dirty", "--root", str(repo), "--prepare"])
    assert rc == 0

    ws = _sidecar_ws(str(repo))
    plan = json.loads((ws.runs / "review_plan.json").read_text())
    assert {e["path"] for e in plan} == {"app.py", "new.py"}
