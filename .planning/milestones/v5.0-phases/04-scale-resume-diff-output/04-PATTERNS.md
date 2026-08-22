# Phase 4: Scale, Resume & Diff Output - Pattern Map

**Mapped:** 2026-08-20
**Files analyzed:** 7 (2 new, 5 extended)
**Analogs found:** 7 / 7 — every file has an exact in-repo analog already; this phase is additive
to Phases 2-3's existing machinery, not new architecture (per RESEARCH.md's own framing).

All paths are relative to `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` unless
otherwise noted.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `bundle.py` (NEW) | utility (pure grouping) | transform | `file_select.py` (`partition`) | exact — same "pure function over `list[ChangedFile]`, returns a frozen-dataclass grouping" shape |
| `review_coverage.py` (EXTEND — model/profile identity) | model / state machine | CRUD (state transitions) | itself, `recorded_return_source` in `review_agent.py` for the rejection idiom | exact (same file) / role-match (rejection idiom) |
| `review_agent.py` (EXTEND — bundle-aware `parse_review_response`) | service (parser) | transform | itself (`parse_review_response`, `ReviewPlanEntry`) | exact (same file) |
| `review_comments.py` (NEW) | service (artifact writer) | file-I/O | `report.py` (`write_review_ledger`) | exact — same writer idiom (`_atomic_write` + `json.dumps(..., indent=2)` + dataclass→dict) |
| `sarif.py` (EXTEND — `partialFingerprints`) | utility (pure transform) | transform | itself (`to_sarif`), `fingerprint.py` (hash primitive) | exact (same file) / role-match (hash primitive) |
| `cli.py` (EXTEND — `--concurrency`/`--timeout`/`--max-git-procs` + bounded git fan-out) | controller (CLI entrypoint) | request-response | itself (`run_review`), `prefilter.py` (`ThreadPoolExecutor` fan-out) | exact (same file) / exact (concurrency pattern) |
| `test_bundle.py`, `test_review_coverage.py` (EXTEND), `test_sarif.py` (EXTEND), `test_review_agent.py`/`test_review_comments.py` (NEW) | test | — | `tests/test_review_coverage.py`, `tests/test_sarif.py`, `tests/test_review_agent.py` (existing siblings) | exact |

## Pattern Assignments

### `bundle.py` (NEW) — utility, transform

**Analog:** `file_select.py` (full file read this session, 201 lines)

**Imports pattern** (`file_select.py:1-14`):
```python
"""Partition changed files into reviewable and excluded sets — path-shaped, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
```
`bundle.py` should mirror this: `from __future__ import annotations`, stdlib-only imports, plus
`from sec_overlay.diffscope import ChangedFile` for the input type (per RESEARCH.md Pattern 1's
example).

**Core pattern — frozen-dataclass output + pure function** (`file_select.py:123-150`):
```python
@dataclass(frozen=True)
class ExcludedFile:
    """A changed file routed out of review, with the reason it was excluded."""
    path: str
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in EXCLUSION_REASONS:
            raise ValueError(...)

@dataclass
class Selection:
    reviewable: list[ChangedFile] = field(default_factory=list)
    excluded: list[ExcludedFile] = field(default_factory=list)

def partition(
    records: list[ChangedFile],
    *,
    diff_line_counts: dict[str, int],
    binary_paths: frozenset[str] | set[str],
) -> Selection:
```
`bundle.py::group_bundles(reviewable: list[ChangedFile]) -> list[ReviewUnit]` copies this exact
shape: a frozen dataclass for the output unit (`ReviewUnit`, per RESEARCH.md's example at
research lines 209-224), a pure function with no I/O, explicit typed input parameter name
(never accept the raw unfiltered `changed_file_records` — see Common Pitfall 4 in research).

**Error handling:** `file_select.py` raises `ValueError` in `__post_init__` for an invalid
enum member — match this for any `ReviewUnit` invariant (e.g. `files` must be non-empty).

**No test file exists yet for `file_select.py`'s exact counterpart to copy 1:1** — use
`tests/test_review_coverage.py`'s structure (plain `assert`-based pytest functions, one behavior
per test, no fixtures beyond simple constructors) as the test-file shape for `test_bundle.py`.

