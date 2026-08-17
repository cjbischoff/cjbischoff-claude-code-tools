# Phase 2: Diff Pipeline & Positioning - Research

**Researched:** 2026-08-17
**Domain:** Deterministic git-diff scoping, unified-diff hunk parsing, and never-guess finding
positioning for a stdlib-only Python CLI security-review harness
**Confidence:** HIGH

## Summary

This phase extends `sec-overlay`'s existing scan/audit pipeline with a `review` mode that
scopes work to a base/head diff instead of a whole repo. Six modules are involved: two
extensions to existing files (`diffscope.py`, `phase_gate.py`) and four new files
(`file_select.py`, `review_coverage.py`, `diffhunks.py`, `positioning.py`). The design is not
novel — it is a direct, verified port of algorithms already implemented and battle-tested in
the Go reference tool `open-code-review` (OCR), located locally at
`/Users/christopher/tools/open-code-review/`. Every algorithm this research recommends was read
from OCR's actual source (not the milestone spec's paraphrase of it), because one paraphrase in
the spec was found to diverge from the real implementation (see Common Pitfalls, Pitfall 2).

The existing `sec_overlay` codebase already has the exact scaffolding this phase needs:
injectable-runner git subprocess calls (`diffscope.py`), atomic JSON writes (`workspace.py`
`_atomic_write`), and a stdlib-only, zero-dependency `pyproject.toml`. Two real gaps exist that
the plan must account for: (1) `Workspace` has no `artifacts` property/directory today — D-02's
`artifacts/coverage_manifest.json` path requires adding one; (2) the "existing whole-file check
in audit mode" that POS-03's acceptance criterion and the milestone spec both assume exists for
`Finding.line` does not actually exist in the codebase today — the `1 <= line <= n` pattern only
guards markdown citation refs (`phase_gate.py:42-49`, used by `resolve_ref`), never a `Finding`.

**Primary recommendation:** Port OCR's hunk parser (`internal/diff/hunk.go`) and positioning
resolver (`internal/diff/resolver.go`) near-verbatim into `diffhunks.py`/`positioning.py`,
including OCR's **exact-string-match** algorithm — not the milestone spec's suggested
`difflib.SequenceMatcher` fuzzy match, which OCR does not actually use anywhere in the ladder.

## Architectural Responsibility Map

This is a single-process stdlib CLI tool, not a multi-tier web app. The standard
Browser/SSR/API/CDN/Database tiers do not apply; the phase's tiers are the pipeline stages a
`review` run passes through, in order.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ref validation + SHA pinning | Git/VCS integration layer (`diffscope.py`) | CLI driver (`cli.py`, exit-code mapping) | Only this layer touches `subprocess`/git; the CLI layer only translates its `ValueError` to exit code 2 |
| Changed-file + hunk acquisition | Git/VCS integration layer (`diffscope.py`) | — | Owns every `git diff`/`git rev-parse` call |
| File selection (allowlist/exclude) | Deterministic pipeline core (`file_select.py`) | — | Pure function over `ChangedFile` records + hardcoded constants; no I/O beyond reading diff text already in hand |
| Coverage tracking | Persisted state layer (`review_coverage.py` + `artifacts/coverage_manifest.json`) | CLI driver (seals/exit code) | Only this module may write manifest transitions (D-03); CLI reads the sealed result to pick an exit code |
| Hunk parsing | Deterministic pipeline core (`diffhunks.py`) | — | Pure stdlib `re` parser, no I/O |
| Positioning | Deterministic pipeline core (`positioning.py`) | — | Pure function over hunks + finding + file content; never touches git or network |
| Gate filtering (outside-diff drop) | Deterministic pipeline core (`phase_gate.py` review branch) | Report/output layer (dropped-findings ledger, D-14) | Filtering logic is pure; the ledger write is the report layer's job |
| Report/output emission | Report/output layer (`report.py`, `sarif.py`, existing) | — | Out of Phase 2's module list but consumes its outputs (D-13/D-14 sections) |

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Coverage manifest module
- **D-01:** The manifest lives in a new module `review_coverage.py`. The existing
  `coverage.py` (audit-mode coverage) is not modified. — **Reversibility:** costly —
  a later merge into `coverage.py` would touch every manifest call site and the
  shipped audit module.
- **D-02:** The manifest persists as JSON at `artifacts/coverage_manifest.json` in
  the run's artifact directory, written incrementally during the run. Phase 4 resume
  reads the same file. — **Reversibility:** one-way once Phase 4 ships — resume and
  external readers depend on the file's location and shape.
- **D-03:** `review_coverage.py` owns state transitions. Illegal transitions
  (done back to pending, sealing with a pending entry) raise. The driver calls
  module methods; nothing else edits the JSON.
- **D-04:** `partial` seals only when every non-done entry is `failed`, each named.
  Any `pending` entry blocks sealing entirely. `complete` requires all entries `done`.

#### diffscope extension
- **D-05:** The extension is additive. `ChangedFile` dataclass and
  `changed_file_records(base, head)` land alongside the existing `changed_files()`
  and `head_sha()`; existing callers are untouched.
- **D-06:** Ref validation lives in `diffscope.py` and raises `ValueError` quoting
  the offending ref; `cli.py` catches it and exits 2 with a one-line actionable
  message. No git subprocess ever receives an unvalidated ref. — **Reversibility:**
  reversible, but the exit code becomes CLI contract once documented.
- **D-07:** Base and head resolve to commit SHAs once at run start
  (`git rev-parse` after validation). Every later git call uses the pinned SHAs.
  Both SHAs are recorded in the coverage manifest.
- **D-08:** Renames (status R) carry `path` = new path, `old_path` = old path;
  review runs against the new path's hunks (git rename detection stays at defaults).

#### File selection and exclusion
- **D-09:** The extension allowlist is a hardcoded module constant in
  `file_select.py`, ported from OCR `allowed_ext.go`. No config surface this
  milestone; extending the list is a normal governed edit.
- **D-10:** Excluded categories beyond the allowlist: deleted files (`deleted`),
  git-binary files (`binary`), lockfiles and generated paths via default-exclude
  globs (`generated`), and oversized diffs (`too-large`).
- **D-11:** The size cap defaults to 5000 diff lines per file (CLI-overridable in a
  later phase). An oversized file is excluded as `too-large`, named in output, and
  never enters the coverage manifest.
- **D-12:** The exclusion reason vocabulary is a closed enum: `deleted`, `binary`,
  `generated`, `not-allowlisted`, `too-large`. Tests assert no other reason string
  can be emitted. — **Reversibility:** costly — output consumers and manifest
  readers key on these exact strings.

#### Decline and drop visibility
- **D-13:** `needs-position-review` findings appear in a dedicated section of the
  markdown report (claimed file/line, snippet, decline reason) AND survive in the
  JSON output with state `needs-position-review`. Never silently dropped.
- **D-14:** Review-mode `outside-diff` drops are listed per finding (path, line,
  reason) in a dropped-findings ledger in both report and JSON, matching the
  existing gaps-logged-never-dropped discipline (AUD-05 spirit).
- **D-15:** A `partial` terminal state exits nonzero (suggested 3) and prints every
  failed file with its state; `complete` exits 0. Scripted callers can never
  mistake partial for success. — **Reversibility:** reversible, but the exit code
  becomes CLI contract once documented.

