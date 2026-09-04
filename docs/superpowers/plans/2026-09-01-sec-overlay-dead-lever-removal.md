# sec-overlay Dead Lever Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every sec-overlay capability that is implemented and documented but never called, and wire the one lever that must stay.

**Architecture:** Group 2 of the defect spec covers root cause RC-14 — a function that exists, that a document promises, and that no caller reaches. This plan takes each of the four requirements to its verified target: it passes the drift set into postflight so the prior-context merge can drop a stale conclusion, it deletes the token and USD accounting whose only producer was never called, it deletes the dead ingested-scope module and the dead path helper while keeping the live `scanscope` module the spec proposed to delete, and it lands a test that fails when a new public helper gains no caller.

**Tech Stack:** Python 3.11 (standard library only in `sec_overlay/`), pytest, ruff, ty, `uv` for every command. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `docs/superpowers/specs/2026-09-01-sec-overlay-defect-repairs-design.md` (Section 5, Group 2)

## Global Constraints

- Requirement numbering starts at REQ-40. REQ-35 through REQ-39 stay unused; the prior spec names a phantom REQ-35.
- The test baseline is 1766 tests passing at plugin version 1.122.0. Run the full suite after the group.
- Run `uv run ruff check sec_overlay/ bench/ tests/` and `uv run ty check` after the group.
- One requirement per red-green pair. The red commit adds the failing acceptance test. The green commit adds the code. A single commit holding both skips the red phase.
- Carry the requirement id in both commit subjects.
- Stage explicit paths only. Never bypass the hooks. Run `prek run` before each commit.
- Bump the plugin version in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit as any shipping-file change. Everything under `helpers/` and `agents/` is a shipping file, including `README.md` files and tests.
- Stage the touched folder's `README.md` in the same commit, plus `plugins/sec-overlay/CHANGELOG.md`.
- `helpers/sec_overlay/models.py` and `helpers/sec_overlay/evidence.py` are byte-pinned by `helpers/tests/test_frozen_contract.py`. This plan edits neither file, so neither digest changes.
- Do not merge and do not push. The branch is `docs/sec-overlay-defect-repairs-spec`.
- This plan starts at plugin version `2.1.4`, the version Plan 1 ends on. It ends at `2.1.12`.

---

## Pre-flight scan

Every `file:line` below was confirmed against HEAD `1724dc2`, plugin version `1.122.0`. Version numbers in the task steps assume Plan 1 landed first.

### Corrections to the specification

The specification cites five locations that do not hold. Each correction below was read at the source.

| # | Spec text | What the source holds |
|---|---|---|
| C-1 | REQ-45 cites `driver.py:324`. | The postflight action is `_act_postflight` at `driver.py:436-439`. Its body is `run_postflight(ctx.ws, ctx.sha)`. |
| C-2 | REQ-46 says wall-clock is measured at `driver.py:97`. | The `time.perf_counter()` block around `action(ctx)` and the `cost.record_timing` call are at `driver.py:101-108`. |
| C-3 | REQ-46 lists three references in `SKILL.md:255-261`. | A fourth reference sits at `SKILL.md:332`: "Record measured token spend per phase with `cost.record_agent` so the next run can calibrate." |
| C-4 | REQ-47 names `cli.py:276` as a scanscope call site and implies the helper is `_persist_scope`. | The helper is `write_scan_scope`, defined at `cli.py:253` and called at `cli.py:1073`. |
| C-5 | REQ-48 says the test "fails today on the four helpers above". | An AST-precise scan of `sec_overlay/` and `bench/` finds 39 public functions with no importer and no prompt mention, plus 33 named only by a prompt. |

### Rulings taken against plugin HEAD

| # | Ruling | Why |
|---|---|---|
| R-1 | REQ-47 keeps `scanscope.py` and deletes `scope.py` and `scanscope.rel_to_root` instead. | `scanscope.py` is live: `cli.py:82-83` imports `resolve` and `write_scope`, `cli.py:1073` calls `write_scan_scope` on the documented prefilter step (`SKILL.md:72`, `SKILL.md:411`), and `agents/context-ingest.md:13` runs `load_scope` in a shell one-liner. Deleting it would break the CLI, that prompt, `test_scanscope.py`, `test_scanscope_cli.py`, and `test_docs_invariants.py:42`. `scope.py` is the module that matches the requirement's description: `is_external_package` has no importer, and Plan 1's REQ-41 already put the external-boundary rule inside `calibrate.py`. |
| R-2 | REQ-47 also corrects `SKILL.md:206-209`. | That paragraph says agents read `{{REPO_ROOT}}` and `{{SCAN_SCOPE}}` from `kb/scan-scope.json`. `DISPATCH_TOKENS` (`driver.py:118-126`) holds neither token, so no dispatch block can carry them. Agents receive both through `run.env`, written at `run.py:139-161`. The document must describe `run.env`. |
| R-3 | REQ-45's second half is a shared key normalizer, not a path re-derivation. | `models.py:72` documents `Finding.file` as a repo-relative path, and `git diff --name-only` returns top-level-relative paths, so the two sides already agree on the base. The remaining gap is a leading `./` or `/`. One `_file_of` helper applied to both sides closes it without duplicating `scanscope`. |
| R-4 | REQ-48 seeds its allowlist with names and a shared reason, and requires a per-entry reason only for a name added after this plan. | The specification asks for a one-line reason per entry. Writing 37 individual reasons requires reading 37 functions this session. Inventing them would break the specification's own evidence rule. The seed reason states the verified fact: unreferenced at plugin 2.1.10. |
| R-5 | REQ-46 and REQ-47 are `refactor:` commits and bump patch, not major. | Plan 1's REQ-42 took the major because it removed a phase from `PHASE_TABLE` and a value from a declared verification enum. The functions this plan deletes have no importer, so no caller can break. The one visible output change is the removal of a `$0.0000` estimate line. |
| R-6 | REQ-46 also deletes `aggregate_by_phase`, `aggregate_by_model`, and the bench token columns. | Both aggregators read `state.budget["records"]`, which only `record_agent` writes. With `record_agent` gone, both return `{}` forever. `bench/run.py:116-123` already sets `usd_estimate` to `None` whenever `tokens` is 0, and `tokens` is always 0, so `bench/tally.py:113-118` already prints `n/a`. |

