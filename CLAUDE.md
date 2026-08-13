# cjbischoff-claude-code-tools

## Purpose

This workspace is a Claude Code plugin marketplace. It distributes personal plugins for Christopher Bischoff.

## Desired outcome

- A valid marketplace manifest at `.claude-plugin/marketplace.json`.
- One plugin per directory under `plugins/`.
- Each plugin passes `claude plugin validate .` before release.

## Branching and commits — required for every functionality change

Every change to a tracked file goes through a branch and a Conventional Commits message. Direct commits to `main` are not permitted, including by an agent. Hooks enforce these rules (`prek install` activates them).

- Direct pushes to `main` are also blocked on GitHub by a repository ruleset (pull request required; force-push and deletion blocked).
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
- Bump a plugin's `version` automatically, in the same commit that changes a **shipping file** in that plugin. A shipping file is any tracked file a user receives on install: `plugin.json`, `SKILL.md`, and everything under `skills/`, `agents/`, `helpers/`, and `references/`, including their folder `README.md` files. A plugin `CLAUDE.md` (operating manual) is **not** a shipping file; editing one alone does not bump.
- Derive the increment from the commit's Conventional Commit type with semver: a breaking change (`!` or `BREAKING CHANGE:`) bumps major, `feat` bumps minor, and every other type (`fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`) bumps patch. Edit `version` in the plugin's `.claude-plugin/plugin.json` in the same commit. `marketplace.json` does not pin versions, so it needs no edit.
