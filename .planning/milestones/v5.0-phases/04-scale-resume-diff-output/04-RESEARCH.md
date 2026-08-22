# Phase 4: Scale, Resume & Diff Output - Research

**Researched:** 2026-08-20
**Domain:** Python stdlib concurrency/timeout bounding, git-diff review-mode resume/identity, SARIF fingerprinting, diff-anchored comment payloads (sec-overlay plugin, `helpers/sec_overlay/`)
**Confidence:** HIGH

## Summary

Phase 4 extends the diff-review pipeline (`cli.py::run_review`) that Phases 2-3 already built.
Every mechanism SCALE-01/02/03 and OUT-01/02 need already has a close architectural neighbor in
the codebase: `review_coverage.CoverageManifest`'s `pending -> in_review -> {done, failed}` state
machine and its `seal()` method (`complete`/`partial`) already implement the exact terminal-state
behavior SCALE-02 asks for — a timed-out unit only needs to call the existing `.fail(path,
note="timeout")`, no new state machine required. `review_agent.recorded_return_source` already
rejects a stale base/head pair before consuming a recorded return — the identical pattern SCALE-03
needs for model/profile identity. `file_select.partition()` already produces the `Selection`
SCALE-01's bundler must consume downstream, without touching `partition()` itself. `Finding.evidence`
is already backfilled from real on-disk text (never LLM-claimed) in `run_review` — this is OUT-01's
`existing_code` source, with zero new code needed to produce it correctly.

The stdlib is sufficient for every SCALE-02 mechanism: `concurrent.futures.ThreadPoolExecutor`
(already used in `prefilter.py` with an identical "byte-identical serial vs. concurrent" design
constraint) bounds concurrent git subprocess calls, and `subprocess.run(..., timeout=N)` plus
`subprocess.TimeoutExpired` bounds per-bundle wall time. No new dependency is justified or
permitted — `pyproject.toml` `dependencies = []` and REL-03 both require this stay true.

**Primary recommendation:** Build `bundle.py` as a new pure module downstream of
`file_select.partition()`; extend `review_coverage.CoverageManifest` (not a new file) with a
`model`/`profile` identity block sealed at first `add()` and checked on every resume before any
agent spawn; wrap `run_review`'s two git-subprocess hot loops in a `ThreadPoolExecutor` bounded by
`--max-git-procs`; wrap each bundle's coverage-loop body in a `subprocess.run(timeout=)`-style
wall-clock guard that calls the existing `manifest.fail(path, note="timeout")` on expiry; add a new
sibling module (e.g. `review_comments.py`) for OUT-01's payload, and extend `sarif.py::to_sarif`
in place for OUT-02's `partialFingerprints`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCALE-01 | `bundle.py` deterministically groups locale/config siblings and impl/test pairs into single review units, one file per unit as fallback, documented as a sec-overlay addition beyond OCR | See Architecture Patterns → Pattern 1 (Bundling as a New Stage); Don't Hand-Roll row 1; Common Pitfalls 1, 4 |
| SCALE-02 | `--concurrency` (default 8), per-bundle `--timeout` (default 10m), and `--max-git-procs` (default 16) bound execution; a timed-out bundle marks its files `failed` and the run terminal state becomes `partial` | See Architecture Patterns → Pattern 2 (Bounded Concurrency); Code Examples 1-2; Common Pitfalls 2, 3, 5 |
| SCALE-03 | Resume validates identity before any agent spawn — an implicit model or profile change is rejected with nothing persisted, and file reads stay pinned to sealed commit SHAs | See Architecture Patterns → Pattern 3 (Identity-Pinned Resume); Common Pitfalls 6, 7 |
| OUT-01 | Diff-review mode emits a diff-anchored comment payload `{path, line, side, existing_code, content}` alongside the existing SARIF, markdown, and per-finding files, with the coverage manifest included | See Architecture Patterns → Pattern 4 (Diff Comment Payload); Code Examples 3; Common Pitfalls 8 |
| OUT-02 | SARIF fingerprints use `Path\|Category\|ExistingCode` excluding message text | See Architecture Patterns → Pattern 5 (SARIF partialFingerprints); Code Examples 4; Common Pitfalls 9 |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| File bundling (SCALE-01) | Backend (deterministic Python) | — | Pure grouping logic over `Selection.reviewable`; no I/O beyond paths already collected by `file_select` |
| Concurrency/timeout bounding (SCALE-02, git calls) | Backend (deterministic Python) | — | Bounds `subprocess` calls inside `cli.py::run_review`; no agent/model involvement |
| Concurrency bounding (SCALE-02, agent dispatch fan-out) | Orchestration (SKILL.md-driven agent dispatch) | Backend (plan entries it dispatches from) | `SKILL.md` already owns "dispatch in waves" (D-13); `--concurrency` formalizes the existing informal wave-size convention documented in `SKILL.md:129` |
| Resume/identity validation (SCALE-03) | Backend (deterministic Python, `review_coverage.py`) | — | Same tier that already owns `CoverageManifest`'s state and `seal()`; SHA pinning is already enforced by `resolve_ref_sha`/`file_text_at_ref` at this tier |
| Diff comment payload (OUT-01) | Backend (deterministic Python, `report.py`/new module) | — | Derived from `ReviewFinding`/`Finding.evidence`, already assembled at this tier in `write_report` |
| SARIF fingerprinting (OUT-02) | Backend (deterministic Python, `sarif.py`) | — | Pure function over already-assembled `Finding` fields, no new tier |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `concurrent.futures.ThreadPoolExecutor` | stdlib (3.12+) | Bound parallel git subprocess calls (`--max-git-procs`) | Already the established pattern in this codebase for bounded I/O-bound fan-out [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py:10,86,110,122,225,230,273] — `prefilter.py` uses `ThreadPoolExecutor(max_workers=workers)` with `workers = max_workers or max(1, min(8, (os.cpu_count() or 2) - 1))` and documents "byte-identical between serial (`max_workers=1`) and concurrent runs because `ThreadPoolExecutor.map` returns results in submission order" — the exact determinism property SCALE-02 needs preserved. |
| `subprocess.run(..., timeout=N)` / `subprocess.TimeoutExpired` | stdlib (3.12+) | Per-bundle `--timeout` wall-clock bound | Every git-calling function in this codebase already takes an injectable `runner=subprocess.run` keyword [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py:35,67,96,115,141,160] (`resolve_ref_sha`, `changed_file_records`, `file_diff_line_count`, `binary_paths`, `file_diff_text`, `file_text_at_ref` all take `*, runner=subprocess.run`) — `subprocess.run`'s own `timeout=` kwarg composes directly through this seam with no new abstraction. |
| `dataclasses` (frozen) | stdlib | New state/record types (bundle unit, identity block, comment payload) | Every existing sibling module in this codebase (`review_coverage.py`, `review_findings.py`, `review_agent.py`, `phase_gate.py`) uses `@dataclass(frozen=True)` exclusively for new state shapes [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py, review_findings.py:68-89, review_agent.py:197-206,223-229]. |
| `hashlib.sha256` | stdlib | SARIF fingerprint hash, bundle-unit label | Same primitive already used for `fingerprint.py`'s dedup fingerprint and `review_agent.agent_label`/`_stable_finding_id` [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py:110-113,186-194]. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` | stdlib | Serialize new artifacts (identity block, comment payload) | Matches every existing artifact writer (`review_coverage.py::to_dict`, `review_agent.py::write_review_plan`) |
| `workspace._atomic_write` | in-repo (not a library, but a mandatory reused helper) | Persist any new state file durably | Used by every existing state writer in this codebase [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py:27,219] (`from sec_overlay.workspace import ... _atomic_write`) — mkstemp-in-same-dir + `os.replace`, avoiding partial-write corruption on a crash mid-resume, which is precisely the failure window SCALE-03 must be robust to. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ThreadPoolExecutor` | `asyncio` + `asyncio.subprocess` | Async would require a new event-loop boundary threaded through `cli.py`'s synchronous call graph for no measurable benefit on I/O-bound `git` subprocess calls; rejected — adds an execution model the rest of the module doesn't use, violates "match existing conventions." |
| `ThreadPoolExecutor` | `multiprocessing.Pool` | Processes add serialization overhead and IPC complexity for what is pure I/O-wait (subprocess calls already run in their own OS process); `prefilter.py`'s existing precedent uses threads, not processes, for the identical shape of problem. |
| New `identity.json` sibling artifact for SCALE-03 | Extend `CoverageManifest` fields | See Architecture Patterns → Pattern 3 for the explicit recommendation and rationale; presented as a fork, not silently picked, since it is the one genuinely open design question in this phase. |

**Installation:**
```bash
# No installation required — every recommended tool is stdlib (Python 3.12+, already the
# project's floor). REL-03 requires helpers/pyproject.toml dependencies stay empty.
```

**Version verification:** `python3 --version` in the dev environment reports 3.13.14
[VERIFIED: shell `python3 --version` output this session] — above the project's declared floor.
`pyproject.toml` declares `requires-python = ">=3.12"`, `target-version = "py312"`, and
`dependencies = []` [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml:1-10]
— confirming both the floor and the zero-new-dependency constraint. `concurrent.futures` and
`subprocess` are part of the Python standard library since Python 3.2 and 3.0 respectively; no
registry version check applies to stdlib modules.

## Package Legitimacy Audit

No external packages are introduced by this phase. `helpers/pyproject.toml` `dependencies = []`
[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml:8] is a project invariant
(REL-03) this phase must not break. Every recommended tool (`concurrent.futures`, `subprocess`,
`dataclasses`, `hashlib`, `json`) ships in the Python standard library.

**Packages removed due to [SLOP] verdict:** none — no packages were proposed.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                        run_review(base, head, root, --concurrency, --timeout, --max-git-procs)
                                          |
                 +------------------------+------------------------+
                 |                        |                        |
        resolve_ref_sha(base)     resolve_ref_sha(head)     [SCALE-03: identity check]
                 |                        |                 CoverageManifest.load(existing)
                 +------------------------+                 if model/profile != recorded ->
                                          |                  reject, exit before ANY write
                          changed_file_records (git diff --name-status)
                                          |
                          file_select.partition()  -> Selection(reviewable, excluded)
                                          |
                     [SCALE-01] bundle.py: group_bundles(reviewable)
                     locale/config siblings + impl/test pairs -> ReviewUnit
                     ungrouped file -> ReviewUnit of size 1 (fallback)
                                          |
        +---------------[SCALE-02: --max-git-procs bound]------------------+
        |         ThreadPoolExecutor(max_workers=max_git_procs)            |
        |   per-file: file_diff_text / parse_hunks / file_text_at_ref      |
        +--------------------------------+----------------------------------+
                                          |
                     CoverageManifest.add/start (per file, per bundle)
                                          |
        +---------------[SCALE-02: --timeout per bundle]--------------------+
        |  wall-clock guard around each bundle's review-agent work unit     |
        |  on expiry -> manifest.fail(path, note="timeout") for every file  |
        |  in that bundle (never partial-file success inside one bundle)   |
        +--------------------------------+----------------------------------+
                                          |
                     review_source(path) -> live Finding list (per file)
                     [REVIEW_AGENT_CLAIM only -- never self-confirms]
                                          |
              evidence backfill: finding.evidence = real on-disk text
              at finding.line (never the LLM's claimed snippet)
                                          |
                     review_position_gate -> kept, dropped, declines
                     apply_profile -> ReviewFinding list
                     apply_verdict (reflection, retract-only)
                                          |
                     manifest.seal() -> "complete" | "partial"
                     [SCALE-02: any .fail() entry -> "partial"]
                                          |
                     write_report(...) :
                       - report.sarif  [OUT-02: partialFingerprints added]
                       - report.md
                       - findings/F-*.json
                       - review_ledger.json
                       - [OUT-01 NEW] review_comments.json
                         {path, line, side, existing_code, content}[]
                         + embedded coverage_manifest snapshot
```

