# Phase 5: End-to-End Verification (Audit & Review) - Context

**Gathered:** 2026-08-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase proves both shipped pipelines on a real target. A full `/sec-overlay:audit` run and a full `review` run (both profiles) complete end to end. Every claim is receipt-backed. Every gap is logged, never hidden. The phase delivers run evidence for AUD-01 through AUD-06. It does not deliver remediation — Phase 6 owns fixes beyond run-blockers.

</domain>

<decisions>
## Implementation Decisions

### Audit target
- **D-01:** The audit target is the local work repo `/Users/christopher/Documents/Development/_hy/mando` (React Router + Cloudflare Functions TypeScript app). — **Reversibility:** reversible — a different target only changes run inputs, not tool code.
- **D-02:** Pin the audit to mando's `main` HEAD at run start. Record the SHA in the receipts (`80e2abc` at discussion time; re-resolve at run time). Do not audit the live working tree.
- **D-03:** Audit the full repo with the tool's default excludes (node_modules, build outputs, lockfiles). Use the full AUD-05 coverage denominator. Do not narrow scope to app/ and functions/.

### Review diff
- **D-04:** The review run uses a real historical diff from mando — the same target as the audit. No seeded or synthetic diff this phase.
- **D-05:** The planner selects the concrete diff by criteria, not by name. Criteria: a merged PR or commit range that touches roughly 5–30 allowlisted files (TS/TSX), mixes app/ and functions/ code, and stays within the default per-file size caps. The executor resolves the exact `base..head` SHA range at run time and records it.
- **D-06:** Run both profiles (`security`, then `general`) on the identical SHA range. This evidences the Phase 3 D-10 profile-superset contract on real code.

### Evidence capture
- **D-07:** Full run artifacts (reports, findings, coverage manifests, ledgers) stay in mando's `.sec-overlay` sidecar. This marketplace repo commits sanitized receipts only: commands, exit codes, seal states, headline counts, gate verdicts, and SHAs. No mando file paths, code snippets, or finding bodies enter this repo. — **Reversibility:** one-way for history — committed mando internals cannot be removed from git history later.
- **D-08:** The phase verifier reads the sidecar live at mando to check the six success criteria. Committed receipts cite what to check and where. No artifact copies.
- **D-09:** Retain the sidecar artifacts untouched until the v5.0 milestone ships (through Phase 6 and the milestone audit). Record the sidecar path in the receipts.

### Defect disposition
- **D-10:** Phase 5 fixes run-blockers only: defects that stop a run from completing or sealing (crashes, hangs, gate false-halts). Fixes follow full governance (branch, Conventional Commit, version bump, tests). All other defects (finding quality, noisy output, scoring oddities) go to the defect ledger for Phase 6.
- **D-11:** The defect ledger is `05-DEFECTS.md` in this phase directory. Each entry records: defect, severity, repro command, disposition (`fixed-here` or `deferred`). The D-07 sanitization rule applies to ledger entries.
- **D-12:** A success-criterion failure on real output (for example, a Tier-2-only finding reaches `confirmed`) is a ledger entry, not a run-blocker. The phase verification reports `gaps_found` honestly. Closure comes through a gap plan or Phase 6. Do not re-run until green to hide the defect.

### Claude's Discretion
- Concrete diff selection within the D-05 criteria.
- Receipt document structure, provided it follows the Phase 1 evidence format (exact command, exit code, decisive tail lines, version block — 01-CONTEXT D-05..D-07).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and success criteria
- `.planning/REQUIREMENTS.md` — AUD-01 through AUD-06 definitions (lines ~114–131)
- `.planning/ROADMAP.md` — Phase 5 goal and the six success criteria

### Pipeline drivers under test
- `plugins/sec-overlay/skills/sec-overlay/SKILL.md` — the audit driver and the review dispatch loop
- `plugins/sec-overlay/commands/audit.md` — the `/sec-overlay:audit` entry point
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` — the `review` verb, `--profile`, `--model`, `--concurrency`, `--timeout`, `--max-git-procs` flags
- `plugins/sec-overlay/CLAUDE.md` — plugin operating manual and governance

### Prior-phase contracts the runs must honor
- `.planning/phases/02-diff-pipeline-positioning/02-CONTEXT.md` — coverage manifest seal semantics, exclusion enum, decline visibility
- `.planning/phases/03-rule-matching-review-modes/03-CONTEXT.md` — profile mechanics, disposition ladder (D-12), reflection filter
- `.planning/phases/04-scale-resume-diff-output/04-VERIFICATION.md` — bounded-run and resume behavior proven in Phase 4
- `.planning/phases/01-baseline-health-verification/01-CONTEXT.md` — evidence format (D-05..D-08) reused for Phase 5 receipts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RepoMemory.for_target` in `cli.py`: `run_review`, `scan`, and `audit` all route their workspace through the target's `.sec-overlay/<slug>/` sidecar (DIFF-04, Phase 04.1). Cross-repo runs against mando need no new isolation work.
- `review_coverage.py` `CoverageManifest`: seal states, identity pinning, and SHA-pinned resume are the run's self-evidence — receipts can quote its JSON.
- Phase 1 verification doc format: command + exit code + decisive tail + version block.

### Established Patterns
- Working-tree fence: audit writes nothing to the target's tracked tree; AUD-01 asserts the fence holds on mando.
- Governance: any run-blocker fix bumps the plugin version and updates the plugin CHANGELOG in the same commit.

### Integration Points
- The audit run drives `SKILL.md` phases against `/Users/christopher/Documents/Development/_hy/mando` at pinned `main` HEAD.
- The review run drives `cli.py review` twice (both profiles) against one resolved `base..head` range in mando.

</code_context>

<specifics>
## Specific Ideas

- Mando is a work repository. Treat its contents as sensitive: nothing beyond sanitized receipt data (commands, counts, states, SHAs) may be committed to this marketplace repo.

</specifics>

<deferred>
## Deferred Ideas

- Handing audit findings to the mando team (triage, issue filing) — outside this milestone; the runs here verify the tool, not mando.
- Seeded-defect detection benchmark diff — considered for AUD-06, not selected; could become a fixture-based regression suite in a later milestone.

</deferred>

---

*Phase: 5-End-to-End Verification (Audit & Review)*
*Context gathered: 2026-08-20*
