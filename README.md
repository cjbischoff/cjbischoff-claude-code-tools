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
| `docs/decisions/` | Project architecture decisions, one file per decision |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `.planning/` | GSD planning setup: PROJECT.md, ROADMAP.md, STATE.md, MILESTONES.md, synthesized intel from the 50 ingested design docs, the ingest conflict report, and the onboarding summary. Milestone v5.0 Hybrid Diff-Review Architecture shipped 2026-08-22 (7 phases, 30 plans, 32/32 requirements). Its roadmap, requirements, audit, and phase directories are archived under `.planning/milestones/`; `RETROSPECTIVE.md` holds the milestone retrospective. Milestone v5.1 Tech-Debt Cleanup shipped 2026-08-22 (2 phases, 7/7 requirements, PRs #32-#33): all six Phase 06 tech-debt items cleared and the ingest WARNING closed. Its roadmap, requirements, and phase directories are archived under `.planning/milestones/`; `MILESTONES.md` and `RETROSPECTIVE.md` carry the milestone records. Next milestone not yet defined; a fresh `REQUIREMENTS.md` arrives with `/gsd-new-milestone`. |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest |
| `plugins/sec-overlay/README.md` | sec-overlay user-facing README: install, prerequisites, quick start |
| `plugins/sec-overlay/CHANGELOG.md` | sec-overlay Common Changelog |
| `plugins/sec-overlay/CLAUDE.md` | sec-overlay maintainer manual: development commands, folder-README rule, history |
| `plugins/sec-overlay/commands/` | Slash commands the plugin installs, including `/sec-overlay:audit`; a plugin-root `commands/` file is install payload, so a change there bumps the plugin version |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness; links to the skill's `CLAUDE.md` for prerequisites and operating rules |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `docs/` | Design specs and implementation plans (see `docs/README.md`), including the sec-overlay defect-remediation design and its Plan A audit-driver, Plan B shared-vocabulary, Plan C coverage/accuracy, and Plan D report/telemetry/artifact-review implementation plans, and the architecture/threat-model standards design (C4/arc42 + derived DFD/STRIDE, CVSS v4.0, Mermaid caps, STE prose) with its Plans 1–3 (CVSS v4.0 migration, diagram/STE enforcement, phase rebuild), and the sec-overlay invocation design (one `/sec-overlay:audit` command, a `run.py` driver, scan-profile role inference feeding the correlation core) with its nine-task implementation plan, and the sec-overlay recall-gaps design (absence-rule pack, recall adversary, JSON dependency-sink catalog, catalog-gated proof tuples, policy-engine indicators, deterministic route census) with its three implementation plans (Plan 1 dependency-sink catalog and policy-engine indicators, Plan 2 absence detection and catalog-gated proof tuples, Plan 3 route census and recall adversary), and the sec-overlay improvements build spec (29 requirements in six ordered groups, a cite-verification record against plugin HEAD, and the opt-in proof-by-execution lane) with its Plan 1 contract layer (REQ-02, REQ-18, REQ-07, REQ-10, REQ-32 as five red/green commit pairs, the contract lint created in the first pair and extended by each later one, plus the three HEAD conflicts it resolves) and its Plan 2 data integrity (REQ-13, REQ-15, REQ-16, REQ-17, REQ-08 and the moved REQ-09 as six red/green commit pairs, plus the six rulings it takes against plugin HEAD) and its Plan 3 verification and scoring (REQ-21, REQ-22, REQ-06 with REQ-19, REQ-20, REQ-01, REQ-27 as six red/green commit pairs, plus the three tests it deliberately reverses) and its Plan 4 coverage and routing (REQ-04, REQ-11, REQ-25, REQ-24 as four red/green commit pairs, plus the corrected REQ-04 red test and the non-monotonic suite count the group produces) and its Plan 5 render and terminal gate (REQ-03, REQ-05, REQ-31 as three red/green commit pairs, plus the three-bucket next-action mapping and the narrowed REQ-05 scope) and its Plan 6 capability lanes (REQ-33, REQ-34, REQ-12, REQ-14, REQ-30 as five red/green commit pairs, plus the six rulings it takes against plugin HEAD and the opt-in prove lane it lands last), and the sec-overlay defect-repair spec (22 requirements in seven root-cause-ordered groups, a three-table cite-verification record against plugin 1.122.0, and three removals of unreachable capability that make the build a major version bump) with its Plan 1 phase/artifact contract (REQ-42, REQ-40, REQ-43, REQ-41, REQ-44 as five red/green commit pairs, plus the six rulings it takes against plugin 1.122.0 and the frozen-contract digest recomputation the `factcheck` deletion forces) and its Plan 2 dead-lever removal (REQ-45, REQ-46, REQ-47, REQ-48 as four red/green commit pairs, plus the five citation corrections and six rulings it takes against plugin 1.122.0, the redirect of REQ-47 from the live `scanscope.py` to the unreachable `scope.py`, and the four adjacent findings it records without fixing) |
| `docs/decisions/` | Project architecture decisions in the Decision / Context / Alternatives / Reasoning / Trade-offs / Supersedes form, one file per decision, listed in `docs/decisions/INDEX.md` (see `docs/decisions/README.md`) |
| `docs/templates/plugin/` | New-plugin skeleton copied to `plugins/<name>/` and filled in per the root `CLAUDE.md` "New plugin" checklist |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `scripts/openwiki-history-digest.sh` | Writes the bounded `.openwiki-history.md` change digest an OpenWiki update run reads in place of `git log` |
| `CHANGELOG.md` | Common Changelog for repo-level changes; plugin changes live in `plugins/<name>/CHANGELOG.md` |
| `SECURITY.md` | How to report vulnerabilities (GitHub private reporting) |
| `.github/workflows/dependency-review.yml` | GitHub Dependency review on pull requests |
| `.github/dependabot.yml` | Weekly Dependabot updates for Actions and pip |
| `.github/codeql/codeql-config.yml` | CodeQL path exclusions (test fixtures, caches) |
| `.github/workflows/sec-overlay-tests.yml` | sec-overlay pytest plus an offline detection-regression gate on pull requests |
| `.gitignore` | Keeps caches, venvs, local secrets, and the vendored semgrep-rules clone out of git |
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