### Recommended Project Structure

```
helpers/sec_overlay/
├── bundle.py              # NEW (SCALE-01): group_bundles(reviewable) -> list[ReviewUnit]
├── review_coverage.py      # EXTEND (SCALE-02/03): timeout-driven .fail(), identity block
├── review_agent.py         # EXTEND (SCALE-01): ReviewPlanEntry -> bundle-aware plan entry
├── review_comments.py      # NEW (OUT-01): build_comment_payload(...) -> review_comments.json
├── sarif.py                # EXTEND (OUT-02): partialFingerprints on each result
├── cli.py                  # EXTEND: --concurrency/--timeout/--max-git-procs argparse + wiring
tests/
├── test_bundle.py          # NEW — matches existing test_<module>.py convention
├── test_review_coverage.py # EXTEND — timeout/identity cases
├── test_sarif.py           # EXTEND — fingerprint cases
├── test_review_agent.py    # EXTEND or new test_review_comments.py
```

### Pattern 1: Bundling as a New Stage (SCALE-01)

**What:** `bundle.py` is a pure function operating on `file_select.partition()`'s
`Selection.reviewable` (`list[ChangedFile]`), grouping locale/config siblings (e.g. `en.json` /
`fr.json` under the same directory, or a `config.*.yaml` family) and impl/test pairs (e.g.
`foo.py` / `test_foo.py`) into a single `ReviewUnit`. Every file not matched by a grouping rule
becomes its own one-file `ReviewUnit` (explicit fallback, never dropped).

**When to use:** Immediately after `partition()`, before the per-file coverage-manifest loop and
before `--prepare`'s prompt-rendering loop in `cli.py::run_review`.

**Why NOT modify `partition()` itself:** `partition()`'s docstring and inline comment scope it
strictly to inclusion/exclusion decisions (`reviewable` vs. `excluded`, with reasons)
[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py — confirmed
via full read this session: `Selection`/`ExcludedFile`/`EXCLUSION_REASONS =
{deleted,binary,generated,not-allowlisted,too-large}` frozen dataclasses]. Grouping is a distinct
concern; conflating the two would force every `partition()` caller (including any future audit-mode
reuse) to reason about bundling even when it never dispatches an agent per unit.

**Example (recommended shape, not yet in codebase):**
```python
# Source: pattern inferred from this session's read of file_select.py's Selection shape
# and review_agent.py's existing ReviewPlanEntry (path, prompt_path, agent_label, base, head)
from dataclasses import dataclass
from sec_overlay.diffscope import ChangedFile

@dataclass(frozen=True)
class ReviewUnit:
    """One or more related changed files reviewed together as a single unit."""
    files: tuple[str, ...]      # always >=1; the fallback case has exactly 1
    unit_id: str                # deterministic, derived from sorted(files) — see agent_label

def group_bundles(reviewable: list[ChangedFile]) -> list[ReviewUnit]:
    """Deterministically group locale/config siblings and impl/test pairs.

    Every file not claimed by a grouping rule becomes its own one-file unit — the
    fallback this requirement names explicitly, never a silently dropped file.
    """
    # grouping logic: sibling detection by directory + filename pattern (locale/config),
    # and impl/test pairing by conventional naming (test_X.py <-> X.py, X.test.ts <-> X.ts)
    ...
```

