# Phase 2: Diff Pipeline & Positioning - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 8 (2 extended, 6 new/extended incl. workspace.py)
**Analogs found:** 8 / 8 (all have a real in-repo analog; positioning/hunk logic additionally
ported from a verified external reference, `open-code-review`, cited in RESEARCH.md)

All code excerpts below were extracted from RESEARCH.md's already-verified `[VERIFIED: path:lines]`
citations (RESEARCH.md read this session in full) and cross-checked by `wc -l` against the live
files in `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/`. Line counts matched:
`diffscope.py` 36, `exclusions.py` 74, `phase_gate.py` 375, `workspace.py` 236,
`findings_gate.py` 148, `models.py` 183.

All paths below are relative to
`plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` unless stated otherwise.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `diffscope.py` (extend) | service (git integration) | request-response (subprocess call/parse) | itself, existing `changed_files()`/`head_sha()` | exact — additive to same file |
| `file_select.py` (new) | utility (pure filter) | transform | `exclusions.py` | role-match (finding-shaped, not file-shaped — see below) |
| `review_coverage.py` (new) | model + service (state machine + persistence) | CRUD (manifest entries) + file-I/O | `workspace.py` (`_atomic_write`), OCR `manifest.go` (external, verified) | role-match (persistence), exact (state-machine shape, external) |
| `diffhunks.py` (new) | utility (parser) | transform | OCR `internal/diff/hunk.go` (external, verified) | exact (no in-repo analog; ported) |
| `positioning.py` (new) | service (pure resolution ladder) | transform | OCR `internal/diff/resolver.go` (external, verified) | exact (no in-repo analog; ported) |
| `phase_gate.py` (extend) | middleware (gate/filter) | transform | itself, `_line_in_range` at lines 42-49 | exact — additive branch in same file |
| `workspace.py` (extend) | config/model (path properties) | CRUD (directory layout) | itself, existing property list lines 46-97 | exact — additive to same file |
| `cli.py` (extend, per DIFF-01/D-06/D-15) | controller | request-response | existing `cli.py` verb dispatch (not read this session — planner should open it directly) | role-match |

## Pattern Assignments

### `diffscope.py` (extend) — service, request-response

**Analog:** itself, lines 1-37 (verified in RESEARCH.md)

**Existing imports + injectable-runner pattern** (`diffscope.py:1-37`):
```python
"""Scope incremental passes to changed files via git."""
from __future__ import annotations
import subprocess

def changed_files(base: str, head: str = "HEAD", *, runner=subprocess.run) -> list[str]:
    completed = runner(
        ["git", "diff", "--name-only", base, head, "--"], capture_output=True, text=True, check=False
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]

def head_sha(*, runner=subprocess.run) -> str:
    completed = runner(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return completed.stdout.strip()
```

**Core pattern to copy for new additions** — same injectable-`runner` signature shape, same
`--` path separator convention, same `capture_output=True, text=True, check=False` call style.
New code (D-05, additive, do not touch existing two functions):
```python
from dataclasses import dataclass
import re

_REF_RE = re.compile(r"^[A-Za-z0-9._/\-]+$")

def validate_ref(ref: str) -> str:
    if not ref or ref.startswith("-") or not _REF_RE.match(ref):
        raise ValueError(f"invalid ref: {ref!r}")
    return ref

@dataclass
class ChangedFile:
    path: str
    old_path: str | None
    status: str  # "A" | "M" | "D" | "R"
    diff_text: str

def changed_file_records(base: str, head: str, *, runner=subprocess.run) -> list[ChangedFile]:
    ...  # git diff --name-status for status/renames, git diff --unified=3 per path for diff_text
```

**Test pattern to copy** (from `tests/test_diffscope.py:1-23`, verified):
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
Use this exact fake-runner-class shape (`class R` with `.stdout`/`.returncode`, `fake_run(cmd,
capture_output, text, check)` matching positional args) for every new `changed_file_records`
test — not `MagicMock`.

**Error handling:** None present in the analog — subprocess failures surface as empty output,
not exceptions. `validate_ref` is the one new place that raises (`ValueError`), caught only in
`cli.py`.

---

### `file_select.py` (new) — utility, transform