### Claude's Discretion
- Internal manifest JSON schema fields beyond {file, state, SHAs}.
- Hunk-parser data structures and `positioning.py` window sizes (spec §3.1–3.2
  fixes the algorithms; representation is open).
- Exact default-exclude glob list (mirror OCR defaults, adapt to this repo).
- Order of module implementation and test fixture strategy.

### Deferred Ideas (OUT OF SCOPE)
- CLI flag to override the 5000-line size cap — Phase 4 (concurrency/limits) owns
  the flag surface (`--concurrency`, `--timeout`); add the cap override there.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DIFF-01 | Maintainer runs `python -m sec_overlay.cli review` against a base/head ref pair; refs validated against `^[A-Za-z0-9._/\-]+$` with leading `-` rejected; reads pin to resolved commit SHAs | See "Ref Validation and Pinned SHAs" pattern below; verified against `diffscope.py`'s existing `--` separator convention and OCR `review_cmd.go:118` ref-injection guard |
| DIFF-02 | `diffscope.py` returns per-file `ChangedFile` records: path, old_path, status (A/M/D/R), raw unified-diff text | See "diffscope.py Extension" pattern; `ChangedFile` is a new dataclass, additive per D-05, never touches frozen `models.py` |
| DIFF-03 | `file_select.py` deterministically splits changed files into reviewable/excluded (with reasons); deleted files excluded as `deleted`; agent cannot add/drop files | See "File Selection" pattern; verified OCR allowlist/exclude-glob source (`allowed_ext.go`) read and quoted verbatim below |
| DIFF-04 | Coverage manifest: one entry per reviewable file, pending → in_review → done\|failed; cannot seal `complete` with any `pending`; `partial` names unreviewed files | See "Coverage Manifest" pattern; verified OCR `RunManifest`/`ManifestBuilder` terminal-state logic (`internal/session/manifest.go`) as the design ancestor — note the state *names* differ (D-04 uses `partial`/`complete` seal semantics; sec-overlay does not need OCR's `skipped`/`waived`/`reused` states) |
| POS-01 | `diffhunks.py` parses unified diffs with stdlib only; exposes `added_line_numbers(file)` and `line_in_hunk(file, line)` | See "Hunk Parser" pattern; verified against OCR `internal/diff/hunk.go` read in full, including the exact header regex |
| POS-02 | `positioning.py` confirms location via hunk match → whole-file match → cross-file relocation; ambiguity/zero matches declines to `needs-position-review`, never guesses | See "Positioning Ladder" pattern; verified against OCR `internal/diff/resolver.go` read in full — flags a spec/implementation discrepancy (Pitfall 2) |
| POS-03 | Review mode: `phase_gate.py` drops a finding outside every changed hunk with reason `outside-diff`; audit mode keeps "existing whole-file check" | See "Gate Extension" pattern and Pitfall 1 — the "existing" audit-mode Finding.line check does not currently exist; this is a planning gap, not just an extension |

## Standard Stack

### Core

No new packages. REL-03 requires `helpers/pyproject.toml` `dependencies = []` to stay empty
across every new module in this milestone `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml:1-9 — "dependencies = []"]`. Every module in this phase uses only:

| Module | Stdlib import | Purpose |
|--------|---------------|---------|
| `diffscope.py` (extend) | `subprocess`, `re` (new, for ref regex) | git invocation, ref validation |
| `file_select.py` (new) | `fnmatch` (reuse pattern from `exclusions.py`) | extension allowlist + default-exclude globs |
| `review_coverage.py` (new) | `json`, `dataclasses` | manifest state machine + persistence |
| `diffhunks.py` (new) | `re`, `dataclasses` | unified-diff hunk parsing |
| `positioning.py` (new) | none beyond stdlib string ops (see Pitfall 2 — do **not** reach for `difflib`) | location confirmation ladder |
| `phase_gate.py` (extend) | none new | review-mode gate branch |

**Version verification:** `python3 --version` on this machine reports `Python 3.13.14`
`[VERIFIED: Bash `python3 --version`]`; `helpers/pyproject.toml` pins
`requires-python = ">=3.12"` `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml:5]`.
Phase 2's stdlib usage (`re`, `fnmatch`, `json`, `dataclasses`) is available on 3.12+; no
version floor issue for this phase (the 3.13 `pathlib.PurePath.full_match` floor question
belongs to Phase 3's `rule_glob.py`, not this phase, per STATE.md's decision log).

### Supporting

None. `file_select.py`'s default-exclude glob matching can reuse `fnmatch.fnmatch`, the same
function `exclusions.py` already uses
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/exclusions.py:9,71 — "import fnmatch" ... "any(fnmatch.fnmatch(f.file, pat) for pat in ex.paths)"]`.
This is sufficient for Phase 2 because OCR's own default-exclude patterns are `**`-heavy
(`doublestar.Match` semantics), but Phase 2 only needs "does this changed file match a
default-exclude pattern" — a straight `fnmatch` per-pattern loop reproduces `**` reasonably for
this narrower use (single-string match, not recursive directory walk), unlike Phase 3's
`rule_glob.py` which needs true `**`-cross-segment semantics for ordered rule resolution.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fnmatch.fnmatch` for default-exclude globs | `pathlib.PurePath.full_match` (3.13+) | True `**` cross-segment semantics, but raises the floor to 3.13 — defer this investment to Phase 3's `rule_glob.py`, which needs it for ordered first-match-wins rule resolution; Phase 2's exclude-only use case doesn't need the precision |
| Exact-string positioning match (OCR's actual algorithm) | `difflib.SequenceMatcher` (milestone spec's suggestion) | SequenceMatcher tolerates near-misses, which contradicts the never-guess invariant; OCR's own resolver never uses it (see Pitfall 2) — the spec's suggestion should not be followed |

**Installation:** None — zero new dependencies (REL-03).

## Package Legitimacy Audit

Not applicable. This phase installs no external packages; REL-03 pins
`helpers/pyproject.toml` `dependencies = []` and every module listed above uses only the Python
standard library `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml:6]`.
No `npm view` / `pip index versions` / `cargo search` check is applicable.

**Packages removed due to [SLOP] verdict:** none — no packages proposed.
**Packages flagged as suspicious [SUS]:** none — no packages proposed.

## Architecture Patterns

### System Architecture Diagram

