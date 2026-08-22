---
phase: 03-rule-matching-review-modes
plan: 03
subsystem: security-review-rules
tags: [sec-overlay, rule-docs, pytest, tdd, python]

requires:
  - phase: 03-rule-matching-review-modes
    provides: "03-01/03-02 shipped python.md, default.md, the four-layer rule resolution, and the RULE-03 safety gate"
provides:
  - "Nine built-in rule docs (go, java, python, php, rust, ts_js_tsx_jsx, kotlin, swift, default) each covering the five RULE-05 defect families with exclusion blocks"
  - "BUILTIN_PATH_RULE_MAP extended to nine entries with a trailing **/* -> default.md catch-all, mirroring OCR's system_rules.json order (D-02)"
  - "REQUIRED_RULE_SECTIONS and RULE_SECTION_SYNONYMS constants driving a data-driven conformance test"
  - "tests/test_rule_docs.py: a fully parametrized suite proving map<->doc coverage, section ordering, exclusion blocks, and idempotent resolution"
affects: [rule-matching-review-modes, sec-overlay-review-mode]

actuals:
  tokens: 13162
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Rule docs are LLM prompt payloads (D-05): terse imperative checklists, no STE100 prose pass, each `####` section ends with an explicit 'Do not report in the following cases:' exclusion block."
    - "Conformance tests are driven entirely from BUILTIN_PATH_RULE_MAP / REQUIRED_RULE_SECTIONS / RULE_SECTION_SYNONYMS, never a hardcoded per-language filename list, so a language added later cannot skip coverage."

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/go.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/java.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/php.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/rust.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/ts_js_tsx_jsx.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/kotlin.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/swift.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_docs.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md
    - plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

key-decisions:
  - "BUILTIN_PATH_RULE_MAP gets a trailing \"**/*\": \"default.md\" catch-all so default.md is a reachable, testable map value like every other doc, instead of living outside the map as a post-loop fallback."
  - "default.md rewritten to the same five-family/exclusion-block structure as the other eight docs (out of the plan's originally scoped file list) because the conformance test's per-doc family-coverage check is parametrized over every mapped doc, default.md included."
  - "Task 3's README/CHANGELOG/version-bump deliverable landed inside Task 2's commit, not a separate one, because the repo's doc-update-guard hook forces those updates into the same commit that touches the rule_docs/ folder; there was no remaining file left uncommitted for a distinct Task 3 commit."

requirements-completed: [RULE-05]

coverage:
  - id: D1
    description: "Nine rule docs ship, each covering null/nil dereference, thread safety, injection (SQL and XSS), resource leaks, and swallowed errors with an explicit exclusion block per family"
    requirement: "RULE-05"
    verification:
      - kind: unit
        ref: "tests/test_rule_docs.py::test_doc_covers_required_families_with_exclusion_blocks"
        status: pass
      - kind: unit
        ref: "tests/test_rule_docs.py::test_mapped_doc_exists_and_is_nonempty"
        status: pass
    human_judgment: false
  - id: D2
    description: "BUILTIN_PATH_RULE_MAP and the rule_docs directory have no orphan in either direction; a colliding path resolves to the first map entry; resolution is idempotent"
    requirement: "RULE-05"
    verification:
      - kind: unit
        ref: "tests/test_rule_docs.py::test_no_orphan_rule_doc"
        status: pass
      - kind: unit
        ref: "tests/test_rule_docs.py::test_first_matching_map_entry_wins_on_collision"
        status: pass
      - kind: unit
        ref: "tests/test_rule_docs.py::test_resolve_rule_doc_is_idempotent"
        status: pass
    human_judgment: false
  - id: D3
    description: "ts/js/tsx/jsx all resolve to one doc; unmatched/extensionless paths resolve to default.md; representative paths for go/java/php/rust/kotlin/swift resolve to their own doc"
    requirement: "RULE-05"
    verification:
      - kind: unit
        ref: "tests/test_rule_docs.py::test_ts_js_tsx_jsx_extensions_resolve_to_same_doc"
        status: pass
      - kind: unit
        ref: "tests/test_rule_docs.py::test_unmatched_extension_and_no_extension_resolve_to_default"
        status: pass
      - kind: unit
        ref: "tests/test_rule_docs.py::test_representative_path_resolves_to_mapped_doc"
        status: pass
    human_judgment: false
  - id: D4
    description: "No rule doc instructs the reviewing agent to assign a finding status, severity, or receipt tier (REV-03)"
    requirement: "RULE-05"
    verification:
      - kind: other
        ref: "rg -n 'confirmed|receipt_tier|severity: ' plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/*.md (no match, exit 1)"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-18
status: complete
---

# Phase 03 Plan 03: Seven Per-Language Rule Docs and Conformance Test Summary

