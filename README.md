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

### OpenWiki

First init is local (do not run `--init` in CI). From the repo root, with an Anthropic key in the environment:

```bash
export OPENWIKI_PROVIDER=anthropic
export OPENWIKI_MODEL_ID=claude-sonnet-5
export OPENWIKI_TELEMETRY_DISABLED=1
export DO_NOT_TRACK=1
openwiki code --init --print
```

Keep `openwiki/INSTRUCTIONS.md` and `.openwikiignore`. The generated wiki under `openwiki/` is tracked; start at `openwiki/quickstart.md`. Later refreshes: `openwiki code --update --print`, or the `OpenWiki Update` workflow (set `ANTHROPIC_API_KEY` as a repository secret; weekly Monday 08:00 UTC plus manual dispatch).

An update run reads `.openwiki-history.md` to learn what changed since the last run, because `.openwikiignore` blocks the agent from running `git log`. CI regenerates it automatically; before a local `--update`, run it yourself:

```bash
./scripts/openwiki-history-digest.sh
```

## Directory Guide

Each folder below has its own README.md describing what it holds, its naming convention, and who writes to it. A commit that changes a tracked file inside a folder that has a README.md must update that folder's README.md in the same commit; inside `plugins/`, this applies per plugin. The only exemption is a commit that stages exclusively a plugin's own `CHANGELOG.md`; any other staged file under that plugin still requires the immediate-folder README.md (see [CLAUDE.md](CLAUDE.md) for the exact routing).