### Drift rows

| Row | HEAD state | Action |
|---|---|---|
| `postflight.py:98-106` | `main` calls `run_postflight(Workspace(...), args.sha)` with no drift set. | REQ-45 green step adds `--target` and forwards it, so the CLI path gets the same behaviour as the driver path. |
| `SKILL.md:640` | Tells the orchestrator to compute `changed = diffscope.changed_files(<prior_sha>, "HEAD")` by hand. | REQ-45 green step rewrites the bullet: the `postflight` phase computes the drift set itself; the orchestrator passes only the target. |
| `test_report.py:437` | Calls `cost.record_agent` to build a state for the economics test. | REQ-46 green step deletes the call and the assertions that depend on token totals. |
| `test_report.py:691-692` | `test_run_economics_section_renders_phase_model_and_usd_estimate`. | REQ-46 green step deletes the test. `test_report.py:909` asserts the same rendered text and is deleted with it. |
| `test_bench.py:266`, `:277`, `:284` | Assert `usd_estimate` and `usd_per_confirmed_tp` keys. | REQ-46 green step deletes the three assertions and any test whose only subject is a token or USD column. |
| `test_cost.py` | Holds tests for `record_agent`, `aggregate_by_phase`, `aggregate_by_model`, and `estimate_cost_usd`. | REQ-46 green step deletes those tests and keeps the `record_timing` and `aggregate_timings_by_phase` tests. |
| `test_scope.py` | Writes an `{"ingested_packages": [...]}` manifest and exercises `is_external_package`. | REQ-47 green step deletes the file with the module. |
| `test_scanscope.py` | Holds a `rel_to_root` test alongside five tests for the functions that stay. | REQ-47 green step deletes only the `rel_to_root` test. |
| `helpers/README.md:62` | A mermaid node `SS["scanscope.py<br/>pin repo_root + scan_scope"]`. | Stays. R-1 keeps `scanscope.py`. |
| `helpers/README.md:186` | The `scope.py` row describing `is_external_package`. | REQ-47 green step deletes the row. |
| `helpers/sec_overlay/README.md:229` | A paragraph describing `scope.py`'s manifest check. | REQ-47 green step deletes the paragraph. |

### Adjacent findings this plan does not fix

Each item below was found while verifying Group 2 and is outside REQ-45 through REQ-48. None is fixed here.

| # | Finding | Why it is deferred |
|---|---|---|
| A-1 | `run.py:161` writes `REPO_ROOT={target}` into `run.env`, not the git top-level. For a monorepo sub-path scan every agent then receives the wrong repository root. | The fix changes what every agent prompt resolves paths against. It needs its own requirement and its own acceptance test. |
| A-2 | `kb/scan-scope.json` has two writers with disjoint schemas. `scanscope.write_scope` (`scanscope.py:113-118`) writes `repo_root`, `scan_scope`, `path_base`, `slug`, `sha`, and `doc_roots`. `scope.py:24` reads `ingested_packages` from the same path. | REQ-47 removes the reader, which removes the live half of the collision. Restoring an ingested-package manifest is new capability, not a repair. |
| A-3 | `prove.py:run_prove` and `prove.py:loopback_collector` have no importer. `DETERMINISTIC_ACTIONS` (`driver.py:442-461`) holds no `prove` entry, so the opt-in prove lane the prior spec's REQ-34 shipped cannot run. | This is a fifth RC-14 instance. It needs a requirement of its own, because wiring it changes what a run executes. REQ-48's allowlist records both names so the gap stays visible. |
| A-4 | `graph.py:build_and_write_tier1`, `graph.py:merge_tier2`, `graph.py:entry_point_nodes`, `graph.py:attacker_controls`, and `graph.py:is_unresolvable` have no importer and no prompt mention — the whole tier-1/tier-2 graph surface. | Five functions in one module is a design question, not a defect repair. REQ-48's allowlist records them. |

---

## File Structure

**Created:**
- `helpers/tests/test_dead_lever.py` — Tasks 1 to 3 acceptance tests. Task 1 creates it; Tasks 2 and 3 extend it.
- `helpers/tests/test_no_dead_helpers.py` — Task 4 only. Separate file because it scans the whole package and has no subject module.

**Deleted:**
- `helpers/sec_overlay/scope.py`
- `helpers/tests/test_scope.py`

