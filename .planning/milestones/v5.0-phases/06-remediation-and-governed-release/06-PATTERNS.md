# Phase 6: Remediation and Governed Release - Pattern Map

**Mapped:** 2026-08-21
**Files analyzed:** 8 (all modifications; no new source files — D-11 ledger and
D-15 test are new files with clear analogs)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `helpers/sec_overlay/cli.py` (`review` subparser + `run_review`, D-03/D-04) | CLI/controller | request-response | same file, `audit` subparser + `main()` `args.cmd == "audit"` branch | exact (same file, sibling verb) |
| `helpers/sec_overlay/phases.py` (`PHASE_TABLE`, D-01) | config/table | batch/sequencer | same file, existing `PhaseSpec` entries (`artifact-review`, `arch-gate`) | exact |
| `helpers/sec_overlay/driver.py` (`DETERMINISTIC_ACTIONS`, D-01) | service/dispatcher | event-driven (phase dispatch) | same file, `_act_arch_gate`/`_act_tm_gate`/`_act_artifact_gate` + `DETERMINISTIC_ACTIONS.update(...)` | exact |
| `helpers/skills/sec-overlay/agents/redteam.md` (prose rewrite, D-02) | agent prompt (doc) | request-response (LLM prompt) | same file (rewrite in place); sibling `agents/*.md` for prose conventions | exact |
| `plugins/sec-overlay/CLAUDE.md` (submodule claim fix, D-04) | doc/config | — | same file | exact |
| `helpers/tests/README.md` (cwd-bug explanation fix, D-04) | doc | — | same file | exact |
| `helpers/tests/test_review_findings.py` (new, D-08 subset backstop) | test | transform (pure function assertion) | `helpers/tests/test_contracts.py` (existing pure-function/contract test style) | role-match |
| `helpers/tests/test_frozen_contract.py` (new, D-15 identity guard) | test | CRUD-adjacent (checksum/AST compare) | `helpers/tests/test_fingerprint.py` (golden-value assertion style already in suite) | exact |

## Pattern Assignments

### `helpers/sec_overlay/cli.py` — `review` subparser gains `--workspace` (D-03)

**Analog:** same file, `audit` subparser (lines 606-610) and its handling in
`main()` (lines 695-710).

**Argparse pattern to copy** (`cli.py:606-610`):
```python
audit = sub.add_parser("audit", help="run the deterministic audit driver")
audit.add_argument("--target", required=True)
audit.add_argument("--workspace")
audit.add_argument("--config", required=True)
audit.add_argument("--sha")
```
Add `review.add_argument("--workspace", default=None, help="Override the workspace; "
"mirrors `audit`'s flag (default: per-repo sidecar beneath --root).")` next to the
existing `review` subparser block (`cli.py:612-653`).

**Dispatch pattern to copy** (`cli.py:695-710`):
```python
if args.cmd == "audit":
    ...
    if args.workspace:
        ws = load_paths(workspace=args.workspace)
    else:
        memory = RepoMemory.for_target(args.target)
        memory.ensure(target=args.target)
        ws = memory.workspace
```
`run_review` (`cli.py:233`) currently resolves its workspace internally from
`root` with no override path — thread `args.workspace` through to `run_review`
the same way `args.workspace` is threaded to `AuditContext` for `audit`,
resolving via `load_paths(workspace=...)` when set, else falling back to the
existing per-repo-sidecar resolution. Extend `run_review`'s docstring
`Args:` block (`cli.py:273-309`) with a `workspace` entry matching the style of
its `model` entry.

### `helpers/sec_overlay/cli.py` — WR-01 clean exit-2 for nonexistent `--root` (D-04)

**Analog:** same file, existing exit-2 validation block (`cli.py:321-327`):
```python
try:
    _bounded_int(concurrency, flag="--concurrency", ceiling=MAX_WORKERS)
    _bounded_int(timeout, flag="--timeout", ceiling=MAX_TIMEOUT_SECONDS)
    _bounded_int(max_git_procs, flag="--max-git-procs", ceiling=MAX_WORKERS)
except ValueError as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 2
```
Add a root-existence check before any git subprocess call, same
`print(..., file=sys.stderr); return 2` shape — replaces the raw
`FileNotFoundError` traceback WR-01 reports. Message should name the flag and
path, matching the `_bounded_int` error string convention (`error: <what> <why>`).

### `helpers/sec_overlay/phases.py` — wire `redteam`/`postflight` into `PHASE_TABLE` (D-01)

