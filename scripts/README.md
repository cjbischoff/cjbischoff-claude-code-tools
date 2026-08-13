# scripts/

Holds repo-level tooling scripts. Plugin logic does not live here — it lives inside each plugin directory, because only the plugin directory is copied to the plugin cache on install.

**Naming convention:** `hooks/<hook-stage>-check.sh` for git hook scripts; bash with `set -euo pipefail`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| File | Purpose |
|------|---------|
| `hooks/pre-commit-check.sh` | Blocks commits to main; requires README.md, CHANGELOG.md, and folder README updates |
| `hooks/commit-msg-check.sh` | Enforces Conventional Commits message format with summary under 50 chars |
| `hooks/test-pre-commit-check.sh` | Bash invocation test for `pre-commit-check.sh`; cleans its temp repos via an EXIT trap; run with `bash scripts/hooks/test-pre-commit-check.sh` |

`pre-commit-check.sh` enforces a generalized per-folder rule: any staged file whose immediate directory has a tracked `README.md` requires that `README.md` to be staged too (folders with no tracked README are not gated). The `plugins`/`scripts`/`docs`/`.github` top-level check is kept alongside this as a stricter, redundant-but-harmless special case.