**Modified:**
- `helpers/sec_overlay/postflight.py` — Task 1. Gains the drift-set computation and the shared key normalizer.
- `helpers/sec_overlay/driver.py:436-439` — Task 1. Passes the target.
- `helpers/sec_overlay/cost.py` — Task 2. Keeps only the two timing functions.
- `helpers/sec_overlay/report.py` — Task 2. The economics section keeps wall-clock only.
- `helpers/bench/run.py`, `helpers/bench/tally.py` — Task 2. Drop the token and USD columns.
- `helpers/sec_overlay/scanscope.py` — Task 3. Drops `rel_to_root`.
- `SKILL.md` — Tasks 1, 2, and 3.
- `helpers/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md`, `helpers/bench/README.md` — the folder READMEs the hook requires.

---

## Task 1: REQ-45 — postflight receives the drift set

**Files:**
- Create: `helpers/tests/test_dead_lever.py`
- Modify: `helpers/sec_overlay/postflight.py:59-106`
- Modify: `helpers/sec_overlay/driver.py:436-439`
- Modify: `SKILL.md:640`
- Modify: `helpers/tests/README.md`, `helpers/sec_overlay/README.md`

**Interfaces:**
- Consumes: `sec_overlay.diffscope.changed_files(base: str, head: str = "HEAD", *, runner=subprocess.run) -> list[str]`; `sec_overlay.diffscope.validate_ref(ref: str) -> str`; `sec_overlay.context.Context.provenance: dict`; `sec_overlay.context.prior_context_path(ws) -> Path`.
- Produces: `run_postflight(ws: Workspace, sha: str | None, *, changed_files: set[str] | None = None, target: str | None = None, runner=subprocess.run) -> int`. An explicit `changed_files` wins over `target`. Also `_file_of(where: str) -> str`, private to `postflight.py`.

- [ ] **Step 1: Write the failing tests**

Create `helpers/tests/test_dead_lever.py`:

```python
"""Group 2 acceptance tests: every declared lever has a caller (RC-14)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from sec_overlay.context import Context, ContextItem, prior_context_path
from sec_overlay.postflight import run_postflight
from sec_overlay.workspace import Workspace


def _ws_with_prior(tmp_path: Path, where: str) -> Workspace:
    """A workspace whose prior context holds one settled non-finding at ``where``."""
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    old = Context(
        items=[ContextItem(
            kind="note", trust="prior-scan", cls="xss",
            text="settled non-finding (xss): sanitized at the sink",
            where=where, source_doc="scan@aaa")],
        provenance={"sha": "aaa", "kind": "postflight"},
    )
    prior_context_path(ws).write_text(json.dumps(old.to_dict()))
    return ws


def _fake_git(stdout: str, seen: list[dict]):
    """A runner that records every call and returns ``stdout`` for the diff."""
    def run(cmd, **kwargs):
        seen.append({"cmd": cmd, "cwd": kwargs.get("cwd")})
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")
    return run


def test_postflight_drops_prior_items_on_changed_files(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    seen: list[dict] = []
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/a.ts\n", seen))
    merged = Context.from_dict(json.loads(prior_context_path(ws).read_text()))
    assert total == 0
    assert merged.items == []
    assert seen and seen[0]["cwd"] == "/repo"
    assert seen[0]["cmd"][:4] == ["git", "diff", "--name-only", "aaa"]


def test_postflight_keeps_prior_items_on_unchanged_files(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/other.ts\n", []))
    assert total == 1


def test_postflight_merge_key_ignores_a_leading_dot_slash(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "./src/a.ts:9")
    total = run_postflight(
        ws, "bbb", target="/repo", runner=_fake_git("src/a.ts\n", []))
    assert total == 0


def test_postflight_without_a_target_keeps_every_prior_item(tmp_path: Path):
    ws = _ws_with_prior(tmp_path, "src/a.ts:9")
    assert run_postflight(ws, "bbb") == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_dead_lever.py -v`

Expected: three failures. `test_postflight_drops_prior_items_on_changed_files` fails with `TypeError: run_postflight() got an unexpected keyword argument 'target'`.

- [ ] **Step 3: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.5"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dead_lever.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(postflight): pin the REQ-45 drift-set contract"
```

- [ ] **Step 4: Add the drift-set computation**

Replace `helpers/sec_overlay/postflight.py:59-106` with:

```python
def _file_of(where: str) -> str:
    """Return the file part of a ``ContextItem.where`` note, base-normalized.

    ``Finding.file`` is repo-relative by contract (``models.py``), and ``git diff
    --name-only`` returns top-level-relative paths, so both sides share a base. A
    leading ``./`` or ``/`` is the only remaining difference, and this strips it.

    Args:
        where: A ``ContextItem.where`` value, normally ``"<file>:<line>"``.

    Returns:
        The file path with any leading ``./`` or ``/`` removed.
    """
    return where.split(":", 1)[0].removeprefix("./").lstrip("/")


def _merge(old: Context, new: Context, changed_files: set[str]) -> Context:
    """Merge new postflight over old prior-context, drift-aware.

    Old items whose file is in ``changed_files`` are dropped (re-opened this pass); the
    rest are kept. New items are appended (deduped by (kind, where, text-prefix)).
    """
    def key(i: ContextItem):
        return (i.kind, i.where, i.text[:60])
    drift = {_file_of(f) for f in changed_files}
    kept = [i for i in old.items if _file_of(i.where) not in drift]
    seen = {key(i) for i in kept}
    for i in new.items:
        if key(i) not in seen:
            kept.append(i)
            seen.add(key(i))
    return Context(items=kept, provenance=new.provenance)


