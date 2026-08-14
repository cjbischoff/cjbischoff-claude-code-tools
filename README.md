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
| `.openwikiignore` | Paths OpenWiki must not read during wiki init/update (separate from `.gitignore`) |
| `openwiki/INSTRUCTIONS.md` | User-authored wiki brief for init and CI `--update`; OpenWiki does not rewrite it |
| `.env.example` | Local OpenWiki provider, model, and telemetry-off settings (no secrets) |
| `.github/workflows/openwiki-update.yml` | Weekly/manual OpenWiki `--update` that opens a PR using Anthropic Sonnet 5 |
| `openwiki/` | Generated marketplace wiki (quickstart, marketplace, governance, sec-overlay, operations); do not hand-edit except `INSTRUCTIONS.md` |
| `AGENTS.md` | OpenWiki pointer block for coding agents; the generated `<!-- OPENWIKI:START -->` region only |

## Contributing

All changes go through feature branches with Conventional Commits. See [CLAUDE.md](CLAUDE.md) for detailed branching, commit, and code review processes.

## License

MIT