**Documentation requirement (part of SCALE-01's own text):** "documented as a sec-overlay
addition beyond OCR" — this means `bundle.py`'s module docstring, plus
`skills/sec-overlay/helpers/README.md` (per the plugin's own README-tracks-code hard rule
[VERIFIED: plugins/sec-overlay/CLAUDE.md — "Hard rule — docs track code in the same commit... for
every staged file whose folder contains a tracked README.md, that README.md must also be staged"]),
must explicitly call out that grouping siblings into one review unit has no analog in the OCR
predecessor this harness's review mode otherwise mirrors — the planner must include a README-update
task in the same commit/task as `bundle.py`, not as an afterthought.

### Pattern 2: Bounded Concurrency and Timeout (SCALE-02)

**What:** Three independent bounds, three independent mechanisms:

1. **`--max-git-procs` (default 16)** bounds the two existing serial git-subprocess hot loops
   inside `cli.py::run_review`: the `diff_line_counts` dict-comprehension and the per-file
   `file_diff_text`/`parse_hunks`/`file_text_at_ref` block inside the coverage-manifest loop
   [file:line locations of these call sites were read in full in a prior session turn — see the
   `run_review` body; both loops call `runner=r` per file with no bound today]. Wrap each loop's
   body in `ThreadPoolExecutor(max_workers=args.max_git_procs).map(...)`, matching `prefilter.py`'s
   established pattern exactly.
2. **`--concurrency` (default 8)** bounds parallel `ReviewUnit` (bundle) processing/dispatch —
   both the deterministic Python loop that renders one prompt per bundle during `--prepare`, and
   (per `SKILL.md`'s existing informal "waves of three to four" convention
   [VERIFIED: plugins/sec-overlay/skills/sec-overlay/SKILL.md:129] — "matching the fan-out rule the
   audit pipeline already uses under provider load") the SKILL.md-driven agent-dispatch loop. This
   phase formalizes an existing informal convention into an explicit, user-controllable flag; it
   does not invent a new dispatch model.
3. **`--timeout` (per-bundle, default 10m)** bounds each bundle's total review-agent wall time.
   On expiry, call `manifest.fail(path, note="timeout")` for every file in that bundle — reusing
   `CoverageManifest`'s existing transition, never inventing a new status.

**When to use:** All three flags are always active (with their defaults) unless overridden;
`--max-git-procs` and `--concurrency` are the same *kind* of bound (parallelism) at two different
tiers (git subprocess vs. agent dispatch) and must not be conflated into one flag.

**Example:**
```python
# Source: pattern mirrors plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py
# lines 225-230 [VERIFIED: prefilter.py:225,230] — reused verbatim shape, different call site.
from concurrent.futures import ThreadPoolExecutor

def _diff_line_counts(records, base_sha, head_sha, runner, max_git_procs):
    with ThreadPoolExecutor(max_workers=max_git_procs) as ex:
        counts = list(ex.map(
            lambda r: file_diff_line_count(r.path, base_sha, head_sha, runner=runner),
            records,
        ))
    return dict(zip((r.path for r in records), counts))
```

```python
# Timeout guard around one bundle's coverage work — reuses the existing manifest.fail()
# transition (review_coverage.py) rather than inventing a new failure path.
import subprocess

DEFAULT_BUNDLE_TIMEOUT_SECONDS = 600  # 10m, matches SCALE-02's stated default

def process_bundle_with_timeout(unit, manifest, work_fn, timeout_seconds):
    try:
        work_fn(unit, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        for path in unit.files:
            manifest.fail(path, note="timeout")
```

### Pattern 3: Identity-Pinned Resume (SCALE-03)

**What:** Before spawning any agent on a resumed run, validate that the `model` and `profile`
recorded at the *start* of the sealed (or in-progress) manifest match what this invocation is
about to use. On mismatch: reject with a non-zero exit and **write nothing** — no partial manifest
update, no new prompt files.

**Two design options, presented as an explicit fork (this is the one genuinely open architectural
question in this phase — do not silently pick one without flagging it to the user/planner):**

| Option | Description | Evidence for | Evidence against |
|--------|-------------|---------------|-------------------|
| A. Extend `CoverageManifest` | Add `model: str`, `profile: str` fields to the existing `coverage_manifest.json` shape, set once on first `.add()`, checked on `.load()` | Manifest is already the sole persisted state review mode has [VERIFIED: no `CampaignState`/`state.json` usage anywhere in `run_review` — confirmed via full read of `cli.py`, `state.py`, `campaign.py` this session]; keeps one artifact, one file to check on resume; `base_sha`/`head_sha` are already pinned here, so identity fields join sha pinning naturally | `CoverageManifest`'s existing `to_dict()`/`load()` contract and its test suite (`test_review_coverage.py`) would need extending — not a breaking change, but a shape change to an artifact other code already reads |
| B. New sibling identity file (e.g. `review_identity.json`) | Mirror audit-mode's `RepoMemory`/`state.json` pattern with a review-mode-specific file | Keeps `CoverageManifest` scoped purely to per-file coverage state, matching its current single-responsibility docstring | Introduces a second state file to keep in sync on every resume check — more moving parts for a check that's conceptually "one gate before any spawn"; audit mode's `CampaignState` machinery (`state.py`, `campaign.py`) is verified as entirely unused by `run_review` today, so importing that pattern is not free reuse, it's new code either way |

**Recommendation: Option A.** The manifest is already the single source of truth review mode
resumes from; adding `model`/`profile` alongside `base_sha`/`head_sha` keeps identity-pinning in
the same place as SHA-pinning, and a single `.load()` call can validate all four fields together
before any spawn — satisfying "validates identity before any agent spawn" with one read, one
check, one rejection path.

**Precedent to imitate for the rejection mechanics:** `review_agent.recorded_return_source`
already rejects a stale return outright rather than partially consuming it — "A return recorded
for a different base/head pair is refused rather than consumed, so a stale return can never
masquerade as this run's finding" [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py:236-238,261-262].
SCALE-03's model/profile check is the same shape of guard, one tier earlier (before any prompt is
even rendered, not just before a return is consumed).

**"File reads stay pinned to sealed commit SHAs":** already satisfied by existing code —
`resolve_ref_sha` resolves `base`/`head` to SHAs once at the start of `run_review`
[VERIFIED: `run_review`'s body, read in full a prior turn this session — `resolve_ref_sha(base
sha)`/`resolve_ref_sha(head)` calls immediately after ref validation], and every subsequent git
read (`file_diff_text`, `file_text_at_ref`) takes the resolved SHA, never a mutable ref name. No
new work is needed for this clause of SCALE-03 beyond ensuring the identity check in Pattern 3
runs *before* any of these reads are repeated on resume (i.e., the check must gate the top of
`run_review`, not run interleaved with the coverage loop).

**Example:**
```python
# Source: pattern extends review_coverage.CoverageManifest — new fields, same class,
# validated the same way recorded_return_source validates base/head.
def validate_identity(manifest: "CoverageManifest", *, model: str, profile: str) -> None:
    """Raise before any agent spawn if this run's model/profile differs from the sealed run's.

    Raises:
        ValueError: manifest.model/profile is set and differs from the arguments given.
    """
    if manifest.model is not None and manifest.model != model:
        raise ValueError(f"resume rejected: model changed from {manifest.model!r} to {model!r}")
    if manifest.profile is not None and manifest.profile != profile:
        raise ValueError(f"resume rejected: profile changed from {manifest.profile!r} to {profile!r}")
```

### Pattern 4: Diff-Anchored Comment Payload (OUT-01)

**What:** A new artifact (recommend `review_comments.json`) listing one entry per surviving
`ReviewFinding`, shaped `{path, line, side, existing_code, content}`, written "alongside" (not
instead of) the existing `report.sarif`, `report.md`, and `findings/F-*.json` files, with the
coverage manifest's contents included.

**Field mapping (all fields exist today, no new upstream computation needed):**

| Payload field | Source | Evidence |
|----------------|--------|----------|
| `path` | `Finding.file` | [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py — Finding dataclass field `file`] |
| `line` | `Finding.line` (post position-gate, i.e. the CONFIRMED line, never the claimed one) | `review_position_gate` output already resolves this before `write_report` runs |
| `side` | New — **always `"RIGHT"` in this milestone** | No old-side/LEFT-side concept exists anywhere in this codebase's positioning logic: `diffhunks.py`'s `line_in_hunk`/`hunk_for_line` operate exclusively on `Hunk.new_start`/`new_count` [VERIFIED: full read of diffhunks.py this session], and `positioning.py`'s four-rung ladder (hunk match / whole-file match / cross-file relocation / decline) never resolves against a deleted/old-side line [VERIFIED: full read of positioning.py this session — `resolve_position`'s three success paths all return a `PositionResult` whose `path`/`line` come from `hunk.added`-derived or whole-file/cross-file text matches, never from a diff's removed-line side]. **This is a strong inference, not a directly-stated fact — flagged in Assumptions Log.** |
| `existing_code` | `Finding.evidence` | Already backfilled from real on-disk file text at `finding.line`, never the LLM's claimed snippet [confirmed via prior-turn full read of `run_review`'s evidence-backfill block] — this is the SAME field `reflection.ReflectionComment`'s `existing_code` attribute already names as an established concept in this codebase [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py:1-140 read this session — `ReflectionComment` frozen dataclass has fields `id, content, existing_code`] |
| `content` | `Finding.message` | The human-readable comment text; matches `ReflectionComment.content`'s naming precedent |

**"with the coverage manifest included"** — recommend embedding the manifest's `.to_dict()` output
as a top-level `coverage_manifest` key in the same JSON document, e.g. `{"comments": [...],
"coverage_manifest": {...}}`, rather than only cross-referencing the separate
`coverage_manifest.json` file by path. This gives a consumer (e.g. a CI bot posting PR comments) a
single self-contained artifact to fetch, matching the requirement's literal wording ("with the
coverage manifest included," not "cross-referenced").

**Why NOT extend `review_ledger.json` instead of adding a new file:** `write_review_ledger`'s
existing `review_findings` list is shaped `{id, path, line, rule_id, profile, defect_class,
disposition}` [confirmed via prior-turn `sed` read of `write_review_ledger`'s body] — it has no
`existing_code`/`content`/`side` fields today. The requirement's own wording — "emits a
diff-anchored comment payload... **alongside** the existing SARIF, markdown, and per-finding
files" — reads as "alongside" (a new artifact), not "extending." Given `write_report` is shared
between audit and review modes, adding a wholly new artifact rather than growing an
already-multi-purpose shared function's output is also lower-risk for audit-mode regression.

**Example:**
```python
# Source: pattern extends report.py's existing write_review_ledger — same file-writing
# idiom (workspace._atomic_write, dataclasses.asdict), new sibling function.
from dataclasses import dataclass, asdict
import json
from sec_overlay.workspace import Workspace, _atomic_write

@dataclass(frozen=True)
class DiffComment:
    path: str
    line: int
    side: str          # always "RIGHT" this milestone — see Assumptions Log A1
    existing_code: str
    content: str

def write_review_comments(ws: Workspace, comments: list[DiffComment], manifest_dict: dict) -> Path:
    """Write artifacts/review_comments.json — OUT-01's diff-anchored payload."""
    path = ws.artifacts / "review_comments.json"
    payload = {"comments": [asdict(c) for c in comments], "coverage_manifest": manifest_dict}
    _atomic_write(path, json.dumps(payload, indent=2))
    return path
```

### Pattern 5: SARIF `partialFingerprints` (OUT-02)

**What:** Add a `partialFingerprints` key to each SARIF `result` object in `sarif.py::to_sarif`,
keyed on a stable hash of `Path|Category|ExistingCode`, explicitly excluding `message`/`content`
text — so a finding whose message wording varies slightly across re-runs (e.g. LLM phrasing
drift) still produces the same fingerprint and does not appear as a "new" alert to a Result
Management System (GitHub code scanning, etc.).

**Field mapping:**

| Requirement term | `Finding` field | Evidence |
|-------------------|-------------------|----------|
| `Path` | `finding.file` | Same field OUT-01 uses |
| `Category` | `finding.cls` | `models.py`'s `Finding.cls` docstring: "attack class (e.g. `sqli`/`secrets`/`ssrf`)" [VERIFIED: models.py, read in full a prior turn this session] — `review_findings.classify()` already reads `finding.cls` the same way [VERIFIED: review_findings.py:92-104, read this session] |
| `ExistingCode` | `finding.evidence` | Same field OUT-01's `existing_code` uses — confirms one canonical source feeds both new requirements |

**Why this must be a NEW function, not a reuse of `fingerprint.fingerprint()`:** the existing
dedup fingerprint's key is `rule_id|cls|anchor-or-file:line`
[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/fingerprint.py, read in full
a prior turn this session] — it uses `rule_id` (not `Path` as its first component) and a
line-anchor (not `evidence`/`ExistingCode`). OUT-02's spec explicitly composes `Path|Category|
ExistingCode`, a different key entirely. Reusing the existing `fingerprint()` for this purpose
would silently conflate two distinct identity concepts (dedup identity vs. SARIF re-run stability)
that happen to look similar. Write a small new function in `sarif.py` instead, reusing the same
`hashlib.sha256(...).hexdigest()[:N]` primitive for consistency, not the same function.

**No mention of `partialFingerprints` exists anywhere in `sarif.py` today**
[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py, read in full a
prior turn this session — 91 lines, `to_sarif`'s only per-result keys are `ruleId`, `level`,
`message.text`, `locations`, and an optional `suppressions` block]. This is unambiguously new work.

**Example:**
```python
# Source: extends sarif.py's existing to_sarif(); reuses hashlib pattern from
# fingerprint.py (different key composition, same primitive).
import hashlib

def _sarif_fingerprint(finding) -> str:
    """Compute OUT-02's Path|Category|ExistingCode fingerprint, excluding message text."""
    key = f"{finding.file}|{finding.cls}|{finding.evidence}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

# inside to_sarif's per-finding result-building loop:
result["partialFingerprints"] = {"sec-overlay/v1": _sarif_fingerprint(f)}
```

### Anti-Patterns to Avoid

- **Adding a field to `models.Finding` for `side`, bundle membership, or the SARIF fingerprint:**
  `models.py` is the frozen, Go-port-mirrored milestone contract (D-02, D-11) — every prior phase
  solved an identical "need a new field" problem with a new sibling module (`review_coverage.py`,
  `review_findings.py`), never by touching `models.py`. Phase 4 must follow the same discipline.
- **Bounding agent-dispatch concurrency (`--concurrency`) inside the Python deterministic core
  when `SKILL.md` is what actually spawns subagents:** the concurrency bound for the actual agent
  fan-out belongs in the orchestration layer `SKILL.md` documents (D-13, "SKILL.md owns dispatch");
  the Python core should expose `--concurrency` as a value SKILL.md reads/honors for its wave size
  and use its own copy only for the git-subprocess-adjacent work it directly performs. Conflating
  these into one Python-side thread pool that also tries to spawn subagents would violate the
  "review_agent.py never dispatches" invariant [VERIFIED: review_agent.py:1-14 module docstring].
- **Treating a `ReflectionSkip`/`ReviewSourceSkip` as a coverage failure for SCALE-02's timeout
  purposes:** D-15 already establishes that a reviewer failure is NOT a coverage failure — only
  `manifest.fail()` flips the seal to `partial`. A timeout must route through `manifest.fail()`
  specifically, not through the reflection/review-source skip ledgers, or the run's terminal state
  won't reflect the timeout at all.
- **Picking Option A or B for SCALE-03 silently:** presented above as an explicit fork with a
  recommendation — do not let the planner discover this fork mid-implementation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Bounded parallel git subprocess calls | A custom semaphore/queue/worker-pool | `concurrent.futures.ThreadPoolExecutor(max_workers=N)` | Already the established pattern at `prefilter.py:225-230`; reinventing it introduces a second concurrency idiom in the same codebase for no benefit |
| Per-bundle wall-clock timeout | A custom `signal.alarm`/thread-watchdog | `subprocess.run(..., timeout=N)` + catching `subprocess.TimeoutExpired` | stdlib's own subprocess timeout mechanism is exactly fit-for-purpose when the work being bounded is itself a subprocess call chain; `signal.alarm` is Unix-only and interacts badly with threads, an unnecessary portability and correctness risk |
| Coverage/resume state machine | A new state-machine class for SCALE-02's pass/fail tracking | `review_coverage.CoverageManifest`'s existing `_ALLOWED_TRANSITIONS` table and `seal()` | This machinery is already built, already tested, and already produces exactly `complete`/`partial` — building a second one duplicates logic the planner must then keep in sync forever |
| Stale-run rejection | A custom "compare two config dicts" diffing utility | The same explicit-field-equality check `recorded_return_source` already uses for base/head | Two fields (`model`, `profile`), direct equality — no generic diffing tool adds value over `if a != b: raise` |

**Key insight:** every new piece of state Phase 4 needs (bundle grouping, timeout-driven failure,
identity pinning, comment payload, SARIF fingerprint) is a *thin* addition on top of machinery this
codebase already built in Phases 2-3 specifically anticipating scale/output work. The risk in this
phase is not "what do we build" but "don't rebuild what already exists one file over" — the
Ponytail ladder's rung 2 ("already in this codebase?") resolves nearly every design question here.

## Common Pitfalls

### Pitfall 1: Bundling breaks the Strict Focus Rule
**What goes wrong:** `review_agent.parse_review_response` currently discards any `code_comment`
naming a path other than the single file under review (Strict Focus Rule, REV-03's elevation-of-
privilege backstop) [VERIFIED: review_agent.py:116-137, `if entry.get("path") != path: discarded
+= 1; continue`]. If bundling renders one prompt covering N files but `parse_review_response` still
checks against a single `path`, every comment about any file but the first in the bundle silently
discards.
**Why it happens:** The Strict Focus Rule was designed and tested exclusively against
single-file review units; bundling is genuinely new scope for this function's contract.
**How to avoid:** `parse_review_response`'s `path` parameter (or its caller) must become "one of
the bundle's member paths," checking `entry.get("path") in bundle.files`, not `== path`. This is a
required, not optional, change alongside `bundle.py` itself — flag it in the plan's task list
explicitly, since SCALE-01's text doesn't mention `review_agent.py` at all.
**Warning signs:** A bundled multi-file review producing suspiciously few findings compared to the
same files reviewed individually — the discard counter (`discarded`) would silently climb.

### Pitfall 2: `--max-git-procs` and `--concurrency` bound different things — don't conflate them
**What goes wrong:** Treating "16 max git procs" as the same value/mechanism as "8 bundles at a
time" leads to over- or under-provisioning one or the other (e.g. 8 bundles each spawning several
git calls simultaneously could still exceed 16 concurrent git processes if not independently
capped).
**Why it happens:** Both are "concurrency limits" conceptually, easy to merge into one flag during
implementation.
**How to avoid:** Two independent `ThreadPoolExecutor`/bound mechanisms, two independent flags,
as designed in Pattern 2. Do not let one flag default from or scale off the other.
**Warning signs:** A test asserting `--max-git-procs 1 --concurrency 8` still parallelizes git
calls (or vice versa) would reveal a conflation bug immediately.

### Pitfall 3: A partial-bundle timeout must fail EVERY file in the bundle, not just the slow one
**What goes wrong:** SCALE-02 says "a timed-out bundle marks its files failed" (plural) — if the
timeout implementation only calls `manifest.fail()` for whichever single file happened to be
mid-flight when the timer fired, sibling files in the same bundle that already completed
successfully would incorrectly stay `done`, while files that never started stay `pending` forever
(which would then make `manifest.seal()` raise instead of returning `partial`, since `seal()`
explicitly raises on any remaining `pending`/`in_review` entry [VERIFIED: review_coverage.py — full
read this session confirmed `seal()`'s raise-on-incomplete behavior]).
**Why it happens:** A naive timeout wrapped around a per-file loop degrades to "the file being
processed when time ran out fails," not "the whole unit fails together."
**How to avoid:** The timeout must wrap the *whole bundle's* processing as one unit; on expiry,
iterate `unit.files` and call `.fail(path, note="timeout")` for every member, including ones
already `in_review` or still `pending`.
**Warning signs:** `manifest.seal()` raising `CoverageTransitionError` on a run that should have
produced a `partial` terminal state is the direct symptom.

### Pitfall 4: Bundling must still respect `file_select`'s exclusions
**What goes wrong:** If `bundle.py` runs on `changed_file_records` (unfiltered) instead of
`Selection.reviewable` (already filtered for deleted/binary/generated/not-allowlisted/too-large),
an excluded file could get pulled into a bundle with a reviewable sibling and reviewed anyway,
silently bypassing `file_select`'s exclusion contract.
**Why it happens:** Both `changed_file_records` and `Selection.reviewable` are `list[ChangedFile]`
-shaped, an easy mix-up at the call site.
**How to avoid:** `bundle.group_bundles` must take `Selection.reviewable` explicitly (as typed in
Pattern 1's example), never the raw `changed_file_records` output; a type alias or explicit
parameter name (`reviewable: list[ChangedFile]`) reduces the chance of passing the wrong list.
**Warning signs:** A bundle containing a path that also appears in `Selection.excluded`.

### Pitfall 5: git-subprocess result ordering must stay deterministic under concurrency
**What goes wrong:** `ThreadPoolExecutor.map`'s ordering guarantee (results returned in submission
order, not completion order) is what makes `prefilter.py`'s serial-vs-concurrent runs
byte-identical [VERIFIED: prefilter.py:122-123 docstring, 273 comment]. If `--max-git-procs`'s
implementation instead uses `as_completed()` or a raw thread pool without preserving submission
order, the resulting `diff_line_counts` dict (keyed by path, so ordering is actually moot there) is
safe, but any code that assumes a *list* result stays index-aligned with its input list would
silently corrupt.
**Why it happens:** `as_completed()` is a common, reasonable-looking alternative that trades
determinism for marginally faster wall time.
**How to avoid:** Use `.map()`, matching `prefilter.py`'s exact pattern, not `as_completed()`.
**Warning signs:** A flaky test that passes under `--max-git-procs 1` but fails intermittently
under `--max-git-procs 16` on ordering-sensitive assertions.

### Pitfall 6: Identity check must run before ANY write, including the manifest's own `.add()`
**What goes wrong:** SCALE-03 requires "nothing persisted" on a rejected implicit identity change.
If the identity check happens after `CoverageManifest.add(path)` has already been called for even
one file, that `.add()` call has already mutated in-memory state that `._persist()` may write to
disk on the next `.start()`/`.finish()`/`.fail()` call, partially violating "nothing persisted."
**Why it happens:** The natural place to check "does this manifest already have entries" is
inside the per-file loop, which is too late.
**How to avoid:** Load the existing manifest (if present) and run `validate_identity(...)` (Pattern
3) as the very first action in `run_review`, before `changed_file_records`/`partition`/`bundle`
even run — a pure "read old state, compare, maybe raise" step with zero mutation.
**Warning signs:** A test that resumes with a changed `--profile` still sees a
`coverage_manifest.json` with an updated `mtime` — the file was rewritten before the rejection.

### Pitfall 7: `resolve_ref_sha` on resume must re-validate, not trust a persisted SHA blindly
**What goes wrong:** SCALE-03 requires "file reads stay pinned to sealed commit SHAs" — if resume
logic reads `base_sha`/`head_sha` directly from the persisted manifest without also confirming
that `--base`/`--head` (or their absence, defaulting to a stored value) still refer to a SHA the
current repository state can resolve, a resumed run could silently operate against a since-rewritten
or garbage-collected ref.
**Why it happens:** "The manifest already has the SHAs, just reuse them" is the path of least
resistance and is *usually* correct — but skips validating the repo still has that commit.
**How to avoid:** On resume, still call `resolve_ref_sha`/`file_text_at_ref` against the actual
git repository using the persisted SHA as the ref argument (a SHA is a valid ref), so a missing
commit still surfaces its natural git error rather than being silently assumed present.
**Warning signs:** A resumed run against a shallow clone or a repo that has since garbage-collected
the original head_sha's commit produces a confusing downstream error instead of a clear "commit not
found" failure at the top of `run_review`.

### Pitfall 8: `side` hardcoded as `"RIGHT"` forecloses future old-side support silently
**What goes wrong:** If `side: "RIGHT"` is hardcoded as a literal string scattered across
`review_comments.py`, a future phase adding old-side/deleted-line comment support would need to
find and change every occurrence.
**Why it happens:** It's genuinely a constant today (see Pattern 4's evidence) — easy to inline.
**How to avoid:** Define `DEFAULT_SIDE = "RIGHT"` as a module-level constant in `review_comments.py`
with a comment citing why (no old-side positioning exists in this milestone's `positioning.py`),
so a future change is a one-line edit with an explicit marker, not a grep-and-replace.
**Warning signs:** N/A for this phase — this is a forward-maintainability note, not a correctness
risk for Phase 4 itself.

### Pitfall 9: SARIF fingerprint stability requires normalizing `existing_code` whitespace
**What goes wrong:** If `finding.evidence` (the on-disk line text) carries trailing whitespace or
platform-specific line endings that vary between a Linux CI run and a local run, the same logical
finding could hash to two different `partialFingerprints` values, defeating the entire purpose of
excluding message text for stability.
**Why it happens:** `finding.evidence` is raw text sliced from `lines[finding.line - 1]`
[confirmed via prior-turn read of the evidence-backfill block in `run_review`] with no normalization
applied.
**How to avoid:** Normalize (e.g. `.strip()` or `.rstrip("\r\n")`) the `evidence` string before
hashing in `_sarif_fingerprint`, matching the whitespace-tolerance already used elsewhere in this
codebase (`positioning._match_consecutive` strips both sides before comparing
[VERIFIED: positioning.py:97-98, read in full this session — `stripped_needle = [line.strip() for
line in needle_lines]`]).
**Warning signs:** The same finding across two runs of the identical diff on different OSes/CI
producing different SARIF fingerprints in a test asserting fingerprint stability.

## Code Examples

### Bounded git-subprocess fan-out (SCALE-02, `--max-git-procs`)
```python
# Source: mirrors plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py:225,230
# [VERIFIED this session via full read of prefilter.py's relevant lines]
from concurrent.futures import ThreadPoolExecutor

workers = max_git_procs or max(1, min(16, (os.cpu_count() or 2) - 1))
with ThreadPoolExecutor(max_workers=workers) as ex:
    results = list(ex.map(worker_fn, items))  # .map preserves submission order — determinism
```

### Timeout-driven coverage failure, reusing existing transitions (SCALE-02)
```python
# Source: extends existing manifest.fail() call site in cli.py::run_review's coverage loop
# [confirmed via prior-turn read of run_review's try/except -> manifest.fail() block]
import subprocess

try:
    result = subprocess.run(bundle_review_cmd, timeout=timeout_seconds, ...)
except subprocess.TimeoutExpired:
    for path in unit.files:
        manifest.fail(path, note="timeout")
```

### Identity rejection before any write (SCALE-03)
```python
# Source: mirrors review_agent.recorded_return_source's stale base/head rejection
# [VERIFIED: review_agent.py:261-262 this session]
existing = CoverageManifest.load(manifest_path) if manifest_path.exists() else None
if existing is not None:
    if existing.model is not None and existing.model != args.model:
        print(f"resume rejected: model changed from {existing.model} to {args.model}", file=sys.stderr)
        return 2  # matches existing convention: 2 = rejected before any work started
    if existing.profile is not None and existing.profile != args.profile:
        print(f"resume rejected: profile changed from {existing.profile} to {args.profile}", file=sys.stderr)
        return 2
```

### SARIF fingerprint addition (OUT-02)
```python
# Source: extends sarif.py::to_sarif's per-result dict construction
# [VERIFIED: sarif.py, full read this session — no partialFingerprints key exists today]
result["partialFingerprints"] = {
    "sec-overlay/v1": hashlib.sha256(
        f"{f.file}|{f.cls}|{f.evidence.strip()}".encode("utf-8")
    ).hexdigest()[:16]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Serial per-file git subprocess calls in `run_review` | Bounded `ThreadPoolExecutor` fan-out | This phase (SCALE-02) | Large diffs no longer spawn unbounded concurrent `git` processes; wall time scales with `--max-git-procs`, not file count |
| No resume identity check | `CoverageManifest`-embedded model/profile pinning | This phase (SCALE-03) | A silently-changed `--profile` or model between runs can no longer corrupt a resumed review's findings mix |
| SARIF results with no fingerprint | `partialFingerprints` keyed on `Path\|Category\|ExistingCode` | This phase (OUT-02) | Downstream Result Management Systems (GitHub code scanning, etc.) can dedupe/track findings across runs even when message wording drifts |

**Deprecated/outdated:** None — this phase is additive to an actively-maintained, recently-built
pipeline (Phases 2-3 completed 2026-08, per `.planning/STATE.md`'s decision log). No legacy
approach is being replaced.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OUT-01's `side` field is always `"RIGHT"` in this milestone | Architecture Patterns → Pattern 4 | If a future/overlooked code path resolves an old-side position, hardcoding `"RIGHT"` would silently mislabel a deleted-line comment as landing on the new side, confusing a PR-comment consumer about which line to anchor to. Low risk given the exhaustive read of `diffhunks.py`/`positioning.py` found zero old-side handling, but this is an inference from absence, not a stated design decision. |
| A2 | OUT-01's payload should be a NEW sibling artifact (`review_comments.json`), not an extension of `review_ledger.json` | Architecture Patterns → Pattern 4 | If the planner or user intends `review_ledger.json` to gain these fields instead, presenting this as settled would cost a rework; flagged prominently in Pattern 4's "Why NOT extend" subsection with the exact existing shape quoted, so the planner can confirm or override deliberately. |
| A3 | SCALE-03's identity state should extend `CoverageManifest` (Option A) rather than introduce a new sibling file (Option B) | Architecture Patterns → Pattern 3 | Presented explicitly as a fork with a recommendation, not silently decided — if the planner picks Option B instead, no research finding here is invalidated, only the recommendation is not followed. |
| A4 | `--concurrency`'s primary enforcement point for actual agent dispatch lives in `SKILL.md`'s orchestration loop, with the Python core only exposing/honoring the value for its own git-adjacent bounded work | Architectural Responsibility Map; Anti-Patterns | `SKILL.md` itself was not read in full this session (only grepped for "dispatch"/"concurrency"/"wave" occurrences) — if `SKILL.md`'s actual dispatch loop structure differs materially from the "waves of three to four" convention quoted, this recommendation's specifics (not its general direction) could need adjustment. |

## Open Questions

1. **Does `--concurrency`'s default of 8 apply to bundles, or to individual review-agent dispatches within `SKILL.md`'s wave loop?**
   - What we know: `SKILL.md` already documents an informal "waves of three to four" convention for audit-mode fan-out under provider load, and cites the same rule applying to review-mode dispatch (`SKILL.md:129`).
   - What's unclear: Whether SCALE-02's `--concurrency 8` is meant to *replace* that informal 3-4 convention with a formal, larger default, or whether it governs a different tier entirely (e.g. bundle-level Python-side parallelism, distinct from agent-dispatch wave size).
   - Recommendation: The planner should treat `--concurrency` as governing bundle-level dispatch fan-out and explicitly reconcile its default (8) against `SKILL.md`'s existing informal 3-4 convention in the plan's task description — this reconciliation was not fully resolved by this research pass since `SKILL.md`'s full dispatch-loop implementation was not read in this session (only grepped).

2. **Should `bundle.py` be added to the CLI-callable module list in `plugins/sec-overlay/CLAUDE.md`?**
   - What we know: The plugin's maintainer manual lists specific modules as independently `python -m sec_overlay.<module>`-invokable; `bundle` is not currently in that list, and `file_select.py` (the closest architectural precedent — a pure library consumed by `cli.py`, never its own subcommand) is also absent from that list.
   - What's unclear: Whether `bundle.py` needs standalone CLI invocation for testing/debugging (e.g. `python -m sec_overlay.bundle --root . --base X --head Y` to preview groupings) or is purely a library import.
   - Recommendation: Default to library-only (matching `file_select.py`'s precedent) unless the plan surfaces a concrete need for standalone invocation; if added, the plugin CLAUDE.md's CLI-callable list must be updated in the same commit (per that file's own convention).

3. **`positioning.py`'s cross-file relocation (`RELOCATION_REASONS = {"whole-file-match",
   "cross-file-match"}`) — does OUT-01's `path` field reflect the RESOLVED (possibly relocated)
   path, or the originally-claimed path?**
   - What we know: `PositionResult.path` is the confirmed file path after the ladder runs, which
     can differ from `claimed_path` on a `"relocated"` decision [VERIFIED: positioning.py:37,41,
     `path: str | None  # The confirmed file path, or None on a decline` vs. `claimed_path: str  #
     The original claimed path, carried on every result including declines`].
   - What's unclear: Whether OUT-01's diff-anchored comment should anchor to the resolved
     (possibly different) file, or whether a relocated finding should be excluded from the diff
     comment payload entirely (since a diff-review PR-comment UI typically anchors comments to
     lines within the diff being reviewed, and a cross-file relocation could point outside the
     file the comment's containing hunk belongs to).
   - Recommendation: Use the resolved `path`/`line` (matching how `review_position_gate` already
     treats relocated findings as "kept," not "declined," downstream) — but the planner should
     explicitly verify this against `phase_gate.review_position_gate`'s full body (only partially
     read this session, lines 370-470) before finalizing, since the interaction between "relocated"
     and "outside-diff" dropping was not fully traced end-to-end in this research pass.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | All of Phase 4 | Yes | 3.13.14 [VERIFIED: `python3 --version` this session] | — |
| `concurrent.futures` (stdlib) | SCALE-02 | Yes | bundled with Python 3.13.14 | — |
| `subprocess` (stdlib) | SCALE-02 | Yes | bundled with Python 3.13.14 | — |
| git | All git-calling functions (`diffscope.py`) | Assumed yes — existing tests already depend on it | Not independently re-verified this session | — |
| `uv` (dev tool, for `uv run pytest`) | Test execution per plugin CLAUDE.md | Assumed yes — plugin CLAUDE.md's documented workflow already depends on it | Not independently re-verified this session | — |

**Missing dependencies with no fallback:** none identified.

**Missing dependencies with fallback:** none identified — this phase adds no dependency requiring one.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 [VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml — `dev = ["pytest>=8", "ruff>=0.6", "ty>=0.0.1a1"]`] |
| Config file | `helpers/pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` [VERIFIED: pyproject.toml this session] |
| Quick run command | `uv run pytest tests/test_bundle.py -q` (or the specific new/extended test file) |
| Full suite command | `uv run pytest -q` (run from `helpers/`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|--------------------|--------------|
| SCALE-01 | Locale/config siblings and impl/test pairs group into one `ReviewUnit`; ungrouped files fall back to one-file units | unit | `uv run pytest tests/test_bundle.py -x` | ❌ Wave 0 — new file, no existing `test_bundle.py` [VERIFIED: `ls tests/` output this session confirmed absence] |
| SCALE-02 | `ThreadPoolExecutor`-bounded git calls stay under `--max-git-procs`; a simulated per-bundle timeout marks every file in that bundle `failed` and `manifest.seal()` returns `"partial"` | unit | `uv run pytest tests/test_review_coverage.py -x` (extend existing file) | ✅ existing file, extend with new cases |
| SCALE-03 | A resume with a changed `--profile`/model is rejected with no manifest write; resolving a persisted SHA still round-trips through `resolve_ref_sha` | unit | `uv run pytest tests/test_review_coverage.py -x` and/or `tests/test_cli.py -x` | ✅ existing files, extend |
| OUT-01 | `review_comments.json` contains `{path, line, side, existing_code, content}` per surviving finding, plus an embedded `coverage_manifest` snapshot | unit | `uv run pytest tests/test_review_comments.py -x` (new) or extend `tests/test_review_agent.py` | ❌ Wave 0 if new file chosen |
| OUT-02 | SARIF `partialFingerprints` is stable across two findings differing only in message text, and differs when `evidence` differs | unit | `uv run pytest tests/test_sarif.py -x` (extend existing file — confirmed present via `ls tests/` listing this session) | ✅ existing file, extend |

### Sampling Rate

- **Per task commit:** the specific extended/new test file's quick run (e.g. `uv run pytest
  tests/test_bundle.py -q`)
- **Per wave merge:** `uv run pytest -q` (full suite, from `helpers/`)
- **Phase gate:** Full suite green, plus `uv run ruff check sec_overlay/ bench/ tests/` and
  `uv run ty check` clean (per plugin CLAUDE.md's documented zero-warnings workflow), before
  `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_bundle.py` — covers SCALE-01 (does not exist yet; confirmed via `ls tests/ |
  sort` this session — no `bundle` or `test_bundle` entry present)
- [ ] `tests/test_review_comments.py` — covers OUT-01, if the new-sibling-artifact design
  (Pattern 4, Assumption A2) is adopted as recommended
- Framework install: none — pytest/ruff/ty are already dev dependencies; no new install needed.

*(SCALE-02, SCALE-03, and OUT-02 have no Wave 0 gap — existing test infrastructure
(`test_review_coverage.py`, `test_sarif.py`, `test_cli.py`) covers the extension points; only new
test *cases* are needed within those files, not new fixtures or framework setup.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|--------------------|
| V2 Authentication | No | This phase touches no auth surface |
| V3 Session Management | No | No session concept in this CLI tool |
| V4 Access Control | No | No multi-user access control surface |
| V5 Input Validation | Yes | `--concurrency`/`--timeout`/`--max-git-procs` are integer CLI flags — validate positive-integer bounds via `argparse`'s `type=int` plus an explicit range check (e.g. reject 0 or negative) before use, matching this codebase's existing input-validation discipline for `--base`/`--head` (`diffscope.validate_ref`'s regex gate) and rule paths (`rule_glob`'s symlink-resolution + extension + size caps) |
| V6 Cryptography | No new cryptographic use — `hashlib.sha256` is used only for non-security identifier derivation (fingerprints, labels), not for authentication or confidentiality, matching this codebase's existing use of the same primitive in `fingerprint.py`/`review_agent.py` |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Git-argument injection via a malicious `--timeout`/`--concurrency`/`--max-git-procs` value reaching a subprocess call unsanitized | Tampering | These three flags are never interpolated into a shell string or git argument — they configure Python-level `ThreadPoolExecutor`/`subprocess.run(timeout=)` parameters only, never passed to `git` itself. No new git-argument-injection surface is introduced by this phase (unlike `--base`/`--head`, which already have `validate_ref`'s regex gate). |
| Resource exhaustion via an unbounded or maliciously large `--concurrency`/`--max-git-procs` value | Denial of Service | Clamp both flags to a sane upper bound (e.g. reject values above some ceiling like 128) in addition to rejecting non-positive values — matches this codebase's existing "no CLI override without a cap" discipline already noted at `file_select.py`'s `DEFAULT_MAX_DIFF_LINES` comment [VERIFIED: file_select.py inline comment, read this session — "No CLI override — a cap-override flag belongs to Phase 4, not this milestone"]. |
| A resumed run silently using a different model/profile than the original run, producing a finding set that looks coherent but was actually produced under mixed settings | Tampering / Repudiation | SCALE-03's identity-pinning gate (Pattern 3) is itself the mitigation — this IS the security-relevant requirement in this phase, not an incidental concern. |
| SARIF fingerprint collision across genuinely different findings that happen to share `Path\|Category\|ExistingCode` | Tampering (a distinct real finding gets silently merged/suppressed by a downstream RMS as a "duplicate") | Truncating the hash to 16 hex chars (64 bits) keeps collision probability negligible for any realistic finding volume; if two genuinely distinct findings share the exact same file, category, AND exact on-disk line text, they are likely true duplicates of the same underlying issue, which is the intended dedup behavior, not a false merge. |

## Sources

### Primary (HIGH confidence)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py` (read in full this
  session, lines 1-273 relevant sections) — `ThreadPoolExecutor` bounded-concurrency precedent
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py` (read in full
  this session, 171 lines) — `CoverageManifest` state machine and `seal()` contract
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py` (read in full this
  session, 269 lines) — stale-return rejection precedent, `ReviewPlanEntry`/`agent_label`
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/positioning.py` (read in full this
  session, 219 lines) — confirmed no old-side positioning exists anywhere in the ladder
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py` (read in full
  this session, 178 lines) — `Finding.cls`/`ReviewFinding` field mapping for OUT-02's "Category"
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py` (function signatures
  confirmed via `grep -n "^def \|^class "` this session, lines 12-198) — injectable-runner pattern
  across every git-calling function
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py` (read in full a prior turn
  this session, 91 lines) — confirmed no `partialFingerprints` exists today
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/fingerprint.py` (read in full a prior
  turn this session, 57 lines) — confirmed the existing dedup fingerprint's different key shape
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/file_select.py` (read in full a prior
  turn this session, ~195 lines) — `Selection`/`partition()` contract, `DEFAULT_MAX_DIFF_LINES`
  no-CLI-override note
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reflection.py` (read partially this
  session, lines 1-140) — `ReflectionComment` established `existing_code` field precedent
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py` (read in full a prior turn
  this session, 184 lines) — frozen `Finding` contract fields
- `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` (read in full this session) —
  Python floor, zero-dependency constraint, pytest/ruff/ty config
- `.planning/REQUIREMENTS.md` (read in full this session, 225 lines) — verbatim requirement text,
  design invariants, traceability
- `.planning/STATE.md` (read in full this session, 167 lines) — decision-log entries D-01 through
  D-16 and unnumbered decisions establishing prior architectural precedent
- `plugins/sec-overlay/CLAUDE.md` and `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` (full
  content provided via system context this session) — maintainer/operating manuals, CLI-callable
  module list, `SKILL.md`'s documented dispatch-wave convention

### Secondary (MEDIUM confidence)
- OASIS SARIF 2.1.0 specification, `partialFingerprints` property description (WebSearch this
  session, cross-referenced against docs.oasis-open.org and GitHub's code-scanning SARIF docs) —
  confirms `partialFingerprints` is a Result Management System disambiguation mechanism, matching
  this phase's intended use; full spec text not fetched directly, summary only [CITED:
  https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html]

### Tertiary (LOW confidence)
- None — every claim in this document is either directly verified against source this session or
  explicitly logged in the Assumptions Log above.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommended tool is stdlib, already used elsewhere in this exact
  codebase for the identical problem shape (concurrency bounding, timeout-adjacent patterns)
- Architecture: HIGH for Patterns 1, 2, 4, 5 (directly derived from verified existing code and
  explicit field mappings); MEDIUM for Pattern 3 (a genuine open design fork, resolved with a
  reasoned recommendation rather than a verified fact)
- Pitfalls: HIGH — 7 of 9 pitfalls are derived from directly-read code behavior (e.g. `seal()`'s
  raise-on-incomplete, `parse_review_response`'s Strict Focus Rule); 2 (Pitfalls 8, 9) are forward-
  looking maintainability/correctness notes flagged as such

**Research date:** 2026-08-20
**Valid until:** 2026-09-19 (30 days — this is a stable, actively-developed but not fast-moving
internal codebase; re-research if Phase 3 or 04.1 introduce further changes to `cli.py::run_review`
before Phase 4 planning begins)
