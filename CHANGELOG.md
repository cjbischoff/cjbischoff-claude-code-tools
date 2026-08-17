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
