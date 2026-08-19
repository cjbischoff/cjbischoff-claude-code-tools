# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format:

- One `## <version> - <YYYY-MM-DD>` section per release, newest first.
- Entries are grouped under `### Changed`, `### Added`, `### Removed`, `### Fixed` — in that order.
- Each entry is one sentence in the imperative mood, describing the change from the user's point of view.
- A repo-level or mixed-scope commit adds an entry here in the same commit.
- A commit whose changes are all inside `plugins/<name>/` adds the entry to that plugin's `CHANGELOG.md` instead.
- A commit that stages only a plugin's own `CHANGELOG.md` needs no entry here.

## Unreleased

### Changed

- Verify and close Phase 04.1 (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-VERIFICATION.md`, status passed: 6/6 must-haves, DIFF-04 traced); `.planning/ROADMAP.md` and `.planning/STATE.md` mark Phase 04.1 complete (2026-08-19) and point at Phase 5 (End-to-End Verification) next.
- Record the Phase 04.1 code-review report (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-REVIEW.md`, status clean: 0 critical, 0 warning, 0 info across 14 files at standard depth).
- Complete Phase 04.1 Plan 01 (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-01-SUMMARY.md`, DIFF-04 closed): `run_review` now resolves its workspace through `RepoMemory.for_target` instead of `Workspace(args.root)`, matching `scan`/`audit`; every review test that read an artifact path now resolves it through the same sidecar. Mark Phase 04.1 complete (1/1 plan) in `.planning/STATE.md` and `.planning/ROADMAP.md`.
- Record the Phase 04.1 pattern map (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-PATTERNS.md`, 6/6 analogs found — the fix mirrors the `scan`/`audit` `RepoMemory.for_target` branches in `cli.py`) and mark Phase 04.1 "Ready to execute" (1 plan, plan checker passed 10/10 dimensions) in `.planning/STATE.md`.
- Add the Phase 04.1 execution plan (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-01-PLAN.md`, wave 1, requirement DIFF-04, 3 tasks) and fill the Phase 04.1 goal, requirement, and plan checklist in `.planning/ROADMAP.md`. The plan re-roots `run_review`'s workspace onto the `<target>/.sec-overlay/<slug>/` sidecar, pins the convention with a regression test, and re-roots the roughly 28 assertions across four test files that currently treat the tracked-tree location as correct — including `tests/test_review_tracer.py`, which the phase research had wrongly recorded as unaffected.
- Add the Phase 04.1 phase research and draft validation strategy (`.planning/phases/04.1-close-gap-diff-04-review-sidecar-workspace-isolation/04.1-RESEARCH.md`, confidence HIGH — the DIFF-04 fix routes `run_review`'s workspace through `RepoMemory.for_target` as `scan`/`audit` already do; `04.1-VALIDATION.md`, status draft).
- Refresh the milestone audit a second time (`.planning/v5.0-MILESTONE-AUDIT.md`, audited 2026-08-19 at 3/6 phases, status still gaps_found: the `review` workspace-isolation sidecar blocker at `cli.py:173` remains open; Nyquist validation now compliant for all three executed phases, pytest count updated to 1175 passed).
- Validate the Phase 1 Nyquist strategy retroactively (`.planning/phases/01-baseline-health-verification/01-VALIDATION.md`, status validated, nyquist_compliant true, 1 gap found and resolved: tests added for the `stage_validate.py` `_adapt_dict`/`_adapt_optional_dict` non-dict rejection paths).
- Refresh the milestone audit (`.planning/v5.0-MILESTONE-AUDIT.md`, audited 2026-08-19 at 3/6 phases, status gaps_found: 10/32 requirements satisfied, 7 partial, 1 unsatisfied — the `review` workspace-isolation sidecar blocker at `cli.py:173`; Phase 2's three verification gaps confirmed fixed post-verification, Phase 1 flagged for missing Nyquist validation).
- Validate the Phase 3 Nyquist strategy (`.planning/phases/03-rule-matching-review-modes/03-VALIDATION.md`, status validated, nyquist_compliant true, 1 gap found and resolved, 191 phase tests green, `ty check` clean; three rows added for the 03-07 gap-closure plan).
- Record the Phase 3 security threat verification (`.planning/phases/03-rule-matching-review-modes/03-SECURITY.md`, status verified: 27 threats from the seven plan threat models, 27 closed, threats_open 0, 3 accepted risks logged).
- Evolve `.planning/PROJECT.md` after Phase 3: move REV-01, REV-04, and REV-05 (Phase 3) plus REV-02 and REV-03 (Phase 2, previously unrecorded) from Active to Validated, and bump the footer to 2026-08-19.
- Close out Phase 3 as complete and verified: re-verification passes 5/5 must-haves (`.planning/phases/03-rule-matching-review-modes/03-VERIFICATION.md`, status passed, CR-01 and WR-01 confirmed closed, all 8 requirement IDs traced), and `.planning/ROADMAP.md` and `.planning/STATE.md` advance to Phase 4 (Scale, Resume & Diff Output).
- Regenerate the Phase 3 code-review report after the Plan 7 gap closure (`.planning/phases/03-rule-matching-review-modes/03-REVIEW.md`, status issues_found: 0 critical, 2 warning, 1 info across 39 files at standard depth; prior findings CR-01 and WR-01 confirmed fixed).
- Complete Phase 3 Plan 7, the gap-closure plan (rewires `run_review`'s reflection loop to actually remove a retracted finding from the ledger, and routes `apply_profile`'s kept-finding disposition through the D-12 receipt-gate ladder instead of hardcoding `unconfirmed`): record its summary in `.planning/phases/03-rule-matching-review-modes/03-07-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Phase 3 complete (7 of 7 plans done), and confirm REV-02 and REV-03 Complete in `.planning/REQUIREMENTS.md`.
- Record the Phase 3 gap-closure planning pass in `.planning/STATE.md`: status returns to executing, the plan total rises to 15, and the phase shows "Ready to execute" for the checker-approved `03-07-PLAN.md`.
- Add the Phase 3 gap-closure plan `.planning/phases/03-rule-matching-review-modes/03-07-PLAN.md` (wave 7), which closes the two wiring gaps `03-VERIFICATION.md` found: `run_review` discards the kept half of `reflection.apply_verdict`'s return so a retracted finding still reaches the ledger, and `findings_gate.disposition_without_receipt` is dead code because `apply_profile` hardcodes `unconfirmed`; ROADMAP.md now lists 7 plans for Phase 3.
- Record the Phase 3 verification report (`.planning/phases/03-rule-matching-review-modes/03-VERIFICATION.md`, status gaps_found: 4/5 must-haves verified, two gaps in REV-02/REV-03 wiring).
- Record the Phase 3 code-review report (`.planning/phases/03-rule-matching-review-modes/03-REVIEW.md`, status issues_found: 1 critical, 3 warning, 1 info across 29 files at standard depth).
- Complete Phase 3 Plan 6, the final plan of Phase 3 (wires a real finding source into the review verb: `review_agent.py`'s per-file prompt render and response parser, the ported `agents/review-file.md` prompt, and `run_review`'s live gate-chain wiring proven by a `--profile security`/`--profile general` split on one fixture diff): record its summary in `.planning/phases/03-rule-matching-review-modes/03-06-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Phase 3 complete (6 of 6 plans done), and confirm RULE-01, REV-01, and REV-02 Complete in `.planning/REQUIREMENTS.md`.
- Complete Phase 3 Plan 5 (the retract-only reflection filter, its never-silent ledger markdown rendering, and the D-12 receipt-gate disposition ladder for general-defect findings): record its summary in `.planning/phases/03-rule-matching-review-modes/03-05-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 5 of 6 done, and mark REV-03 Complete in `.planning/REQUIREMENTS.md`.
- Complete Phase 3 Plan 4 (the `security`/`general` review profiles and the general-defect-class allowlist bypass, proven a strict superset by a committed dual-run baseline fixture): record its summary in `.planning/phases/03-rule-matching-review-modes/03-04-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 4 of 6 done, and mark REV-01 Complete in `.planning/REQUIREMENTS.md`.
- Complete Phase 3 Plan 3 (seven per-language rule docs and a data-driven conformance test): record its summary in `.planning/phases/03-rule-matching-review-modes/03-03-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 3 of 6 done, and confirm RULE-05 Complete in `.planning/REQUIREMENTS.md`.
- Complete Phase 3 Plan 2 (four-layer rule resolution and the RULE-03 safety gate): record its summary in `.planning/phases/03-rule-matching-review-modes/03-02-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 2 of 6 done, and mark RULE-02, RULE-03, and RULE-04 Complete in `.planning/REQUIREMENTS.md`.
- Complete Phase 3 Plan 1 (the review-mode tracer): record its summary in `.planning/phases/03-rule-matching-review-modes/03-01-SUMMARY.md`, advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 1 of 6 done, and mark RULE-01, RULE-05, and REV-02 Complete in `.planning/REQUIREMENTS.md`.
- Append a passed self-check to `03-01-SUMMARY.md` confirming its created files and its four commits resolve in the repo.
- Close Phase 3 planning: record plan-checker approval (6/6 plans valid, 8/8 requirement IDs and 16/16 context decisions covered), annotate `.planning/ROADMAP.md` with the six-wave order, and advance `.planning/STATE.md` to "Ready to execute" (6 plans).
- Revise the Phase 3 plan set after the plan check: add `03-06-PLAN.md` (wave 6), which wires a per-file review-agent dispatch so the resolved rule doc reaches a reviewing agent as `{{system_rule}}` and real findings reach `review_position_gate`, replacing the hardcoded empty list that made phase success criterion 4 unreachable; fill `03-VALIDATION.md` with the test infrastructure, sampling rate, and a per-task verification map covering all 6 plans; mark `03-RESEARCH.md`'s three open questions resolved with inline resolutions; document in `03-04-PLAN.md` why `apply_profile` returns a 2-tuple where the position gate returns a 3-tuple; ROADMAP.md now lists 6 plans for Phase 3.
- Add the five Phase 3 execution plans and the phase pattern map in `.planning/phases/03-rule-matching-review-modes/` (`03-01-PLAN.md` through `03-05-PLAN.md`, `03-PATTERNS.md`): a tracer plan proving one Python file end to end, four-layer rule resolution with the fail-fast rule-file safety gate, the seven remaining per-language rule docs with a conformance test, the security and general profiles with a same-fixture no-regression proof behind a blocking decision checkpoint, and the reflection filter with its code-enforced protected-subject veto, never-silent ledger, and receipt-gate disposition ladder; ROADMAP.md now lists 5 plans for Phase 3.
- Record the Phase 3 research and draft validation strategy in `.planning/phases/03-rule-matching-review-modes/` (`03-RESEARCH.md`, confidence HIGH with 3 open questions on the `"unconfirmed"` disposition home, OCR safety-check ordering, and `run_review` finding-source wiring; `03-VALIDATION.md`, status draft).
- Record the Phase 3 context-gathering session in `.planning/STATE.md` (stopped-at marker and resume file), pointing the next session at `03-CONTEXT.md`.
- Capture Phase 3 (Rule Matching & Review Modes) implementation decisions in `.planning/phases/03-rule-matching-review-modes/`: a custom `**`-aware glob matcher that keeps the Python 3.12 floor and byte-mirrors OCR `system_rules.go` semantics, OCR-ported per-language rule docs kept in machine-optimized prompt-payload format under `rules/rule_docs/` with fail-fast rule-file safety, a class-allowlist bypass of gates A/B for `--profile general` proven by a same-fixture dual-run regression test, and a skill-dispatched reflection filter with per-retraction ledger entries, logged fail-open events, and code-enforced protected-subject vetoes.
- Record the milestone v5.0 audit at `.planning/v5.0-MILESTONE-AUDIT.md` (status gaps_found: 6/32 requirements satisfied, 22 belong to unstarted Phases 3–6; one new integration blocker — the `review` subcommand writes artifacts into the target repo root instead of the `.sec-overlay/<slug>/` sidecar — plus a `ty` regression in `tests/test_review_tracer.py` and a stale `02-VERIFICATION.md`).
- Fill and approve the Phase 2 validation strategy at `.planning/phases/02-diff-pipeline-positioning/02-VALIDATION.md` (status validated, nyquist_compliant true, 0 gaps; all 7 requirements map to green tests, 304 phase tests pass).
- Record the Phase 2 security verification at `.planning/phases/02-diff-pipeline-positioning/02-SECURITY.md` (24 threats, all closed, threats_open 0; the two open report/ledger wiring threats were fixed in the sec-overlay plugin before sign-off).
- Record the Phase 2 code review fix report at `.planning/phases/02-diff-pipeline-positioning/02-REVIEW-FIX.md` (status all_fixed: 5/5 findings fixed, 0 skipped).
- Record the Phase 2 verification report at `.planning/phases/02-diff-pipeline-positioning/02-VERIFICATION.md` (status gaps_found, 6/9 must-haves verified; the 3 gaps mirror the code review's critical findings).
- Record the Phase 2 code review report at `.planning/phases/02-diff-pipeline-positioning/02-REVIEW.md` (26 files at standard depth: 3 critical, 2 warning findings).
- Mark Phase 2 Plan 5 (the review-mode position gate's three-way split, the dropped-findings report section and ledger, and the seal-to-exit-code mapping) complete: record `02-05-SUMMARY.md` and update the `.planning/ROADMAP.md` progress table (8/8 plans, 100%).
- Mark Phase 2 Plan 4 (the never-guess four-rung positioning ladder plus the position-review markdown section and JSON ledger) complete: record `02-04-SUMMARY.md`, advance `.planning/STATE.md` to Plan 5, update the `.planning/ROADMAP.md` progress table (7/8 plans, 88%), and move POS-02 to Complete in `.planning/REQUIREMENTS.md`.
- Mark Phase 2 Plan 3 (the `CoverageManifest` state machine and unified-diff hunk parser) complete: record `02-03-SUMMARY.md`, advance `.planning/STATE.md` to Plan 4, and update the `.planning/ROADMAP.md` progress table (6/8 plans, 75%).
- Mark Phase 2 Plan 2 (the `file_select.py` allowlist, exclude-glob, and exclusion-reason enum) complete: record `02-02-SUMMARY.md`, advance `.planning/STATE.md` to Plan 3, and update the `.planning/ROADMAP.md` progress table (5/8 plans, 63%).
- Mark Phase 2 Plan 1 (the end-to-end review tracer) complete: record `02-01-SUMMARY.md`, advance `.planning/STATE.md` to Plan 2, update the `.planning/ROADMAP.md` progress table (4/8 plans, 50%), and move DIFF-01 through DIFF-04 and POS-01/POS-03 to Complete in `.planning/REQUIREMENTS.md`.
- Close the Phase 2 decision-coverage gate and record planning state: cite D-05 (additive `diffscope.py` extension) in `02-02-PLAN.md`, commit the `02-PATTERNS.md` pattern map, annotate `.planning/ROADMAP.md` with the five-wave order, and advance `.planning/STATE.md` to "Ready to execute" (5 plans).
- Add the five Phase 2 execution plans (`02-01-PLAN.md` through `02-05-PLAN.md`) covering DIFF-01 through DIFF-04 and POS-01 through POS-03, and record the plan list in `.planning/ROADMAP.md`. Plan 01 is a tracer that wires one changed file through every layer before any layer is built out; plans 02 through 05 expand file selection, the coverage manifest and hunk parser, the never-guess positioning ladder, and the review-mode drop gate with its exit codes.
- Seed the Phase 2 validation strategy at `.planning/phases/02-diff-pipeline-positioning/02-VALIDATION.md` (status `draft`); planning fills the verification map before execution.
- Research Phase 2 (Diff Pipeline & Positioning) in `.planning/phases/02-diff-pipeline-positioning/02-RESEARCH.md`: verified algorithm ports from the `open-code-review` reference (exact-match positioning, not fuzzy `difflib`), flagged that no whole-file `Finding.line` check exists today for audit mode to "keep," and flagged that `Workspace` needs a new `artifacts` property before the coverage manifest can be written.
- Record the Phase 2 context-gathering session in `.planning/STATE.md` (stopped-at marker and resume file), pointing the next session at `02-CONTEXT.md`.
- Capture Phase 2 (Diff Pipeline & Positioning) implementation decisions in `.planning/phases/02-diff-pipeline-positioning/`: a new `review_coverage.py` manifest module persisted at `artifacts/coverage_manifest.json` with strict module-enforced state transitions, an additive `ChangedFile` extension to `diffscope.py` with run-start SHA pinning and exit-2 ref validation, a closed five-reason exclusion vocabulary with a hardcoded OCR-mirror allowlist and a 5000-line size cap, and full report+JSON visibility for position declines, outside-diff drops, and nonzero-exit partial seals.
- Mark Phase 1 (Baseline Health Verification) complete across the planning tracking files: check the phase off in `.planning/ROADMAP.md`, advance `.planning/STATE.md` to Phase 2, and move requirements VAL-01/VAL-02/VAL-03 to Validated in `.planning/PROJECT.md` with the recorded pytest override noted.
- Record Phase 1 planning completion in `.planning/STATE.md`, annotate the Phase 1 roadmap entry with wave dependencies, and add the Phase 1 pattern map (`01-PATTERNS.md`) that maps contingent fix targets to their closest in-repo analogs.
- Plan Phase 1 (Baseline Health Verification) as three sequential plans: capture receipts for all three gate families with a tool version block and a triage ledger, fix every triaged defect under governance without touching the frozen JSON contract, then re-run the gates green and record the fix ledger with a constraint proof. Update the Phase 1 roadmap entry with the plan list.
- Capture Phase 1 (Baseline Health Verification) implementation decisions in `.planning/phases/01-baseline-health-verification/`: fix-in-phase failure policy with a frozen-file hard stop, VERIFICATION.md evidence format with version block and fix ledger, installed-tool versions recorded rather than pinned, and gate scopes for prek, ruff/ty, and plugin validation.
- Add `commands/` to the root `CLAUDE.md` shipping-file list, so a change to a plugin-root slash command bumps the plugin version; a `commands/*.md` file is install payload, and without the bump the update mechanism never ships it. Record the folder in the root README artifact inventory.
- Correct the sec-overlay invocation design spec's multi-repo output paths: the four unified docs and `report.sarif` land in `<cwd>/artifacts/`, and `edges.json`, `verdicts.json`, and `product.json` land at `<cwd>` itself.
- Rewrite the root `CLAUDE.md` around marketplace governance, new-plugin scaffolding, and release process; replace the single changelog rule with routing (plugin-only changes update the plugin's changelog, other changes update the root changelog), note the doc split in the root README, and keep the OpenWiki hand-edit rule's "unless explicitly asked" exception through the section merge.
- Make `pre-commit-check.sh` enforce the changelog routing rule: a commit touching only one plugin's files requires that plugin's `CHANGELOG.md`, and a commit touching anything else requires the root `README.md` and `CHANGELOG.md`; drop `plugins` from the blanket Directory Guide check since the per-plugin routing and the existing immediate-folder README rule already cover it, and add invocation tests for the new routing.
- Direct the OpenWiki brief to read the change digest first on an update run and to mine `docs/superpowers/` under an explicit budget (specs in full, plans by summary only), and drop its reference to a README status section that no longer exists.
- Move governance, code review, status, and decisions sections from README.md to CLAUDE.md for better separation of concerns; README now focuses on what the project is and how to use it.
- Stop treating `.github/` as a Directory Guide folder so it does not require a README that GitHub would promote to the repository homepage.
- Exempt a plugin's own `CHANGELOG.md` from the general immediate-folder README rule in `pre-commit-check.sh`, so a changelog-only plugin commit can pass even when the plugin also has a tracked `README.md`, and restore two governance rules dropped from the root `CLAUDE.md` during the skill-`CLAUDE.md` condensation: stage explicit paths only (never `git add -A`/`-a` or `--no-verify`), and ship new or changed executable logic with a test in the same change.
- Define the full changelog routing matrix here and in `plugins/README.md`, replacing the stale "every commit adds an entry" and "one entry per functionality commit" wording; scope the plugin-script path restriction in `CLAUDE.md` to `plugins/<name>/` scripts, excluding repository tooling under `scripts/`; state in `plugins/README.md` that a skill-level operational `CLAUDE.md` is an optional companion to `SKILL.md`, not a requirement of the five-file plugin template; and clarify in the root README that only a plugin's own `CHANGELOG.md` is exempt from the immediate-folder README rule, not its other staged files.
- Make `pre-commit-check.sh`'s scope-classification `grep` calls fail closed: treat exit status 1 (no match) as empty and any other status as a real failure that stops the hook, and iterate plugin names with a quoted `while read` loop instead of unquoted word-splitting.
- Execute Phase 1 Plan 2: fix every VAL-02 `code defect` row from the Plan 1 triage ledger (4 ruff lint errors, 161 `ty` type diagnostics) under sec-overlay's own governance, leaving the two documented environmental pytest failures and the frozen JSON contract untouched; record VAL-01 and VAL-03 as green at baseline with no fix required.
- Complete Phase 1 Plan 2 (Baseline Health Verification): add `01-02-SUMMARY.md`, confirm requirements VAL-01/VAL-02/VAL-03 already complete in `.planning/REQUIREMENTS.md`, and advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 3 of 3 — closing out the phase's baseline-gate remediation work.

### Added

- Add the Phase 1 independent verification report (`.planning/phases/01-baseline-health-verification/01-VERIFICATION-REPORT.md`): an adversarial re-run of all six gate commands confirming 7/7 phase truths, with one recorded maintainer override accepting the two environmental pytest failures (missing local-only bench corpus and vendored semgrep rules) as provisioning gaps rather than code defects; mark the phase evidence document's status as passed.
- Add the Phase 1 code-review report (`.planning/phases/01-baseline-health-verification/01-REVIEW.md`): a standard-depth review of the 22 files the phase changed, with a clean verdict (0 critical, 0 warning, 2 info) and confirmation the frozen `models.py`/`evidence.py` contract stayed untouched.
- Complete Phase 1 Plan 3 (Baseline Health Verification): add `01-03-SUMMARY.md`, confirm requirements VAL-01/VAL-02/VAL-03 already complete in `.planning/REQUIREMENTS.md`, and advance `.planning/STATE.md` and `.planning/ROADMAP.md` to reflect Phase 1's completion — sealing the phase.
- Add a fix ledger, constraint proof, and phase outcome to `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md`: a per-commit table mapping all 165 baseline ruff/ty findings to their 9 fix commits, proof the frozen `models.py`/`evidence.py` contract stayed empty across every fix, proof each fix commit carried its own plugin-version bump and changelog entry, and a plain-language statement of the two residual environmental gaps.
- Record Phase 1's final gate verification in `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md`: six post-fix receipts (both plugin validations, pytest, ruff, ty, prek) captured after Plan 2's last fix commit, appended alongside the baseline red without overwriting it.
- Capture VAL-01 baseline receipts in `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md`: a tool version block (ruff, ty, pytest, python, claude CLI) and two `claude plugin validate .` receipts, one at the repo root and one inside `plugins/sec-overlay/`, both exit 0.
- Capture VAL-02 and VAL-03 baseline receipts in the same evidence document: pytest/ruff/ty against the sec-overlay helpers package, `prek run --all-files` at the repo root, and a triage ledger dispositioning the two pytest failures as environmental, the ruff and ty findings as code defects, and the untriggered `conventional-commit-msg` hook as a config characteristic of `--all-files`.
- Record the `proceed-as-triaged` remediation route in `01-VERIFICATION.md`: the maintainer confirmed no triaged fix touches the frozen `models.py`/`evidence.py` contract, clearing Plan 02 to execute the ledger's ruff and ty fixes under normal governance.
- Complete Phase 1 Plan 1 (Baseline Health Verification): add `01-01-SUMMARY.md`, mark requirements VAL-01/VAL-02/VAL-03 complete in `.planning/REQUIREMENTS.md`, and advance `.planning/STATE.md` and `.planning/ROADMAP.md` to Plan 2 of 3.
- Start milestone v5.0 (Hybrid Diff-Review Architecture) in `.planning/`: update PROJECT.md with the milestone goal and target features, and reset STATE.md for the new cycle.
- Create the milestone v5.0 roadmap in `.planning/ROADMAP.md`: six phases from baseline health through diff pipeline, rule matching, scale, end-to-end verification, and governed release, with all 32 requirements mapped.
- Define milestone v5.0 requirements in `.planning/REQUIREMENTS.md`: 24 requirements across validation, diff pipeline, positioning, rule matching, review modes, scale, output, audit integrity, and release governance.
- Add the onboarding summary at `.planning/onboarding/SUMMARY.md`: an index of the planning state, codebase map status, and the recommended next command.
- Add the GSD planning setup under `.planning/`: PROJECT.md, REQUIREMENTS.md, ROADMAP.md, and STATE.md bootstrapped from 50 ingested design docs, with synthesized intel files and the ingest conflict report.
- Add the sec-overlay invocation implementation plan: TDD tasks for the `run.py` driver (working-tree fence, per-phase receipt, token env, role inference, manifest synthesis, single-repo drive loop), the driver `on_complete` hook, the O-65 red-team gate path fix, and the `/sec-overlay:audit` command.
- Add the sec-overlay invocation design spec: one `/sec-overlay:audit` command that audits one repo or audits several and correlates them, a thin `run.py` driver (token env, per-phase receipts, working-tree fence), scan-profile role inference feeding the existing correlation core, and the one-writer redteam-adversary path fix; the coverage/recall defect family is named as deferred.
- Add the previously uncommitted Plan B (themes T2/T3, shared reference parser and status/receipt vocabulary) of the sec-overlay defect-remediation spec for the record; its implementation already shipped.
- Add the three implementation plans for the architecture/threat-model standards rebuild: CVSS v4.0 migration, diagram/STE enforcement modules, and the phase rebuild with consumer rewiring.
- Add the architecture/threat-model standards design spec (with its user-authored source standard) rebuilding sec-overlay's architecture and threat-model phases around C4/arc42, a derived DFD with STRIDE(+PASTA/LINDDUN), CVSS v4.0 migration, hard Mermaid caps, and an STE prose linter.
- Add the sec-overlay defect-remediation design spec covering all 57 issues from the agent-gateway run across seven fix themes plus a new independent artifact-review phase.
- Add Plan D (themes T6/T7 plus artifact-review) of the sec-overlay defect-remediation spec: TDD tasks for a split risk-ordered report with real impact text and counts-in-words, per-finding detail files, phase telemetry via campaign-state timings, context doc-citation cross-checks, backend-completeness strictness, self-score critic metrics, and a new adversarial artifact-review phase with a deterministic artifact gate.
- Add Plan C (themes T4/T5) of the sec-overlay defect-remediation spec: TDD tasks for a derived route-to-control coverage table with logged gaps, doc-coverage provenance, resolver-backed finding citations, prefilter sidecar exclusion, same-line dedupe, class-extension alias-map gap logging, and red-team payload reachability.
- Add Plan A (theme T1) of the sec-overlay defect-remediation spec: TDD implementation tasks for the deterministic `audit` phase-driver, wiring the six unwired modules and the findings-gate, unrouted-class, and verify-honesty fixes.
- Add `docs/templates/plugin/`, a new-plugin skeleton (`plugin.json`, README, CLAUDE.md, CHANGELOG, sample `SKILL.md`) with `{{PLACEHOLDER}}` markers, matching the root `CLAUDE.md` "New plugin" checklist.
- Add the four-commit implementation plan for the marketplace documentation split.
- Add the marketplace documentation-structure design spec: root CLAUDE.md focuses on governance and new-plugin scaffolding, each plugin carries its own CLAUDE.md, README, and CHANGELOG, and hook changelog routing follows.
- Add `scripts/openwiki-history-digest.sh` and run it from the OpenWiki Update workflow, so each update run reads a bounded `.openwiki-history.md` digest of commits and changed files; the agent cannot run `git log` itself while `.openwikiignore` restricts its shell to `pwd` and `git rev-parse HEAD`.
- Add OpenWiki ignore rules, a durable `openwiki/INSTRUCTIONS.md` brief, local env sample with telemetry off, and a SHA-pinned weekly/manual update workflow that uses Anthropic Claude Sonnet 5 and opens a review PR instead of writing to main.
- Add the generated OpenWiki pages covering marketplace contract, commit governance, the sec-overlay pipeline, and repository operations.
- Add `.coderabbit.yaml` so CodeRabbit reviews pull requests with repo-specific path instructions, governance pre-merge checks, and only the linters this stack uses, and exclude the intentionally vulnerable detector fixtures from review.
- Document the open-source review rate limit in the README code review section, including `@coderabbitai rate limit` to check capacity and `@coderabbitai review` to run a skipped review, after a pull request was skipped with "Review limit reached".
- Set `abort_on_close: false` so a CodeRabbit review still finishes when a pull request merges mid-review, and document waiting for the review in `CLAUDE.md`.
- Protect `main` with a GitHub ruleset requiring pull requests and blocking force-pushes and deletions, and turn on free GitHub code security (CodeQL default setup, Dependency review, Dependabot updates, private vulnerability reporting).
- Track the CodeGuard secure-coding rules under `.cursor/rules/`, so the guidance applies to anyone working in a clone rather than only on the machine that happens to have them.
- Extend the pre-commit Directory Guide special-case to `docs/` so that folder's README stays in lockstep with its files.
- Reduce the commit-msg hook to the Conventional Commits format and summary length checks.
- Split sec-overlay plugin docs by audience: a user-facing README and CHANGELOG at the plugin root, a maintainer CLAUDE.md that never loads for plugin installers, and a trimmed skill CLAUDE.md focused on running the harness. Point SKILL.md at the skill CLAUDE.md and fix the skill README's semver-bump link to the marketplace root CLAUDE.md.

### Removed

- Drop 21 unused CodeGuard Cursor rules so editor context keeps only the always-on hardcoded-credentials rule.
- Drop `.github/README.md` so GitHub shows the marketplace README on the repository homepage instead of the `.github/` folder guide.

## 0.2.0 - 2026-08-12

### Changed

- Apply `ruff format` to the sec-overlay helper files touched by the review-improvements branch (`calibrate.py`, `selfscore.py`, `sarif.py`, `report.py`, and their tests), so the branch's own code conforms to the project formatter.
- Default `report.write_report` SARIF output to carry every reportable finding plus `needs-deployment-testing` findings marked with an `inSource` suppression, so downstream gates see them without failing on them; pass `--confirmed-only` (or `confirmed_only=True`) to restore the prior confirmed/fixed-only SARIF.

### Added

- Populate SARIF `driver.rules` from the finding set, de-duplicated by `rule_id`, with `cls` as the rule name and ASVS/CodeGuard ids as properties.
- Instruct the trace agent to set `reachability.blocker = "external-boundary"` when a sink resolves into a dependency outside the ingested set, and instruct the validate agent to never promote such a finding to `confirmed`.
- Add the design spec for four sec-overlay improvements from the lumedeodorant review: per-stage token accounting with a run self-score, systemic finding clustering, an external-boundary confidence disposition, and SARIF completeness.
- Add the task-by-task TDD implementation plan for the four sec-overlay improvements (build order I3, I1, I2, I4).
- Add a "Run economics" report section (token totals by phase and model, plus a USD estimate) backed by `cost.aggregate_by_model`.
- Add `cluster_id` and `affected_sites` fields to `Finding` and the finding schema.
- Add `sec_overlay.cluster`, a deterministic pass that groups ≥3 same-class, same-sink `raw` findings into one systemic cluster before the critic/gate ladder.
- Add `sec_overlay.selfscore`, a per-run finding-status score persisted to `state.budget`.
- Document token proxy fallback and self-score call in the sec-overlay SKILL orchestration (cost recording when harness token reporting is ambiguous; per-run self-score persisted to state for next-run calibration).
- Add `report.collapse_clusters`, which reduces each systemic cluster to one representative finding (un-clustered findings pass through unchanged) applied to both the confirmed and needs-runtime report buckets.
- Add an "Affected sites" table to the needs-runtime finding view, listing every member of a collapsed cluster.
- Add `sec_overlay.scope`, an ingested-package boundary check (`is_external_package`) reading `kb/scan-scope.json`, so a sink resolving into an un-ingested dependency can be flagged without inventing a boundary when no manifest exists.
- Cap calibrated `risk_score` at 3 and set `completeness_tier` to `external-unverifiable` for findings whose `reachability.blocker` is `external-boundary`, so they can never present as a confirmed medium.
- Render findings stamped `completeness_tier == "external-unverifiable"` in their own report section, "Leads — pending external-dependency verification", separate from the source-provable needs-runtime bucket.
- Bump sec-overlay to 0.2.0 for this review-improvements release, above the 0.1.1 governance release.

## 0.1.1 - 2026-08-12

### Changed

- Replace the manual plugin-version-bump policy with automatic Conventional-Commits semver bumping, triggered when a commit changes a plugin's shipping files (breaking → major, `feat` → minor, other types → patch); a plugin `CLAUDE.md` edit alone does not bump.
- Align the sec-overlay skill `CLAUDE.md` with the automatic-bump rule and bump sec-overlay to 0.1.1.

## 0.1.0 - 2026-08-11

### Changed

- Rewrite the root README to the marketplace template (Installation, Plugins, Development, Governance, License) and collapse the per-task Status log.
- Refocus the sec-overlay skill CLAUDE.md on repo mechanics: real git/governance section, the correct 2 env-only failure count, and the prek folder-README hook.
- Extend the pre-commit hook to require a folder's README.md whenever files in that folder change, with a Bash invocation test.

### Added

- Scaffold the plugin marketplace manifest and the sec-overlay plugin (v0.1.0) with a placeholder skill script.
- Add commit governance: Conventional Commits check, main-branch block, and forced README/CHANGELOG updates via prek hooks.
- Add the design spec for porting the sec-harness skill into the sec-overlay plugin.
- Add the implementation plan for the sec-overlay port and extend the rename scope to the HARNESS_ROOT and SEC_HARNESS_HOME tokens.
- Add the design spec for incorporating upstream's KB doc/diagram redesign into the sec-overlay plugin.
- Add the design spec for the sec-overlay documentation overhaul.
- Add the implementation plan for the KB doc/diagram redesign port.
- Add the implementation plan for the sec-overlay documentation overhaul.
- Import the sec-harness skill source tree into the sec-overlay plugin (semgrep submodule excluded).
- Rename the ported identifiers to sec-overlay: the `sec_overlay` Python package, the `sec-overlay` distribution name, and the `SEC_OVERLAY_HOME` and `OVERLAY_ROOT` tokens.
- Point the SKILL.md run instructions at `${CLAUDE_PLUGIN_ROOT}` and document the semgrep ruleset as a prerequisite (the semgrep-rules submodule is not shipped).
- Verify the rename preserved behavior: 552 tests pass; the two failures are environment-only (gitignored bench corpus, excluded semgrep submodule), not rename regressions.
- Update sec-overlay manifest descriptions to the agentic security-audit harness.
- Add the DIAGRAM_STYLE, FIELD_OWNERSHIP, and QUALIFIER_PROOF prompt-constants blocks.
- Add the `open_questions` field to `Finding` and the finding schema.
- Flag comment-only `file:line` citations in the phase gate as a scrutiny note.
- Add the `deployment_config` context kind, `deployed_in` tag, and `Context.diagram` slot rendered into `CONTEXT.md`.
- Render a Questions-to-ask section in the red-team plan and wire the diagram/field-ownership/qualifier guidance and deployment-config lens into the agent prompts.
- Add per-folder READMEs for agents/classes, references/asvs, references/codeguard, references/hunting, helpers/sec_overlay, and helpers/tests.

### Removed

- Remove stale Go-rewrite prose from the four live sec-overlay docs.

### Fixed

- Prevent the report renderer from crashing when a red-team agent writes `runtime_test.expected_signal` as a bare string; the report and red-team renderers now share one tolerant helper and the finding schema validates the `runtime_test` inner shape.
- Reject placeholder-version deps bumps and stop `verify_findings` from overriding a `validate-fix` not-fixed verdict.
- Document the `open_questions` field in the `finding.schema.json` reference table and correct the sec-overlay `CLAUDE.md` prompt-constants block counts (§6 and §8) from six and nine to twelve.
- Correct the sec-overlay README and helpers/README test counts to 575 tests / 2 env-only failures and verify the diagrams and worked example against the current pipeline.
- Clean up the hook test's temporary repos with an EXIT trap so no `mktemp` directories are left behind.
- Rename the sec-overlay overview architecture diagram's subgraph id from `HARNESS` to `OVERLAY` (rendered label unchanged).
