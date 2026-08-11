# cjbischoff-claude-code-tools

Claude Code plugin marketplace.

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest (v0.1.0) |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill instructions; logic lives in scripts/ |
| `plugins/sec-overlay/skills/sec-overlay/scripts/run.py` | Skill entry script (placeholder, no checks yet) |

## Status

- Scaffold complete. Validation status: see latest commit notes.
- `run.py` is a placeholder. Actual check logic is not implemented yet.

## Next steps

- Fill in real check logic in `scripts/run.py`.
- Test local install: `/plugin marketplace add <this repo>` then `/plugin install sec-overlay@cjbischoff-claude-code-tools`.

## Decisions

- plugin.json declares no components; the default `skills/` directory scan handles discovery, and strict mode stays at its default (true).
- Version stays at 0.1.0 until the user approves a bump.
