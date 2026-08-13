# scripts/

Holds repo-level tooling scripts. Plugin logic does not live here — it lives inside each plugin directory, because only the plugin directory is copied to the plugin cache on install.

**Naming convention:** `hooks/<subject>-check.sh`, where `<subject>` is the git hook stage for a hook script; bash with `set -euo pipefail`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| File | Purpose |
|------|---------|
| `hooks/pre-commit-check.sh` | Blocks commits to main; requires README.md, CHANGELOG.md, and folder README updates |
| `hooks/commit-msg-check.sh` | Enforces Conventional Commits; strips Cursor `Co-authored-by` trailers |
| `hooks/pr-body-check.sh` | Rejects agent attribution on a footer or trailer line of a pull request body; reads the body from a file argument or stdin |
| `hooks/test-pre-commit-check.sh` | Bash invocation test for `pre-commit-check.sh`; cleans its temp repos via an EXIT trap; run with `bash scripts/hooks/test-pre-commit-check.sh` |
| `hooks/test-commit-msg-check.sh` | Bash invocation test for `commit-msg-check.sh`; run with `bash scripts/hooks/test-commit-msg-check.sh` |
| `hooks/test-pr-body-check.sh` | Bash invocation test for `pr-body-check.sh`; run with `bash scripts/hooks/test-pr-body-check.sh` |

`pr-body-check.sh` is not a git hook — no git stage sees a pull request body. The `.github/workflows/pr-attribution.yml` workflow runs it on every pull request against `main`, and it can be run locally against an open pull request:

```bash
gh pr view <n> --json body -q .body | bash scripts/hooks/pr-body-check.sh
```

`pre-commit-check.sh` enforces a generalized per-folder rule: any staged file whose immediate directory has a tracked `README.md` requires that `README.md` to be staged too (folders with no tracked README are not gated). The `plugins`/`scripts`/`docs` top-level check is kept alongside this as a stricter, redundant-but-harmless special case. `.github/` has no folder README: GitHub would display `.github/README.md` as the repository homepage instead of the root README.