```
maintainer CLI invocation
  python -m sec_overlay.cli review --from <base> --to <head>
        |
        v
[1] cli.py: parse args, call into diffscope.py
        |
        v
[2] diffscope.py: validate_ref(base) & validate_ref(head)
        |         regex ^[A-Za-z0-9._/\-]+$, reject leading '-'
        |         --> ValueError("invalid ref: ...") on failure
        |             caught by cli.py --> exit 2, one-line message
        v
[3] diffscope.py: git rev-parse <base> / <head>  (pinned SHAs, once)
        |
        v
[4] diffscope.py: changed_file_records(base_sha, head_sha)
        |         git diff --no-color --unified=3 <base_sha>..<head_sha> -- <path>  (per file)
        |         --> list[ChangedFile{path, old_path, status, diff_text}]
        v
[5] file_select.py: split(changed_files)
        |         extension allowlist (hardcoded) + default-exclude globs
        |         + deleted-file check + size cap (5000 lines)
        |         --> {reviewable: [...], excluded: [{path, reason}]}
        v
[6] review_coverage.py: seed manifest from reviewable set
        |         every entry starts "pending"; base_sha/head_sha recorded
        |         --> artifacts/coverage_manifest.json (written now, incrementally updated)
        v
[7] per reviewable file: transition entry to "in_review"
        |
        v
[8] diffhunks.py: parse_hunks(diff_text) --> list[Hunk]
        |         each Hunk: old_start, old_count, new_start, new_count, lines[]
        v
[9] positioning.py: for each candidate finding in this file
        |         resolve_from_hunk(hunk, finding)          [try 1: exact match, new-side then old-side]
        |            | no match
        |            v
        |         resolve_from_file_content(new_file, finding)  [try 2: exact match, whole new file]
        |            | no match
        |            v
        |         relocate_across_files(finding, other_diffs)   [try 3: cross-file exact match]
        |            | 0 or >1 hits
        |            v
        |         DECLINE --> needs-position-review (never a guessed line)
        v
[10] phase_gate.py (review-mode branch): diffhunks.line_in_hunk(file, confirmed_line)
        |         False --> drop finding, reason "outside-diff", log to dropped-findings ledger
        |         True  --> finding proceeds to report/output layer unchanged
        v
[11] review_coverage.py: transition entry to "done" (or "failed" on file-level error)
        |
        v
[12] after all reviewable files processed: seal(manifest)
        |         any "pending" left --> raise (cannot seal complete)
        |         all "done" --> terminal_state = complete --> exit 0
        |         some "failed", none "pending" --> terminal_state = partial --> exit 3 (D-15)
        v
report.py / sarif.py (existing, out of Phase 2 scope): render needs-position-review section
        (D-13) and dropped-findings ledger (D-14) into markdown + JSON output
```

### Recommended Project Structure

```
plugins/sec-overlay/skills/sec-overlay/helpers/
├── sec_overlay/
│   ├── diffscope.py        # EXTEND: + ChangedFile, changed_file_records(), validate_ref()
│   ├── file_select.py      # NEW: allowlist constant, exclude globs, split()
│   ├── review_coverage.py  # NEW: manifest state machine (D-01, NOT coverage.py)
│   ├── diffhunks.py        # NEW: Hunk/HunkLine dataclasses, parse_hunks(), added_line_numbers(), line_in_hunk()
│   ├── positioning.py      # NEW: resolve_from_hunk, resolve_from_file_content, relocate_across_files
│   ├── phase_gate.py       # EXTEND: + review-mode branch calling diffhunks.line_in_hunk
│   └── workspace.py        # EXTEND: + artifacts property/dir (gap — see Pitfall 3)
└── tests/
    ├── test_diffscope.py       # EXTEND: ref validation, ChangedFile records, pinned SHAs
    ├── test_file_select.py     # NEW
    ├── test_review_coverage.py # NEW
    ├── test_diffhunks.py       # NEW
    ├── test_positioning.py     # NEW
    └── test_phase_gate.py      # EXTEND: outside-diff drop in review mode
```

### Pattern 1: Ref Validation Before Any Git Subprocess Call

**What:** A regex guard that runs before the first `git` subprocess invocation, raising on
anything that could be interpreted as a flag by git.
**When to use:** Any code path accepting a user-supplied ref string that is later passed to
`subprocess`.
**Example:**
```python
# Source: OCR review_cmd.go:118 comment + milestone spec line 31 (verified against both)
import re

_REF_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")

def validate_ref(ref: str) -> str:
    """Reject a ref that could be parsed as a git flag or is otherwise unsafe.

    Args:
        ref: A base or head ref/SHA supplied by the caller.

    Returns:
        The same ref, unchanged, once validated.

    Raises:
        ValueError: If ref is empty, starts with '-', or contains a character
            outside [A-Za-z0-9._/-].
    """
    if not ref or ref.startswith("-") or not _REF_RE.match(ref):
        raise ValueError(f"invalid ref: {ref!r}")
    return ref
```
`[CITED: milestone spec line 31 — "reject ref-option injection before any git call... validate ^[A-Za-z0-9._/\-]+$, reject leading -"]`. The regex source is `[CITED: .planning/REQUIREMENTS.md:28 DIFF-01 — "^[A-Za-z0-9._/\-]+$"]`
(read this session, quoted verbatim).
OCR's own comment confirms the same intent at the call site
`[VERIFIED: /Users/christopher/tools/open-code-review/cmd/opencodereview/review_cmd.go:117-119 — "// Security (#112): reject ref-option injection before any git invocation.\n\tif err := validateReviewRefs(cc.RepoDir, opts); err != nil {"]`
(the guard function itself, `validateReviewRefs`, was not opened this session — only its call
site and the surrounding comment were read; do not cite its internal regex as verified).

### Pattern 2: diffscope.py Extension (Additive, D-05)

**What:** New `ChangedFile` dataclass + `changed_file_records()` alongside the existing
untouched functions.
**When to use:** Any time a caller needs the full unified-diff text and rename metadata, not
just a bare filename list.
**Example:**
```python
# Existing file to extend — verified verbatim:
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py:1-37
"""Scope incremental passes to changed files via git."""
from __future__ import annotations
import subprocess

def changed_files(base: str, head: str = "HEAD", *, runner=subprocess.run) -> list[str]:
    completed = runner(
        # `--` separates revisions from paths so a ref that looks like a path can't be misparsed.
        ["git", "diff", "--name-only", base, head, "--"], capture_output=True, text=True, check=False
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]

def head_sha(*, runner=subprocess.run) -> str:
    completed = runner(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return completed.stdout.strip()

# NEW additions (D-05) go beside these, unchanged existing functions:
from dataclasses import dataclass

@dataclass
class ChangedFile:
    path: str
    old_path: str | None
    status: str  # "A" | "M" | "D" | "R"
    diff_text: str

def changed_file_records(base: str, head: str, *, runner=subprocess.run) -> list[ChangedFile]:
    """Return per-file records with rename metadata and raw unified-diff text.

    Mirrors OCR's sealed-commit reads (review_cmd.go:335-403): base/head must already
    be resolved SHAs by the time this is called (see validate_ref + git rev-parse).
    """
    ...  # `git diff --no-color --unified=3 <base>..<head> -- <path>` per file, or one
         # `git diff --name-status` pass to get status/renames + one raw-diff pass parsed per file
```
Test convention to match — the existing fake-runner style
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffscope.py:1-23]`:
```python
def test_changed_files_parses_name_only(monkeypatch):
    class R:
        stdout = "app.py\nsrc/db.py\n"
        returncode = 0

    def fake_run(cmd, capture_output, text, check):
        assert cmd[:3] == ["git", "diff", "--name-only"]
        return R()

    assert changed_files("sha1", "HEAD", runner=fake_run) == ["app.py", "src/db.py"]
