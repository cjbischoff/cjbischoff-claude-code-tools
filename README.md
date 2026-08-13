# cjbischoff-claude-code-tools

Claude Code plugin marketplace — personal plugins for Christopher Bischoff.

## Installation

```
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
```

## Plugins

- **sec-overlay**: agentic security-audit harness (static analysis, tool-receipt gate).

## Development

```bash
claude plugin validate .      # validate plugin + marketplace manifests
prek run                      # run governance hooks
cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q   # Python core tests
```

## Directory Guide

Each folder below has its own README.md describing what it holds, its naming convention, and who writes to it. A commit that changes a tracked file inside a folder that has a README.md must update that folder's README.md in the same commit.

| Folder | Purpose |
|--------|---------|
| `plugins/` | One directory per distributed plugin |
| `scripts/` | Repo-level tooling (git hook scripts) |
| `docs/` | Design specs and planning documents |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `docs/` | Design specs and implementation plans (see `docs/README.md`) |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `CHANGELOG.md` | Common Changelog; one entry per functionality commit |
| `SECURITY.md` | How to report vulnerabilities (GitHub private reporting) |
| `.github/workflows/dependency-review.yml` | GitHub Dependency review on pull requests |
| `.github/dependabot.yml` | Weekly Dependabot updates for Actions and pip |
| `.github/codeql/codeql-config.yml` | CodeQL path exclusions (test fixtures, caches) |
| `.gitignore` | Keeps caches, venvs, and local secrets out of git |
| `.coderabbit.yaml` | CodeRabbit pull request review config: path rules, governance pre-merge checks, tool selection |
| `.cursor/rules/codeguard-*.mdc` | CodeGuard secure-coding rules; three always apply, the rest match file globs |

## Governance

- Direct commits to `main` are blocked by a pre-commit hook and by a GitHub ruleset (pull requests required; force-push and deletion blocked). Work on a `<type>/<short-kebab-description>` branch.
- Do not add `.github/README.md`; GitHub would show it as the repository homepage instead of this file.
- Conventional Commits; summary under 50 chars; body wrapped at 72.
- Every commit that changes tracked files updates `README.md` and `CHANGELOG.md` in the same commit, plus the affected folder's `README.md`. Hooks enforce this.
- A commit that changes a plugin's shipping files bumps that plugin's `version` in the same commit: breaking → major, `feat` → minor, all other types → patch. Editing a plugin `CLAUDE.md` alone does not bump.
- Run `prek install` once after cloning to activate the hooks.

## Code review

CodeRabbit reviews every pull request against `main`, configured by `.coderabbit.yaml`. Because this repository is public it qualifies for CodeRabbit's open-source plan, which grants Pro+ features without a subscription.

- Wait for CodeRabbit's walkthrough comment before merging. A pull request merged within seconds of opening gets no findings.
- The review comments but never blocks: the GitHub ruleset is the only required gate on `main`.
- Pre-merge checks mirror the governance rules above in `warning` mode, so a violation shows up in the review as well as in the hooks: README and CHANGELOG updated, plugin version bumped, folder README updated, and no path escaping a plugin directory.
- Intentionally vulnerable detector fixtures under `**/fixtures/` are excluded from review, so seeded findings do not bury real ones.
- The open-source plan meters reviews per hour, so a burst of pull requests can exhaust the allowance and skip a review outright. Comment `@coderabbitai rate limit` to check remaining capacity, then `@coderabbitai review` to run the review once capacity returns.

## Status

sec-overlay is ported and green (593 pass, 2 env-only failures); plugin and marketplace manifests validate. The `feat/sec-overlay-review-improvements` branch is complete: all 12 planned tasks landed and passed final whole-branch review, and the branch-touched helpers are `ruff format`-clean. Plugin versions bump automatically on shipping-file changes (Conventional-Commits semver); this review-improvements release ships sec-overlay as 0.2.0, above the 0.1.1 governance release on `main`.

Changed the default SARIF output to carry every reportable finding plus `needs-deployment-testing` findings marked with an `inSource` suppression, so downstream gates see them without failing; `--confirmed-only` restores the prior confirmed/fixed-only SARIF.

Populated SARIF `driver.rules` from the finding set (de-duplicated by `rule_id`, `cls` as name, ASVS/CodeGuard ids as properties); `results` unchanged.

Instructed the trace and validate agents to set `reachability.blocker = "external-boundary"` when a sink resolves into an un-ingested dependency, and to keep such findings as leads rather than promoting them to confirmed.

Rendered external-unverifiable findings in their own report section, separate from the source-provable needs-runtime bucket.

Capped calibrated risk for external-boundary findings so they can never present as a confirmed medium, regardless of claimed severity.

Added an ingested-package scope check (`scope.is_external_package`) so a sink resolving into an un-ingested dependency can be flagged, without inventing a boundary when no manifest exists.

Collapsed systemic clusters to one representative in the rendered report, with a per-representative affected-sites table.

Added a systemic finding-clustering pass that groups related findings by class and sink before the critic/gate ladder.

Wired token proxy fallback and self-score call into the sec-overlay SKILL orchestration documentation (cost recording for ambiguous harness token reporting; per-run self-score persisted to state).

Added `cluster_id` and `affected_sites` fields to the `Finding` model and finding schema.

Added a per-run self-score module that counts findings by status and persists them to state.

Added the design spec and the task-by-task TDD implementation plan for four sec-overlay improvements from the lumedeodorant review (token accounting/self-score, systemic finding clustering, external-boundary disposition, SARIF completeness).

Refocused the sec-overlay skill CLAUDE.md on repo mechanics (git/governance, testing, hook).

Added an EXIT-trap cleanup to the pre-commit hook test so it leaves no temp directories behind.

Added a "Run economics" report section (tokens by phase/model, USD estimate) via `cost.aggregate_by_model`.

Renamed the sec-overlay overview diagram's subgraph id to `OVERLAY`.

Corrected the sec-overlay README/helpers test counts and verified the diagrams and worked example.

Added six per-folder READMEs under the sec-overlay skill.

Generalized the pre-commit hook to enforce per-folder README freshness (with a Bash test).

## Decisions

- plugin.json declares no components; the default `skills/` directory scan handles discovery, strict mode stays at its default (true).
- Plugin versions bump automatically on shipping-file changes, using Conventional-Commits semver (breaking → major, `feat` → minor, other types → patch); a plugin `CLAUDE.md` edit alone does not bump. Replaces the prior manual-bump policy.
- Governance is enforced with prek local hooks rather than convention only, per user request for forced updates.

## License

MIT