**Shipped go.md, java.md, php.md, rust.md, ts_js_tsx_jsx.md, kotlin.md, and swift.md rule docs, rewrote default.md to match, and extended `BUILTIN_PATH_RULE_MAP`/`REQUIRED_RULE_SECTIONS` with a 36-case data-driven conformance test (`test_rule_docs.py`), closing RULE-05.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-08-18T18:35:00Z
- **Completed:** 2026-08-18T19:30:00Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments
- Nine built-in rule docs now exist (go, java, python, php, rust, ts_js_tsx_jsx, kotlin, swift, default), each covering the same five defect families in `python.md`'s fixed order, each with an explicit "Do not report in the following cases:" exclusion block per family, ported from OCR's field-tested per-language checklists (D-02) and restructured into this plan's fixed five-family contract.
- `BUILTIN_PATH_RULE_MAP` extended from one entry to nine, insertion order mirroring OCR's `system_rules.json` exactly, with a trailing `"**/*": "default.md"` catch-all making `default.md` a reachable map value.
- `REQUIRED_RULE_SECTIONS` (5-tuple of defect families) and `RULE_SECTION_SYNONYMS` (per-language heading wording per family) added to `rule_glob.py`, giving the conformance test data to assert against instead of hardcoded doc names.
- `tests/test_rule_docs.py`: 36 parametrized/direct tests proving map↔doc coverage (no orphan on either side), fixed section order with exclusion blocks, TS/JS/TSX/JSX collapsing to one doc, representative-path resolution per language, extensionless/unmatched-extension fallback to `default.md`, first-match-wins on a colliding map, and idempotent resolution.
- `rule_docs/README.md` now carries the full nine-row pattern table plus the D-05 style-exemption note.

## Task Commits

Each task was committed atomically:

