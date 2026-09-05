# External Integrations

**Analysis Date:** 2026-09-05

## Plugin Marketplace Distribution

### `marketplace.json` Manifest

**File:** `.claude-plugin/marketplace.json`

This repo is a Claude Code plugin marketplace. It publishes one plugin to any Claude Code instance via:

```
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools
```

The marketplace manifest is the single entry point for all plugin discovery. It currently lists `sec-overlay` as the only plugin.

### Plugin Manifest

**File:** `plugins/sec-overlay/.claude-plugin/plugin.json`

The sec-overlay plugin declares no components — the default `skills/` directory scan handles discovery. Plugin version bumps automatically on shipping-file changes.

## External Security Tools (Binary Calls)

The sec-overlay harness calls these as subprocesses — they must be installed on the system:

| Integration | Type | Interface | Config |
|-------------|------|-----------|--------|
| **semgrep** | SAST engine | CLI subprocess (`semgrep --config <ruleset> <target>`) | User-provided rulesets; vendored at `helpers/rules/semgrep/` (gitignored) |
| **CodeQL** | Deep dataflow SAST | CLI subprocess (`codeql database create`, `codeql database analyze`) | `.github/codeql/codeql-config.yml`; query packs per language |
| **OSV (Open Source Vulnerabilities)** | Dependency vulnerability scanner | First-party `sec_overlay.sca` module | N/A — runs `osv` CLI under `sca.py` |
| **Secrets detection** | Hardcoded credential finder | First-party `sec_overlay.secrets` module | N/A — pattern-based detection in `secrets.py` |
| **Crypto policy check** | Approved algorithm enforcement | First-party `sec_overlay.crypto_policy` module | `references/approved-crypto-algorithms.yaml`, `references/approved-key-sources.yaml` |

## CI/CD Integrations

### GitHub Actions

- **sec-overlay-tests.yml** — Triggered on PRs; runs pytest + offline detection-regression gate
- **dependency-review.yml** — Triggered on PRs; GitHub-native dependency review
- **openwiki-update.yml** — Scheduled (weekly Mon 08:00 UTC) + manual dispatch; requires `ANTHROPIC_API_KEY` repo secret

### Dependabot

- **`.github/dependabot.yml`** — Weekly updates for GitHub Actions and pip packages

### CodeQL

- **`.github/codeql/codeql-config.yml`** — Path exclusions for test fixtures, caches. Runs on schedule.

### CodeRabbit

- **`.coderabbit.yaml`** — AI code review on PRs. Path rules, governance pre-merge checks (warning mode), tool selection. Incremental reviews pause after 2 commits (rate limit conservation). Manual re-review via `@coderabbitai review`.

## Git Hooks (prek)

**File:** `.pre-commit-config.yaml`

- **doc-update guard** — Ensures folder-level READMEs are updated when tracked files inside them change
- **commit message check** — Validates Conventional Commits format

Hook scripts at `scripts/hooks/` (commit-msg-check.sh, pre-commit-check.sh).

## OpenWiki Integration

- **Tool:** `openwiki` binary (local install or GitHub Actions)
- **Provider:** Anthropic (`OPENWIKI_PROVIDER=anthropic`, `OPENWIKI_MODEL_ID=claude-sonnet-5`)
- **Output:** Generated wiki under `openwiki/` directory
- **Read boundary:** `.openwikiignore` (separate from `.gitignore`)

## No External Databases, Auth Providers, or Webhooks

This project does not integrate with:
- No external databases (SQL, NoSQL, etc.)
- No authentication providers (OAuth, SSO, etc.)
- No webhook receivers or third-party API integrations
- No message queues or event streams
- No cloud provider SDKs
- No observability platforms (Datadog, Sentry, etc.)

All state is local to the filesystem (workspace directories, SARIF reports, JSON state files). The only network-dependent integrations are GitHub Actions CI/CD and OpenWiki (which calls Anthropic API).