---

### `review_coverage.py` (EXTEND) — model, CRUD state transitions

**Analog:** itself (full file read this session, 171 lines) — see `MANIFEST_VERSION`,
`_ALLOWED_TRANSITIONS`, `CoverageManifest.__init__`, `.add()`, `.load()`, `.to_dict()`.

**Full current file already read; key excerpts to extend from:**

`__init__` (`review_coverage.py:52-65`):
```python
def __init__(self, base_sha: str, head_sha: str, path: Path) -> None:
    self.version = MANIFEST_VERSION
    self.base_sha = base_sha
    self.head_sha = head_sha
    self.path = path
    self._seal: str | None = None
    self.files: list[FileCoverage] = []
```
Add `model: str | None = None, profile: str | None = None` constructor params here — same
pattern as `base_sha`/`head_sha`, per RESEARCH.md Pattern 3 Option A (recommended).

`to_dict()` (`review_coverage.py:139-147`) and `load()` (`review_coverage.py:152-170`) must
grow the same two fields symmetrically — `to_dict` writes them, `load` reads them with
`data.get("model")`/`data.get("profile")` (default `None`, matching the optional-fields style
already used for `note` at `review_coverage.py:167`: `note=entry.get("note")`).

**Rejection-idiom analog for the new `validate_identity` function** —
`review_agent.py::recorded_return_source` (`review_agent.py:261-262`):
```python
if envelope.get("base") != base or envelope.get("head") != head:
    raise ValueError(f"recorded return for {path} was captured for a different base/head")
```
Copy this exact "explicit field-equality check, raise with both values named" shape for
`validate_identity(manifest, *, model, profile)` — do not build a generic diffing utility
(per RESEARCH.md's Don't Hand-Roll table, row "Stale-run rejection").

**State-transition idiom to reuse for SCALE-02's timeout** — `.fail()` already exists
(`review_coverage.py:96-98`):
```python
def fail(self, file_path: str, note: str | None = None) -> None:
    """Transition ``pending`` or ``in_review`` to ``failed``, recording ``note``."""
    self._transition(file_path, "failed", note=note)
```
The timeout guard calls this verbatim (`manifest.fail(path, note="timeout")`) for every file in
a timed-out bundle — no new transition, no new state (per Pitfall 3: iterate `unit.files`, not
just the in-flight file).

**`seal()`'s raise-on-incomplete** (`review_coverage.py:130-137`) is the exact mechanism that
will raise `CoverageTransitionError` if a timeout handler misses a sibling file — this is the
regression signature named in Pitfall 3's "Warning signs".

---

### `review_agent.py` (EXTEND) — service/parser, transform

**Analog:** itself (`parse_review_response`, `review_agent.py:116-183`, full excerpt already
read).

**The one required change (Pitfall 1):** line 165 —
```python
if entry.get("path") != path:
    discarded += 1
    continue
```
must become `if entry.get("path") not in bundle_paths:` where `bundle_paths` is the bundle's
member-path set, not a single `path` string. `_stable_finding_id`, `Finding(...)`'s `file=path`
assignment (line 177) needs the *matched* path from the entry, not the outer loop's single
`path` var, once multi-file bundles are possible.

**Sibling-record pattern for a new bundle-aware plan entry** — `ReviewPlanEntry`
(`review_agent.py:197-205`):
```python
@dataclass(frozen=True)
class ReviewPlanEntry:
    """One `--prepare` plan entry: where its prompt lives and what to record it under."""
    path: str
    prompt_path: str
    agent_label: str
    base: str
    head: str
```
Extend or add a bundle-aware variant using this exact `@dataclass(frozen=True)` + docstring
shape — `write_review_plan` (`review_agent.py:208-220`) already does `_atomic_write(path,
json.dumps([asdict(e) for e in entries], indent=2))`, reusable as-is if the plan entry keeps a
`path`-shaped identity field.

---

### `review_comments.py` (NEW) — service/artifact writer, file-I/O

**Analog:** `report.py::write_review_ledger` (`report.py:811-886`, full excerpt already read).

