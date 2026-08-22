# Phase 2: Diff Pipeline & Positioning - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the diff pipeline and the positioning discipline for review
mode. Given a base/head ref pair, the harness deterministically identifies every
changed file (`diffscope.py` extension), splits the files into reviewable and
excluded sets (`file_select.py`), tracks per-file review coverage in a manifest
(`review_coverage.py`), parses unified diffs with the stdlib (`diffhunks.py`),
confirms exact finding locations without guessing (`positioning.py`), and drops
review-mode findings outside every changed hunk (`phase_gate.py` extension).
Requirements: DIFF-01..04, POS-01..03. Rule matching, review profiles, bundling,
and resume belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Coverage manifest module
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

### diffscope extension
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

### File selection and exclusion
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

### Decline and drop visibility
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (primary)
- `/Users/christopher/Workspace/review_open-code-review/spec_sec-overlay-improvement_20260816_0920.md`
  §2 (diff pipeline), §3 (hunk parser, positioning, position-vs-hunk gate) — the
  authoritative module designs, invariants, and OCR source mappings this phase
  implements. Outside the repo; if unreachable at planning time, stop and ask.

### Milestone planning
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria 1–5, and the
  coverage-module naming-collision note.
- `.planning/REQUIREMENTS.md` — DIFF-01..04, POS-01..03 exact wording.
- `.planning/intel/SYNTHESIS.md` — entry point to delivered-baseline intel.
- `.planning/intel/constraints.md` — stdlib-only invariant, frozen-contract rule.

### Prior phase decisions
- `.planning/phases/01-baseline-health-verification/01-CONTEXT.md` — carried
  forward: frozen `models.py`/`evidence.py` contract (one-way), per-commit plugin
  version bump governance (D-04), uv-run gate commands (D-10), zero-warnings
  meaning (D-14).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `sec_overlay/diffscope.py` (36 lines): `changed_files()`, `head_sha()` with
  injectable `runner=subprocess.run` — the extension keeps this test pattern.
- `sec_overlay/exclusions.py`: existing exclusion machinery; spec directs
  `file_select.py` to reuse it where possible.
- `sec_overlay/phase_gate.py` (375 lines): whole-file check at lines ~42-50 is the
  audit-mode path to keep; the hunk gate is a review-mode branch beside it.
- `tests/` conventions: pytest with fake-runner test doubles (see
  `test_wiring.py`, Phase 1's fake-runner class fix).

### Established Patterns
- Stdlib-only core (ADR-2026-08-04) — `diffhunks.py` parses with `re`,
  `positioning.py` falls back to `difflib.SequenceMatcher`. No new dependencies.
- Frozen contract: `models.py` and `evidence.py` must not change. New record
  types (`ChangedFile`, manifest entries) live in the new modules, not in
  `models.py`.
- Injectable subprocess runner for all git calls (existing `diffscope.py` style).

### Integration Points
- `cli.py` gains the `review` verb entry (DIFF-01) — ref validation error handling
  (exit 2) and partial-seal exit (nonzero) land here.
- `phase_gate.py` review-mode branch calls `diffhunks.line_in_hunk`.
- Run artifact directory (`artifacts/`) receives `coverage_manifest.json`.

</code_context>

<specifics>
## Specific Ideas

- Mirror OCR (`open-code-review`) semantics wherever the spec cites a Go source
  file: `allowed_ext.go` (allowlist), `resolver.go` (positioning ladder),
  `shared.go` RunManifest (coverage states), MAIN_TASK rule (no comments on
  unchanged code).
- Never-guess invariant is the phase's identity: ambiguity always declines to
  `needs-position-review`; a guessed line is a defect.

</specifics>

<deferred>
## Deferred Ideas

- CLI flag to override the 5000-line size cap — Phase 4 (concurrency/limits) owns
  the flag surface (`--concurrency`, `--timeout`); add the cap override there.

</deferred>

---

*Phase: 02-diff-pipeline-positioning*
*Context gathered: 2026-08-17*
