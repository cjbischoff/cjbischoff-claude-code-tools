# sec-overlay Driven Invocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one `/sec-overlay:audit` command and a small `run.py` driver so a repo (or several) is audited without hand token-substitution, every phase leaves a receipt, an audit never writes into the tree it audits, and multiple repos correlate into unified docs in the invocation directory.

**Architecture:** A new `sec_overlay/run.py` holds pure helpers (`write_env`, `receipt`, `fence`, `infer_role`, `synthesize_manifest`) plus a `drive` loop that reuses the existing `driver.run_audit`. `run_audit` and `run_deterministic_phase` gain one optional `on_complete` callback fired just before each `record_stage`, so fence+receipt run before a phase is marked done. A one-line prompt path edit fixes the O-65 gate collision. A `commands/audit.md` file documents routing (1 repo → audit; N repos → audit each then correlate via the existing `python -m sec_overlay.correlate`).

**Tech Stack:** Python 3.13, stdlib-only (no new runtime deps), `uv run pytest`, `ruff`, `ty`. Markdown command/README files. Git worktree fence via `git status --porcelain`.

**Spec:** `docs/superpowers/specs/2026-08-16-sec-overlay-invocation-design.md`

## Global Constraints

- **Stdlib-only core.** No new runtime dependency in `pyproject.toml`. Dev deps stay pytest/ruff/ty only.
- **TDD.** Every executable change ships its failing-first test in the same commit.
- **Version bump.** This is a `feat` → minor bump. The **first** shipping commit (Task 1) bumps `plugins/sec-overlay/.claude-plugin/plugin.json` from `1.30.3` to `1.31.0`. Later commits in this PR do not re-bump.
- **Plugin CHANGELOG.** Every commit that touches a plugin-internal file stages `plugins/sec-overlay/CHANGELOG.md` with a line under an `Unreleased`/`Added` (or `Fixed`) block — the pre-commit hook rejects a plugin-internal commit that does not.
- **Docs-track-code (hook-enforced).** For every staged file, if its folder holds a tracked `README.md`, stage that `README.md` too. Concretely:
  - a `helpers/sec_overlay/*.py` change → stage `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`;
  - a `helpers/tests/*.py` change → stage `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`;
  - an `agents/*.md` change → stage `plugins/sec-overlay/skills/sec-overlay/agents/README.md`;
  - a new `commands/*.md` file → stage `plugins/sec-overlay/skills/sec-overlay/commands/README.md`.
  A one-line note in the README satisfies the rule.
- **Paths.** All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`. All plan paths below are relative to that directory unless prefixed with `plugins/` or `docs/`.
- **Git.** Branch `feat/sec-overlay-invocation`. Conventional Commits. Stage explicit paths only — never `git add -A`/`.`/`-a`, never `--no-verify`. No `Co-Authored-By` trailer.
- **Plugin scripts must not reference paths outside the plugin directory.** `run.py` uses only `sec_overlay.*` imports and paths under the workspace/target.

---

## File Structure

- Create `helpers/sec_overlay/run.py` — driver helpers + `drive` loop (Tasks 1–6).
- Create `helpers/tests/test_run.py` — tests for the above (Tasks 1–6).
- Modify `helpers/sec_overlay/driver.py` — add `on_complete` callback to `run_deterministic_phase` and `run_audit` (Task 6).
- Modify `helpers/tests/test_driver.py` — test the callback fires (Task 6).
- Modify `agents/redteam-adversary.md` — one path string, O-65 (Task 7).
- Create `helpers/tests/test_redteam_gate_paths.py` — O-65 regression (Task 7).
- Create `commands/audit.md` and `commands/README.md` — command surface (Task 8).
- Create `helpers/tests/test_command_audit.py` — command-content invariants (Task 8).
- Modify `plugins/sec-overlay/.claude-plugin/plugin.json` — version bump (Task 1).
- Modify `plugins/sec-overlay/CHANGELOG.md` — one entry per commit.
- Modify folder `README.md`s per Global Constraints.

---

## Task 1: `fence` — working-tree guard (O-68)

**Files:**
- Create: `helpers/sec_overlay/run.py`
- Test: `helpers/tests/test_run.py`

**Interfaces:**
- Produces: `WorkingTreeFenceError(RuntimeError)`; `fence(target: str | Path, baseline: str, *, runner=subprocess.run) -> None` — runs `git -C <target> status --porcelain`; raises `WorkingTreeFenceError` naming the delta lines when output differs from `baseline`; returns `None` on match.

- [ ] **Step 1: Write the failing test**

```python
# helpers/tests/test_run.py
import subprocess
from pathlib import Path

