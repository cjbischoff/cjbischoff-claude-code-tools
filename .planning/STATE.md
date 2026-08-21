---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Hybrid Diff-Review Architecture
current_phase: 05
current_phase_name: End-to-End Verification (Audit & Review)
status: executing
stopped_at: Completed 05-03-PLAN.md
last_updated: "2026-08-21T04:26:30.000Z"
last_activity: 2026-08-20
last_activity_desc: Phase 5 Plan 3 complete — AUD-02/AUD-03 proven on real audit output
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 24
  completed_plans: 23
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-16)

**Core value:** The marketplace never ships an unverified claim — validated plugins,
governed releases, receipt-backed findings.
**Current focus:** Phase 5 — End-to-End Verification (Audit & Review)

## Current Position

Phase: 05 — End-to-End Verification (Audit & Review)
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-08-20 — Plan 03 complete: AUD-02 and AUD-03 proven on Plan 02's real audit output (0 ladder violations, 0 missing/zero risk scores, report headline matches); position advances to Plan 4 of 4

Progress: [█████████░] 96%

## Performance Metrics

**Velocity:**

- Total plans completed: 21
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3 | - | - |
| 03 | 7 | - | - |
| 04.1 | 1 | - | - |
| 02 | 5 | - | - |
| 04 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 48min | 3 tasks | 3 files |
| Phase 01 P02 | 33min | 2 tasks | 24 files |
| Phase 01 P03 | 14min | 2 tasks | 3 files |
| Phase 02 P01 | 2h35m | 3 tasks | 15 files |
| Phase 02 P02 | 1 session | 3 tasks | 6 files |
| Phase 02 P03 | 1 session | 3 tasks | 10 files |
| Phase 02 P04 | one session | 3 tasks | 10 files |
| Phase 02 P05 | 1 session | 3 tasks | 6 files |
| Phase 03 P01 | 1h31m | 2 tasks | 14 files |
| Phase 03 P02 | 1h10m | 3 tasks | 7 files |
| Phase 03 P03 | 55min | 3 tasks | 15 files |
| Phase 03 P04 | 40min | 3 tasks | 14 files |
| Phase 03 P05 | 150m | 3 tasks | 12 files |
| Phase 03 P06 | ~2 hours across two sessions | 3 tasks | 11 files |
| Phase 03 P07 | 55min | 3 tasks | 8 files |
| Phase 04.1 P01 | 55min | 3 tasks | 12 files |
| Phase 04 P01 | 47min | 3 tasks | 12 files |
| Phase 04 P02 | 55min | 3 tasks | 10 files |
| Phase 04 P03 | 18min | 2 tasks | 8 files |
| Phase 04 P04 | 26min | 3 tasks | 10 files |
| Phase 05 P01 | 87m | 2 tasks | 10 files |
| Phase 05 P02 | 84min | 3 tasks | 5 files |
| Phase 05 P03 | 22min | 3 tasks | 1 file |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- ADR-2026-08-04 (aghast/OpenAnt native adoption) is proposed, not locked
- CVSS v4.0 pinned harness-wide (ruling R2); Mermaid caps hard-enforced
- All 50 ingested docs are delivered baseline — do not re-plan delivered work
- Phase 2 must rename or extend the new coverage-manifest module to avoid colliding
  with the already-shipped `helpers/sec_overlay/coverage.py`

- Phase 3 must state its Python-version floor for `**`-aware globbing explicitly
  (`pathlib.PurePath.full_match` needs 3.13; fall back to a custom matcher otherwise)

