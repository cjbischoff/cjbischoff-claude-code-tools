# scripts/

Holds repo-level tooling scripts. Plugin logic does not live here — it lives inside each plugin directory, because only the plugin directory is copied to the plugin cache on install.

**Naming convention:** `hooks/<hook-stage>-check.sh` for git hook scripts; bash with `set -euo pipefail`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| File | Purpose |
|------|---------|
| `hooks/pre-commit-check.sh` | Blocks commits to main; requires README.md, CHANGELOG.md, and folder README updates |
| `hooks/commit-msg-check.sh` | Enforces Conventional Commits message format with summary under 50 chars |