**Writer idiom to copy exactly:**
```python
def write_review_ledger(
    ws: Workspace,
    *,
    position_reviews: list[PositionResult],
    dropped: list,
    ...
) -> Path:
    ledger = {
        "position_reviews": [...],
        "dropped": [asdict(d) if is_dataclass(d) else d for d in dropped],
        ...
    }
    path = ws.artifacts / "review_ledger.json"
    _atomic_write(path, json.dumps(ledger, indent=2))
    return path
```
`write_review_comments(ws, comments, manifest_dict) -> Path` mirrors this: keyword-only inputs,
a single dict literal assembled from dataclass-to-dict conversions, `ws.artifacts / "<name>.json"`
path, `_atomic_write` + `json.dumps(..., indent=2)`, return the `Path`. Import line to copy:
`from sec_overlay.workspace import Workspace, _atomic_write` (`report.py:22`).

**Field source mapping (all verified against `models.py`, `Finding` dataclass fields
`file:106-123`):** `path` ← `finding.file`, `line` ← `finding.line`, `existing_code` ←
`finding.evidence`, `content` ← `finding.message`, `side` ← module-level constant
`DEFAULT_SIDE = "RIGHT"` (Pitfall 8 — never inline the literal).

**Error handling:** none needed beyond what `_atomic_write` already provides — this is a pure
serialization step over already-validated in-memory data, matching `write_review_ledger`'s own
lack of a try/except.

---

### `sarif.py` (EXTEND) — utility, pure transform

**Analog:** itself (`sarif.py`, full 91-line file already read).

**Exact insertion point** — inside `to_sarif`'s per-finding loop (`sarif.py:67-83`):
```python
for f in findings:
    result = {
        "ruleId": f.rule_id,
        "level": _level(f.severity),
        "message": {"text": f.message},
        "locations": [...],
    }
    if f.id in suppressed_ids:
        result["suppressions"] = [...]
    results.append(result)
```
Add `result["partialFingerprints"] = {"sec-overlay/v1": _sarif_fingerprint(f)}` right after the
`suppressions` block, before `results.append(result)`.

**New helper function, hash primitive borrowed from `review_agent.py::_stable_finding_id`
(`review_agent.py:110-113`)** — same `hashlib.sha256(key.encode("utf-8")).hexdigest()[:N]`
shape, different key composition (per RESEARCH.md's explicit "why this must be a NEW function"
rationale — do not reuse `fingerprint.fingerprint()`, whose key is `rule_id|cls|anchor`, a
different identity concept):
```python
def _sarif_fingerprint(finding: Finding) -> str:
    """Compute Path|Category|ExistingCode fingerprint, excluding message text."""
    key = f"{finding.file}|{finding.cls}|{finding.evidence.strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
```
`.strip()` on `evidence` is required (Pitfall 9) — matches `positioning.py`'s existing
whitespace-tolerant comparison convention (`stripped_needle = [line.strip() for line in
needle_lines]`).

**Import to add:** `import hashlib` at the top of `sarif.py` (currently absent — file has only
`from __future__ import annotations` and `from sec_overlay.models import Finding, Severity`).

---

### `cli.py` (EXTEND) — controller, request-response

**Analog:** itself (`run_review`, `cli.py:105-244`, full excerpt already read) for the wiring
points; `prefilter.py:225-230` for the concurrency primitive.

**Bounded git fan-out — exact primitive to copy** (`prefilter.py:225,230`):
```python
workers = max_workers or max(1, min(8, (os.cpu_count() or 2) - 1))
with ThreadPoolExecutor(max_workers=workers) as ex:
    results = list(ex.map(lambda u: u(), units))
```
Apply this shape to the two existing serial git-subprocess loops in `run_review`:
1. `diff_line_counts` dict comprehension (`cli.py:196-199`):
   ```python
   diff_line_counts = {
       record.path: file_diff_line_count(record.path, base_sha, head_sha, runner=r)
       for record in records
   }
   ```
   becomes `ex.map(lambda record: file_diff_line_count(...), records)` inside a
   `ThreadPoolExecutor(max_workers=args.max_git_procs)`, then zipped back into a dict by path.