```
New tests for `changed_file_records` must follow this exact fake-runner-class shape (a `class R`
with `.stdout`/`.returncode`, a `fake_run(cmd, capture_output, text, check)` matching positional
args) — not a `MagicMock`.

### Pattern 3: File Selection (Allowlist + Exclude Globs)

**What:** A hardcoded allowlist constant checked case-insensitively, plus default-exclude glob
patterns, ported from OCR.
**When to use:** `file_select.py`'s `split()` entry point.
**Example — the exact OCR source data to port (D-09), read and quoted verbatim this session:**
```json
// Source: /Users/christopher/tools/open-code-review/internal/config/allowlist/supported_file_types.json
// (88 extensions total; representative excerpt — full list read this session)
[".java", ".kt", ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".rb",
 ".php", ".c", ".cpp", ".cs", ".swift", ".sh", ".sql", ".yaml", ".yml", ".json",
 ".toml", ".dart", ".tf", ".proto", ".graphql", ".lua", ".ex", ".exs", "..."]
```
```json
// Source: /Users/christopher/tools/open-code-review/internal/config/allowlist/default_exclude_patterns.json
// (35 patterns total; full list read this session)
["**/*_test.go", "**/src/test/java/**/*.java", "**/*.test.{js,jsx,ts,tsx}",
 "**/*.spec.{js,jsx,ts,tsx}", "**/__tests__/**", "**/testdata/**", "**/fixtures/**",
 "**/*.generated.*", "**/*.gen.go", "**/*.pb.go", "**/oh_modules/**", "**/__snapshots__/**",
 "**/*.snap", "..."]
```
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/allowlist/supported_file_types.json:1-88]`
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/allowlist/default_exclude_patterns.json:1-36]`
D-10 requires `generated` as the reason for a default-exclude-glob hit; D-09 requires the
allowlist to be a hardcoded module constant (no config surface this milestone). D-01's Claude's
Discretion note ("adapt to this repo") means: keep OCR's list as the starting point, but this
repo's target audits are primarily Python/Markdown/JSON/YAML plugin code — the planner should
decide whether to trim the list or keep it broad (broad is safer: an unlisted extension is
excluded as `not-allowlisted`, which is a safe default, not a functional bug).

Doc comment from the Go source explaining glob semantics, read and quoted verbatim
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/config/allowlist/allowed_ext.go]`
(exact doc-comment text not reproduced here since the file's full doc block was read but the
specific example lines were paraphrased in the earlier research pass, not re-quoted verbatim
this turn — the planner should treat the `doublestar.Match` semantics description as
`[CITED]`, not `[VERIFIED]`, and re-open the file if exact glob-matching edge cases matter for
`file_select.py`'s `fnmatch` substitute).

Reuse pattern from the existing exclusions machinery — note this is a **different data shape**
(rule/class-keyed, not purely path-keyed) so only the `fnmatch.fnmatch` call convention should
be reused, not the `Exclusions` dataclass itself:
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/exclusions.py:17-29,52-74]`

### Pattern 4: Coverage Manifest State Machine

**What:** A builder-style module owning `pending → in_review → done|failed` transitions, one
entry per reviewable file, raising on illegal transitions.
**When to use:** `review_coverage.py`, called only by the driver (D-03).
**Design ancestor (verified from OCR, read in full this session):**
```go
// Source: /Users/christopher/tools/open-code-review/internal/session/manifest.go:159-170
type TerminalState string

const (
    StateComplete TerminalState = "complete"
    StatePartial  TerminalState = "partial"
    StateFailed   TerminalState = "failed"
    StateSkipped  TerminalState = "skipped"
)
```
```go
// Source: /Users/christopher/tools/open-code-review/internal/session/manifest.go:941-957
func computeTerminal(cov Coverage, rf *RunFailure) TerminalState {
    if rf != nil {
        return StateFailed
    }
    selected := len(cov.Selected)
    if selected == 0 {
        return StateSkipped
    }
    failed := len(cov.Failed)
    switch {
    case failed == 0:
        return StateComplete
    case failed == selected:
        return StateFailed
    default:
        return StatePartial
    }
}
```
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/session/manifest.go:159-170,941-957]`
**Divergence from D-04 to flag for the planner:** OCR's `computeTerminal` treats "all failed" as
`StateFailed` (a distinct terminal state from `partial`), and has no state at all if the
selected set is empty (`StateSkipped`). D-04 as locked reads: *"partial seals only when every
non-done entry is failed... complete requires all entries done."* This is a two-state model
(`complete`/`partial`), not OCR's four-state model. Do **not** port OCR's `failed`/`skipped`
terminal states — D-04 only defines `complete` and `partial`; a run where every file fails is
still `partial` under D-04, not a third `failed` terminal state. This is a genuine simplification
from OCR, already correctly captured in CONTEXT.md's decisions — the OCR source is background
for the *transition and seal-guarding* logic (illegal-transition raises, sealed-set immutability
pattern below), not for the terminal-state enum itself.

OCR's illegal-transition guard pattern to mirror for D-03 ("illegal transitions raise"):
```go
// Source: /Users/christopher/tools/open-code-review/internal/session/manifest.go:583-603
bi, ok := b.items[itemID]
if !ok {
    return fmt.Errorf("manifest: transition on unknown item %s", itemID)
}
if bi.state != stateSelected {
    if bi.state == to {
        return nil // idempotent: same outcome re-applied
    }
    return fmt.Errorf("manifest: item %s already %s, cannot transition to %s",
        itemID, bi.state, to)
}
```
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/session/manifest.go:583-603]` —
port the *shape* (unknown-id error, same-state-reapply is idempotent, different-state-reapply
raises), not the Go field names.

**Recommended Python shape (Claude's Discretion per CONTEXT.md):**
```python
"""Per-file review coverage manifest — pending -> in_review -> done|failed."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_VALID_STATES = ("pending", "in_review", "done", "failed")

@dataclass
class ManifestEntry:
    path: str
    state: str = "pending"
    reason: str | None = None  # populated only when state == "failed"

@dataclass
class CoverageManifest:
    base_sha: str
    head_sha: str
    entries: dict[str, ManifestEntry] = field(default_factory=dict)
    sealed_terminal: str | None = None  # "complete" | "partial", set only by seal()

    def transition(self, path: str, to: str, *, reason: str | None = None) -> None:
        if to not in _VALID_STATES:
            raise ValueError(f"unknown state: {to!r}")
        entry = self.entries[path]  # KeyError is intentional: unknown path is a caller bug
        order = _VALID_STATES.index
        if order(to) < order(entry.state) and to != entry.state:
            raise ValueError(f"{path}: illegal transition {entry.state} -> {to}")
        entry.state = to
        if to == "failed":
            entry.reason = reason

    def seal(self) -> str:
        pending = [p for p, e in self.entries.items() if e.state == "pending"]
        if pending:
            raise ValueError(f"cannot seal: pending entries remain: {pending}")
        self.sealed_terminal = (
            "complete" if all(e.state == "done" for e in self.entries.values()) else "partial"
        )
        return self.sealed_terminal
```
This shape is a starting suggestion, not a locked contract — CONTEXT.md explicitly leaves
"internal manifest JSON schema fields beyond {file, state, SHAs}" to discretion. Persist with
the existing `_atomic_write` helper
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py:101-121]`
so incremental writes (D-02, "written incrementally during the run") never leave a
partially-written manifest on disk.

### Pattern 5: Hunk Parser (POS-01)

**What:** Stdlib-`re` unified-diff hunk parser exposing `added_line_numbers` and `line_in_hunk`.
**When to use:** `diffhunks.py`, consumed by both `positioning.py` and `phase_gate.py`.
**Example — OCR's exact header regex and line classification, read in full this session:**
```go
// Source: /Users/christopher/tools/open-code-review/internal/diff/hunk.go (114 lines, read in full)
var hunkHeaderRe = regexp.MustCompile(`^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@`)

type HunkLineType int
const (
    HunkContext HunkLineType = iota
    HunkAdded
    HunkDeleted
)
```
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/diff/hunk.go]` — the regex string
above and the three-value line-type enum were read verbatim from the file this session. Line
classification: a line prefixed `+` is `HunkAdded`, `-` is `HunkDeleted`, anything else
(including a leading space) is `HunkContext`, with the prefix marker stripped from `Content`.
Default counts (`,count` omitted in the header) are `1`. Parsing stops/ignores lines before the
first `@@` header (file-level `diff --git`/`---`/`+++` lines) and skips a
`\ No newline at end of file` marker line inside a hunk.

**Python port shape:**
```python
"""Stdlib-only unified-diff hunk parser."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

