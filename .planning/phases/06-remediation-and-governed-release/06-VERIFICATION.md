---
phase: 06-remediation-and-governed-release
verified: 2026-08-22T00:01:11Z
status: gaps_found
score: 6/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Documentation accurately reflects the shipped `review --workspace` behavior (no self-contradicting docs)"
    status: failed
    reason: >
      06-REVIEW.md (this phase's own code-review artifact, committed at 01818ed, the current
      HEAD) flagged three doc files as still stating `review` has no `--workspace` override —
      directly contradicted by the `--workspace` flag this same phase (06-01) shipped. Confirmed
      by direct grep against the live files: the stale claim is still present, verbatim, in all
      three. No commit after 01818ed touches any of them, and neither 06-DEFECTS.md nor
      deferred-items.md records a disposition for this finding (it is a distinct issue from
      05-REVIEW.md's identically-numbered but unrelated WR-01 FileNotFoundError bug, which *is*
      closed — see 06-DEFECTS.md row 10). This is a hard-rule violation per the plugin's own
      `plugins/sec-overlay/CLAUDE.md`: "docs track code in the same commit."
    artifacts:
      - path: "plugins/sec-overlay/skills/sec-overlay/SKILL.md:95"
        issue: "States '`--root` has no `--workspace` override for review (unlike `scan`/`audit`)' — false as of 06-01's `3354f44`."
      - path: "plugins/sec-overlay/skills/sec-overlay/README.md:34-36"
        issue: "States 'review... has no `--workspace` override, so pass the same `--root` string to every invocation' — false."
      - path: "plugins/sec-overlay/skills/sec-overlay/helpers/README.md:267"
        issue: "States '`review` has no `--workspace` override, so the same `--root` string must be passed to every invocation of one run' — false."
    missing:
      - "Update all three passages to describe the real `--workspace` flag (06-REVIEW.md's own \"Fix\" section gives exact before/after text for SKILL.md:95)."
      - "Add a disposition row for this finding to 06-DEFECTS.md, or a fix commit, before closing the phase."
      - "Consider the doc-invariant assertion 06-REVIEW.md suggests (grep the three files for the stale phrase) so a future flag addition can't silently leave documentation behind again."
  - truth: "ROADMAP.md accurately reflects Phase 6's completion state"
    status: failed
    reason: >
      .planning/ROADMAP.md line 30 still lists Phase 6 with an unchecked `- [ ]` box, and the
      Progress table (line 263) still reads "In Progress" with no completion date — both stale
      relative to STATE.md (`status: complete`, `current_phase: 06`, all 5 plans `[x]`), the
      merged PR history, and 06-DEFECTS.md's own closure statement ("Phase 6 is closed"). Every
      other completed phase in the same table (1-5) carries "Complete" plus a date; Phase 6 does
      not. This is a tracking inconsistency the phase's own closure commit (`45660a9`) partially
      fixed (bumped the plans list to 5/5 and checked 06-05's box) but did not finish.
    artifacts:
      - path: ".planning/ROADMAP.md:30"
        issue: "Phase 6 header checkbox still `- [ ]`, unlike Phases 1-5 (`- [x]`)."
      - path: ".planning/ROADMAP.md:263"
        issue: "Progress table row still reads 'In Progress' with an empty completion-date cell."
    missing:
      - "Check the Phase 6 header box and set the Progress-table status/date to match Phases 1-5's format."
deferred: []
human_verification:
  - test: "Confirm the three shipping PRs (#24-#27, four of five total) that merged without a CodeRabbit walkthrough — due to the OSS rate limit and a standing waiver — were each an explicit, informed decision by the repository owner at merge time, not an automated bypass."
    expected: "Each merge was a deliberate human call, matching the receipt's stated reasoning (rate limit / waiver), not a default that happened silently."
    why_human: "This is a policy judgment about whether the root CLAUDE.md's 'wait for CodeRabbit's walkthrough before merging' rule was legitimately waived case-by-case versus habitually skipped; the git/GitHub evidence corroborates the receipt's factual claims (rate-limit message on PR #24, no walkthrough comment on PRs #24/#25/#26/#27) but cannot establish intent or whether the waiver should stand as project policy going forward."
---

# Phase 6: Remediation and Governed Release Verification Report

**Phase Goal:** Remediation and governed release — every defect from the Phase 5 verification
runs is fixed or given a written disposition, all fixes ship through full repo governance, and
the milestone's remaining claims (REL-01, REL-02, REL-03) are backed by evidence: the frozen
contract asserted by tests, a real per-file reviewer dispatch with a non-vacuous profile-subset
verdict, and a governance receipt covering the shipping PRs.
**Verified:** 2026-08-22T00:01:11Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every defect logged during Phase 5's verification runs (05-DEFECTS.md, 11 rows) has a merged fix or a written disposition | ✓ VERIFIED | 06-DEFECTS.md's 12-row table (11 original + 1 newly-surfaced) all resolve to `fixed`, `dispositioned`, or `carried`, never `deferred`. Cross-checked rows 2, 4, 5, 6, 7, 8, 9, 10, 11 against the actual code/tests below — every citation resolves. |
| 2 | `models.py`, `evidence.py`, and `fingerprint()` identity are unchanged after fixes, asserted by the test suite | ✓ VERIFIED | `helpers/tests/test_frozen_contract.py` — sha256 pins on both files (`_MODELS_SHA256`, `_EVIDENCE_SHA256`) plus three `fingerprint()` golden-value tests (fully/minimally-populated, field-order-permuted). `git diff 0095550..HEAD -- .../models.py .../evidence.py` is empty (zero commits touched either file). All 6 tests in the file pass (`uv run pytest tests/test_frozen_contract.py -q` → 6 passed). |
| 3 | A real per-file reviewer dispatch ran against the target range, and the receipt shows the count flip proving it | ✓ VERIFIED | 06-RECEIPTS.md "Command 2"/"Command 4": `review_source_skipped: 0` (both profiles) against Phase 5's documented `review_source_skipped: 14` baseline for the identical 14-file set — a genuine count flip, not a re-narrated claim. |
| 4 | The E-12 profile-superset verdict (security-kept ⊆ general-kept) is recorded as non-vacuous, computed over one identical reviewer-output set | ✓ VERIFIED | 06-RECEIPTS.md: security-kept=0, general-kept=5, `∅ ⊆ {5 ids}`. Confirmed architecturally sound at `review_findings.py:100-160` — the general profile is a strict superset by construction (only relaxes gates A/B for `GENERAL_DEFECT_CLASSES` members; never drops anything security keeps) — and empirically at the unit level: `test_review_profiles.py`'s 4 new subset-boundary tests (vacuous/single-element/boundary/permutation, added at `cdfbe49`) all pass. |
| 5 | Each fix lands on a branch with a Conventional Commit, semver bump, and CHANGELOG entry in the same commit (adjacency), version sequence strictly increasing (ordering) | ✓ VERIFIED | Walked all 14 shipping commits (`dbac919` → `cdfbe49`) individually: each stages its own `plugins/sec-overlay/.claude-plugin/plugin.json` bump + `plugins/sec-overlay/CHANGELOG.md` entry; version sequence `1.68.8 → 1.68.9 → 1.68.10 → 1.69.0 → 1.69.1 → ... → 1.69.10` with no skip or reuse. `feat` commit (`3354f44`) bumps minor (`1.68.10→1.69.0`); every other commit type (`test`/`fix`/`docs`) bumps patch. `06-05`'s two commits (`c5ea810`, `188ff37`) touch zero `plugins/` files — the deliberate zero-bump row, confirmed by `git show --stat`. |
| 6 | Every shipping PR is merged only after CodeRabbit's walkthrough comment posts, and targets the milestone branch, never `main` | ⚠️ PARTIAL — see human verification | All 4 PRs confirmed merged into `docs/milestone-v5-diff-review` (never `main`) via `gh pr view`. Walkthrough posted for PR #23 only. PRs #24 (rate-limited, confirmed via `gh pr view 24` — CodeRabbit's own "Review limit reached... 21 minutes" comment), #25, #26, and #27 (this phase's own PR) merged **without** a walkthrough, per a "standing waiver" the receipt attributes to the repository owner. This is a literal deviation from ROADMAP Success Criterion 3's text ("merged only after CodeRabbit's walkthrough comment posts") for 3 of 4 original shipping PRs plus the phase's own closing PR — transparently disclosed in 06-RECEIPTS.md, not hidden, but not something a static check can validate as an intentional policy exception versus habit. Routed to human verification. |
| 7 | `helpers/pyproject.toml` dependencies stay empty across every new module | ✓ VERIFIED | `pyproject.toml` line 8: `dependencies = []`. `test_helpers_declare_zero_runtime_dependencies` reads this live via `tomllib` and asserts `== []`; passes. `git diff 0095550..HEAD -- .../pyproject.toml` is empty. |
| 8 | Documentation shipped by this phase does not contradict the code it documents | ✗ FAILED | See Gaps — three doc files (`SKILL.md`, `skills/sec-overlay/README.md`, `helpers/README.md`) still falsely state `review` has no `--workspace` override, a claim this same phase's own 06-01 plan disproved. Flagged by 06-REVIEW.md (this phase's own code-review artifact) and never fixed or dispositioned. |

