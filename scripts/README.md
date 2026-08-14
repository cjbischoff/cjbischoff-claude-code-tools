# scripts/

Holds repo-level tooling scripts. Plugin logic does not live here — it lives inside each plugin directory, because only the plugin directory is copied to the plugin cache on install.

**Naming convention:** `hooks/<hook-stage>-check.sh` for git hook scripts, `<area>-<purpose>.sh` for everything else; bash with `set -euo pipefail`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review before merge.

## Contents

| File | Purpose |
|------|---------|
| `hooks/pre-commit-check.sh` | Blocks commits to main; routes changelog and README requirements by scope (see below) |
| `hooks/commit-msg-check.sh` | Enforces Conventional Commits and a summary under 50 chars |
| `hooks/test-pre-commit-check.sh` | Bash invocation test for `pre-commit-check.sh`; cleans its temp repos via an EXIT trap; run with `bash scripts/hooks/test-pre-commit-check.sh` |
| `hooks/test-commit-msg-check.sh` | Bash invocation test for `commit-msg-check.sh`; run with `bash scripts/hooks/test-commit-msg-check.sh` |
| `openwiki-history-digest.sh` | Writes `.openwiki-history.md`, the bounded commit-and-changed-file digest the OpenWiki update run reads in place of `git log` |

`openwiki-history-digest.sh` exists because the OpenWiki agent cannot reach git history: while `.openwikiignore` has active rules, OpenWiki restricts shell execution to `pwd`, `git rev-parse HEAD`, and deleting its own plan file. The digest is capped at 400 commits and 400 changed files (`OPENWIKI_HISTORY_MAX_COMMITS`, `OPENWIKI_HISTORY_MAX_FILES`), carries no patches, and excludes `openwiki/` itself. It requires `jq`.

`pre-commit-check.sh` routes changelog checks by scope: a commit touching only `plugins/<name>/` files requires that plugin's `CHANGELOG.md`; a commit touching anything else (including `plugins/README.md` itself) requires the root `README.md` and `CHANGELOG.md`. It also enforces a generalized per-folder rule: any staged file whose immediate directory has a tracked `README.md` requires that `README.md` to be staged too (folders with no tracked README are not gated) — this still applies inside `plugins/<name>/` and its subfolders, except a plugin-root `CHANGELOG.md` itself, which the per-folder rule exempts so a changelog-only plugin commit can pass. The `scripts`/`docs` top-level Directory Guide check is kept alongside this as a stricter, redundant-but-harmless special case; `plugins` is excluded from that check because the routing and per-folder rules above already cover it. `.github/` has no folder README: GitHub would display `.github/README.md` as the repository homepage instead of the root README.