def _drift_since(old: Context, sha: str | None, target: str, runner) -> set[str]:
    """Return the files changed between the prior pass's SHA and this pass's SHA.

    Args:
        old: The prior context, whose provenance holds the last postflight's SHA.
        sha: This pass's SHA; ``None`` falls back to ``HEAD``.
        target: The audited repository, bound as the git working directory.
        runner: Injectable process runner.

    Returns:
        Repo-relative changed paths, or an empty set when the prior context carries
        no SHA — the first pass has nothing to drift against.
    """
    base = str(old.provenance.get("sha") or "")
    if not base:
        return set()
    validate_ref(base)
    head = validate_ref(sha) if sha else "HEAD"

    def git(cmd, **kwargs):
        return runner(cmd, cwd=target, **kwargs)

    return set(changed_files_between(base, head, runner=git))


def run_postflight(
    ws: Workspace,
    sha: str | None,
    *,
    changed_files: set[str] | None = None,
    target: str | None = None,
    runner=subprocess.run,
) -> int:
    """Distill the scan and merge into the durable prior_context.json.

    Args:
        ws: Finished scan workspace.
        sha: Scanned SHA.
        changed_files: Repo-relative files changed since the last postflight (drift);
            old conclusions on these are dropped so the next scan re-examines them.
            Wins over ``target`` when both are given.
        target: The audited repository. With no explicit ``changed_files``, the drift
            set is computed from it against the prior context's SHA.
        runner: Injectable process runner for the git call.

    Returns:
        Total item count in the merged prior context.
    """
    new = build_prior_context(ws, sha)
    p = prior_context_path(ws)
    old = Context.from_dict(json.loads(p.read_text())) if p.exists() else Context()
    if changed_files is None:
        changed_files = _drift_since(old, sha, target, runner) if target else set()
    merged = _merge(old, new, changed_files)
    ws.kb.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(merged.to_dict(), indent=2))
    record_stage(ws, "postflight")
    return len(merged.items)


def main(argv: list[str] | None = None) -> int:
    """CLI: run postflight distillation for a workspace."""
    ap = argparse.ArgumentParser(prog="sec-overlay-postflight")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--target", default=None,
                    help="Audited repository; enables the drift-set computation.")
    args = ap.parse_args(argv)
    n = run_postflight(Workspace(Path(args.workspace)), args.sha, target=args.target)
    print(f"prior_context.json now holds {n} item(s)")
    return 0
```

Then extend the import block at `helpers/sec_overlay/postflight.py:11-20` to:

```python
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.context import Context, ContextItem, prior_context_path
from sec_overlay.diffscope import changed_files as changed_files_between
from sec_overlay.diffscope import validate_ref
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.workspace import Workspace, read_findings
```

The import alias matters: the module-level name `changed_files` is the keyword argument, so the imported function is bound as `changed_files_between`.

- [ ] **Step 5: Pass the target from the driver**

Replace `helpers/sec_overlay/driver.py:436-439` with:

```python
def _act_postflight(ctx: AuditContext) -> None:
    from sec_overlay.postflight import run_postflight  # local: avoid import cycle

    run_postflight(ctx.ws, ctx.sha, target=ctx.target)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_dead_lever.py tests/test_postflight.py tests/test_driver.py tests/test_diffscope.py -v`

Expected: PASS.

- [ ] **Step 7: Update the documents**

In `SKILL.md`, replace the `**Pass N>1 (incremental):**` first bullet at line 640:

```markdown
- Scope to changed code: the `postflight` phase computes the drift set itself from
  the prior context's pinned SHA, so pass only the target. Nothing computes
  `changed_files` by hand.
```

Add a row to `helpers/sec_overlay/README.md` under the `postflight.py` entry stating that `run_postflight` takes `target` and derives the drift set from the prior context's SHA. Add the new test file to `helpers/tests/README.md`.

- [ ] **Step 8: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.6"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/postflight.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(postflight): derive the REQ-45 drift set from the target"
```

---

## Task 2: REQ-46 — delete the token and USD accounting

**Files:**
- Modify: `helpers/tests/test_dead_lever.py`
- Modify: `helpers/sec_overlay/cost.py:1-59`, `:90-106`
- Modify: `helpers/sec_overlay/report.py:351-373`, `:681-688`
- Modify: `helpers/bench/run.py:116-123`
- Modify: `helpers/bench/tally.py:42`, `:111-118`, `:197-239`
- Modify: `SKILL.md:255-261`, `:332`
- Modify: `helpers/tests/test_cost.py`, `helpers/tests/test_report.py`, `helpers/tests/test_bench.py`
- Modify: `helpers/README.md:248`, `helpers/sec_overlay/README.md:150-151`, `helpers/tests/README.md`, `helpers/bench/README.md`

**Interfaces:**
- Consumes: `sec_overlay.cost.record_timing(state, phase, seconds)` and `sec_overlay.cost.aggregate_timings_by_phase(state) -> dict[str, float]`, both unchanged.
- Produces: `sec_overlay.cost` exposes exactly `record_timing` and `aggregate_timings_by_phase`. `report.write_report`'s economics dict carries only `by_phase_seconds`. `bench`'s cost record carries only `wall_time_s`.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_dead_lever.py`:

```python
def test_cost_module_exposes_only_timing_helpers():
    import sec_overlay.cost as cost

    public = {n for n in vars(cost) if not n.startswith("_") and callable(getattr(cost, n))}
    assert public == {"record_timing", "aggregate_timings_by_phase"}


def test_report_renders_no_token_or_usd_line(tmp_path: Path):
    from sec_overlay.report import write_report

    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_report(ws)
    md = (ws.reports / "report.md").read_text()
    assert "Tokens by" not in md
    assert "Estimated cost" not in md