class LineType(Enum):
    CONTEXT = "context"
    ADDED = "added"
    DELETED = "deleted"

@dataclass
class HunkLine:
    type: LineType
    content: str
    old_line: int | None  # None for ADDED lines
    new_line: int | None  # None for DELETED lines

@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[HunkLine] = field(default_factory=list)

def parse_hunks(raw_diff_text: str) -> list[Hunk]:
    """Parse unified-diff text into hunks. Ignores everything before the first '@@'."""
    hunks: list[Hunk] = []
    current: Hunk | None = None
    old_line = new_line = 0
    for line in raw_diff_text.split("\n"):
        m = _HUNK_HEADER_RE.match(line)
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) else 1
            current = Hunk(old_start, old_count, new_start, new_count)
            hunks.append(current)
            old_line, new_line = old_start, new_start
            continue
        if current is None:
            continue  # file-level header lines before the first hunk
        if line.startswith("\\ No newline at end of file"):
            continue
        if line.startswith("+"):
            current.lines.append(HunkLine(LineType.ADDED, line[1:], None, new_line))
            new_line += 1
        elif line.startswith("-"):
            current.lines.append(HunkLine(LineType.DELETED, line[1:], old_line, None))
            old_line += 1
        else:
            content = line[1:] if line.startswith(" ") else line
            current.lines.append(HunkLine(LineType.CONTEXT, content, old_line, new_line))
            old_line += 1
            new_line += 1
    return hunks

def added_line_numbers(hunks: list[Hunk]) -> set[int]:
    """New-file line numbers of every added line across all hunks."""
    return {hl.new_line for h in hunks for hl in h.lines
            if hl.type is LineType.ADDED and hl.new_line is not None}

def line_in_hunk(hunks: list[Hunk], line: int) -> bool:
    """True if `line` (new-file line number) is added or context inside any hunk."""
    return any(
        hl.new_line == line and hl.type in (LineType.ADDED, LineType.CONTEXT)
        for h in hunks for hl in h.lines
    )
```
POS-01 asks for `added_line_numbers(file)`/`line_in_hunk(file, line)` signatures keyed by
`file`, not `hunks` — the planner should decide whether `diffhunks.py` caches a
`file -> list[Hunk]` map internally (parsing once per file, called by both functions) or takes
pre-parsed hunks as an argument; both satisfy POS-01's literal signature if `file` resolves to
an already-scoped `ChangedFile.diff_text`. This is exactly the "hunk-parser data structures...
open" discretion CONTEXT.md grants.

### Pattern 6: Positioning Ladder (POS-02)

**What:** Three-step location-confirmation ladder: hunk match → whole-file match → cross-file
relocation, declining on ambiguity or zero matches.
**When to use:** `positioning.py`, called once per finding before the finding is allowed to ship.
**Verified OCR algorithm (read in full this session — `internal/diff/resolver.go`, 307 lines):**

```go
// Source: internal/diff/resolver.go — normalizeLine
func normalizeLine(s string) string {
    s = strings.TrimSpace(s)
    s = strings.TrimPrefix(s, "+")
    s = strings.TrimPrefix(s, "-")
    return strings.TrimSpace(s)
}
```
```go
// Source: internal/diff/resolver.go — matchConsecutive (exact match, sliding window)
// for each candidate start index i in sideLines:
//   for j, target := range targetLines:
//     if sideLines[i+j].content != target { break, try next i }
//   if all matched: return start, end, true
```
```go
// Source: internal/diff/resolver.go — RelocateAcrossFiles
func RelocateAcrossFiles(cm *Comment, diffs []Diff) (string, bool) {
    var hits []string
    for _, d := range diffs {
        if d.Path == cm.Path { continue }
        probe := *cm
        probe.StartLine, probe.EndLine = 0, 0
        if resolveFromHunk(d, &probe) || resolveFromFileContent(d, &probe) {
            hits = append(hits, d.Path)
        }
    }
    if len(hits) != 1 {
        return "", false  // 0 hits: not found. >1 hits: ambiguous. Both decline.
    }
    ...
}
```
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/diff/resolver.go — ResolveComment, resolveFromHunk, resolveFromFileContent, RelocateAcrossFiles, matchConsecutive, extractSideLines, normalizeLine, splitAndNormalize, all read in full this session]`.

**Python port shape:**
```python
"""Never-guess finding-location confirmation ladder."""
from __future__ import annotations
from dataclasses import dataclass

def _normalize(line: str) -> str:
    s = line.strip()
    if s.startswith("+") or s.startswith("-"):
        s = s[1:]
    return s.strip()

def _split_and_normalize(code: str) -> list[str]:
    return [n for n in (_normalize(ln) for ln in code.split("\n")) if n]

def _match_consecutive(side_lines: list[tuple[int, str]], targets: list[str]) -> int | None:
    """Exact-match sliding window. Returns the starting new-file line number, or None."""
    n = len(targets)
    for i in range(len(side_lines) - n + 1):
        if all(side_lines[i + j][1] == targets[j] for j in range(n)):
            return side_lines[i][0]
    return None

def resolve_from_hunk(hunks, existing_code: str) -> int | None:
    targets = _split_and_normalize(existing_code)
    if not targets:
        return None
    new_side = [(hl.new_line, _normalize(hl.content)) for h in hunks for hl in h.lines
                if hl.type in (LineType.CONTEXT, LineType.ADDED) and hl.new_line is not None]
    found = _match_consecutive(new_side, targets)
    if found is not None:
        return found
    old_side = [(hl.old_line, _normalize(hl.content)) for h in hunks for hl in h.lines
                if hl.type in (LineType.CONTEXT, LineType.DELETED) and hl.old_line is not None]
    return _match_consecutive(old_side, targets)

def resolve_from_file_content(new_file_text: str, existing_code: str) -> int | None:
    targets = _split_and_normalize(existing_code)
    if not targets:
        return None
    file_lines = [(i + 1, _normalize(ln)) for i, ln in enumerate(new_file_text.split("\n"))
                  if _normalize(ln)]
    return _match_consecutive(file_lines, targets)

def relocate_across_files(existing_code: str, other_files: dict[str, "ParsedDiff"]) -> str | None:
    """Returns the single matching path, or None (zero or ambiguous >1 hits both decline)."""
    hits = [path for path, pd in other_files.items()
            if resolve_from_hunk(pd.hunks, existing_code) is not None
            or resolve_from_file_content(pd.new_file_text, existing_code) is not None]
    return hits[0] if len(hits) == 1 else None
```