- [Phase ?]: Recorded the real observed pytest failure instead of a stale documented one (test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd vs test_citations.py::test_all_mapped_ids_exist_in_seed, which now passes)
- [Phase ?]: VAL-03 prek receipt cannot show conventional-commit-msg under --all-files (stages: [commit-msg] never fires); recorded honestly with a config disposition instead of forcing a match
- [Phase ?]: Maintainer selected proceed-as-triaged: no ty diagnostic touches sec_overlay/models.py or evidence.py (frozen contract, D-02); Plan 02 executes ruff/ty fixes under normal governance
- [Phase ?]: Stayed on docs/milestone-v5-diff-review branch for Plan 02 fixes rather than opening a new fix/* branch
- [Phase ?]: VAL-03 config-dispositioned row got no fix commit per maintainer's proceed-as-triaged Remediation Route, despite generic template language listing config as actionable
- [Phase ?]: Applied deviation Rule 2 in stage_validate.py: adapter wrappers close a real crash-on-malformed-input gap while also satisfying ty
- [Phase ?]: Recorded pytest's final receipt honestly at Exit code 1 (2 environmental failures unchanged from baseline) rather than fabricate a green result to satisfy the plan's literal six-line automated-verify count
- [Phase ?]: Proceeded past two untracked GSD-orchestration files that made Task 1's precondition literally unmet, rather than halting, since they touch none of the six gates and are outside this plan's files_modified scope
- [Phase ?]: Confirmed all 9 Plan 02 fix commits carried plugin.json + CHANGELOG.md together (9 consecutive patch bumps 1.37.3-1.37.11), proving governance compliance across every fix
- [Phase ?]: Coverage manifest shape/path confirmed: artifacts/coverage_manifest.json, {version, base_sha, head_sha, seal, files}
- [Phase ?]: PositionResult kept as phase-owned dataclass, not a models.FindingStatus member — models.py stays frozen
- [Phase ?]: positioning.py uses exact consecutive-string matching only; no difflib, no fuzzy-match-as-exact risk
- [Phase ?]: partition's new keyword params (diff_line_counts, binary_paths, max_diff_lines) default to no-op values so cli.py's call site needs no change
- [Phase ?]: CoverageTransitionError extends RuntimeError (plan spec), not ValueError
- [Phase ?]: seal() raises on empty manifest instead of vacuously returning complete (T-02-05)
- [Phase ?]: review_ledger.json is a separate artifact from findings.json because models.py is the frozen milestone contract and a new FindingStatus member would break the Go port's byte mirror
- [Phase ?]: PositionResult carries the original claimed snippet on every result, including declines, so the report can show the claim without a second file lookup
- [Phase ?]: Partial coverage seal isolated via try/except around parse_hunks; no organic trigger exists today, so tests drive it by monkeypatching parse_hunks (D-15)
- [Phase ?]: Kept Python floor at 3.12 (D-01): rule_glob.glob_match hand-rolls a **-aware segment matcher instead of the 3.13-only pathlib.PurePath.full_match
- [Phase ?]: reflection.apply_verdict is retract-only: a verdict can remove only a finding the code submitted, never add/rank/rewrite; PROTECTED_SUBJECT_CLASSES is a hardcoded veto (D-16)
- [Phase ?]: read_rule_file_safe's repo_root is the per-layer resolution base, not a separately threaded true project root
- [Phase ?]: Rule-file safety gate hard-raises on any violation; no OCR-style warn-and-fallthrough (D-08)
- [Phase ?]: Boundary check runs against the symlink-resolved path, stronger than OCR's pre-resolution check
- [Phase ?]: BUILTIN_PATH_RULE_MAP trailing **/* catch-all makes default.md a reachable, testable map value
- [Phase ?]: default.md rewritten to five-family/exclusion-block structure to satisfy the parametrized conformance test (Rule 2)
- [Phase ?]: REV-01: option-a — new review_findings.py module wraps findings in ReviewFinding, keeping models.py/evidence.py frozen (D-11)
- [Phase ?]: apply_profile returns a 2-tuple (kept, dropped), deliberately diverging from review_position_gate's 3-tuple since profile gating cannot produce a decline
- [Phase ?]: Security-profile baseline captured as a committed JSON fixture, not recomputed inline, so a future regression fails the comparison
- [Phase ?]: Injection assigned to STATIC_CHECKABLE_CLASSES explicitly (ships unconfirmed) since its sink matches Tier-1 static-tool reachability targets
- [Phase ?]: disposition_without_receipt raises ValueError on unknown class instead of defaulting, forcing explicit classification of future general-defect classes
- [Phase ?]: diffscope.file_text_at_ref added (Rule 2): finding.evidence is derived by the harness from real file text at a ref, never trusted from the model's claim
- [Phase ?]: run_review gate-chain order fixed: position gate -> apply_profile -> apply_verdict -> receipt gate, never reordered for test convenience
- [Phase ?]: recorded_return_source treats missing return, stale base/head, and ReviewResponseError identically as one review_source_skipped entry (D-15 fail-open)
- [Phase ?]: Task 2 disposition-ladder tests use a fixture local to each test, never a mutation of _dual_run_fixture (its thread-safety entry is gate-C, an unconditional drop)
- [Phase ?]: Task 3's composed test relies on the real reflection.apply_verdict called with an empty verdict dict, which keeps everything by construction, instead of a mock
- [Phase ?]: DIFF-04 closed: run_review resolves workspace via RepoMemory.for_target, matching scan/audit
- [Phase ?]: Task 3 found sarif.py/review_comments.py already correct from tracer plan; closed test coverage gap only, no implementation change
- [Phase ?]: Rewrote Finding(**overrides) test helpers as explicit-parameter functions after ty check flagged the dict-splat as untypeable against the dataclass constructor
- [Phase ?]: Chose the locale-sibling grouping rule (uncapped member count) over the impl/test pairing rule (capped at 2) to build a genuine three-file ReviewUnit for the timeout acceptance test
- [Phase ?]: Reused TimeoutError(TIMEOUT_NOTE) through the existing str(exception)-as-note manifest.fail() path so the timeout branch needs no special-casing versus an ordinary per-file fetch failure
- [Phase ?]: SCALE-03 Task 1: identity lives on CoverageManifest itself (option-a), not a sibling artifact
- [Phase ?]: SCALE-03 Task 3: resumed reads sourced from prior manifest, round-tripped through resolve_ref_sha; no changes needed in diffscope.py
- [Phase ?]: Split test_review_live.py's profile-comparison test into two independent targets (Rule 1 fix for Task 2's identity gate regression)
- [Phase ?]: Zero-reviewable early-return path keeps writing comments from an unsealed manifest.to_dict() rather than sealing an empty manifest, since CoverageManifest.seal() raises by design on an empty manifest (T-02-05).
- [Phase ?]: Production runner default becomes partial(subprocess.run, timeout=timeout) at the single r = runner or ... assignment, so every git call in run_review inherits the kill deadline through the shared r variable with no other call-site change.
- [Phase ?]: Per-call subprocess timeout equals the declared --timeout (not a fraction of it) so the future-level timeout always fires first and TIMEOUT_NOTE bookkeeping stays deterministic.
- [Phase ?]: 05-01: Zero live findings from the CLI-only review run is by-design (D-13/D-15), not a gap — AUD-06 grounds in CoverageManifest.seal()/apply_profile(), not genuine LLM findings
- [Phase ?]: 05-01: Used SEC_OVERLAY_HOME override for Task 2's general-profile run since review has no --workspace flag and the SCALE-03 resume-identity guard rejects a second profile against the default sidecar
- [Phase ?]: 05-01: security-kept subseteq general-kept subset check passed vacuously (empty set); flagged as E-12 in 05-DEFECTS.md for Phase 6 to re-verify against non-empty findings
- [Phase ?]: Triaged redteam/postflight PHASE_TABLE gap as run-blocker; closed via documented standalone module calls, deferred wiring fix to Phase 6
- [Phase ?]: Corrected CRYPTO-0001 runtime_disposition after discovering wants_runtime() also keys on status
- [Phase ?]: 05-03: validate_findings() redirected to a scratch copy via Workspace(findings_dir_override=...) rather than called directly against the live D-09-retained sidecar, since it has an undocumented write side effect on receipt_tier mismatch; non-mutation proven via before/after MD5 checksums
- [Phase ?]: 05-03: No evidence_sources string for the needs-deployment-testing findings is quoted in the committed receipt, since those strings embed real target-repo file paths — the plan's framing that evidence-source names are always safe tool identifiers does not hold universally for this pipeline's real data
- [Phase ?]: 05-03: report.py's intentional "Needs runtime proof"/"needs-runtime" labeling (never the literal enum string) confirmed as by-design after re-verifying the visibility check against the actual rendered labels

### Pending Todos

None yet.

### Blockers/Concerns

- Ingest WARNING: the 2026-08-11 kb-redesign design references a 2026-08-09 spec
  absent from the ingest set. Locate the spec or affirm the design doc as authority.
  See .planning/INGEST-CONFLICTS.md.

- Phase 5 needs a real target repo for both the audit and review verification runs.
  Pick one before planning Phase 5.

### Roadmap Evolution

- Phase 04.1 inserted after Phase 4: Close gap: DIFF-04 — review sidecar workspace isolation (URGENT)

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Growth | GROW-01 second plugin onboarding | v2 | 2026-08-16 |
| Growth | GROW-02 automated plugin-validate gate | v2 | 2026-08-16 |

## Session Continuity

Last session: 2026-08-21T04:26:30.000Z
Stopped at: Completed 05-03-PLAN.md
Resume file: None
