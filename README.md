# cjbischoff-claude-code-tools

Claude Code plugin marketplace.

## Directory Guide

Each folder below has its own README.md describing what it holds, its naming convention, and who writes to it. A commit that changes a tracked file inside one of these folders must update that folder's README.md in the same commit.

| Folder | Purpose |
|--------|---------|
| `plugins/` | One directory per distributed plugin |
| `scripts/` | Repo-level tooling (git hook scripts) |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest (v0.1.0) |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill instructions; logic lives in scripts/ |
| `plugins/sec-overlay/skills/sec-overlay/scripts/run.py` | Skill entry script (placeholder, no checks yet) |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `CHANGELOG.md` | Common Changelog; one entry per functionality commit |

## Commit governance

- Direct commits to `main` are blocked by a pre-commit hook.
- Branch naming: `<type>/<short-kebab-description>` (e.g. `feat/poc-reproducer-retry`).
- Commit messages: Conventional Commits, summary under 50 chars, body wrapped at 72.
- Every commit that changes tracked files must update `README.md` and add a `CHANGELOG.md` entry in the same commit — hooks enforce this.
- Run `prek install` once after cloning to activate the hooks.

## Status

- Scaffold complete; `claude plugin validate .` passed on 2026-08-11.
- `run.py` is a placeholder. Actual check logic is not implemented yet.

## Next steps

- Fill in real check logic in `plugins/sec-overlay/skills/sec-overlay/scripts/run.py`.
- Test local install: `/plugin marketplace add <this repo>` then `/plugin install sec-overlay@cjbischoff-claude-code-tools`.

## Decisions

- plugin.json declares no components; the default `skills/` directory scan handles discovery, and strict mode stays at its default (true).
- Version stays at 0.1.0 until the user approves a bump.
- Governance is enforced with prek local hooks rather than convention only, per user request for forced updates.