**Analog:** `exclusions.py` (lines 17-29, 52-74, verified) — reuse the `fnmatch` call
convention only, not the `Exclusions` dataclass (Pitfall 5: it is finding-shaped, keyed by
rule/class, not file-shaped).

**Pattern to copy — glob-match call style**:
```python
import fnmatch
# exclusions.py:71 pattern:
# any(fnmatch.fnmatch(f.file, pat) for pat in ex.paths)
```
Apply the same `fnmatch.fnmatch(path, pattern)` loop against the hardcoded default-exclude glob
list (D-10, "generated" reason) instead of a `Finding`-keyed structure.

**Core pattern (hardcoded constants, D-09):**
```python
_ALLOWED_EXTENSIONS = {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".go", ...}  # module constant
_DEFAULT_EXCLUDE_GLOBS = ["**/*_test.go", "**/*.test.{js,jsx,ts,tsx}", ...]      # module constant
_EXCLUSION_REASONS = ("deleted", "binary", "generated", "not-allowlisted", "too-large")  # closed enum, D-12

def split(changed_files: list["ChangedFile"]) -> dict:
    reviewable, excluded = [], []
    for cf in changed_files:
        # deleted -> "deleted"; git-binary marker -> "binary"; size cap 5000 lines -> "too-large";
        # fnmatch against _DEFAULT_EXCLUDE_GLOBS -> "generated"; extension not in allowlist -> "not-allowlisted"
        ...
    return {"reviewable": reviewable, "excluded": excluded}
```
Data source for the two constants: OCR `allowed_ext.go` / `supported_file_types.json` (88 exts)
and `default_exclude_patterns.json` (35 patterns) — both verified in RESEARCH.md, quoted there
verbatim; re-open those files directly if exact list content is needed during implementation.

**Error handling:** Pure function, no I/O beyond diff text already in hand — no try/catch
needed (name the failure mode test: nothing here can raise beyond a caller passing malformed
`ChangedFile` records, which is a caller bug, not a runtime failure to guard).

---

### `review_coverage.py` (new) — model + service, CRUD + file-I/O

**Analog:** `workspace.py` `_atomic_write` (lines 101-121, verified) for persistence; OCR
`manifest.go` (external, verified in full) for the state-machine shape only — **do not** port
OCR's 4-state terminal enum (`complete`/`partial`/`failed`/`skipped`); D-04 locks a 2-state model
(`complete`/`partial` only).

**Illegal-transition guard shape to mirror** (OCR `manifest.go:583-603`, verified):
```go
if bi.state != stateSelected {
    if bi.state == to {
        return nil // idempotent: same outcome re-applied
    }
    return fmt.Errorf("manifest: item %s already %s, cannot transition to %s", itemID, bi.state, to)
}
```
Port the *shape* (unknown-path is an error, same-state re-apply is idempotent, different-state
re-apply raises) — not the Go names.