def test_skill_md_never_names_record_agent():
    skill = Path(__file__).resolve().parents[2] / "SKILL.md"
    assert "record_agent(" not in skill.read_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_dead_lever.py -k "cost_module or token_or_usd or record_agent" -v`

Expected: three failures. The first reports the extra names `record_agent`, `aggregate_by_phase`, `aggregate_by_model`, and `estimate_cost_usd`.

- [ ] **Step 3: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.7"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dead_lever.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(cost): pin the REQ-46 timing-only surface"
```

- [ ] **Step 4: Reduce `cost.py` to the two timing functions**

Replace `helpers/sec_overlay/cost.py:1-59` with:

```python
"""Per-phase wall-clock accounting over CampaignState.budget.

The driver measures each deterministic phase with ``time.perf_counter`` and records the
elapsed seconds via :func:`record_timing`; the records live in the existing free-form
``CampaignState.budget`` dict (no contract change). Wall-clock is the only measured
figure this module holds. Token totals were removed at plugin 2.1.8: the harness never
surfaced a subagent's usage, so every token table rendered empty and every USD figure
rendered as zero.
"""

from __future__ import annotations

from sec_overlay.models import CampaignState
```

Delete `helpers/sec_overlay/cost.py:90-106` — the whole `estimate_cost_usd` function and the blank lines above it. `record_timing` and `aggregate_timings_by_phase` stay byte-identical.

- [ ] **Step 5: Reduce the report's economics section**

Replace `helpers/sec_overlay/report.py:351-373`'s body with:

```python
    seconds = economics.get("by_phase_seconds") or {}
    if not seconds:
        return []
    body = ["**Wall-clock by phase, seconds** (measured):"]
    body += [f"- **{k}**: {v:.2f}" for k, v in seconds.items()]
    return ["", "## Run economics", ""] + body
```

At `helpers/sec_overlay/report.py:681-688`, delete the `by_phase`, `by_model`, and `usd_estimate` entries and the `cost.aggregate_by_phase(state)` assignment above them, leaving only the `by_phase_seconds` entry that calls `cost.aggregate_timings_by_phase(state)`.

- [ ] **Step 6: Drop the bench token and USD columns**

Replace `helpers/bench/run.py:116-123` with:

```python
    cost = {"wall_time_s": wall}
```

Delete the now-unused `costmod` import and the `CampaignState`/`json` uses that only served it, but keep any use either name has elsewhere in the file — check with `uv run ruff check bench/`.

In `helpers/bench/tally.py`: change the line 42 comment to `# {wall_time_s} (REQ-M6)`; replace lines 111-118 with a block that prints only the wall-clock line; and replace lines 233-239 with:

```python
    if cost:
        sc.cost = {"wall_time_s": float(cost.get("wall_time_s", 0.0))}
```

Delete the `usd_estimate` and `usd_per_confirmed_tp` mentions in the `tally` docstring at lines 205-206.

- [ ] **Step 7: Delete the reversed tests**

- In `helpers/tests/test_cost.py`: delete every test whose subject is `record_agent`, `aggregate_by_phase`, `aggregate_by_model`, or `estimate_cost_usd`, and remove those names from the import block. Keep the `record_timing` and `aggregate_timings_by_phase` tests.
- In `helpers/tests/test_report.py`: delete `test_run_economics_section_renders_phase_model_and_usd_estimate` (line 691) and the assertion at line 909 that checks the same rendered text. At line 437, delete the `cost.record_agent` call and any assertion that reads a token total; keep the surrounding test if it also asserts a wall-clock row, otherwise delete it.
- In `helpers/tests/test_bench.py`: delete the assertions at lines 266, 277, and 284, and any test whose only subject is a token or USD column.

- [ ] **Step 8: Update the documents**

- `SKILL.md`: delete lines 255-261 in full — both the cost-recording convention paragraph and the labelled-proxy paragraph.
- `SKILL.md:332`: replace with "Record measured wall-clock per phase with `cost.record_timing` so the next run can calibrate."
- `helpers/README.md:248`: rewrite the `cost.py` row to describe wall-clock only.
- `helpers/sec_overlay/README.md:150-151` and the paragraph at `:1348`: same rewrite.
- `helpers/bench/README.md`: remove the token and USD columns from the metrics description.
- `helpers/tests/README.md`: note the deleted tests.

- [ ] **Step 9: Run the tests to verify they pass**

Run: `uv run pytest tests/test_dead_lever.py tests/test_cost.py tests/test_report.py tests/test_bench.py tests/test_docs_invariants.py -v`

Expected: PASS. Then run `uv run ruff check sec_overlay/ bench/ tests/` and expect no unused-import findings.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.8"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cost.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/run.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/tally.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cost.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bench.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "refactor(cost): drop REQ-46 token and USD accounting"
```

---

## Task 3: REQ-47 — delete the dead scope module and path helper

**Files:**
- Modify: `helpers/tests/test_dead_lever.py`
- Delete: `helpers/sec_overlay/scope.py`, `helpers/tests/test_scope.py`
- Modify: `helpers/sec_overlay/scanscope.py:127-152`
- Modify: `helpers/tests/test_scanscope.py`
- Modify: `SKILL.md:206-209`
- Modify: `helpers/README.md:186`, `:249`, `helpers/sec_overlay/README.md:229`, `helpers/tests/README.md`

**Interfaces:**
- Consumes: nothing new.
- Produces: `sec_overlay.scope` no longer imports. `sec_overlay.scanscope` exposes `ScanScope`, `resolve`, `write_scope`, and `load_scope` only.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_dead_lever.py`:

