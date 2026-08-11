# cjbischoff-claude-code-tools

## Purpose

This workspace is a Claude Code plugin marketplace. It distributes personal plugins for Christopher Bischoff.

## Desired outcome

- A valid marketplace manifest at `.claude-plugin/marketplace.json`.
- One plugin per directory under `plugins/`.
- Each plugin passes `claude plugin validate .` before release.

## Branching and commits — required for every functionality change

Every change to a tracked file goes through a branch and a Conventional Commits message. Direct commits to `main` are not permitted, including by an agent. Hooks enforce these rules (`prek install` activates them).

- **Branch naming:** `<type>/<short-kebab-description>`, e.g. `feat/poc-reproducer-retry`, `fix/hook-grace-period`.
- **Commit types:** `feat` · `fix` · `chore` · `docs` · `style` · `refactor` · `perf` · `test`.
- **Message format:** `<type>(<optional-scope>): <imperative summary, under 50 chars>`, optional body wrapped at 72 chars explaining why, optional footer.
- **Breaking changes** to a plugin's contract or a script's CLI: `!` after the type/scope plus a `BREAKING CHANGE:` footer.
- Merge the branch into `main` when the change is verified; delete the branch after merge.
- Every commit that changes tracked files must update `README.md` and add a `CHANGELOG.md` entry (Common Changelog format) in the same commit.
- Every folder in the README.md Directory Guide has its own `README.md`. A commit that changes a tracked file inside one of those folders must update that folder's README.md in the same commit.

## Conventions

- Plugin skills keep all executable logic under `skills/<name>/scripts/`, not in SKILL.md.
- Scripts must not reference paths outside their plugin directory. Only the plugin directory is copied to the plugin cache on install.
- Do not bump a plugin's `version` field without user approval. The user bumps it manually on each release so update detection works.
