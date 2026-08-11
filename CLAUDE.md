# cjbischoff-claude-code-tools

## Purpose

This workspace is a Claude Code plugin marketplace. It distributes personal plugins for Christopher Bischoff.

## Desired outcome

- A valid marketplace manifest at `.claude-plugin/marketplace.json`.
- One plugin per directory under `plugins/`.
- Each plugin passes `claude plugin validate .` before release.

## Conventions

- Plugin skills keep all executable logic under `skills/<name>/scripts/`, not in SKILL.md.
- Scripts must not reference paths outside their plugin directory. Only the plugin directory is copied to the plugin cache on install.
- Do not bump a plugin's `version` field without user approval. The user bumps it manually on each release so update detection works.
