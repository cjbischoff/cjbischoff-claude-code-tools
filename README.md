# cjbischoff-claude-code-tools

Claude Code plugin marketplace: personal plugins for Christopher Bischoff.

## Installation

Add the marketplace once, then install the plugins you want:

```text
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
/plugin install plainspoken@cjbischoff-claude-code-tools
/plugin install readme-keeper@cjbischoff-claude-code-tools
```

## Plugins

| Plugin | What it does |
|---|---|
| [sec-overlay](plugins/sec-overlay/) | Agentic security-audit harness: runs SAST, investigates candidates with multi-agent gates, and emits SARIF + Markdown reports. |
| [plainspoken](plugins/plainspoken/) | Draft, rewrite, review, deep-review, brief, and lint prose so it is specific, useful, and the writer's own, without inventing facts. |
| [readme-keeper](plugins/readme-keeper/) | Write a README from the code, keep it true with marker-based updates, check it offline for drift, and review it, without inventing facts. |

## Development

```bash
claude plugin validate .      # validate plugin + marketplace manifests
prek run                      # run governance hooks
cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q   # Python core tests
cd plugins/plainspoken && uv run --with pytest pytest -q                 # plainspoken lint + eval schema tests
cd plugins/readme-keeper && uv run --with pytest pytest -q                # readme-keeper checker + eval schema tests
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
| `.omp/` | omp-native context wrappers at repo-root, plugin, and skill depths. Each `.omp/AGENTS.md` uses `@import` to pull in the corresponding `CLAUDE.md` so omp discovers and respects marketplace, plugin, and skill governance rules at priority 100 (native). |
| `.planning/` | GSD planning setup: `PROJECT.md`, `ROADMAP.md`, `STATE.md`, `MILESTONES.md`, ingested design-doc intel, and `RETROSPECTIVE.md`. Shipped milestones v5.0, v5.1, and v5.2 are archived under `.planning/milestones/`. Milestone v5.3 is in planning (`STATE.md`). |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest |
| `plugins/sec-overlay/README.md` | sec-overlay user-facing README: install, prerequisites, quick start |
| `plugins/sec-overlay/CHANGELOG.md` | sec-overlay Common Changelog |
| `plugins/sec-overlay/CLAUDE.md` | sec-overlay maintainer manual: development commands, folder-README rule, history |
| `plugins/sec-overlay/commands/` | Slash commands the plugin installs, including `/sec-overlay:audit`; a plugin-root `commands/` file is install payload, so a change there bumps the plugin version |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness; links to the skill's `CLAUDE.md` for prerequisites and operating rules |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `plugins/plainspoken/` | plainspoken writing plugin: one skill (`skills/plainspoken/`), six slash commands, four read-only lens agents (`agents/`), the stdlib `lint.py`, tests, development-only evals, and `NOTICE.md` for the adapted MIT sources (clarity, work-humanizer, humanizer) |
| `plugins/readme-keeper/` | readme-keeper plugin: one skill (`skills/readme-keeper/`), four slash commands, the stdlib `check.py`, a CI workflow template, fixture-based tests, development-only evals, and `NOTICE.md` for the adapted MIT sources |
| `docs/` | Design specs (`docs/superpowers/specs/`) and implementation plans (`docs/superpowers/plans/`) for sec-overlay, plainspoken, and readme-keeper. `docs/README.md` lists each one with a summary. |
| `docs/decisions/` | Architecture decisions, one file each, in the Decision / Context / Alternatives / Reasoning / Trade-offs / Supersedes form. `docs/decisions/INDEX.md` lists them. |
| `docs/templates/plugin/` | New-plugin skeleton copied to `plugins/<name>/` and filled in per the root `CLAUDE.md` "New plugin" checklist |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `scripts/openwiki-history-digest.sh` | Writes the bounded `.openwiki-history.md` change digest an OpenWiki update run reads in place of `git log` |
| `LICENSE` | MIT license for the repository |
| `CHANGELOG.md` | Common Changelog for repo-level changes; plugin changes live in `plugins/<name>/CHANGELOG.md` |
| `SECURITY.md` | How to report vulnerabilities (GitHub private reporting) |
| `.github/workflows/dependency-review.yml` | GitHub Dependency review on pull requests |
| `.github/dependabot.yml` | Weekly Dependabot updates for Actions and pip |
| `.github/codeql/codeql-config.yml` | CodeQL path exclusions (test fixtures, caches) |
| `.github/workflows/sec-overlay-tests.yml` | sec-overlay pytest plus an offline detection-regression gate on pull requests |
| `.github/workflows/plainspoken-tests.yml` | plainspoken pytest (lint script and eval case schema) on pull requests that change `plugins/plainspoken/` |
| `.github/workflows/readme-keeper-tests.yml` | readme-keeper pytest (checker against fixture repos, eval case schema) on pull requests that change `plugins/readme-keeper/` |
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

MIT. See [LICENSE](LICENSE).
