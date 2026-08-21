# Phase 6: Remediation and Governed Release - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase closes the v5.0 milestone. It dispositions every deferred row in `05-DEFECTS.md` (10 rows), runs one full agent-dispatched review on the real target to close E-12 and the tracer non-dispatch row, and ships every fix through the repo's own governance. The frozen contract (`models.py`, `evidence.py`, `fingerprint()` identity) stays unchanged, asserted by tests. `helpers/pyproject.toml` dependencies stay empty. The phase does not add new review features beyond the agreed fixes.

</domain>

<decisions>
## Implementation Decisions

### Fix vs disposition line (the 10 deferred rows)
- **D-01:** Wire `redteam` and `postflight` into `phases.py` as real `PHASE_TABLE`/`DETERMINISTIC_ACTIONS` entries so `run.drive()`/`run.advance()` invoke them. Update the docs to match the new wiring. This closes the confusing late `artifact-gate` halt at its root. — **Reversibility:** costly — the audit pipeline's phase order is consumed by `run.drive()`, gate checks, and the maintainer manual; unwiring later touches all three.
- **D-02:** Reconcile the `wants_runtime()` gap doc-side: rewrite `agents/redteam.md` to describe the actual 2-way mechanical split. The status-forces-inclusion behavior stays — it is the safe default for a security tool. No code change to `redteam.py`.
- **D-03:** Add a `--workspace` flag to the `review` CLI verb, mirroring `audit`'s flag. This makes the documented multi-profile workflow first-class and removes the `SEC_OVERLAY_HOME` workaround. Conventional Commit type is `feat` (minor bump).
- **D-04:** Fix all remaining fixable rows: WR-01 (clean exit-2 message when `--root` names a nonexistent directory, replacing the raw `FileNotFoundError` traceback), the deps-finding-detail template's empty-backtick package-name interpolation, the false submodule claim in `plugins/sec-overlay/CLAUDE.md`, and the wrong cwd-bug explanation in `helpers/tests/README.md`.
- **D-05:** Written dispositions (no code change) for the two remaining rows: the D-05 mixing-criterion unsatisfiability (target-repo history makes it impossible; criterion retired) and the Phase 5 tracer non-dispatch row (superseded by this phase's real dispatched run, D-07).

### E-12 re-verification (profile-superset contract)
- **D-06:** Produce a non-empty finding set via a real SKILL.md-driven per-file reviewer dispatch against mando, both profiles, and check security-kept ⊆ general-kept on the results.
- **D-07:** Reuse Phase 5's exact `base..head` SHA range on mando for direct comparability with the tracer run. The executor re-reads the range from the Phase 5 receipts.
- **D-08:** Add a deterministic pytest backstop regardless of live-run outcome: synthetic findings through `review_findings.apply_profile()` asserting the subset relation. The live run is the primary evidence; the test is the permanent regression guard. If the live run returns zero findings, E-12 still closes on the test plus an honest receipt note.
- **D-09:** Evidence rules carry forward unchanged from Phase 5 (05-CONTEXT D-07/D-08): sanitized receipts only in this repo (commands, exit codes, seal states, headline counts, subset verdict, SHAs); full artifacts stay in mando's sidecar; the verifier reads the sidecar live. — **Reversibility:** one-way for history — committed mando internals cannot be removed from git history later.

### Agent-dispatched review scope
- **D-10:** The deliverable is one evidenced run: both profiles on the D-07 SHA range, with receipts proving dispatch happened (review-source counts showing per-file reviewer returns instead of `review_source_skipped`, findings ledger, sealed manifest). No new review features beyond the fixes in D-01..D-04.
- **D-11:** New defects surfaced by this phase's run follow the Phase 5 ladder (05-CONTEXT D-10/D-11): run-blockers fixed in-phase under full governance; everything else gets a ledgered row in `06-DEFECTS.md` with a written disposition. Sanitization per D-09 applies to ledger entries.
- **D-12:** Sequencing: land the `--workspace` fix (D-03) before the dispatched run, then run both profiles into a fresh Phase 6 workspace via `--workspace`. The retained Phase 5 sidecar stays untouched (05-CONTEXT D-09), and the new flag gets real-run proof in the same phase.

### Release and merge shape
- **D-13:** Ship fixes as a few thematic PRs, not one-per-fix and not one big release PR. Suggested grouping: CLI fixes (`--workspace` + WR-01), pipeline wiring (PHASE_TABLE + deps template), doc corrections, run receipts + E-12 evidence. Each PR waits for CodeRabbit's walkthrough comment before merge, per repo governance.
- **D-14:** Phase 6 fix branches fork from `docs/milestone-v5-diff-review` and merge back into it. The milestone branch merges to `main` once at milestone close, with one final CodeRabbit pass on the milestone PR. Matches the Phase 1–5 pattern.
- **D-15:** Add a dedicated frozen-contract identity-guard test: one test asserting the identity of `models.py` and `evidence.py` (checksum or AST identity) and a `fingerprint()` golden value, run in the suite. This gives the verifier a single named, citable assertion for success criterion 2.
- **D-16:** Semver per commit by Conventional Commit type, exactly as the hooks enforce: `feat` (the `--workspace` flag) bumps minor; fixes and doc corrections bump patch; every shipping-file commit carries its `plugin.json` bump and CHANGELOG entry in the same commit.

### Claude's Discretion
- Exact PR grouping within D-13's thematic shape.
- Reviewer run configuration (`--model`, `--concurrency`, `--timeout`) for the dispatched run — draw on Phase 4's proven bounded-run settings and CLI defaults; record whatever is used in the receipts.
- Identity-guard test mechanism (checksum vs AST comparison vs golden fingerprint fixture) — planner picks after checking what the suite already asserts.
- Receipt document structure, provided it follows the Phase 1 evidence format (exact command, exit code, decisive tail lines, version block — 01-CONTEXT D-05..D-07).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and success criteria
- `.planning/REQUIREMENTS.md` — REL-01, REL-02, REL-03 definitions (lines ~134–143)
- `.planning/ROADMAP.md` — Phase 6 goal and the four success criteria

### The defect ledger this phase dispositions
- `.planning/phases/05-end-to-end-verification-audit-review/05-DEFECTS.md` — all 10 deferred rows, each with severity, repro command, and rationale
- `.planning/phases/05-end-to-end-verification-audit-review/05-REVIEW.md` — WR-01/WR-02 origin findings
- `.planning/phases/05-end-to-end-verification-audit-review/05-VERIFICATION.md` — E-12 flagged assumption and run evidence locations

### Prior-phase contracts fixes must honor
- `.planning/phases/05-end-to-end-verification-audit-review/05-CONTEXT.md` — D-07/D-08 sanitization and sidecar-evidence rules, D-09 sidecar retention, D-10/D-11 defect ladder (all carried forward)
- `.planning/phases/03-rule-matching-review-modes/03-CONTEXT.md` — profile mechanics and the D-10 profile-superset contract E-12 re-verifies
- `.planning/phases/02-diff-pipeline-positioning/02-CONTEXT.md` — coverage manifest seal semantics
- `.planning/phases/04-scale-resume-diff-output/04-VERIFICATION.md` — SCALE-03 resume-identity guard behavior the `--workspace` flag must respect

### Code under change
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — `review` verb (gains `--workspace`), WR-01 error handling
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py` — `PHASE_TABLE`/`DETERMINISTIC_ACTIONS` (gains `redteam`, `postflight`)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py` — `wants_runtime()` (unchanged; prose aligns to it)
- `plugins/sec-overlay/skills/sec-overlay/agents/redteam.md` — prose rewrite to 2-way split
- `plugins/sec-overlay/CLAUDE.md` — false submodule claim
- `helpers/tests/README.md` (under the plugin helpers) — wrong cwd-bug explanation
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` — the review dispatch loop the D-10 run exercises
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_findings.py` — `apply_profile()` for the D-08 subset test

### Governance
- `CLAUDE.md` (repo root) — branch/commit/CHANGELOG/version-bump rules and the CodeRabbit walkthrough-wait rule

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `audit`'s existing `--workspace` flag: the pattern to mirror for `review` (flag parsing, workspace resolution through `RepoMemory.for_target`).
- Phase 5's sanitized-receipt format and the retained mando sidecar: the evidence pattern and the comparison baseline for the dispatched run.
- Phase 4 bounded-run settings (`--concurrency`, `--timeout`, `--max-git-procs`): proven configuration for the live run.

### Established Patterns
- Frozen contract discipline: new behavior wraps around `models.py`/`evidence.py` (e.g., `review_findings.py` wrapper, separate `review_ledger.json` artifact) — never a new `FindingStatus` member.
- Per-commit governance: every shipping-file commit carries plugin.json bump + CHANGELOG entry; Phase 5's 9-commit fix wave proved the cadence.
- Defect ledger format (D-11 four-column table with rationale sentences, sanitized repro commands) — reuse for `06-DEFECTS.md`.

### Integration Points
- `run.drive()`/`run.advance()` and the gate chain consume `PHASE_TABLE` — the redteam/postflight wiring must not break the existing 22-phase order or the artifact-gate's red-team-plan requirement.
- SCALE-03 resume-identity guard in the review workspace sidecar — `--workspace` must route around it the same way `audit`'s flag does, not weaken it.

</code_context>

<specifics>
## Specific Ideas

- The dispatched run must show per-file reviewer returns in the review-source ledger (not `review_source_skipped: 14`) — that count flip is the receipt-level proof the tracer gap closed.
- The E-12 receipt states the subset verdict explicitly, including the vacuous case if the live run yields zero findings, with the pytest backstop cited as the substantive guard.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 6-Remediation and Governed Release*
*Context gathered: 2026-08-21*