import pytest

from sec_overlay.run import WorkingTreeFenceError, fence


def _fake_runner(stdout: str):
    def run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
    return run


def test_fence_passes_when_tree_matches_baseline(tmp_path):
    baseline = "?? untracked.txt\n"
    fence(tmp_path, baseline, runner=_fake_runner("?? untracked.txt\n"))


def test_fence_raises_and_names_new_delta(tmp_path):
    baseline = ""
    with pytest.raises(WorkingTreeFenceError) as exc:
        fence(tmp_path, baseline, runner=_fake_runner(" M src/app.go\n"))
    assert "src/app.go" in str(exc.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.run'`.

- [ ] **Step 3: Write minimal implementation**

```python
# helpers/sec_overlay/run.py
"""Driver helpers for a sec-overlay audit run.

Pure functions the command/orchestrator composes: a working-tree fence, a
per-phase receipt writer, a one-time token env writer, scan-profile role
inference, and manifest synthesis, plus the single-repo ``drive`` loop.
"""

import subprocess
from pathlib import Path


class WorkingTreeFenceError(RuntimeError):
    """The audited tree changed during the run. The run stops loudly."""


def fence(target, baseline, *, runner=subprocess.run):
    """Stop the run if the audited working tree changed since the baseline.

    Args:
        target: Path to the audited repository.
        baseline: ``git status --porcelain`` output captured when the run opened.
        runner: Injectable process runner (defaults to ``subprocess.run``).

    Raises:
        WorkingTreeFenceError: The current porcelain status differs from the
            baseline; the message names the added/removed status lines.
    """
    proc = runner(
        ["git", "-C", str(target), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    if proc.stdout == baseline:
        return
    before = set(baseline.splitlines())
    after = set(proc.stdout.splitlines())
    delta = sorted((after - before) | (before - after))
    raise WorkingTreeFenceError(
        "audited tree changed during the run: " + "; ".join(delta)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q && uv run ruff check sec_overlay/run.py && uv run ty check`
Expected: PASS, no lint/type errors.

- [ ] **Step 5: Commit**

Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `"version"` to `1.31.0`. Add a `## [1.31.0]` `### Added` entry to `plugins/sec-overlay/CHANGELOG.md` ("Add run.py driver working-tree fence."). Add a one-line row to both `helpers/sec_overlay/README.md` and `helpers/tests/README.md` naming `run.py` / `test_run.py`.

```bash
git checkout -b feat/sec-overlay-invocation
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add run.py working-tree fence"
```

---

## Task 2: `receipt` — per-phase receipt writer (O-67, O-69)

**Files:**
- Modify: `helpers/sec_overlay/run.py`
- Test: `helpers/tests/test_run.py`

**Interfaces:**
- Consumes: `Workspace` (has `.kb` property → `<root>/kb`).
- Produces: `receipt(ws: Workspace, phase: str, *, stdout: str = "", artifacts: list[str] | None = None, counts: dict | None = None) -> Path` — writes `<ws.kb>/receipts/<phase>.json` with keys `phase`, `stdout`, `artifacts`, `counts`; returns the path.

- [ ] **Step 1: Write the failing test**

```python
# add to helpers/tests/test_run.py
import json

from sec_overlay.run import receipt
from sec_overlay.workspace import Workspace


def test_receipt_writes_counts_even_when_stdout_empty(tmp_path):
    ws = Workspace(root=tmp_path)
    ws.ensure()
    path = receipt(ws, "findings-gate", stdout="", counts={"findings": 3})
    assert path == ws.kb / "receipts" / "findings-gate.json"
    body = json.loads(path.read_text())
    assert body["phase"] == "findings-gate"
    assert body["stdout"] == ""
    assert body["counts"] == {"findings": 3}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py::test_receipt_writes_counts_even_when_stdout_empty -q`
Expected: FAIL — `ImportError: cannot import name 'receipt'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/run.py
import json  # add to the existing imports at the top

from sec_overlay.workspace import Workspace  # add to the existing imports


def receipt(ws: Workspace, phase, *, stdout="", artifacts=None, counts=None):
    """Persist a phase receipt so no stage advances without one on disk.

    Args:
        ws: The audit workspace.
        phase: The phase name (the receipt file stem).
        stdout: Captured phase stdout, verbatim (empty for in-process phases).
        artifacts: Paths the phase produced, as strings.
        counts: Small numeric summary (e.g. ``{"findings": 3}``).

    Returns:
        The path written: ``<ws.kb>/receipts/<phase>.json``.
    """
    out_dir = ws.kb / "receipts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{phase}.json"
    path.write_text(
        json.dumps(
            {
                "phase": phase,
                "stdout": stdout,
                "artifacts": artifacts or [],
                "counts": counts or {},
            },
            indent=2,
        )
    )
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q && uv run ruff check sec_overlay/run.py && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

Add a `### Added` line to `plugins/sec-overlay/CHANGELOG.md` ("Add per-phase receipt writer.").

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add per-phase receipt writer"
```

---

## Task 3: `write_env` — one-time token env (kills hand substitution)

**Files:**
- Modify: `helpers/sec_overlay/run.py`
- Test: `helpers/tests/test_run.py`

**Interfaces:**
- Produces: `write_env(ws: Workspace, target: str, scope: str, sha: str) -> Path` — writes `<ws.root>/run.env` with `KEY=value` lines for `TARGET`, `WORKSPACE`, `SHA`, `SCAN_SCOPE`, `REPO_ROOT`; returns the path.

- [ ] **Step 1: Write the failing test**

```python
# add to helpers/tests/test_run.py
from sec_overlay.run import write_env


def test_write_env_writes_all_tokens(tmp_path):
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    path = write_env(ws, target="/repos/app", scope=".", sha="abc123")
    assert path == ws.root / "run.env"
    lines = dict(
        line.split("=", 1) for line in path.read_text().splitlines() if "=" in line
    )
    assert lines["TARGET"] == "/repos/app"
    assert lines["WORKSPACE"] == str(ws.root)
    assert lines["SHA"] == "abc123"
    assert lines["SCAN_SCOPE"] == "."
    assert lines["REPO_ROOT"] == "/repos/app"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py::test_write_env_writes_all_tokens -q`
Expected: FAIL — `ImportError: cannot import name 'write_env'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/run.py
def write_env(ws: Workspace, target, scope, sha):
    """Resolve the substitution tokens once and write ``run.env``.

    Agent phases read tokens from this file instead of the orchestrator
    re-substituting them by hand on every spawn.

    Args:
        ws: The audit workspace.
        target: Path to the audited repository.
        scope: Scanned scope relative to the repo root ("." for the whole repo).
        sha: The pinned target SHA for this pass.

    Returns:
        The path written: ``<ws.root>/run.env``.
    """
    path = ws.root / "run.env"
    path.write_text(
        f"TARGET={target}\n"
        f"WORKSPACE={ws.root}\n"
        f"SHA={sha}\n"
        f"SCAN_SCOPE={scope}\n"
        f"REPO_ROOT={target}\n"
    )
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q && uv run ruff check sec_overlay/run.py && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

Add a `### Added` CHANGELOG line ("Add run.env token writer.").

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add run.env token writer"
```

---

## Task 4: `infer_role` — scan-profile → correlation role (net-new)

**Files:**
- Modify: `helpers/sec_overlay/run.py`
- Test: `helpers/tests/test_run.py`

**Interfaces:**
- Consumes: `ScanProfile` (fields: `frameworks`, `subsystems`, `attack_surface`) from `sec_overlay.profile`; `ROLES = ("rbac-source", "service-enforcer", "infra")` from `sec_overlay.correlate.manifest`.
- Produces: `infer_role(profile: ScanProfile) -> str` — returns one of `ROLES`; `rbac-source` when auth/authz machinery is named, else `service-enforcer` when network request handlers are exposed, else `infra` (the default when ambiguous).

- [ ] **Step 1: Write the failing test**

```python
# add to helpers/tests/test_run.py
from sec_overlay.profile import ScanProfile
from sec_overlay.run import infer_role


def _profile(**kw) -> ScanProfile:
    base = dict(
        languages=[], frameworks=[], entrypoints=[], runnable=[],
        attack_surface=[], sast_plan=[], agents_to_spawn=[], budget_hint="",
        notes="", subsystems=[], attack_surface_evidence=[], scan_options={},
    )
    base.update(kw)
    return ScanProfile(**base)


def test_infer_role_rbac_source_from_auth_subsystem():
    p = _profile(subsystems=["identity", "rbac-policy"])
    assert infer_role(p) == "rbac-source"


def test_infer_role_service_enforcer_from_network_surface():
    p = _profile(attack_surface=["gRPC service", "HTTP handler"])
    assert infer_role(p) == "service-enforcer"


def test_infer_role_defaults_to_infra_when_ambiguous():
    p = _profile(subsystems=["batch-jobs"], attack_surface=["config files"])
    assert infer_role(p) == "infra"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -k infer_role -q`
Expected: FAIL — `ImportError: cannot import name 'infer_role'`.

Note: confirm the `ScanProfile` constructor field names by reading `sec_overlay/profile.py` before writing the test; adjust the `_profile` base dict to match the actual dataclass fields if they differ.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/run.py
from sec_overlay.correlate.manifest import ROLES  # add to imports
from sec_overlay.profile import ScanProfile  # add to imports

_RBAC_SIGNALS = ("auth", "rbac", "iam", "policy", "interceptor", "middleware", "identity")
_SERVICE_SIGNALS = ("grpc", "http", "service", "handler", "endpoint", "network")


def infer_role(profile: ScanProfile) -> str:
    """Infer a correlation role from a repo's scan profile.

    Under-correlating is safer than over-correlating: a wrong ``rbac-source``
    label fabricates a ``control-enforces`` edge and drives a false verdict, so
    ambiguity falls through to ``infra``.

    Args:
        profile: The recon-produced scan profile.

    Returns:
        One of :data:`ROLES`.
    """
    rbac_text = " ".join(profile.subsystems + profile.frameworks + profile.attack_surface).lower()
    if any(sig in rbac_text for sig in _RBAC_SIGNALS):
        return "rbac-source"
    surface_text = " ".join(profile.attack_surface).lower()
    if any(sig in surface_text for sig in _SERVICE_SIGNALS):
        return "service-enforcer"
    assert "infra" in ROLES  # invariant: the default is a valid role
    return "infra"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q && uv run ruff check sec_overlay/run.py && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

Add a `### Added` CHANGELOG line ("Add scan-profile role inference.").

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add scan-profile role inference"
```

---

## Task 5: `synthesize_manifest` — build the correlation manifest

**Files:**
- Modify: `helpers/sec_overlay/run.py`
- Test: `helpers/tests/test_run.py`

**Interfaces:**
- Consumes: `validate_manifest(d: dict) -> list[str]` and `ROLES` from `sec_overlay.correlate.manifest`.
- Produces: `synthesize_manifest(product: str, members: list[dict]) -> dict` — each `members` entry is `{"slug", "repo_root", "scan_scope", "role"}`; returns a manifest dict `{"product", "members"}` that passes `validate_manifest` (raises `ValueError` if it does not).

- [ ] **Step 1: Write the failing test**

```python
# add to helpers/tests/test_run.py
from sec_overlay.correlate.manifest import validate_manifest
from sec_overlay.run import synthesize_manifest


def test_synthesize_manifest_is_valid_and_keys_distinct():
    members = [
        {"slug": "app", "repo_root": "/repos/app", "scan_scope": "svc-a", "role": "service-enforcer"},
        {"slug": "app", "repo_root": "/repos/app", "scan_scope": "svc-b", "role": "infra"},
    ]
    manifest = synthesize_manifest("product-x", members)
    assert validate_manifest(manifest) == []
    keys = {f'{m["slug"]}#{m["scan_scope"]}' for m in manifest["members"]}
    assert keys == {"app#svc-a", "app#svc-b"}


def test_synthesize_manifest_rejects_bad_role():
    import pytest

    with pytest.raises(ValueError):
        synthesize_manifest(
            "p", [{"slug": "a", "repo_root": "/a", "scan_scope": ".", "role": "nonsense"}]
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py -k synthesize_manifest -q`
Expected: FAIL — `ImportError: cannot import name 'synthesize_manifest'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to helpers/sec_overlay/run.py
from sec_overlay.correlate.manifest import validate_manifest  # add to imports


def synthesize_manifest(product: str, members: list[dict]) -> dict:
    """Build a correlation manifest from per-repo members.

    Args:
        product: The product identifier the correlation groups under.
        members: One dict per repo/sub-service with keys ``slug``,
            ``repo_root``, ``scan_scope``, ``role``.

    Returns:
        A manifest dict ready for ``python -m sec_overlay.correlate``.

    Raises:
        ValueError: The synthesized manifest fails ``validate_manifest``.
    """
    manifest = {"product": product, "members": members}
    errs = validate_manifest(manifest)
    if errs:
        raise ValueError("synthesized invalid manifest: " + "; ".join(errs))
    return manifest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_run.py -q && uv run ruff check sec_overlay/run.py && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

Add a `### Added` CHANGELOG line ("Add manifest synthesis for correlation.").

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add manifest synthesis"
```

---

## Task 6: Driver `on_complete` hook + single-repo `drive` loop

**Files:**
- Modify: `helpers/sec_overlay/driver.py:65-94` (add `on_complete` to `run_deterministic_phase`), `driver.py:298-350` (add `on_complete` to `run_audit`, thread it, call it in the agent auto-advance branch)
- Modify: `helpers/sec_overlay/run.py` (add `drive`)
- Test: `helpers/tests/test_driver.py`, `helpers/tests/test_run.py`

**Interfaces:**
- Consumes: `run_audit(ctx, *, table=PHASE_TABLE, on_complete=None) -> str`; `run_deterministic_phase(phase, ctx, *, on_complete=None) -> None`; `fence`, `receipt`, `write_env`, `WorkingTreeFenceError` from Tasks 1–3; `RepoMemory.for_target`, `.workspace`, `.run_status()` from `sec_overlay.repo_memory`; `begin_pass(ws, sha)` from `sec_overlay.state`.
- Produces: `drive(target: str, config: str, *, scope: str = ".", workspace=None, runner=subprocess.run) -> str` — opens/resumes the workspace, snapshots the fence baseline, writes `run.env`, runs `run_audit` with an `on_complete` that fences then writes a receipt before each `record_stage`; returns `run_audit`'s result string.

The `on_complete` callback signature is `Callable[[str], None]`; the driver calls `on_complete(phase.name)` immediately before every `record_stage`. It fences first (halt-before-record on a dirtied tree), then writes the receipt (so the receipt exists before the stage is recorded done — O-67 ordering).

- [ ] **Step 1: Write the failing test (driver hook)**

```python
# add to helpers/tests/test_driver.py
def test_run_audit_calls_on_complete_before_recording(tmp_path):
    from sec_overlay.driver import AuditContext, run_audit
    from sec_overlay.phases import PhaseSpec
    from sec_overlay.workspace import Workspace

    ws = Workspace(root=tmp_path)
    ws.ensure()
    marker = ws.kb / "marker.json"
    marker.write_text("{}")  # single deterministic phase whose output already exists

    from sec_overlay.driver import DETERMINISTIC_ACTIONS

    DETERMINISTIC_ACTIONS["noop"] = lambda ctx: None
    table = (PhaseSpec("noop", "deterministic", (), (lambda w: w.kb / "marker.json",)),)
    ctx = AuditContext(ws=ws, target=str(tmp_path), config="", sha="deadbeef")

    seen: list[str] = []
    result = run_audit(ctx, table=table, on_complete=seen.append)
    assert seen == ["noop"]
    assert result == "AUDIT COMPLETE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_driver.py::test_run_audit_calls_on_complete_before_recording -q`
Expected: FAIL — `TypeError: run_audit() got an unexpected keyword argument 'on_complete'`.

- [ ] **Step 3: Wire the hook in `driver.py`**

In `run_deterministic_phase`, add the parameter and call it just before `record_stage` (line 94):

```python
def run_deterministic_phase(phase: PhaseSpec, ctx: AuditContext, *, on_complete=None) -> None:
    # ... unchanged body through save_state(ctx.ws, state) ...
    if on_complete is not None:
        on_complete(phase.name)
    record_stage(ctx.ws, phase.name)
```

In `run_audit`, add the parameter, pass it through, and call it in the agent auto-advance branch before its `record_stage`:

```python
def run_audit(ctx: AuditContext, *, table: tuple[PhaseSpec, ...] = PHASE_TABLE, on_complete=None) -> str:
    while True:
        phase = next_actionable_phase(table, load_state(ctx.ws))
        if phase is None:
            return "AUDIT COMPLETE"
        if phase.kind == "deterministic":
            run_deterministic_phase(phase, ctx, on_complete=on_complete)
            continue
        distinct_outputs = tuple(p for p in phase.outputs if p not in phase.inputs)
        if distinct_outputs and all(p(ctx.ws).exists() for p in distinct_outputs):
            if on_complete is not None:
                on_complete(phase.name)
            record_stage(ctx.ws, phase.name)
            continue
        # ... unchanged investigate/patch/render_dispatch tail ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_driver.py -q`
Expected: PASS.

- [ ] **Step 5: Write the failing test (drive loop + fence integration)**

```python
# add to helpers/tests/test_run.py
def test_drive_writes_receipt_and_env_and_fences(tmp_path, monkeypatch):
    import subprocess
    from sec_overlay import run as run_mod

    target = tmp_path / "repo"
    target.mkdir()
    ws_root = tmp_path / "ws"

    # git status --porcelain returns clean both at baseline and per phase
    def fake_git(cmd, *a, **k):
        if cmd[:2] == ["git", "-C"] and "status" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeef\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    from sec_overlay.driver import DETERMINISTIC_ACTIONS
    from sec_overlay.phases import PhaseSpec

    DETERMINISTIC_ACTIONS["noop"] = lambda ctx: None
    table = (PhaseSpec("noop", "deterministic", (), ()),)
    monkeypatch.setattr(run_mod, "_PHASE_TABLE", table, raising=False)

    result = run_mod.drive(
        str(target), config="", workspace=str(ws_root), runner=fake_git, table=table
    )
    assert result == "AUDIT COMPLETE"
    assert (ws_root / "run.env").exists()
    assert (ws_root / "kb" / "receipts" / "noop.json").exists()
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_run.py::test_drive_writes_receipt_and_env_and_fences -q`
Expected: FAIL — `AttributeError: module 'sec_overlay.run' has no attribute 'drive'`.

- [ ] **Step 7: Implement `drive` in `run.py`**

```python
# add to helpers/sec_overlay/run.py
from sec_overlay.driver import AuditContext, run_audit  # add to imports
from sec_overlay.phases import PHASE_TABLE  # add to imports
from sec_overlay.state import begin_pass, load_state  # add to imports
from sec_overlay.workspace import Workspace  # already imported in Task 2


def drive(target, config, *, scope=".", workspace=None, runner=subprocess.run, table=PHASE_TABLE):
    """Audit one repository, driving every phase with a fence and a receipt.

    Opens (or resumes) the workspace, pins the SHA, snapshots the fence
    baseline, writes ``run.env`` once, then walks the phase table. Before each
    stage is recorded done, the tree is fenced and a receipt is written.

    Args:
        target: Path to the audited repository.
        config: Semgrep/ruleset config path for scanning phases.
        scope: Scanned scope relative to the repo root.
        workspace: Explicit workspace root; ``None`` uses the target sidecar.
        runner: Injectable process runner (git calls).
        table: Phase table to walk (defaults to ``PHASE_TABLE``).

    Returns:
        ``run_audit``'s result: ``"AUDIT COMPLETE"`` or the next dispatch block.
    """
    ws = Workspace(root=workspace) if workspace else _target_workspace(target)
    ws.ensure()
    sha = runner(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    status = load_state(ws)
    if not status.stages:
        begin_pass(ws, sha)
    baseline = runner(
        ["git", "-C", str(target), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    write_env(ws, target, scope, sha)
    ctx = AuditContext(ws=ws, target=str(target), config=config, sha=sha)

    def on_complete(phase_name: str) -> None:
        fence(target, baseline, runner=runner)
        receipt(
            ws,
            phase_name,
            counts={"findings": len(list(ws.findings_dir.glob("F-*.json")))},
        )

    return run_audit(ctx, table=table, on_complete=on_complete)
```

Add a small helper for the sidecar workspace (reuse `RepoMemory` so the sidecar path stays canonical):

```python
# add to helpers/sec_overlay/run.py
from sec_overlay.repo_memory import RepoMemory  # add to imports


def _target_workspace(target) -> Workspace:
    """Return the in-repo sidecar workspace for a target (via RepoMemory)."""
    return RepoMemory.for_target(str(target)).workspace
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_run.py tests/test_driver.py -q && uv run ruff check sec_overlay/run.py sec_overlay/driver.py && uv run ty check`
Expected: PASS.

Note: if `begin_pass`/`load_state` field names differ (e.g. `CampaignState.stages`), read `sec_overlay/state.py` and adjust the `if not status.stages` guard to the real attribute before implementing.

- [ ] **Step 9: Commit**

Add a `### Added` CHANGELOG line ("Add single-repo drive loop with per-phase fence and receipt."). Stage the `agents/README.md`? No — no agents change here. Stage `helpers/README.md`? Only `helpers/sec_overlay/README.md` (folder of `run.py`/`driver.py`).

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): drive audit with per-phase fence and receipt"
```

---

## Task 7: O-65 — one writer per red-team gate path

**Files:**
- Modify: `agents/redteam-adversary.md` (the line reading `record verdicts into `kb/gates/redteam.json`.`)
- Test: `helpers/tests/test_redteam_gate_paths.py`

**Interfaces:**
- No code signature change. The adversary prompt must write `kb/gates/redteam-adversary.json`; `redteam.py`'s `write_plan` continues to write `kb/gates/redteam.json` via `write_gate_record(ws, "redteam", ...)`.

- [ ] **Step 1: Write the failing test**

```python
# helpers/tests/test_redteam_gate_paths.py
from pathlib import Path

_AGENTS = Path(__file__).resolve().parents[2] / "agents"


def test_redteam_adversary_writes_its_own_gate_path():
    text = (_AGENTS / "redteam-adversary.md").read_text()
    assert "kb/gates/redteam-adversary.json" in text
    assert "kb/gates/redteam.json" not in text
```

Confirm the relative path to `agents/` from `helpers/tests/` before relying on `parents[2]`; adjust the index if the directory depth differs.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_redteam_gate_paths.py -q`
Expected: FAIL — the prompt still names `kb/gates/redteam.json`.

- [ ] **Step 3: Edit the prompt**

In `agents/redteam-adversary.md`, change the Output section's last sentence from:

```
record verdicts into `kb/gates/redteam.json`.
```

to:

```
record verdicts into `kb/gates/redteam-adversary.json`.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_redteam_gate_paths.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

Add a `### Fixed` CHANGELOG line ("Fix red-team gate path collision (O-65): the adversary writes redteam-adversary.json."). Update `agents/README.md` with a one-line note that the red-team adversary owns `kb/gates/redteam-adversary.json`.

```bash
git add plugins/sec-overlay/skills/sec-overlay/agents/redteam-adversary.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam_gate_paths.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(sec-overlay): split red-team adversary gate path (O-65)"
```

---

## Task 8: Command surface — `commands/audit.md` + `commands/README.md`

**Files:**
- Create: `commands/audit.md`, `commands/README.md`
- Test: `helpers/tests/test_command_audit.py`

**Interfaces:**
- No code. `commands/audit.md` documents routing (1 repo → `drive`; N repos → `drive` each, confirm, then `python -m sec_overlay.correlate --manifest <synth> --out <cwd>`). The test asserts the load-bearing content is present so the file cannot silently drop the correlate flow.

- [ ] **Step 1: Write the failing test**

```python
# helpers/tests/test_command_audit.py
from pathlib import Path

_CMD = Path(__file__).resolve().parents[2] / "commands" / "audit.md"


def test_command_documents_routing_and_correlate():
    text = _CMD.read_text()
    assert "/sec-overlay:audit" in text
    assert "python -m sec_overlay.run" in text or "run.drive" in text
    assert "python -m sec_overlay.correlate" in text
    assert "--out" in text  # correlation output lands in the CWD
    assert "confirm" in text.lower()  # N-repo confirm step
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_command_audit.py -q`
Expected: FAIL — `FileNotFoundError` (no `commands/audit.md`).

- [ ] **Step 3: Write `commands/audit.md`**

Write the command file. Required content (the test enforces the load-bearing lines):

```markdown
# /sec-overlay:audit

Audit one repository, or audit several and correlate them.

## Usage

    /sec-overlay:audit <repo> [<repo> ...]

## Routing

1. Count the repo arguments.
2. **One repo** — drive the single-repo audit and stop. No correlation, no CWD output.
3. **Two or more repos** — drive each repo's audit, then correlate.

## Single repo

Drive the audit from `helpers/`:

    cd plugins/sec-overlay/skills/sec-overlay/helpers
    uv run python -c "from sec_overlay.run import drive; print(drive('<repo>', config='rules/smoke.yaml'))"

The driver writes `run.env` once, and fences the tree and writes a receipt before
each stage. When it prints a `NEXT AGENT PHASE` block, run that agent prompt, then
re-invoke `drive` to resume from the first phase without a receipt.

## Multiple repos

1. Drive each repo's audit in turn (each resumes from its own receipts).
2. Infer each repo's role from its `kb/scan-profile.json` (`sec_overlay.run.infer_role`).
3. **Confirm** with the operator: the repo count, each repo's inferred role, and that
   correlation will write unified docs into the current directory. A wrong role is the
   cue to abort and correct.
4. On go, synthesize the manifest (`sec_overlay.run.synthesize_manifest`), write it into
   the correlation workspace, and run the existing core:

       uv run python -m sec_overlay.correlate --manifest <synth> --out "$PWD"

5. Output lands in the current directory: `ARCHITECTURE.md`, `THREAT_MODEL.md`,
   `REDTEAM.md`, `FINDINGS.md`, plus `edges.json`, `verdicts.json`, `report.sarif`.

A barrier whose enforcer repo the operator did not include is emitted as a
`coverage-gap`, never a clean result.
```

- [ ] **Step 4: Write `commands/README.md`**

```markdown
# commands/

Slash-command entry points for the sec-overlay skill.

| File | Command | Purpose |
|------|---------|---------|
| `audit.md` | `/sec-overlay:audit <repo> [<repo> ...]` | Drive a single-repo audit, or audit several repos and correlate them into the invocation directory. |

The command is a thin routing document over `sec_overlay.run.drive` (single repo) and
`python -m sec_overlay.correlate` (multi-repo). All executable logic lives under
`helpers/sec_overlay/`; this folder holds no code.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_command_audit.py -q`
Expected: PASS.

- [ ] **Step 6: Validate the plugin manifest**

Run: `cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools && claude plugin validate .`
Expected: no errors (a new `commands/` directory is discovered by the default scan).

- [ ] **Step 7: Commit**

Add a `### Added` CHANGELOG line ("Add /sec-overlay:audit command."). `commands/README.md` is the new folder's README (satisfies docs-track-code for `commands/audit.md`).

```bash
git add plugins/sec-overlay/skills/sec-overlay/commands/audit.md \
        plugins/sec-overlay/skills/sec-overlay/commands/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_command_audit.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add /sec-overlay:audit command"
```

---

## Task 9: Full suite, lint, types, and PR

**Files:** none new — verification and release.

- [ ] **Step 1: Run the full suite**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q`
Expected: PASS except the two documented environment-only failures (missing semgrep submodule + bench seed corpus — skill `CLAUDE.md` §1). Confirm no other failures.

- [ ] **Step 2: Lint and type-check**

Run: `uv run ruff check sec_overlay/ tests/ && uv run ruff format --check sec_overlay/ tests/ && uv run ty check`
Expected: clean.

- [ ] **Step 3: Push and open the PR**

```bash
git fetch origin && git log origin/feat/sec-overlay-invocation..HEAD
git push -u origin feat/sec-overlay-invocation
gh pr create --title "feat(sec-overlay): driven invocation + O-65 fix" \
  --body "$(cat <<'EOF'
Adds a `/sec-overlay:audit` command and a `run.py` driver that audits a repo (or
several and correlates them) without hand token-substitution. Every phase leaves a
receipt before it is recorded done, and a working-tree fence stops a run that dirties
the audited tree. Multi-repo runs infer per-repo roles from the scan profile, synthesize
a manifest, and drop unified docs into the invocation directory via the existing
correlation core. Fixes the O-65 red-team gate path collision.

Spec: docs/superpowers/specs/2026-08-16-sec-overlay-invocation-design.md
Plan: docs/superpowers/plans/2026-08-16-sec-overlay-invocation.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 4: Wait for CodeRabbit**

Run `gh pr view <n> --comments` until CodeRabbit's walkthrough comment lands. Address findings. Merge only after the review appears (repo governance).

---

## Self-Review

**Spec coverage:**

- Section 1 (command + routing) → Task 8. ✓
- Section 2 (`write_env`, `receipt`, `fence`; O-67/O-68/O-69; O-65 edit) → Tasks 1, 2, 3, 7. ✓ Driver loop (open/resume/fence/receipt/record) → Task 6. ✓
- Section 3 (role inference + manifest synthesis; `<slug>#<scan_scope>` key; `infra` default) → Tasks 4, 5. ✓
- Section 4 (multi-repo flow, confirm step, CWD output via `correlate --out`) → Task 8 (`audit.md`). ✓
- Section 5 (verification: fence, receipt, O-65, role inference, routing) → tests in Tasks 1, 2, 4, 7, 8. Routing is documented+content-tested in Task 8 rather than code (routing is prose in the command file, per Section 1). ✓
- Section 6 (version bump, docs-track-code, branching, distribution) → Global Constraints + per-task commit steps. ✓
- Non-goals (coverage/recall O-numbers) → excluded, no task. ✓

**Placeholder scan:** No TBD/TODO. Every code step carries real code. Three steps carry a "confirm the field name / relative-path depth before implementing" note — these are verification guards against drift in code this plan does not own (`ScanProfile` fields, `CampaignState.stages`, `agents/` directory depth), not placeholders; the surrounding code is complete.

**Type consistency:** `on_complete: Callable[[str], None]` used identically in `run_deterministic_phase`, `run_audit`, and `drive`'s closure. `receipt` counts key `"findings"` consistent between Task 2 test and Task 6 closure. `synthesize_manifest`/`validate_manifest` member keys (`slug`, `repo_root`, `scan_scope`, `role`) match `manifest.py`. `ROLES` imported, not re-declared.