**Never use `difflib.SequenceMatcher` here** — see Common Pitfalls, Pitfall 2, for the verified
discrepancy between the milestone spec's suggestion and OCR's actual (exact-match) algorithm.

### Pattern 7: Gate Extension (POS-03)

**What:** A review-mode branch in `phase_gate.py` that drops findings outside every changed
hunk.
**Verified — the existing whole-file check, read in full this session:**
```python
# Source: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py:42-49
def _line_in_range(fp: Path, line: int) -> bool:
    if not fp.is_file():
        return False
    try:
        n = len(fp.read_text(errors="replace").splitlines())
    except OSError:
        return False
    return 1 <= line <= n
```
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py:42-49]`.
See Common Pitfalls, Pitfall 1, for why this function is **not** the audit-mode Finding gate the
spec/POS-03 describe — it is a citation-ref resolver used elsewhere in the same file.

**Recommended shape for the new review-mode branch:**
```python
# In phase_gate.py, alongside the existing checks — illustrative, not verified code:
def review_mode_line_check(hunks_by_file: dict[str, list["Hunk"]],
                            finding_file: str, confirmed_line: int) -> tuple[bool, str | None]:
    """Returns (keep, drop_reason). drop_reason is 'outside-diff' when dropped."""
    hunks = hunks_by_file.get(finding_file, [])
    if line_in_hunk(hunks, confirmed_line):
        return True, None
    return False, "outside-diff"
