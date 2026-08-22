# Phase 6 Defect Ledger

Terminal disposition for every row `05-DEFECTS.md` carried into this phase, per REL-01's first
clause: no row stays in the deferred state it arrived in. Three terminal states are used:

- **fixed** — a Phase 6 plan closed it; cited by plan number and commit.
- **dispositioned** — cannot be fixed as written; the written reason is recorded instead (D-05/D-11).
- **carried** — newly surfaced during this plan's own run, not fixed here, with the reason
  (the four shipping PRs are merged; an untriaged fifth would restart the governance rail).

`05-DEFECTS.md` has **11 data rows**, not the ten the plan's `must_haves.truths` text assumes —
reported as counted, not forced to match the estimate (the same discipline `06-03-SUMMARY.md`
applied to its 6-file/8-mention count). All 11 receive a terminal state below, plus two
newly-surfaced rows: one from this plan's own governance-data verification, and one from
`06-VERIFICATION.md`'s post-closure gap check (06-06). 13 rows total.

| # | Defect (05-DEFECTS.md row) | Severity | Terminal Disposition |
|---|---|---|---|
| 1 | D-05 mixing-criterion unsatisfiable — no diff range in the target repo mixes `app/` and `functions/` while staying within the 5-30 file bound. | non-blocker | **dispositioned.** `functions/` has 5 commits in its entire history (confirmed again this plan, unchanged from Phase 5's count); no candidate range can ever satisfy both the file-count and mixing sub-criteria at once. The mixing sub-criterion is unsatisfiable against this target's real history, not unmet — it should be revised in a future phase's criteria, not retried against this target. |
| 2 | Real-run reviewer dispatch not exercised — the CLI-only `review` invocation never spawns the per-file `review-file` subagent; both profiles sealed with 0 live findings, all files landed in `review_source_skipped`. | non-blocker | **fixed.** Plan 06-05, Task 2, commit `c5ea810`. A real 14-file per-file dispatch ran against the identical Phase 5 `base..head` range; the receipt (`06-RECEIPTS.md`, "Command 2") records `review_source_skipped: 0` against Phase 5's `review_source_skipped: 14` baseline — the count flip this row asked for. |
| 3 | `run_review`'s git-subprocess runner had no `cwd`/`-C` binding to `--root`, silently producing an empty changed-file set from any invocation directory other than `--root`. | blocker | **already terminal at arrival.** Disposition in `05-DEFECTS.md` was already `fixed-here` — this bug was found and fixed inside Phase 5 itself, before the ledger entry was written. No Phase 6 action needed; listed here only for row-completeness against REL-01's "every row" clause. |
| 4 | `review`'s resume-identity guard rejects a second profile run against the same sidecar, and `review` exposed no `--workspace` override (only `audit` did). | non-blocker | **fixed.** Plan 06-01, Task 2, commit `3354f44` (`feat(06-01): add review --workspace override (D-03)`). `review --workspace` now resolves through `load_paths(workspace=...)` exactly like `audit`'s flag; this plan's own Task 2 run used that flag to isolate two profile runs into fresh workspaces without touching the Phase 5 sidecar (`06-RECEIPTS.md`, "Phase 5 sidecar isolation"). |
| 5 | E-12 flagged assumption — the profile-superset contract (security-kept ⊆ general-kept) was only exercised against the vacuous ∅ ⊆ ∅ case. | non-blocker | **fixed.** Plan 06-05, Task 2, commit `c5ea810` closes it at the live-run level: security-kept=0, general-kept=5, `∅ ⊆ {5 ids}` — non-vacuous (`06-RECEIPTS.md`, "E-12 subset verdict"). Plan 06-04, commit `cdfbe49`, additionally closed the same contract at the unit level with four `apply_profile()` edge probes (vacuous/single-element/boundary/permutation) as the permanent regression backstop (D-08). Both evidence layers now exist; neither depends on the other. |
| 6 | `plugins/sec-overlay/CLAUDE.md` documents the vendored semgrep ruleset as a git submodule; no `.gitmodules` exists. | non-blocker | **fixed.** Plan 06-03, Task 3, commit `3e1b7e8` (`docs(06-03): correct submodule claim and cwd-bug explanation`). Corrected across every live doc surface carrying the claim — 6 files, 8 mentions (`06-03-SUMMARY.md`, "Doc surfaces corrected") — not only the one file this row named. A code-derived doc guard (`test_no_live_doc_claims_a_git_submodule_that_does_not_exist`) prevents reintroduction. |
| 7 | `skills/sec-overlay/CLAUDE.md`'s documented "Phase order" list omits `redteam`/`postflight`; neither is wired into `PHASE_TABLE`, so `run.drive()` silently skips both. | non-blocker | **fixed.** Plan 06-02, Task 1-2, commits `4b73d5e`/`61c5645`; doc reconciliation Task 3, commit `73ef5b6`. `redteam` and `postflight` are now real `PHASE_TABLE`/`DETERMINISTIC_ACTIONS` entries (`redteam` between `selfscore` and `artifact-gate`; `postflight` the final row), and three maintainer-doc phase-order lists were corrected to the live 24-entry table. `test_every_deterministic_phase_has_a_registered_action` derives its expected set from `PHASE_TABLE` itself, preventing the two from drifting apart again. |
| 8 | `agents/redteam.md`'s prose describes a 3-way discriminator; `redteam.py`'s `wants_runtime()` implements only a 2-way mechanical split. | non-blocker | **fixed.** Plan 06-03, Task 2, commit `fa012be` (`docs(06-03): rewrite redteam.md to the two-way mechanical split (D-02)`). The prompt now describes the real two-condition OR predicate; a code-derived doc guard reads the real trigger values out of `redteam.py`/`evidence.py` at test time and asserts both appear in the prompt text, so a future rename fails the test instead of silently re-opening the gap. |
| 9 | A shipping deps-class finding's rendered Fix line has a cosmetic template bug: the package-name interpolation renders an empty pair of backticks. | non-blocker | **fixed.** Plan 06-03, Task 1 (RED `2b9b787`, GREEN `34e25f3`, `fix(06-03): split deps Fix-line package name on last @`). One-line fix (`rsplit('@', 1)[0] or pkg`), pinned by 5 new tests covering scoped, unscoped, versionless, absent, and multi-separator identifiers. |
| 10 | 05-REVIEW.md WR-01: `run_review` raises an unhandled `FileNotFoundError` for a nonexistent `--root` instead of a clean exit-2 message. | non-blocker | **fixed.** Plan 06-01, Task 1 (RED `dbac919`, GREEN `dfa112c`, `fix(06-01): reject a bad --root with exit 2 (WR-01)`). A single `if not root or not Path(root).is_dir():` guard now runs before any workspace or git subprocess call, exiting 2 with a one-line message for a missing, empty, or non-directory `--root`. |
| 11 | 05-REVIEW.md WR-02: `helpers/tests/README.md` claims other tests missed the cwd-scoping bug because they "bypass `main()`"; the actual cause is a mocked git runner. | non-blocker | **fixed.** Plan 06-03, Task 3, commit `3e1b7e8` (same commit as row 6). The README now correctly attributes the miss to `monkeypatch.setattr(subprocess, "run", ...)` patching the stdlib function underneath `run_review`'s `partial(subprocess.run, cwd=root)` default, whose fake ignores `cwd`. |
| 12 | *(newly surfaced this plan)* `06-02-SUMMARY.md` states PR #24 "merged ... (fast-forward, no merge commit)". `git cat-file -p c546511` (PR #24's actual merge commit) shows two `parent:` lines (`562b313`, `73ef5b6`) — a genuine two-parent merge commit, not a fast-forward. | non-blocker | **carried, not fixed here.** Discovered while gathering this plan's governance-receipt data (`git cat-file -p c546511`, re-run and reconfirmed for this ledger). This is a documentation-accuracy defect in a Phase 6 plan's own SUMMARY.md, with no functional or code impact — PR #24 is correctly merged into `docs/milestone-v5-diff-review` either way. Not fixed here per the plan's own instruction: the four shipping PRs are merged, and an untriaged fifth commit editing a past plan's SUMMARY.md would restart the governance rail for a defect that has not been triaged. Left for whoever next touches `06-02-SUMMARY.md` or a future doc-accuracy pass. |
| 13 | `06-REVIEW.md` WR-01 *(unrelated to row 10's WR-01, a different 05-REVIEW.md finding)*: three doc surfaces (`SKILL.md:95`, `skills/sec-overlay/README.md:34-36`, `helpers/README.md:267`) still stated `review` has no `--workspace` override, directly contradicted by the flag Plan 06-01 shipped (commit `3354f44`). | non-blocker | **fixed.** Plan 06-06, Task 1, commit `83da4e0` (`docs(06-06): correct review --workspace doc claims`). All three passages corrected to state the override exists and to name the identical-value + SCALE-03 (`--model`) requirements. A code-derived TDD guard, `test_no_live_doc_denies_the_review_workspace_override`, was written RED against the unmodified docs (all three offending paths reported), then GREEN after the fix; its premise is pinned against `run_review`'s real signature so a future flag removal fails the guard's premise loudly instead of leaving a now-true claim unchecked. |

## Governance receipt and REL-03 re-assertion

Full 5-row shipping/governance table (branch, commit types, version transitions, CodeRabbit
outcome per PR, plus this plan's own zero-bump row) and the REL-03 re-assertion command/result
on the merged milestone branch: `06-RECEIPTS.md`, "Governance receipt" and "REL-03 re-assertion
on the merged milestone branch". Not repeated here to keep the governance data in one place.

## Phase closure — the four success criteria, addressed individually

**1. A real per-file reviewer dispatch ran against the target range into an isolated Phase 6
workspace, and the receipt shows the count flip that proves it.**
Met. `06-RECEIPTS.md`, "Command 2" (`review_source_skipped: 0` vs. Phase 5's `14`) and the
"Dispatch mechanism" section (14 fresh-context `review-file` subagents, real returns, not a
mocked substitute). Row 2 above closes the underlying ledger entry.

**2. The Phase 5 sidecar is byte-unchanged, proving the resume guard was satisfied by override
and not weakened; the E-12 verdict is recorded with its vacuity stated, computed over one
identical reviewer output set consumed twice, and the receipt names which evidence closes the
item under D-08.**
Met, not partial. `06-RECEIPTS.md`, "Phase 5 sidecar isolation" (digest match before/after,
stated as fact). "E-12 subset verdict": security-kept=0, general-kept=5, **not vacuous** — the
live run itself is the primary evidence (D-08's deterministic backstop from Plan 06-04 was not
needed as the primary evidence here, though it exists as an independent unit-level guarantee —
row 5 above). This is a stronger outcome than the plan's flagged assumption required either
outcome to close E-12; it is recorded as non-vacuous because that is what the run produced, not
rounded up from a vacuous result.

**3. The governance receipt covers four shipping PRs plus this plan's deliberate zero-bump row,
and REL-03 is re-asserted on the merged milestone branch.**
Met. Governance receipt table above (5 rows). REL-03 re-assertion section above (6/6 tests pass
on this plan's branch, forked from the milestone branch's tip after all four merges).

**4. All Phase 5 defect rows carry a terminal state, every committed line respects the
sanitization boundary confirmed in Task 1, and Phase 6 is closed in STATE.md.**
Met. All 11 original rows plus the 2 newly-surfaced rows above carry `fixed`, `dispositioned`, or
`carried` — none reads as `deferred`. `06-RECEIPTS.md` was re-read line by line against the
prohibitions before staging (Task 2's action); this file contains no path below the target
repository root, no code excerpt, and no finding body — only commit SHAs, branch names, commit
types, version numbers, and CodeRabbit outcomes, all of which are this repository's own history,
not the target's. `.planning/STATE.md` is updated to close Phase 6 in the same commit as this
file.

No criterion above is labelled partial — all four are met in full, including the E-12 criterion,
which per D-08 would have been equally valid to close on the vacuous-plus-backstop path had the
live run produced an empty comparison. It did not; the non-vacuous result is reported as such.

## 06-06 gap closure (post-closure verification)

`06-VERIFICATION.md`, run after Phase 6's original closure, found two gaps: row 13 above (the
`--workspace` doc-claim blocker) and a tracking-only gap where `.planning/ROADMAP.md` had not yet
been updated to show Phase 6 complete. Row 13 is fixed per its own entry. The ROADMAP.md tracking
gap is closed in this same plan's Task 2 (three tracking locations corrected: the header checkbox,
the Plans rollup, and the Progress table) — no code or defect-ledger row was needed for that gap,
since ROADMAP.md is a tracking artifact, not a shipped surface.