**Analog:** same file, existing agent-phase and deterministic-phase entries
(`phases.py:88-122`), e.g.:
```python
PhaseSpec(
    "artifact-review",
    "agent",
    (_artifact_gate_json,),
    (_artifact_review_json,),
    prompt="artifact-review.md",
),
```
Add two new `PhaseSpec` entries after `"artifact-review"`:
- `redteam` — kind `"agent"`, prompt `"redteam.md"`, input `(_artifact_review_json,)`
  (or whatever artifact redteam actually reads — verify against
  `redteam.write_plan`'s workspace reads), output a new path helper for
  `redteam-plan.md` (mirror `_report`/`_sarif` path-helper style at
  `phases.py:72-77`).
- `postflight` — kind `"deterministic"`, input the redteam output, output a
  path helper for the `prior_context`/`MEMORY.md` artifact
  `postflight.run_postflight` writes.

Add a corresponding path-helper function above `PHASE_TABLE`, matching the
existing `_artifact_gate_json`/`_artifact_review_json` pair style
(`phases.py:80-86`).

### `helpers/sec_overlay/driver.py` — register `postflight` deterministic action (D-01)

**Analog:** same file, `_act_arch_gate`/`_act_tm_gate`/`_act_artifact_gate`
(`driver.py:233-283`) and the `DETERMINISTIC_ACTIONS.update({...})` block
(`driver.py:286-299`).

**Core pattern to copy** (`driver.py:233-241`, simplest case — no gate JSON):
```python
def _act_artifact_gate(ctx: AuditContext) -> None:
    from sec_overlay.artifact_gate import run_artifact_gate  # local: avoid import cycle

    errors = run_artifact_gate(ctx.ws)
    if errors:
        raise PhaseHalt(
            f"artifact-gate rejected {len(errors)} issue(s): " + "; ".join(errors)
        )
```
Add `_act_postflight(ctx: AuditContext) -> None` calling
`sec_overlay.postflight.run_postflight(ctx.ws, ctx.sha)` (local import, same
cycle-avoidance comment convention), then add `"postflight": _act_postflight`
to the `DETERMINISTIC_ACTIONS.update({...})` dict (`driver.py:286-299`).
`redteam` stays an **agent** phase (SKILL.md's orchestrator dispatches
`agents/redteam.md`) — it gets a `PhaseSpec` in `phases.py`, not an entry in
`DETERMINISTIC_ACTIONS`.

### `helpers/skills/sec-overlay/agents/redteam.md` — 2-way mechanical split prose (D-02)

**Analog:** same file (rewrite in place). No code change to
`sec_overlay/redteam.py:39` `wants_runtime()` — its actual logic is the source
of truth the prose must now describe accurately (status-forces-inclusion
kept as-is). Per `plugins/sec-overlay/CLAUDE.md`'s "preserve hard rules
verbatim" convention, keep `ANTI_MANIPULATION`/`TOOL_TRUST`/other
`prompt-constants.md` blocks this file already imports untouched — only the
mechanical-split description changes.

### `helpers/tests/test_frozen_contract.py` (new, D-15) — identity guard

**Analog:** `helpers/tests/test_fingerprint.py` (golden-value assertion
pattern already in the suite — reuse its fixture/import style rather than
inventing a new one). Planner should grep `test_fingerprint.py` for its
exact `fingerprint()` golden-value assertion before choosing checksum vs AST
comparison for `models.py`/`evidence.py` identity, per Claude's Discretion.

### `helpers/tests/test_review_findings.py` (new or extended, D-08) — subset backstop

**Analog:** `helpers/sec_overlay/review_findings.py:107` `apply_profile()` is
the function under test — synthesize `GatedFinding` inputs (per the
`GatedFinding`/`ReviewFinding` dataclasses at `review_findings.py:68-89`) and
assert `security-kept ⊆ general-kept`. Match `helpers/tests/test_contracts.py`
for pure-function test structure (no mocks needed — `apply_profile` is a pure
transform per its docstring).

---

## Shared Patterns

### Exit-code convention (CLI validation failures)
**Source:** `helpers/sec_overlay/cli.py:321-327` and the other `return 2`
sites (`cli.py:351,367,373,462,527`).
**Apply to:** WR-01 fix and the new `--workspace` flag's validation (if any
bound-check is needed).
```python
except ValueError as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 2
```

### `--workspace` override resolve-or-fallback
**Source:** `helpers/sec_overlay/cli.py:658-669` (scan) and `698-703` (audit) —
identical shape repeated per-verb:
```python
if args.workspace:
    ws = load_paths(workspace=args.workspace)
else:
    memory = RepoMemory.for_target(args.target)
    memory.ensure(target=args.target)
    ws = memory.workspace
```
**Apply to:** `review`'s new `--workspace` flag (D-03), adapted for
`review`'s `root`-based (not `target`-based) resolution.

### Deterministic phase action registration
**Source:** `helpers/sec_overlay/driver.py:286-299` `DETERMINISTIC_ACTIONS.update({...})`.
**Apply to:** the new `postflight` action (D-01); `redteam` is excluded — it
is an agent phase dispatched via `render_dispatch` (`driver.py:103-130`), not
a `DETERMINISTIC_ACTIONS` entry.

### PhaseSpec path-helper-per-artifact
**Source:** `helpers/sec_overlay/phases.py:40-86` — one small `_xxx(ws) -> Path`
function per artifact, referenced by name (not inline lambda) in the
`PhaseSpec` tuple.
**Apply to:** the new `redteam`/`postflight` output-artifact helpers.

## No Analog Found

None — every file in scope has a same-file or same-role analog already in
the codebase; this phase is a remediation/wiring pass, not new-feature work.

## Metadata

**Analog search scope:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/`,
`plugins/sec-overlay/skills/sec-overlay/helpers/tests/`,
`plugins/sec-overlay/skills/sec-overlay/agents/`, `plugins/sec-overlay/CLAUDE.md`
**Files scanned:** `cli.py`, `phases.py`, `driver.py`, `redteam.py`,
`postflight.py`, `review_findings.py`, `redteam.md`, `test_fingerprint.py`,
`test_contracts.py`, `CLAUDE.md` (root and skill-level)
**Pattern extraction date:** 2026-08-21
