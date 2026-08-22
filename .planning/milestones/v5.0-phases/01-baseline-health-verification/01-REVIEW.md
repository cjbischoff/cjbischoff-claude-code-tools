---
phase: 01-baseline-health-verification
reviewed: 2026-08-17T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - CHANGELOG.md
  - README.md
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/stage_validate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/graph_target/app/api.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/fixtures/graph_target/app/db.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bench.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bucket_b.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_calibrate.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_citations.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_factcheck_baseline_envelope.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_patch_status.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_postflight.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prefilter.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_profile.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_matcher.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_structural_index.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_wiring.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 01: Code Review Report

**Reviewed:** 2026-08-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** clean

## Narrative Findings (AI reviewer)

## Summary

Reviewed all 22 files in scope for Phase 01 (`ruff`/`ty` baseline-health fixes) at standard
depth, reading full file contents and cross-referencing each change against its actual
`git diff 18d01c3^..HEAD` (not just the CHANGELOG/README narrative, to avoid taking the
implementer's own account at face value).

**Frozen-contract check (explicit requirement):** confirmed via `git log --oneline
18d01c3^..HEAD -- .../sec_overlay/models.py .../sec_overlay/evidence.py` (empty output) and
`git diff --stat 18d01c3^..HEAD` (neither path appears in the 30-file changed list) that
`sec_overlay/models.py` and `sec_overlay/evidence.py` were **not touched** in this phase. No
finding suggests otherwise.

**Behavior-preservation check (core adversarial question):** traced every production and test
diff line-by-line against the pre-image:

- `stage_validate.py`: the `_MISSING`-sentinel rewrite of `_validate_runtime_test`'s
  `payloads` check is logically identical to the old `"payloads" in obj` check. The new
  `_adapt_dict`/`_adapt_optional_dict` wrappers are additive — they convert a previously
  possible `AttributeError` crash (non-dict stage output) into a returned validation error,
  which is a strict improvement, not a behavior change for well-formed dict input. All non-dict
  paths for `discovery-ledger`, `coverage-ledger`, `recon`, `scan-profile`, and `context` now
  fail closed instead of crashing.
- `workspace.py`: the hand-written `__init__` replacing `__post_init__` sets exactly the same
  four fields (`root`, `reports_dir`, `findings_dir_override`, `kb_dir_override`), in the same
  order, with the same defaults and the same `Path(...)` coercion semantics the dataclass-driven
  `__post_init__` used to apply after auto-generated field assignment. No parameter-order or
  default-value drift found.
- Test-file fixture builders (`test_bench.py`, `test_citations.py`,
  `test_factcheck_baseline_envelope.py`, `test_profile.py`, `test_report.py`): each `dict +
  .update(kw) + Cls(**d)` splat was replaced with `dataclasses.replace(base, **kw)`, which is
  semantically equivalent for the same `kw` overrides in every call site checked.
- `test_prefilter.py`/`test_wiring.py`: `Exclusions([], [], [])` → `Exclusions(set(), [], set())`
  — verified against the actual `Exclusions` dataclass field order/types
  (`sec_overlay/exclusions.py:27-29`: `rule_ids: set[str]`, `paths: list[str]`, `classes:
  set[str]`) — the fix matches field types positionally; no argument-order swap.
- `test_patch_status.py`: the fake-runner rewrite from a closure with a `.calls` attribute
  bolted onto a function object, to a `_Runner` class with `calls` as a real `__init__`-set
  instance attribute, is behaviorally identical (same call-recording, same
  pop-next-returncode-per-call semantics).
- `test_structural_index.py`: `"\n".join([...])` → adjacent string literal concatenation with
  inline `\n` — produces byte-identical `out` string; the trailing item (`"...prose"`, no
  `\n`) is preserved correctly in both forms.
- `test_calibrate.py`, `test_bucket_b.py`, `test_rule_matcher.py`: added `assert x is not None`
  guards before dereferencing narrow, rather than replace, the prior behavior — a `None` value
  now fails loudly via `AssertionError` at the guard instead of via a later `TypeError`/
  `AttributeError` at the point of use. No assertion was weakened; each addition is a stricter
  gate, not a looser one.
- Fixture files (`tests/fixtures/graph_target/app/{api,db}.py`): confirmed via
  `sec_overlay/graph.py`'s `build_tier1()` and `test_graph.py` that these files are parsed
  structurally (regex-based), never imported/executed by the test suite, so the `cursor`/`app`
  stub placement after their point of use cannot cause a runtime `NameError` in practice. The
  pinned node IDs `app/db.py:1:run_query`, `app/api.py:4:handler`, `app/api.py:10:get_widget`
  that `test_graph.py` asserts on were manually verified against the current file line numbers
  and match exactly.

No weakened assertions, no altered fixture semantics, and no production-behavior change were
found. No security issues (injection, hardcoded secrets, unsafe deserialization, path traversal)
were found in the reviewed diff. Two minor, pre-existing observations are recorded below as
Info; neither was introduced by this phase and neither rises to Warning since both are provably
inert given the current call graph.

## Info

### IN-01: Dead `isinstance` branch in `_validate_context`, now provably unreachable

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/stage_validate.py:44`
**Issue:** `prov = obj.get("provenance", {}) if isinstance(obj, dict) else {}` guards against
`obj` not being a dict, but `_validate_context` is only ever invoked through
`_VALIDATORS["context"] = _adapt_dict(_validate_context)` (line 84), and `_adapt_dict` (lines
51-65) already rejects any non-dict `obj` before calling the wrapped function. The `else {}`
branch can never execute through that call path. This is pre-existing code untouched by this
phase's diff (the line does not appear in `git diff 18d01c3^..HEAD` for this file) — the
`_adapt_dict` wrapper introduced by this phase made an already-questionable defensive branch
newly and *provably* dead, rather than merely redundant. Not a regression; flagged because the
adapter refactor is the right moment to notice it.
**Fix:** Since the type annotation `obj: dict` (line 39) is now enforced by the caller,
simplify to:
```python
def _validate_context(obj: dict) -> list[str]:
    try:
        errors = Context.from_dict(obj).validate()
    except (TypeError, KeyError, AttributeError) as e:
        return [f"context is not a valid Context document: {e}"]
    prov = obj.get("provenance", {})
    read = set(prov.get("docs_read", []) or [])
    ...
```

### IN-02: `Workspace` combines `@dataclass` with a hand-written `__init__`

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py:28-42`
**Issue:** `Workspace` is `@dataclass`-decorated but now defines its own `__init__` instead of
relying on `__post_init__`. This is valid Python (a dataclass skips generating `__init__` when
the class body already defines one) and was verified to preserve exact field-set/coercion
behavior versus the old `__post_init__`. It is a legitimate `ty`-satisfying pattern, not a bug.
Flagged only because a future maintainer skimming the `@dataclass` decorator and field list
might assume vanilla dataclass-generated `__init__` semantics (e.g. that adding a new field
automatically threads through `__init__`) — it no longer does; a new field requires updating the
manual `__init__` too, or the field silently keeps its class-level default regardless of what a
caller passes.
**Fix:** A one-line comment above the field block would close the gap for the next editor:
```python
@dataclass
class Workspace:
    # __init__ is hand-written below (not dataclass-generated) — adding a field here
    # requires adding the matching parameter to __init__ too.
    root: Path
    ...
```

---

_Reviewed: 2026-08-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