**Recommended Python shape (Claude's Discretion, D-01..D-04):**
```python
"""Per-file review coverage manifest — pending -> in_review -> done|failed."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field

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
        entry = self.entries[path]  # KeyError intentional: unknown path is a caller bug
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

**Persistence pattern to copy — reuse existing atomic write** (`workspace.py:101-121`,
verified): call the existing `_atomic_write` helper for every incremental manifest write (D-02)
so a crash never leaves a partially-written `coverage_manifest.json`. Do not hand-roll a new
lock/rename scheme.

**Pitfall to avoid (Pitfall 3):** `Workspace` has no `artifacts` property today
(`workspace.py:46-97` lists `kb`, `findings_dir`, `runs`, `reports`, `state_path`, `sarif_path`,
`report_path`, `findings_json_path` — no `artifacts`). Add `artifacts` as a new property
following the exact style of the existing ones (`return self.root / "artifacts"`) and include it
in `ensure()`'s directory-creation list before `review_coverage.py` can write to it.

**Error handling:** Illegal transitions and sealing-with-pending both raise `ValueError` with a
message naming the offending path(s) — matches the "raise with actionable message" convention
used by `validate_ref` above.

---

### `diffhunks.py` (new) — utility, transform

**Analog:** No in-repo analog; ported near-verbatim from OCR `internal/diff/hunk.go` (114 lines,
read in full and verified in RESEARCH.md).

**Header regex + line-type classification (verified, OCR source):**
```
^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@
```
`+` prefix → ADDED, `-` prefix → DELETED, anything else (incl. leading space) → CONTEXT with the
marker stripped. Missing `,count` defaults to `1`. Lines before the first `@@` are ignored; a
`\ No newline at end of file` marker line is skipped.

**Core pattern:**
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
    old_line: int | None
    new_line: int | None

@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[HunkLine] = field(default_factory=list)

def parse_hunks(raw_diff_text: str) -> list[Hunk]:
    ...  # see RESEARCH.md Pattern 5 for the full loop, verified against OCR line-by-line

def added_line_numbers(hunks: list[Hunk]) -> set[int]:
    return {hl.new_line for h in hunks for hl in h.lines
            if hl.type is LineType.ADDED and hl.new_line is not None}

def line_in_hunk(hunks: list[Hunk], line: int) -> bool:
    return any(hl.new_line == line and hl.type in (LineType.ADDED, LineType.CONTEXT)
               for h in hunks for hl in h.lines)
```
POS-01 names the public signatures `added_line_numbers(file)`/`line_in_hunk(file, line)` keyed
by `file`, not `hunks` — decide whether the module caches a `file -> list[Hunk]` map internally
(parse once, call by both) or takes pre-parsed hunks; either satisfies POS-01 if `file` resolves
to a `ChangedFile.diff_text`.

**Error handling:** Pure `re`-based parser; malformed diff text produces an empty/partial hunk
list, never an exception — matches the stdlib-only, no-new-dependency constraint (REL-03).

---

### `positioning.py` (new) — service, transform

**Analog:** No in-repo analog; ported near-verbatim from OCR `internal/diff/resolver.go` (307
lines, read in full and verified). **Do not use `difflib.SequenceMatcher`** — the milestone
spec's paraphrase suggests it, but OCR's actual algorithm is exact-string-match only (Pitfall 2,
verified by reading the real source).

**Core pattern — exact-match sliding window, three-step ladder:**
```python
"""Never-guess finding-location confirmation ladder."""
from __future__ import annotations

def _normalize(line: str) -> str:
    s = line.strip()
    if s.startswith("+") or s.startswith("-"):
        s = s[1:]
    return s.strip()

def _split_and_normalize(code: str) -> list[str]:
    return [n for n in (_normalize(ln) for ln in code.split("\n")) if n]

def _match_consecutive(side_lines: list[tuple[int, str]], targets: list[str]) -> int | None:
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
    hits = [path for path, pd in other_files.items()
            if resolve_from_hunk(pd.hunks, existing_code) is not None
            or resolve_from_file_content(pd.new_file_text, existing_code) is not None]
    return hits[0] if len(hits) == 1 else None  # 0 or >1 hits both decline
```

**Decline discipline (D-13/D-14):** zero matches or >1 ambiguous cross-file hits both return
`None`/decline — never guess a line. This is the phase's core invariant; do not add any
tolerance or fuzzy fallback.

**Frozen-contract constraint (Pitfall 4):** `models.py`'s `FindingStatus` enum has no
`needs-position-review` slot and must not be edited (frozen contract, Phase 1 D-02, one-way).
`positioning.py` must return its own result type (e.g. a `PositionResult` with a `decision`
field) separate from `Finding.status` — the driver/report layer branches on that result to route
into D-13's dedicated report section without touching `models.py`.

**Error handling:** Every path in the ladder returns `None`/decline rather than raising — the
"error" here is a business outcome (`needs-position-review`), not an exception.

---

### `phase_gate.py` (extend) — middleware, transform

**Analog:** itself, `_line_in_range` at lines 42-49 (verified, existing citation-ref check —
**not** the audit-mode `Finding` gate, per Pitfall 1).

**Existing pattern to model the new branch's shape after (not to reuse directly):**
```python
# phase_gate.py:42-49
def _line_in_range(fp: Path, line: int) -> bool:
    if not fp.is_file():
        return False
    try:
        n = len(fp.read_text(errors="replace").splitlines())
    except OSError:
        return False
    return 1 <= line <= n
```

**New review-mode branch (illustrative, Claude's Discretion on internal shape per POS-03):**
```python
def review_mode_line_check(hunks_by_file: dict[str, list["Hunk"]],
                            finding_file: str, confirmed_line: int) -> tuple[bool, str | None]:
    """Returns (keep, drop_reason). drop_reason is 'outside-diff' when dropped."""
    hunks = hunks_by_file.get(finding_file, [])
    if line_in_hunk(hunks, confirmed_line):
        return True, None
    return False, "outside-diff"
```

**Critical correction for the audit-mode side (Pitfall 1):** POS-03's "audit mode keeps the
existing whole-file check" does NOT mean an upper-bound check on `Finding.line` is being
preserved — no such check exists today. The only existing `Finding.line` check is
lower-bound-only in `findings_gate.py:56-57`:
```python
if f.line < 1:
    errors.append(f"{f.id}: line must be >= 1")
```
"Preserve audit mode" means: leave `findings_gate.py`'s lower-bound-only check exactly as-is. Do
not assume or add an upper-bound `Finding.line` check under the guise of "keeping the existing
check" — that would be new functionality requiring its own decision.

**Error handling:** Same style as `_line_in_range` — return a boolean/tuple outcome, never raise,
on a file-not-found or read error; the drop-with-reason ledger (D-14) is the report layer's
responsibility, not this function's.

---

### `workspace.py` (extend) — config/model, CRUD

**Analog:** itself, existing property list (lines 46-97, verified).

**Pattern to copy — property style:**
```python
# Follow the exact style of existing properties, e.g.:
@property
def reports(self) -> Path:
    return self.root / "reports"
```
Add:
```python
@property
def artifacts(self) -> Path:
    return self.root / "artifacts"
```
And add it to `ensure()`'s directory-creation list alongside the other directories it already
creates.

---

## Shared Patterns

### Injectable subprocess runner
**Source:** `diffscope.py:1-37` (existing `runner=subprocess.run` keyword pattern)
**Apply to:** `changed_file_records()` and any new git call — same signature convention,
`capture_output=True, text=True, check=False`, `--` path separator.

### Atomic JSON writes
**Source:** `workspace.py:101-121` (`_atomic_write`)
**Apply to:** `review_coverage.py`'s every incremental manifest write (D-02).

### Never-guess / decline discipline
**Source:** OCR `resolver.go` (external, verified), applied per D-13/D-14
**Apply to:** `positioning.py` (decline to `None`), `phase_gate.py` review branch (drop with
`outside-diff` reason, logged not silently discarded), and the report layer (dedicated
needs-position-review section + dropped-findings ledger — out of Phase 2's module list but
consumes these outputs).

### Closed-enum exclusion reasons
**Source:** D-12, `exclusions.py`'s existing reason-string convention (finding-shaped analog)
**Apply to:** `file_select.py` — reasons limited to `deleted`, `binary`, `generated`,
`not-allowlisted`, `too-large`; a test must assert no other string can be emitted.

### Fail with actionable, quoted messages
**Source:** `validate_ref`'s `ValueError(f"invalid ref: {ref!r}")` convention, extended to
`review_coverage.py`'s transition/seal errors
**Apply to:** Every new raise site in this phase — quote the offending value, name the operation.

## No Analog Found (in-repo)

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `diffhunks.py` | utility | transform | No unified-diff parser exists in this repo yet; ported from OCR (external, verified) instead of an in-repo analog |
| `positioning.py` | service | transform | No location-confirmation ladder exists in this repo yet; ported from OCR (external, verified) instead of an in-repo analog |

Both have a verified external reference implementation (`open-code-review`,
`internal/diff/hunk.go` and `internal/diff/resolver.go`, read in full this session per
RESEARCH.md) — treat that as the analog for these two files instead of an in-repo one.

## Metadata

**Analog search scope:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` (all
Phase-2-relevant existing modules: `diffscope.py`, `exclusions.py`, `phase_gate.py`,
`workspace.py`, `findings_gate.py`, `models.py`) plus the external reference tool
`open-code-review` cited throughout RESEARCH.md.
**Files scanned:** 8 existing repo files (line counts verified via `wc -l`) + RESEARCH.md's
already-verified external citations (no redundant re-reads of the external tool this session —
its content was already read and quoted verbatim in RESEARCH.md this same research pass).
**Pattern extraction date:** 2026-08-17