2. The per-file coverage loop's git calls (`cli.py:224-229`):
   ```python
   diff_text_by_path[record.path] = file_diff_text(record.path, base_sha, head_sha, runner=r)
   hunks_by_path[record.path] = parse_hunks(diff_text_by_path[record.path])
   file_text_by_path[record.path] = file_text_at_ref(record.path, head_sha, runner=r)
   ```
   is the block SCALE-02's per-bundle timeout guard wraps — **must use `.map()`, never
   `as_completed()`**, to preserve `prefilter.py`'s documented byte-identical-ordering
   guarantee (Pitfall 5).

**Manifest-mutation ordering constraint (Pitfall 6):** the identity check (`validate_identity`
from `review_coverage.py`) must run before `cli.py:216`'s `CoverageManifest(...)` construction
and before `cli.py:222`'s first `manifest.add(record.path)` call — i.e., as the very first
action after `resolve_ref_sha` (`cli.py:180-181`), loading any existing manifest at
`ws.artifacts / MANIFEST_FILENAME` read-only first.

**Argparse wiring:** no existing `--concurrency`/`--timeout`/`--max-git-procs` flags exist in
`cli.py` today (grep confirms zero matches) — add them as new `argparse` options following
whatever existing flag style `cli.py`'s argument parser uses for `--rule`/`--exclude`
(not excerpted here — read the parser block directly when implementing, same file).

**Docstring convention** — `run_review`'s Google-style docstring (`cli.py:117-169`, already
excerpted in full above) is the exact structure (`Args:`/`Returns:`) new/changed parameters must
be documented in.

## Shared Patterns

### Atomic, crash-safe artifact writes
**Source:** `workspace.py:107` (`_atomic_write`), used by `review_coverage.py:150`,
`review_agent.py:219`, `report.py:886`
**Apply to:** `bundle.py` (if it persists anything — likely not, pure function), `review_coverage.py`
(identity fields), `review_comments.py` (new artifact)
```python
from sec_overlay.workspace import _atomic_write
_atomic_write(path, json.dumps(payload, indent=2))
```

### Bounded `ThreadPoolExecutor.map` fan-out (never `as_completed`)
**Source:** `prefilter.py:225-230,273` (docstring/comment explicitly names the
determinism property)
**Apply to:** `cli.py`'s two git-subprocess hot loops (`--max-git-procs`)
```python
workers = max_workers or max(1, min(N, (os.cpu_count() or 2) - 1))
with ThreadPoolExecutor(max_workers=workers) as ex:
    results = list(ex.map(worker_fn, items))  # order-preserving — required for determinism
```

### Explicit field-equality rejection (no generic diff utility)
**Source:** `review_agent.py:261-262` (`recorded_return_source`'s base/head check)
**Apply to:** `review_coverage.py`'s new `validate_identity(model, profile)` check
```python
if existing.model is not None and existing.model != model:
    raise ValueError(f"... changed from {existing.model!r} to {model!r}")
```

### `hashlib.sha256(...).hexdigest()[:N]` identity hash
**Source:** `review_agent.py:110-113` (`_stable_finding_id`), `review_agent.py:186-194`
(`agent_label`)
**Apply to:** `sarif.py::_sarif_fingerprint`, `bundle.py::ReviewUnit.unit_id` (deterministic
label from sorted member paths)

### Frozen-dataclass state/record shapes
**Source:** `file_select.py:123-147` (`ExcludedFile`, `Selection`), `review_agent.py:197-205`
(`ReviewPlanEntry`), `review_coverage.py:36-42` (`FileCoverage`)
**Apply to:** `bundle.py::ReviewUnit`, `review_comments.py::DiffComment`

## No Analog Found

None — every file in this phase's scope has a direct or near-direct in-repo analog (per
RESEARCH.md's own "Key insight": Phase 4 is a thin addition on existing Phase 2-3 machinery).

## Metadata

**Analog search scope:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` (all
modules named in RESEARCH.md's Recommended Project Structure)
**Files scanned/read in full this session:** `review_coverage.py` (171 lines), `sarif.py` (91
lines), `review_agent.py:100-269`, `cli.py:105-244`, `report.py:811-886`, plus targeted greps
of `prefilter.py`, `file_select.py`, `models.py`, `workspace.py`
**Pattern extraction date:** 2026-08-20