1. **Task 1: Data-driven rule-doc conformance test and the extended pattern map** - `59fa3eb` (test — RED, confirmed failing for the 7 missing docs before Task 2)
2. **Task 2: Author the seven remaining per-language rule docs** - `bc1b021` (feat — GREEN; also carries Task 3's README table, CHANGELOG entry, and version bump per the doc-update-guard hook, see Deviations)

**Plan metadata:** pending (this commit)

_Note: Task 1 was TDD (`tdd="true"`); its RED-phase commit `59fa3eb` also carried the repo's mandatory README/CHANGELOG/version-bump updates required by the doc-update-guard hook on any commit touching `plugins/sec-overlay/`._

## Files Created/Modified
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/go.md` - Go rule doc: typed-nil-in-interface, nil map writes, unchecked type assertions, goroutine capture, `html/template` injection, `defer`-in-loop leaks, swallowed errors
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/java.md` - Java rule doc: Optional/null misuse, non-thread-safe collections, `PreparedStatement` injection, try-with-resources leaks, swallowed exceptions
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/php.md` - PHP rule doc: loose-comparison/type-juggling, shared FPM/worker process state, `unserialize()` injection, transaction leaks, `@`-suppressed errors
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/rust.md` - Rust rule doc: `unwrap`/`expect`/`panic!` on fallible values, lock-order inversion, parameterized-query injection, `Drop`/`JoinHandle` leaks, swallowed `Result`s
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/ts_js_tsx_jsx.md` - TS/JS/TSX/JSX rule doc: optional-chaining gaps, unhandled promise rejection, `dangerouslySetInnerHTML` injection, listener/subscription leaks, swallowed rejections
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/kotlin.md` - Kotlin rule doc: `!!`/platform-type nullability, `GlobalScope` coroutine leaks, parameterized-query injection, `use{}` resource leaks, swallowed `Result`/exceptions
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/swift.md` - Swift rule doc: force unwrap/implicitly unwrapped optionals, actor isolation, parameterized-query injection, retain-cycle/observer leaks, `try?` swallowing errors
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md` - Rewritten to the same five-family/exclusion-block structure as the language docs (fallback doc)
- `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/README.md` - Full nine-row pattern table matching `BUILTIN_PATH_RULE_MAP`, D-05 style-exemption note
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_glob.py` - `BUILTIN_PATH_RULE_MAP` extended to 9 entries; `REQUIRED_RULE_SECTIONS`/`RULE_SECTION_SYNONYMS` added
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_docs.py` - New 36-test conformance suite
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` - Notes the two new constants and the map extension
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md` - Notes `test_rule_docs.py`
- `plugins/sec-overlay/CHANGELOG.md` - `1.53.1` (RED test commit) and `1.54.0` (seven docs + default.md rewrite) entries
- `plugins/sec-overlay/.claude-plugin/plugin.json` - `1.53.0` → `1.53.1` → `1.54.0`

## Decisions Made
- `BUILTIN_PATH_RULE_MAP` gets a trailing `"**/*": "default.md"` catch-all rather than leaving `default.md` as an out-of-map fallback, so it is provably reachable and testable like every other doc (carried over from plan 03-01/03-02's design, confirmed unchanged this plan).
- `default.md` was rewritten to the five-family/exclusion-block structure even though the plan's `<files>` list for Task 2 did not name it — the conformance test's per-doc family-coverage check is parametrized over every `BUILTIN_PATH_RULE_MAP` value, `default.md` included, so it had to match the same contract to pass (Rule 2: missing critical functionality for the test to be honest about coverage).
- Each new doc's per-language idioms are grounded in OCR's actual field-tested checklists (`/Users/christopher/tools/open-code-review/internal/config/rules/rule_docs/*.md`, read directly) rather than generic translation, per D-02, then trimmed to exactly the five families this plan's contract requires — OCR's docs cover much broader scope (typos, dead code, performance, macros, platform-specific frameworks) that does not belong here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] doc-update-guard hook required README/CHANGELOG/version-bump in the RED-phase commit**
- **Found during:** Task 1 (writing `test_rule_docs.py` and extending `rule_glob.py`)
- **Issue:** `git commit` for the two core files was rejected by the repo's `doc-update-guard` pre-commit hook: any commit touching `plugins/sec-overlay/` must also update `CHANGELOG.md` and bump `plugin.json`'s version, and any commit touching `sec_overlay/`/`tests/` must stage that folder's README.md.
- **Fix:** Bumped `plugin.json` 1.53.0→1.53.1 (patch, `test` commit type), added a `## 1.53.1` CHANGELOG entry, added notes to `sec_overlay/README.md` and `tests/README.md`, staged all four alongside the two core files.
- **Files modified:** `plugins/sec-overlay/.claude-plugin/plugin.json`, `plugins/sec-overlay/CHANGELOG.md`, `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`, `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`
- **Verification:** `prek` hooks passed on re-run of the commit.
- **Committed in:** `59fa3eb` (Task 1 commit)

**2. [Rule 2 - Missing Critical] `default.md` rewritten to the five-family structure**
- **Found during:** Task 2 (authoring the seven new docs)
- **Issue:** `default.md` still had its original generic Correctness/Security/Resource Handling/Concurrency/Maintainability sections from before this plan; `test_doc_covers_required_families_with_exclusion_blocks` is parametrized over every `BUILTIN_PATH_RULE_MAP` value including `default.md`, so it would fail the family-coverage/exclusion-block check.
- **Fix:** Rewrote `default.md` with the same five families (null/absent-value dereference, thread safety, injection, resource leaks, swallowed errors) in language-agnostic wording, each with an exclusion block, plus a note in its opening blockquote that it is the fallback doc.
- **Files modified:** `plugins/sec-overlay/skills/sec-overlay/rules/rule_docs/default.md`
- **Verification:** `test_doc_covers_required_families_with_exclusion_blocks[default.md]` passes.
- **Committed in:** `bc1b021` (Task 2 commit)

**3. [Rule 3 - Blocking] Task 3's deliverable landed in Task 2's commit, not its own**
- **Found during:** Task 3 (indexing the docs in `rule_docs/README.md`)
- **Issue:** The doc-update-guard hook required `rule_docs/README.md` to be staged in the same commit as the new `.md` doc files (Task 2), since both live in the same hook-tracked folder. Filling the README's full nine-row table at that point (rather than a placeholder) satisfied both the hook and Task 3's own acceptance criteria in one pass, leaving no distinct file changes for a separate Task 3 commit.
- **Fix:** No further commit was made for Task 3. Verified all of Task 3's acceptance criteria against the state left by `bc1b021`: the table has 9 `.md` references, `D-05`/`prompt payload` text is present, `plugin.json`'s version (1.54.0) is strictly greater than the plan's starting version (1.53.0), and `prek run` on the three named files passes.
- **Files modified:** none (verification only)
- **Verification:** `rg -c '\.md' rule_docs/README.md` → 9; `rg -n 'D-05|prompt payload' rule_docs/README.md` → matches; `prek run --files rule_docs/README.md CHANGELOG.md plugin.json` → passed.
- **Committed in:** n/a (no new commit required)

---

**Total deviations:** 3 auto-fixed (2 Rule 3 blocking, 1 Rule 2 missing critical)
**Impact on plan:** All three were necessary for either repo governance compliance or test-contract honesty. No scope creep beyond `default.md`, which the plan's own conformance test required to match the new structure.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RULE-05 is complete: all nine built-in rule docs exist, are indexed, and are conformance-tested.
- `test_rule_docs.py` guards against future regressions — a new language added later without a doc or map entry fails the suite immediately.
- Full test suite is green except the two known environmental failures (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`), both pre-existing and unrelated to this plan.
- `ruff check` and `ty check` are clean for all files this plan touched (`rules/` is excluded from both tools by `pyproject.toml`); the 9 pre-existing `ty` diagnostics in `tests/test_review_tracer.py` predate this plan and are out of scope.

## Self-Check: PASSED

All 9 created/modified deliverable files confirmed present on disk; both task commit hashes
(`59fa3eb`, `bc1b021`) confirmed present in `git log --oneline --all`.

---
*Phase: 03-rule-matching-review-modes*
*Completed: 2026-08-18*