**Score:** 6/8 truths verified (1 partial routed to human verification, 1 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `sec_overlay/cli.py` (`run_review`) | Root guard + `--workspace` flag | ✓ VERIFIED | `cli.py:339-341` guard (`is_dir()` check, `error:` stderr, `return 2`) precedes `cli.py:343-358`'s subprocess runner/workspace resolution — order matches the WR-01 fix intent. `workspace` param threaded into `load_paths(workspace=workspace)` at line 353-354. |
| `sec_overlay/phases.py` (`PHASE_TABLE`) | `redteam` + `postflight` entries, correctly ordered | ✓ VERIFIED | Lines 119 (`redteam`, between `selfscore` and `artifact-gate`) and 128 (`postflight`, last entry). |
| `sec_overlay/driver.py` (`DETERMINISTIC_ACTIONS`) | `postflight` key added; `redteam` absent (agent phase) | ✓ VERIFIED | Lines 292-308: `postflight` present, `redteam` correctly absent. |
| `sec_overlay/report.py` (deps Fix-line) | Package name split on last `@` | ✓ VERIFIED | Line 91: `pkg.rsplit('@', 1)[0] or pkg`. |
| `agents/redteam.md` | Two-way mechanical split, not three-way | ✓ VERIFIED | Line 33 describes the real `needs-runtime` OR `NEEDS_DEPLOYMENT_TESTING` predicate, matching `redteam.py:39-41`'s `wants_runtime()`. Pinned by `test_redteam_agent_describes_the_real_two_way_wants_runtime_predicate`. |
| `helpers/tests/test_frozen_contract.py` | 6 tests: byte-identity ×2, fingerprint golden ×3, zero-deps ×1 | ✓ VERIFIED | All present, all pass. |
| `helpers/tests/test_review_profiles.py` | Profile-subset boundary probes | ✓ VERIFIED | 4 new tests (vacuous/single-element/boundary/permutation) present and passing, alongside pre-existing profile tests (23 total in file, all pass). |
| `06-DEFECTS.md` | Terminal disposition for all 11 Phase-5 rows + newly-surfaced row | ✓ VERIFIED | 12 rows, none `deferred`. |
| `06-RECEIPTS.md` | Governance receipt (4 PRs + zero-bump row), REL-03 re-assertion | ✓ VERIFIED, cross-corroborated | Commit SHAs, version transitions, and CodeRabbit outcomes all independently confirmed against `git log`/`gh pr view` (not merely restated from the receipt). |
| `SKILL.md`, `skills/sec-overlay/README.md`, `helpers/README.md` | Docs describe the code accurately | ✗ STUB (stale claim) | See Gaps — three files retain a disproven claim about `--workspace`. |
| `.planning/ROADMAP.md` | Phase 6 marked complete | ✗ STUB (stale) | Header checkbox unchecked, Progress-table status/date not updated to match Phases 1-5's pattern. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `run_review`'s root guard | git subprocess construction | Guard at `cli.py:339` precedes `r = partial(subprocess.run, ...)` at `cli.py:351` | ✓ WIRED | Confirmed by line order and by the 3 dedicated tests (missing/empty/file-as-root) all asserting no exception escapes. |
| `args.workspace` (CLI parse) | `run_review(workspace=...)` | Threaded, not a silent no-op | ✓ WIRED | `cli.py:353-354`: `if workspace: ws = load_paths(workspace=workspace)`. `06-REVIEW.md` independently traced this and found no defect. |
| `PHASE_TABLE`'s `redteam`/`postflight` entries | `run.drive()`/`run.advance()` | Table walk in `driver.py` | ✓ WIRED | `test_phase_table_contains_redteam_and_postflight`, `test_redteam_precedes_the_artifact_gate`, `test_postflight_is_the_final_phase` all pass; `missing_inputs`/`outputs_present` tested for both new entries including the empty case. |
| 14 recorded reviewer returns (security workspace) | general-profile consume pass | Byte-for-byte copy into a fresh workspace, not a re-dispatch | ✓ WIRED | 06-RECEIPTS.md "Command 3"/"Command 4" — sha256sum-verified copy; both consume passes read the same 14 returns, satisfying the "one identical reviewer output set" requirement for the E-12 comparison. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frozen-contract + fingerprint golden tests pass | `uv run pytest tests/test_frozen_contract.py -q` | `6 passed` | ✓ PASS |
| Profile-subset boundary tests pass | `uv run pytest tests/test_review_profiles.py -q` | `23 passed` | ✓ PASS |
| `PHASE_TABLE`/`DETERMINISTIC_ACTIONS`/doc-invariant tests pass | `uv run pytest tests/test_phases.py tests/test_driver.py tests/test_docs_invariants.py tests/test_report.py -q` | `113 passed` | ✓ PASS |
| Full suite matches the receipt's claimed 1283/1 split exactly | `uv run pytest tests/ -q` | `1 failed, 1283 passed` — the one failure is `test_bench.py::test_seed_corpus_is_valid`, the documented pre-existing environmental gap (gitignored bench corpus absent) | ✓ PASS (matches documented baseline, not a regression) |
| Stale `--workspace` doc claim is actually gone from the shipped docs | `grep -n "has no.*workspace override" SKILL.md README.md helpers/README.md` | Claim still present, verbatim, in all three files | ✗ FAIL (see Gaps) |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| REL-01 | 06-01, 06-02, 06-03, 06-04, 06-05 | Every observed defect fixed or dispositioned; frozen contract unchanged, asserted by tests | ✓ SATISFIED | 06-DEFECTS.md's 12-row terminal-disposition table; `test_frozen_contract.py`'s byte-identity + fingerprint-golden tests, all passing; zero commits touch `models.py`/`evidence.py`. (The undisposed WR-01 doc-drift finding in Gaps is a defect surfaced by this phase's *own* review, not one of the Phase-5-ledger rows REL-01's text scopes to — reported separately, not counted against REL-01's literal satisfaction.) |
| REL-02 | 06-01 through 06-05 | Governance: branch, Conventional Commit, semver bump + CHANGELOG in the same commit, CodeRabbit walkthrough before merge | ⚠️ PARTIALLY SATISFIED | Branch/commit/semver/CHANGELOG discipline fully verified (Truth 5, VERIFIED). The CodeRabbit-walkthrough clause held for only 1 of 4 shipping PRs; the other 3 (plus this phase's own closing PR) merged on a disclosed rate-limit waiver — see Truth 6 and Human Verification. |
| REL-03 | 06-04, 06-05 | `helpers/pyproject.toml` dependencies stay empty | ✓ SATISFIED | `dependencies = []` confirmed live; test passes; re-asserted on the merged milestone branch per 06-RECEIPTS.md (re-run independently in this verification: `test_frozen_contract.py` 6/6 pass on the current `docs/milestone-v5-diff-review` HEAD). |

No orphaned requirements: `grep -n "^requirements:" 06-0{1..5}-PLAN.md` shows REL-01/REL-02 on all five plans and REL-03 added at 06-04/06-05 — every ID REQUIREMENTS.md maps to Phase 6 appears in at least one plan's `requirements` field.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | 95 | Documentation directly contradicts shipped behavior (`review` does have `--workspace`, doc says it doesn't) | 🛑 Blocker | Misleads a user or agent driving a review run into believing per-run workspace isolation is impossible for `review`, when it shipped and is tested in this same phase. |
| `plugins/sec-overlay/skills/sec-overlay/README.md` | 34-36 | Same contradiction | 🛑 Blocker | Same as above; violates the plugin's own hard "docs track code" rule. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` | 267 | Same contradiction | 🛑 Blocker | Same as above. |
| `.planning/ROADMAP.md` | 30, 263 | Stale tracking state — Phase 6 shown incomplete/in-progress despite STATE.md and 06-DEFECTS.md both recording it closed | ⚠️ Warning | Not a code defect, but a real inconsistency in the milestone's own source of truth; could mislead a future `roadmap.get-phase` query or a person skimming the roadmap. |

No `TBD`/`FIXME`/`XXX` markers found in any file this phase modified.

### Human Verification Required

#### 1. CodeRabbit-walkthrough waiver policy

**Test:** Confirm each of the 4 non-walkthrough merges (PRs #24, #25, #26, #27) was a deliberate,
informed decision at merge time, consistent with root `CLAUDE.md`'s "wait for CodeRabbit's
walkthrough before merging" rule being explicitly and knowingly waived rather than habitually
skipped.
**Expected:** The repository owner confirms these were intentional case-by-case waivers (or a
standing policy the owner accepts going forward), not an oversight.
**Why human:** The factual record (rate-limit message on PR #24, absence of a walkthrough
comment on #24/#25/#26/#27) is confirmed by `gh pr view`, but intent — whether waiving the rule
was the right call each time, and whether it should be normalized as policy — is a judgment call
for the person who owns that rule, not something this verifier can settle from the git/GitHub
record alone.

### Gaps Summary

Two gaps block a clean pass, both objectively confirmed against the live codebase rather than
inferred from SUMMARY.md narrative:

1. **Stale, self-contradicting documentation (blocker).** This phase's own code-review pass
   (06-REVIEW.md, committed at the current HEAD `01818ed`) found that three files — `SKILL.md`,
   `skills/sec-overlay/README.md`, and `helpers/README.md` — still claim `review` has no
   `--workspace` override, a claim this same phase's 06-01 plan disproved by shipping exactly
   that flag. The review even wrote out the exact fix text. No commit after the review report
   applies it, and no disposition for this finding exists in 06-DEFECTS.md or
   `deferred-items.md`. This is a real, fixable, already-diagnosed gap — not a matter of
   interpretation.

2. **Stale ROADMAP.md tracking state (warning).** Phase 6's header checkbox and Progress-table
   status/date were not brought in line with STATE.md's `status: complete` and 06-DEFECTS.md's
   own closure statement, even though the phase's plans list within the same file was updated to
   `5/5` and all five plan checkboxes were checked. A small, mechanical fix (check the box, set
   status to "Complete" with the closure date, matching Phases 1-5's format).

Everything else checked — the frozen-contract identity guarantee, the real 14-file dispatched
review with its non-vacuous E-12 subset verdict, the per-commit governance discipline (branch,
Conventional Commit, strictly-increasing semver, CHANGELOG adjacency), the zero-runtime-
dependency claim, and all 12 Phase-5-ledger dispositions — is independently verified against the
live code, git history, and GitHub PR record, not merely restated from 06-RECEIPTS.md or
06-DEFECTS.md. The CodeRabbit-walkthrough clause of REL-02 is the one item this verifier cannot
close on its own and routes to human judgment.

---

_Verified: 2026-08-22T00:01:11Z_
_Verifier: Claude (gsd-verifier)_