| Folder | Purpose |
|--------|---------|
| `plugins/` | One directory per distributed plugin |
| `scripts/` | Repo-level tooling (git hook scripts) |
| `docs/` | Design specs and planning documents |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `.planning/` | GSD planning setup: PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, synthesized intel from the 50 ingested design docs, the ingest conflict report, and the onboarding summary. Current milestone: v5.0 Hybrid Diff-Review Architecture (32 requirements, 6 phases). Phase 1 context, its pattern map, its three execution plans, its baseline-gate evidence document (`01-VERIFICATION.md`, covering VAL-01/02/03, a triage ledger, the approved `proceed-as-triaged` remediation route, the Plan 2 fix/no-fix verdicts, Plan 3's final green receipts, its fix ledger, and its constraint proof), Plan 1, Plan 2, and Plan 3's summaries (`01-01-SUMMARY.md`, `01-02-SUMMARY.md`, `01-03-SUMMARY.md`), the phase code-review report (`01-REVIEW.md`, status clean: 0 critical, 0 warning, 2 info), and the independent verification report (`01-VERIFICATION-REPORT.md`, status passed: 7/7 truths, 1 recorded maintainer override for the two environmental pytest failures) are captured in `.planning/phases/01-baseline-health-verification/`. Phase 1 is complete and verified (3/3 plans, verification passed with 1 recorded override); STATE.md, ROADMAP.md, and PROJECT.md point at Phase 2 (Diff Pipeline & Positioning) next; Phase 2's context, discussion log, phase research, draft validation strategy, pattern map, and five verified execution plans (`02-CONTEXT.md`, `02-DISCUSSION-LOG.md`, `02-RESEARCH.md`, `02-VALIDATION.md`, `02-PATTERNS.md`, `02-01-PLAN.md` through `02-05-PLAN.md`; plan checker passed, 15/15 context decisions covered, 7/7 requirement IDs mapped) are captured in `.planning/phases/02-diff-pipeline-positioning/`. Plan 1 (the review-mode tracer), Plan 2 (the allowlist, exclude-glob, and exclusion-reason enum for `file_select.py`), and Plan 3 (the `CoverageManifest` state machine and unified-diff hunk parser) are complete and summarized (`02-01-SUMMARY.md`, `02-02-SUMMARY.md`, `02-03-SUMMARY.md`); STATE.md is on Plan 4, ROADMAP.md shows 6/8 Phase 2 plans done, and REQUIREMENTS.md marks DIFF-01 through DIFF-04 and POS-01/POS-03 Complete |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest |
| `plugins/sec-overlay/README.md` | sec-overlay user-facing README: install, prerequisites, quick start |
| `plugins/sec-overlay/CHANGELOG.md` | sec-overlay Common Changelog |
| `plugins/sec-overlay/CLAUDE.md` | sec-overlay maintainer manual: development commands, folder-README rule, history |
| `plugins/sec-overlay/commands/` | Slash commands the plugin installs, including `/sec-overlay:audit`; a plugin-root `commands/` file is install payload, so a change there bumps the plugin version |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness; links to the skill's `CLAUDE.md` for prerequisites and operating rules |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `docs/` | Design specs and implementation plans (see `docs/README.md`), including the sec-overlay defect-remediation design and its Plan A audit-driver, Plan B shared-vocabulary, Plan C coverage/accuracy, and Plan D report/telemetry/artifact-review implementation plans, and the architecture/threat-model standards design (C4/arc42 + derived DFD/STRIDE, CVSS v4.0, Mermaid caps, STE prose) with its Plans 1–3 (CVSS v4.0 migration, diagram/STE enforcement, phase rebuild), and the sec-overlay invocation design (one `/sec-overlay:audit` command, a `run.py` driver, scan-profile role inference feeding the correlation core) with its nine-task implementation plan |
| `docs/templates/plugin/` | New-plugin skeleton copied to `plugins/<name>/` and filled in per the root `CLAUDE.md` "New plugin" checklist |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `scripts/openwiki-history-digest.sh` | Writes the bounded `.openwiki-history.md` change digest an OpenWiki update run reads in place of `git log` |
| `CHANGELOG.md` | Common Changelog for repo-level changes; plugin changes live in `plugins/<name>/CHANGELOG.md` |
| `SECURITY.md` | How to report vulnerabilities (GitHub private reporting) |
| `.github/workflows/dependency-review.yml` | GitHub Dependency review on pull requests |
| `.github/dependabot.yml` | Weekly Dependabot updates for Actions and pip |
| `.github/codeql/codeql-config.yml` | CodeQL path exclusions (test fixtures, caches) |
| `.gitignore` | Keeps caches, venvs, and local secrets out of git |
| `.coderabbit.yaml` | CodeRabbit pull request review config: path rules, governance pre-merge checks, tool selection |
| `.cursor/rules/codeguard-1-hardcoded-credentials.mdc` | Always-on Cursor rule: never commit secrets, API keys, or credentials |
| `.openwikiignore` | Paths OpenWiki must not read during wiki init/update (separate from `.gitignore`) |
| `openwiki/INSTRUCTIONS.md` | User-authored wiki brief for init and CI `--update`; OpenWiki does not rewrite it |
| `.env.example` | Local OpenWiki provider, model, and telemetry-off settings (no secrets) |
| `.github/workflows/openwiki-update.yml` | Weekly/manual OpenWiki `--update` that opens a PR using Anthropic Sonnet 5 |
| `openwiki/` | Generated marketplace wiki (quickstart, marketplace, governance, sec-overlay, operations); do not hand-edit except `INSTRUCTIONS.md` |
| `AGENTS.md` | OpenWiki pointer block for coding agents; the generated `<!-- OPENWIKI:START -->` region only |

## Contributing

All changes go through feature branches with Conventional Commits. See [CLAUDE.md](CLAUDE.md) for detailed branching, commit, and code review processes. Root and plugin docs are split by audience: this README and the root `CHANGELOG.md` cover repo-level changes, while each plugin carries its own README, CHANGELOG, and maintainer CLAUDE.md under `plugins/<name>/`. Design specs and implementation plans for in-flight work live under `docs/superpowers/` (see [docs/README.md](docs/README.md)). CLAUDE.md's OpenWiki section covers when a generated page may be hand-edited.

## License

MIT