```python
def test_scope_module_is_gone():
    import importlib

    try:
        importlib.import_module("sec_overlay.scope")
    except ModuleNotFoundError:
        return
    raise AssertionError("sec_overlay.scope still imports")


def test_scanscope_keeps_only_its_live_surface():
    import sec_overlay.scanscope as scanscope

    public = {n for n in vars(scanscope)
              if not n.startswith("_") and callable(getattr(scanscope, n))}
    assert public == {"ScanScope", "resolve", "write_scope", "load_scope"}


def test_skill_md_sources_the_scope_tokens_from_run_env():
    skill = (Path(__file__).resolve().parents[2] / "SKILL.md").read_text()
    assert "run.env" in skill
    assert "{{SCAN_SCOPE}}` (the audit target path relative to `{{REPO_ROOT}}`, also from `kb/scan-scope.json`)" not in skill
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_dead_lever.py -k "scope_module or scanscope_keeps or run_env" -v`

Expected: three failures. The first fails on `AssertionError: sec_overlay.scope still imports`.

- [ ] **Step 3: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.9"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dead_lever.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(scope): pin the REQ-47 live scope surface"
```

- [ ] **Step 4: Delete the dead module and helper**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
trash sec_overlay/scope.py tests/test_scope.py
```

Delete `helpers/sec_overlay/scanscope.py:127-152` — the whole `rel_to_root` function. In `helpers/tests/test_scanscope.py`, delete only the `rel_to_root` test and remove `rel_to_root` from the import block.

- [ ] **Step 5: Correct the scope-token paragraph**

Replace `SKILL.md:206-209` with:

```markdown
the two scope anchors `{{REPO_ROOT}}` and `{{SCAN_SCOPE}}`. Neither is a dispatch
token: `DISPATCH_TOKENS` does not carry them. The driver writes both into
`{{WORKSPACE}}/run.env` (`run.py`'s `write_env`), and every agent reads that file.
All agents cite paths **repo-root-relative**; all gates, dedupe, and verify resolve
against `{{REPO_ROOT}}`. `kb/scan-scope.json` is the durable record the prefilter
writes; `agents/context-ingest.md` reads it through `scanscope.load_scope`.
```

- [ ] **Step 6: Update the folder READMEs**

- `helpers/README.md:186`: delete the `scope.py` row.
- `helpers/README.md:249`: keep the `scanscope.py` half of the row and drop any `scope.py` mention.
- `helpers/sec_overlay/README.md:229`: delete the `scope.py` paragraph. Update the `scanscope.py` entry to list four public names.
- `helpers/tests/README.md`: record the deleted `test_scope.py`.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/test_dead_lever.py tests/test_scanscope.py tests/test_scanscope_cli.py tests/test_docs_invariants.py tests/test_calibrate.py -v`

Expected: PASS. `test_docs_invariants.py:42` asserts `{{SCAN_SCOPE}}` is present in `SKILL.md`; the replacement paragraph keeps the token, so the assertion holds.

- [ ] **Step 8: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.10"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/scope.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_scope.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/scanscope.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_scanscope.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "refactor(scope): delete the REQ-47 unreachable scope module"
```

`git add --` with the deleted paths stages the deletions; `trash` removed the working-tree files in Step 4.

---

## Task 4: REQ-48 — a test that fails on a new dead helper

**Files:**
- Create: `helpers/tests/test_no_dead_helpers.py`
- Modify: `helpers/tests/README.md`

**Interfaces:**
- Consumes: nothing from earlier tasks at runtime. The allowlist contents assume Tasks 1 to 3 landed.
- Produces: `helpers/tests/test_no_dead_helpers.py` with module constants `DEAD_ALLOWLIST: dict[str, str]` and `PROMPT_ONLY: dict[str, str]`, keyed `"<module>.py:<function>"`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_no_dead_helpers.py`:

```python
"""REQ-48: a public helper with no caller must be on a list, and a list entry must stay dead.

The scan is AST-precise. A name counts as referenced when it appears as a loaded
``Name``, an ``Attribute`` attribute, or an ``ImportFrom`` name anywhere in non-test
``sec_overlay/`` or ``bench/`` code. A docstring mention does not count, and neither
does a parameter of the same name.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

HELPERS = Path(__file__).resolve().parents[1]
SKILL_ROOT = HELPERS.parent

# Unreferenced at plugin 2.1.10. Each entry is a real gap, not a false positive.
# A name added here after this plan must carry its own one-line reason.
DEAD_ALLOWLIST: dict[str, str] = {
    "astgrep.py:astgrep_available": "unreferenced at 2.1.10",
    "calibrate.py:calibrate_score": "unreferenced at 2.1.10",
    "class_ext.py:class_extension_status": "unreferenced at 2.1.10",
    "codeguard.py:default_codeguard_dir": "unreferenced at 2.1.10",
    "codeguard.py:load_rules": "unreferenced at 2.1.10",
    "context.py:doc_coverage": "unreferenced at 2.1.10",
    "coverage_guide.py:should_stop": "unreferenced at 2.1.10",
    "crypto_policy.py:load_policy": "unreferenced at 2.1.10",
    "custom_checks.py:custom_check_classes": "unreferenced at 2.1.10",
    "diffhunks.py:added_line_numbers": "unreferenced at 2.1.10",
    "diffhunks.py:line_in_hunk": "unreferenced at 2.1.10",
    "envelope.py:attribution_banner": "unreferenced at 2.1.10",
    "fix_disposition.py:compute_tier": "unreferenced at 2.1.10",
    "gates.py:run_gates": "unreferenced at 2.1.10",
    "githist.py:files_in_commit": "unreferenced at 2.1.10",
    "graph.py:attacker_controls": "unreferenced at 2.1.10; adjacent finding A-4",
    "graph.py:build_and_write_tier1": "unreferenced at 2.1.10; adjacent finding A-4",
    "graph.py:entry_point_nodes": "unreferenced at 2.1.10; adjacent finding A-4",
    "graph.py:is_unresolvable": "unreferenced at 2.1.10; adjacent finding A-4",
    "graph.py:merge_tier2": "unreferenced at 2.1.10; adjacent finding A-4",
    "kb.py:kb_status": "unreferenced at 2.1.10",
    "kb.py:write_profile": "unreferenced at 2.1.10",
    "parse.py:fallback_list": "unreferenced at 2.1.10",
    "phase_gate.py:attack_surface_gate": "unreferenced at 2.1.10",
    "phase_gate.py:claims_from_markdown": "unreferenced at 2.1.10",
    "phase_gate.py:ref_resolves": "unreferenced at 2.1.10",
    "prove.py:loopback_collector": "unreferenced at 2.1.10; adjacent finding A-3",
    "prove.py:run_prove": "unreferenced at 2.1.10; adjacent finding A-3",
    "reachability.py:blocker_of": "unreferenced at 2.1.10",
    "route_control.py:build_route_control_table": "unreferenced at 2.1.10",
    "route_control.py:check_architecture_controls": "unreferenced at 2.1.10",
    "route_control.py:check_recon_routes": "unreferenced at 2.1.10",
    "route_control.py:check_threat_entrypoints": "unreferenced at 2.1.10",
    "rule_matcher.py:build_guided_context": "unreferenced at 2.1.10",
    "rule_matcher.py:match_function": "unreferenced at 2.1.10",
    "run.py:infer_role": "unreferenced at 2.1.10",
    "run.py:synthesize_manifest": "unreferenced at 2.1.10",
}

# No Python importer, but a prompt names the function and runs it in a shell command.
PROMPT_ONLY: dict[str, str] = {
    "campaign.py:carry_forward": "SKILL.md",
    "campaign.py:pass_report": "SKILL.md",
    "campaign.py:salvage_partial": "SKILL.md",
    "context.py:control_findings": "agents/context-ingest.md",
    "context.py:control_worklist": "SKILL.md",
    "context.py:hunt_rows": "SKILL.md",
    "context.py:leads": "agents/redteam.md",
    "context.py:manual_review_findings": "SKILL.md",
    "context.py:save": "agents/context-ingest.md",
    "custom_checks.py:custom_check_instructions": "SKILL.md",
    "custom_checks.py:discover_custom_checks": "SKILL.md",
    "custom_checks.py:merge_custom_check_classes": "SKILL.md",
    "detection_coverage.py:generate": "agents/tune-config.md",
    "githist.py:security_fix_commits": "agents/recon.md",
    "novelty.py:upstream_status": "SKILL.md",
    "partition.py:must_investigate": "SKILL.md",
    "phase_gate.py:claims_from_context": "SKILL.md",
    "phase_gate.py:claims_from_profile": "SKILL.md",
    "phase_gate.py:recall_claims": "agents/README.md",
    "phase_gate.py:run_phase_checks": "SKILL.md",
    "rule_gaps.py:emit_semgrep_rule": "SKILL.md",
    "run.py:advance": "SKILL.md",
    "run.py:drive": "agents/classes/prompt-injection.md",
    "scanscope.py:load_scope": "agents/context-ingest.md",
    "scoring.py:score_fix": "agents/validate-fix.md",
    "stage_validate.py:repair_prompt": "SKILL.md",
    "stage_validate.py:validate_stage": "SKILL.md",
    "tuning.py:gap_report": "SKILL.md",
    "tuning.py:is_improvement": "SKILL.md",
    "tuning.py:signal_snapshot": "SKILL.md",
    "variant.py:variant_seeds": "agents/variant-hunt.md",
    "workspace.py:record_agent_return": "SKILL.md",
}


def _public_functions() -> dict[str, str]:
    """Map ``"<module>.py:<function>"`` to the module file name for every public def."""
    out: dict[str, str] = {}
    for path in sorted((HELPERS / "sec_overlay").rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                out[f"{path.name}:{node.name}"] = path.name
    return out


def _referenced_names() -> set[str]:
    """Every identifier loaded, attribute-accessed, or imported in non-test code."""
    names: set[str] = set()
    for root in ("sec_overlay", "bench"):
        for path in (HELPERS / root).rglob("*.py"):
            if "test" in path.name:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr)
                elif isinstance(node, ast.ImportFrom):
                    names.update(alias.name for alias in node.names)
    return names


def _prompt_texts() -> list[tuple[str, str]]:
    """Every agent prompt and the skill playbook, as ``(label, text)`` pairs."""
    files = sorted((SKILL_ROOT / "agents").rglob("*.md")) + [SKILL_ROOT / "SKILL.md"]
    return [(str(p.relative_to(SKILL_ROOT)), p.read_text()) for p in files]


def test_every_public_helper_has_a_caller_or_a_listed_reason():
    referenced = _referenced_names()
    prompts = _prompt_texts()
    unlisted_dead: list[str] = []
    unlisted_prompt: list[str] = []
    for key in _public_functions():
        name = key.split(":", 1)[1]
        if name in referenced:
            continue
        named_by = [label for label, text in prompts if re.search(rf"\b{re.escape(name)}\b", text)]
        if named_by:
            if key not in PROMPT_ONLY:
                unlisted_prompt.append(f"{key} (named by {named_by[0]})")
        elif key not in DEAD_ALLOWLIST:
            unlisted_dead.append(key)
    assert not unlisted_dead, (
        "public helpers with no caller and no allowlist entry: " + ", ".join(sorted(unlisted_dead)))
    assert not unlisted_prompt, (
        "prompt-only helpers missing a PROMPT_ONLY entry: " + ", ".join(sorted(unlisted_prompt)))


def test_no_list_entry_has_gained_a_caller():
    referenced = _referenced_names()
    stale = sorted(
        key for key in (DEAD_ALLOWLIST | PROMPT_ONLY)
        if key.split(":", 1)[1] in referenced
    )
    assert not stale, "these entries now have a Python caller and must be removed: " + ", ".join(stale)


def test_no_list_entry_names_a_function_that_is_gone():
    known = set(_public_functions())
    missing = sorted(key for key in (DEAD_ALLOWLIST | PROMPT_ONLY) if key not in known)
    assert not missing, "these entries no longer exist and must be removed: " + ", ".join(missing)


def test_every_dead_allowlist_entry_carries_a_reason():
    empty = sorted(key for key, reason in DEAD_ALLOWLIST.items() if not reason.strip())
    assert not empty, "allowlist entries with no reason: " + ", ".join(empty)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_no_dead_helpers.py -v`

Expected: FAIL. The scan reports any name that drifted between the counts recorded in this plan and the tree Tasks 1 to 3 produced — most likely `test_no_list_entry_names_a_function_that_is_gone` on a name Task 2 or Task 3 deleted, or `test_every_public_helper_has_a_caller_or_a_listed_reason` on a name a Plan 1 task added.

- [ ] **Step 3: Reconcile the two lists against the tree**

Run the same scan by hand and print the difference:

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "
import sys; sys.path.insert(0, 'tests')
from test_no_dead_helpers import _public_functions, _referenced_names, _prompt_texts, DEAD_ALLOWLIST, PROMPT_ONLY
import re
ref, prompts, known = _referenced_names(), _prompt_texts(), _public_functions()
for key in sorted(known):
    name = key.split(':', 1)[1]
    if name in ref: continue
    hit = next((l for l, t in prompts if re.search(rf'\b{re.escape(name)}\b', t)), '')
    bucket = 'PROMPT_ONLY' if hit else 'DEAD_ALLOWLIST'
    listed = key in (PROMPT_ONLY if hit else DEAD_ALLOWLIST)
    if not listed: print(f'ADD to {bucket}: \"{key}\": \"{hit or \"unreferenced at 2.1.10\"}\",')
for key in sorted(DEAD_ALLOWLIST | PROMPT_ONLY):
    if key not in known: print(f'REMOVE (gone): {key}')
    elif key.split(':', 1)[1] in ref: print(f'REMOVE (has a caller): {key}')
"
```

Apply every printed line to the two dictionaries in `helpers/tests/test_no_dead_helpers.py`. Each `ADD to DEAD_ALLOWLIST` line needs its own one-line reason, not the seed string, because the name was not in this plan's verified inventory.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_no_dead_helpers.py -v`

Expected: PASS, four tests.

- [ ] **Step 5: Run the whole suite and the checkers**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Expected: no failures. The suite total moved from the 1766 baseline: Plan 1 and this plan both add and delete tests, so the count is not monotonic. Record the new total in the changelog entry.

- [ ] **Step 6: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.12"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_no_dead_helpers.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(helpers): add the REQ-48 dead-helper gate"
```

Version `2.1.11` is skipped. Task 4 has one commit, because the red state and the reconciled state live in the same file and the intermediate state has no separate deliverable. Steps 2 and 3 still run the red phase; they just do not commit it.

---

## Self-review

**1. Specification coverage.** Group 2 names four requirements. REQ-45 is Task 1. REQ-46 is Task 2. REQ-47 is Task 3, redirected by ruling R-1 from `scanscope.py` to `scope.py` and `scanscope.rel_to_root`. REQ-48 is Task 4, reseeded by ruling R-4 and correction C-5. No Group 2 requirement is unaddressed.

**2. Placeholder scan.** Every code step carries the real code. The two dictionaries in Task 4 hold the 37 and 32 names an AST-precise scan returned, not a count. Task 2 Step 7 and Task 3 Step 6 name the exact file and line of each edit rather than showing a rewritten README, because the README text depends on Plan 1's edits to the same rows.

**3. Type consistency.** `run_postflight`'s signature is identical in Task 1's Interfaces block, its docstring, and the driver call. `_file_of(where: str) -> str` takes the same argument in `_merge` and in `_drift_since`'s caller. `changed_files_between` is the import alias for `diffscope.changed_files`, and the plan states why the alias is required. `DEAD_ALLOWLIST` and `PROMPT_ONLY` are both `dict[str, str]` keyed `"<module>.py:<function>"`, and all four Task 4 tests read them with that key shape.

**4. Ordering.** Task 4 must run last: its two dictionaries describe the tree after Tasks 1 to 3. Tasks 1, 2, and 3 are independent of each other and may run in any order.