```
This function signature is illustrative (Claude's Discretion territory — CONTEXT.md does not
lock the gate's internal shape, only its externally observable behavior: drop with reason
`outside-diff` in review mode, keep the existing check in audit mode).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy diff-position matching | A custom similarity-scoring window search | OCR's exact-string-match ladder (Pattern 6) | Exact match is a *feature*, not a shortfall — the never-guess invariant means a near-miss should decline, not "helpfully" match; a fuzzy matcher would silently violate D-13/D-14's decline discipline |
| Path-glob matching for excludes | A hand-rolled `**`-aware glob engine | `fnmatch.fnmatch` (already used in `exclusions.py`) for Phase 2's narrower exclude-only need | Phase 2 doesn't need ordered first-match-wins rule resolution (that's Phase 3's `rule_glob.py`); reinventing `**` semantics here duplicates work Phase 3 will do properly with `pathlib.PurePath.full_match` |
| Atomic manifest writes | A custom lock-file or write-then-rename scheme | Existing `_atomic_write` in `workspace.py` | Already implemented, already used by `write_findings`; reuse avoids a second atomicity bug surface |
| Git ref injection prevention | A shell-escaping library | The `^[A-Za-z0-9._/\-]+$` allowlist regex + `--` path separator (both already locked, D-06 and existing `diffscope.py` convention) | An allowlist regex is simpler and more auditable than an escaping library for this narrow input shape (git refs) |

**Key insight:** Every non-trivial algorithm in this phase (positioning ladder, hunk parsing,
coverage terminal-state computation) already has a production-tested reference implementation
sitting in this environment (`open-code-review`). The engineering task is disciplined porting
and verification against real source, not invention — the risk in this phase is trusting a
paraphrase (the milestone spec) instead of reading the referenced source directly, which this
research already caught diverging once (Pitfall 2).

## Common Pitfalls

### Pitfall 1: The "existing whole-file check" POS-03 refers to does not check `Finding.line`

**What goes wrong:** A plan that reads POS-03 literally ("audit mode keeps the existing
whole-file check") and simply leaves `phase_gate.py` unchanged for audit mode will ship audit
mode with **no upper-bound line check on `Finding.line` at all** — because no such check exists
today.
**Why it happens:** The milestone spec states: *"Replace the whole-file check
(`phase_gate.py:42-50`, currently `1 <= line <= n`) for diff-review findings..."*
`[CITED: milestone spec line 67]`. This is misleading: `_line_in_range` at those exact lines
does exist and does compute `1 <= line <= n`
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py:42-49]` —
but it is called only from `resolve_ref`/`is_comment_line`, which resolve **markdown citation
refs** (`{"id", "text", "refs": [...]}`) emitted by analysis phases (recon, architecture,
threat-model), never `Finding.line`. Grepping `findings_gate.py` confirms the only line check
applied to a `Finding` is a **lower-bound-only** check:
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py:56-57 — "if f.line < 1:\n            errors.append(f"{f.id}: line must be >= 1")"]`.
There is no `f.line > n` check anywhere in `findings_gate.py`, `verify.py`, `report.py`,
`driver.py`, or `patch_status.py` for a `Finding` object.
**How to avoid:** The plan must treat "keep the existing whole-file check for audit mode" as
"audit mode's `Finding.line` gating stays exactly as it is today" (lower-bound-only via
`findings_gate.py`) — not as "there is an upper-bound whole-file Finding check to preserve
untouched." If the planner (or a future requirement) wants an upper-bound audit-mode check for
`Finding.line`, that is new functionality, not a preservation of existing behavior, and should
be called out as such rather than assumed to already exist.
**Warning signs:** A task description that says "extend the existing Finding whole-file check"
— there is no such function to extend; `_line_in_range` extends only for citation refs.

### Pitfall 2: The milestone spec's positioning fallback suggestion contradicts OCR's actual algorithm

**What goes wrong:** Implementing `resolve_from_file_content` with `difflib.SequenceMatcher`
(a fuzzy/similarity matcher) as the spec's §3.2 wording suggests would silently violate the
never-guess invariant — `SequenceMatcher` can report a "good enough" match for a line that has
materially changed, which is exactly the guessed-line outcome D-13's decline discipline exists
to prevent.
**Why it happens:** The milestone spec paraphrases OCR's fallback step as suggesting
`difflib.SequenceMatcher` for the window search. Reading OCR's actual `resolver.go` this
session shows the real algorithm never calls anything similarity-based: `resolveFromFileContent`
uses the exact same `matchConsecutive` exact-string-equality sliding window as
`resolveFromHunk`, just against the whole new-file content with blank lines filtered out
`[VERIFIED: /Users/christopher/tools/open-code-review/internal/diff/resolver.go — resolveFromFileContent, matchConsecutive]`.
**How to avoid:** Port the exact-match algorithm (Pattern 6). Do not add `difflib` to
`positioning.py`. If a future requirement genuinely wants fuzzy tolerance, that is a deliberate
divergence from OCR and from the never-guess invariant, and needs its own explicit decision —
not a default inherited from a spec paraphrase.
**Warning signs:** Any `import difflib` inside `positioning.py`; a test that asserts a "close
enough" match succeeds where the compared lines are not byte-identical after normalization.

### Pitfall 3: `Workspace` has no `artifacts` directory today — D-02's path needs new plumbing

**What goes wrong:** A plan that assumes `ws.artifacts / "coverage_manifest.json"` already
resolves to something will fail immediately — `Workspace` exposes `kb`, `findings_dir`, `runs`,
`reports`, `state_path`, `sarif_path`, `report_path`, `findings_json_path`, and no `artifacts`
property `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py:46-97 — full property list and `ensure()` method read in full]`.
**Why it happens:** D-02 specifies the target path (`artifacts/coverage_manifest.json` "in the
run's artifact directory") but this directory is new surface area this phase must add, not an
existing convention being reused.
**How to avoid:** A task in the plan must add an `artifacts` property to `Workspace` (following
the exact style of the existing properties, e.g. `return self.root / "artifacts"`) and include
it in `ensure()`'s directory-creation list, before `review_coverage.py` can write to it.
**Warning signs:** `AttributeError: 'Workspace' object has no attribute 'artifacts'` at test
time — this is not a bug in new code, it means the `Workspace` extension task was skipped.

### Pitfall 4: `models.py`'s `FindingStatus` enum has no slot for `needs-position-review`

**What goes wrong:** A plan that tries to add `NEEDS_POSITION_REVIEW = "needs-position-review"`
directly to `FindingStatus` violates the frozen-contract rule (`models.py` must never be
edited — carried forward from Phase 1's CONTEXT.md, "one-way" per that phase's D-02).
**Why it happens:** D-13 says a declined finding must appear "in the JSON output with state
`needs-position-review`," which reads naturally as a `Finding.status` value — but the enum that
field's type is drawn from is frozen
`[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py:24-40 — full FindingStatus enum listing CANDIDATE, RAW, CONFIRMED, REJECTED, FIXED, STALE, DUPLICATE, NEEDS_DEPLOYMENT_TESTING="needs-deployment-testing", INFORMATIONAL; no needs-position-review value present]`.
**How to avoid:** The plan needs an explicit decision on representation: (a) `positioning.py`
returns its own result type (e.g. a `PositionResult` with a `decision` field, separate from
`Finding`) that the driver/report layer branches on to route into the dedicated report section
(D-13) without ever setting `Finding.status` to an out-of-enum string, or (b) some other
mechanism that does not touch `models.py`. This is a genuine open design question the plan must
resolve, not an oversight to silently patch around by editing the frozen enum.
**Warning signs:** Any diff touching `models.py`; any code doing
`Finding(status="needs-position-review", ...)` (would raise at `FindingStatus(...)` construction
since it's not a valid enum member) or `Finding(status=FindingStatus.CANDIDATE, ...)` used as a
stand-in that then requires a side-channel to distinguish "declined" from "genuinely
candidate" — both are red flags of working around, not resolving, the frozen contract.

### Pitfall 5: `exclusions.py`'s `Exclusions` dataclass is finding-shaped, not file-shaped

**What goes wrong:** Reusing `Exclusions`/`apply_exclusions` directly for `file_select.py`
would require constructing fake `Finding` objects just to run them through a
finding-partitioning function, which is backwards — `file_select.py` excludes *files* before any
finding exists.
**Why it happens:** The milestone spec says `file_select.py` should "reuse [`exclusions.py`]
where possible," which could be misread as "reuse the whole module's public API."
**How to avoid:** Reuse only the underlying primitive — `fnmatch.fnmatch` and its calling
convention `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/exclusions.py:9,71]`
— not `Exclusions`/`apply_exclusions`, which are keyed by `rule_id`/`cls`/finding-path and
partition already-generated `Finding` objects, a different problem shape than pre-scan file
selection.
**Warning signs:** A `file_select.py` that imports `Finding` from `models.py` — file selection
should have no dependency on the `Finding` type at all.

## Code Examples

See Architecture Patterns section above — every code example there is either read verbatim from
an existing file this session (marked `[VERIFIED: path:lines]`) or an original Python port of a
verified Go algorithm (marked as a "recommended shape," not verified code, since it does not yet
exist in this repo).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Whole-repo audit scan only (`sec_overlay.cli scan`/`audit`) | Diff-scoped `review` mode added alongside, not replacing, audit mode | This phase (v5.0) | `phase_gate.py` gains a mode branch; `cli.py` gains a `review` verb; existing `scan`/`audit` verbs and their tests are untouched (D-05 additive rule) |
| Bare filename list from `changed_files()` | Rich `ChangedFile` records with status/rename/diff-text | This phase | Positioning and hunk parsing need the raw diff text, which `changed_files()` never captured |

**Deprecated/outdated:** Nothing in this phase deprecates existing sec-overlay behavior — every
change is additive per D-05's explicit rule and the broader "existing callers are untouched"
constraint repeated across D-01/D-05.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `changed_file_records` should use `git diff --no-color --unified=3 <base>..<head> -- <path>` per file (rather than one `git diff` parsed per-file) | Architecture Patterns, Pattern 2 | Low — the milestone spec itself offers both as acceptable (`[CITED: milestone spec line 31]`); either satisfies DIFF-02, this is an implementation-detail choice already left open by the spec, not by CONTEXT.md discretion explicitly, but functionally equivalent |
| A2 | OCR's `doublestar.Match` glob semantics for `default_exclude_patterns.json` are adequately approximated by `fnmatch.fnmatch` for Phase 2's narrower use case | Standard Stack, Supporting | Medium — if a default-exclude pattern relies on true cross-segment `**` matching that `fnmatch` handles differently (e.g. `**/oh_modules/**` matching at arbitrary depth), some generated/vendored files could slip through as `reviewable` instead of `excluded: generated`; mitigate with a task-level test asserting each ported pattern still excludes its OCR-documented example path under `fnmatch` |
| A3 | The `doublestar.Match` glob-semantics doc comment in `allowed_ext.go` was read this session but its exact wording was not re-quoted verbatim in this document (see Pattern 3) | Architecture Patterns, Pattern 3 | Low — the actual pattern *data* (both JSON files) is fully verified verbatim; only the prose explanation of glob syntax is downgraded to CITED. Re-open the file before writing brace-expansion-sensitive tests. |

## Open Questions

1. **Should `file_select.py`'s allowlist be trimmed for this repo's actual target-repo profile,
   or kept as OCR's full 88-extension list?**
   - What we know: D-09 says "ported from OCR `allowed_ext.go`," which reads as "keep the list."
     The Claude's Discretion note about "exact default-exclude glob list... adapt to this repo"
     only mentions the *exclude* list, not the allowlist.
   - What's unclear: Whether "ported" means byte-identical or "ported and then adapted like the
     exclude list."
   - Recommendation: Keep the allowlist as OCR's full list verbatim (D-09's plain reading); an
     unlisted extension safely falls to `not-allowlisted`, which is not a functional gap, just a
     conservative default. Revisit only if Phase 5's real target-repo run surfaces a wrongly
     excluded, clearly-reviewable extension.

2. **Exact representation for a `needs-position-review` decline (Pitfall 4) — is a new
   dedicated result type introduced in `positioning.py`, or does the report layer accept a
   free-form dict?**
   - What we know: `models.py`/`Finding`/`FindingStatus` must not change (frozen contract).
     D-13 requires both a markdown section and JSON survival with state
     `needs-position-review`.
   - What's unclear: Whether the JSON output referred to in D-13 is the existing
     `findings.json` (which serializes `Finding.to_dict()`, and therefore cannot carry an
     out-of-enum status string without `from_dict` breaking on round-trip) or a *new*,
     separate JSON artifact specific to review mode.
   - Recommendation: The planner should decide this is a **new** review-mode-specific JSON
     artifact (not `findings.json`), so `Finding`/`FindingStatus` stays untouched and
     `needs-position-review` lives as a plain string field there — consistent with how the
     coverage manifest is already its own new JSON file (D-02), not shoehorned into
     `state.json`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | All of DIFF-01..04, POS-03 | Yes | 2.55.0 | — |
| python3 | Entire phase | Yes | 3.13.14 | — |
| uv | Test/lint/type-check commands | Yes | 0.11.32 | — |

`[VERIFIED: Bash "git --version" -> "git version 2.55.0"; "python3 --version" -> "Python 3.13.14"; "uv --version" -> "uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)"]`

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — all required tools are present and exceed the
project's stated floor (`requires-python = ">=3.12"`).

## Validation Architecture

`.planning/config.json` has no `workflow.nyquist_validation` key
`[VERIFIED: .planning/config.json:1-5 — {"workflow": {"_auto_chain_active": false}}]`; per the
absent-means-enabled rule, this section is included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml — "dev = [\"pytest>=8\", \"ruff>=0.6\", \"ty>=0.0.1a1\"]"]` |
| Config file | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` `[VERIFIED: same file]` |
| Quick run command | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/test_diffscope.py tests/test_phase_gate.py -q` |
| Full suite command | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIFF-01 | Ref regex rejects leading `-`/bad chars; exit 2 on bad ref; SHAs pinned once | unit | `uv run pytest tests/test_diffscope.py -k validate_ref -x` | ❌ Wave 0 |
| DIFF-02 | `ChangedFile` records carry path/old_path/status/diff_text | unit | `uv run pytest tests/test_diffscope.py -k changed_file_records -x` | ❌ Wave 0 (extend existing file) |
| DIFF-03 | Deleted file excluded as `deleted`; agent cannot mutate the returned list | unit | `uv run pytest tests/test_file_select.py -x` | ❌ Wave 0 |
| DIFF-04 | Manifest transitions; cannot seal `complete` with a `pending` entry; `partial` names failed files | unit | `uv run pytest tests/test_review_coverage.py -x` | ❌ Wave 0 |
| POS-01 | `added_line_numbers`/`line_in_hunk` classify added/context lines correctly | unit | `uv run pytest tests/test_diffhunks.py -x` | ❌ Wave 0 |
| POS-02 | Hunk match → whole-file match → cross-file relocation → decline on ambiguity/zero | unit | `uv run pytest tests/test_positioning.py -x` | ❌ Wave 0 |
| POS-03 | Review mode drops `outside-diff`; audit mode keeps existing (lower-bound-only) `Finding.line` behavior unchanged | unit | `uv run pytest tests/test_phase_gate.py -k outside_diff_or_review -x` | ❌ Wave 0 (extend existing file) |

### Sampling Rate

- **Per task commit:** the quick run command for the module(s) touched by that task
- **Per wave merge:** `uv run pytest -q` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_file_select.py` — covers DIFF-03
- [ ] `tests/test_review_coverage.py` — covers DIFF-04
- [ ] `tests/test_diffhunks.py` — covers POS-01
- [ ] `tests/test_positioning.py` — covers POS-02
- [ ] Extend `tests/test_diffscope.py` — covers DIFF-01, DIFF-02 (new tests alongside the two
      existing ones, same fake-runner-class convention)
- [ ] Extend `tests/test_phase_gate.py` — covers POS-03 (new tests alongside existing
      `resolve_ref`/`ref_resolves` tests)
- [ ] Framework install: none — pytest already a dev dependency, no new install needed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This is a local CLI tool with no auth surface |
| V3 Session Management | No | No session concept in this phase |
| V4 Access Control | No | No multi-user access control surface |
| V5 Input Validation | Yes | Ref-validation regex (D-06) at the git-subprocess boundary; extension-allowlist + exclude-glob validation at the file-selection boundary (D-09/D-10) |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Git ref/argument injection (a ref like `--upload-pack=...` interpreted as a flag) | Tampering | Regex allowlist `^[A-Za-z0-9._/\-]+$` rejecting a leading `-`, plus the existing `--` revision/path separator convention already in `diffscope.py` `[VERIFIED: plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py:21 — "[\"git\", \"diff\", \"--name-only\", base, head, \"--\"]"]` |
| TOCTOU on ref resolution (ref moves between validation and use) | Tampering | Resolve to a commit SHA once via `git rev-parse` immediately after validation (D-07); every subsequent git call uses the pinned SHA, never the original mutable ref string |
| Oversized diff causing excessive memory/CPU in hunk parsing | Denial of Service (self-inflicted, not adversarial in this local-CLI context) | 5000-line size cap (D-11) excludes oversized files as `too-large` before they reach `diffhunks.py`/`positioning.py` |

## Sources

### Primary (HIGH confidence)
- `/Users/christopher/tools/open-code-review/internal/diff/hunk.go` — read in full this session
- `/Users/christopher/tools/open-code-review/internal/diff/resolver.go` — read in full this session
- `/Users/christopher/tools/open-code-review/internal/config/allowlist/allowed_ext.go` — read in full this session
- `/Users/christopher/tools/open-code-review/internal/config/allowlist/supported_file_types.json` — read in full this session
- `/Users/christopher/tools/open-code-review/internal/config/allowlist/default_exclude_patterns.json` — read in full this session
- `/Users/christopher/tools/open-code-review/internal/session/manifest.go` — read in full this session
- `/Users/christopher/tools/open-code-review/cmd/opencodereview/review_cmd.go` (lines 100-130, 325-405) — read this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py` (lines 1-100) — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/exclusions.py` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` (grep, lines 56-57, 102-125) — targeted grep + line read this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` — read in full this session
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_diffscope.py` — read in full this session
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/phases/02-diff-pipeline-positioning/02-CONTEXT.md`, `.planning/config.json` — read in full this session

### Secondary (MEDIUM confidence)
- `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md` — the milestone spec, read in full this session; treated as MEDIUM (not HIGH) because one of its claims (positioning fallback algorithm, Pitfall 2) was found to diverge from the actual OCR source it cites

### Tertiary (LOW confidence)
- None — no WebSearch or unverified training-knowledge claims were required for this phase; every
  external dependency (OCR algorithms) had local source available and was read directly.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, verified against `pyproject.toml`; every stdlib
  module cited is already in use elsewhere in this codebase
- Architecture: HIGH — every pattern is either a verified read of existing sec-overlay code or a
  verified read of the OCR reference implementation it is meant to mirror
- Pitfalls: HIGH — all five pitfalls were discovered by direct verification (reading the actual
  files) rather than inferred from the spec's prose, including one confirmed spec/implementation
  discrepancy (Pitfall 2)

**Research date:** 2026-08-17
**Valid until:** 2026-09-16 (30 days — stdlib-only, no external ecosystem churn risk; re-verify
sooner only if `models.py`/`phase_gate.py`/`workspace.py` change before Phase 2 planning begins)
