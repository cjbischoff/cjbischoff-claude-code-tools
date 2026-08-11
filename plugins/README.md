# plugins/

Holds one directory per Claude Code plugin distributed by this marketplace.

**Naming convention:** the directory name equals the plugin `name` in its `.claude-plugin/plugin.json` and in the marketplace manifest.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| Directory | Purpose |
|-----------|---------|
| `sec-overlay/` | Security overlay skill; scripted security checks on code changes. Logic lives in `skills/sec-overlay/scripts/`. |
