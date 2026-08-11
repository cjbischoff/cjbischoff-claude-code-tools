# plugins/

Holds one directory per Claude Code plugin distributed by this marketplace.

**Naming convention:** the directory name equals the plugin `name` in its `.claude-plugin/plugin.json` and in the marketplace manifest.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| Directory | Purpose |
|-----------|---------|
| `sec-overlay/` | Agentic security-audit harness; SAST + multi-agent investigation. Python core is the `sec_overlay` package under `skills/sec-overlay/helpers/`; run instructions resolve paths from `${CLAUDE_PLUGIN_ROOT}`. Test suite green after the rename; plugin manifest validates. The report and red-team renderers tolerate agent-authored `expected_signal` values in any shape (object, bare string, or null) via a shared helper. |
