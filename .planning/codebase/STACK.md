# Technology Stack

**Analysis Date:** 2026-09-05

## Languages

| Language | Where | Purpose |
|----------|-------|---------|
| Python 3.12+ | `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` | Deterministic security-audit core (stdlib-only) |
| Python (test) | `plugins/sec-overlay/skills/sec-overlay/helpers/tests/` | ~150 test files across pytest |
| Shell (bash) | `scripts/hooks/`, `.github/workflows/` | Git hooks, CI workflows, OpenWiki history digest |
| YAML | `.github/workflows/`, `.github/dependabot.yml`, `.pre-commit-config.yaml` | CI/CD, dependency management, pre-commit config |
| JSON | `.claude-plugin/marketplace.json`, `plugins/**/plugin.json`, references | Plugin manifests, scan profiles, finding schemas |
| Markdown | `docs/`, `openwiki/`, plugin `SKILL.md`, `CLAUDE.md` | Documentation, wiki, skill instructions |
| TOML | `pyproject.toml` | Python packaging, Ruff config, pytest config |
| Dockerfile | N/A in this repo | N/A — no containers |
| JavaScript | N/A | N/A — no UI/JS runtime |

## Runtime & Package Management

- **Python runtime:** CPython >=3.12, no third-party runtime dependencies (`dependencies = []` in `pyproject.toml`)
- **Package manager:** `uv` (uv is the tool; `uv.lock` is the lockfile)
- **Build backend:** Hatchling (`hatchling.build`)
- **MSRV:** Python 3.12 floor (D-01 constraints glob matching)

## Core Framework & Libraries

### Zero runtime dependencies

The `sec_overlay` package is deliberately **stdlib-only**. No requests, no Flask/FastAPI, no ORM, no async framework. This is a hard constraint enforced by ADR-2026-08-04.

### Dev-only dependencies

- `pytest >=8` — test runner
- `ruff >=0.6` — linter / formatter
- `ty >=0.0.1a1` — type checker

## External Tools (Called as Binaries)

The sec-overlay harness calls these tool binaries directly — they are NOT Python dependencies:

| Tool | Purpose | Config Location |
|------|---------|-----------------|
| **semgrep** | SAST engine for pattern-based vulnerability scanning | Rulesets at user-provided paths; vendored clone at `helpers/rules/semgrep/` (gitignored) |
| **CodeQL** | Deep dataflow-based security analysis | `.github/codeql/codeql-config.yml` (repo-level); query packs per language (`codeql pack download codeql/<lang>-queries`) |
| **sca** (osv, secrets, crypto fact collectors) | First-party OSV/CVE, secrets detection, crypto policy checks | `helpers/sec_overlay/sca.py` |
| **prek** | Pre-commit hook runner | `.pre-commit-config.yaml` |
| **claude** (plugin validate) | Plugin manifest validation | `.claude-plugin/` manifests |
| **openwiki** | AI-generated wiki builder | `openwiki/INSTRUCTIONS.md`, `.openwikiignore` |
| **git** | Version control, SHA pinning, blame annotations | N/A |

## CI/CD

- **GitHub Actions** — `.github/workflows/`
  - `sec-overlay-tests.yml` — pytest + offline detection-regression gate on PRs
  - `dependency-review.yml` — GitHub Dependency Review on PRs
  - `openwiki-update.yml` — Weekly (Mon 08:00 UTC) + manual dispatch OpenWiki refresh
- **Dependabot** — `.github/dependabot.yml` — Weekly updates for Actions and pip
- **CodeQL** — `.github/codeql/codeql-config.yml` — Path exclusions for test fixtures and caches
- **CodeRabbit** — `.coderabbit.yaml` — PR review with path rules and governance pre-merge checks

## AI/LLM Model Stack

The sec-overlay audit pipeline uses Claude Code subagents with specific model tiers:

| Model Tier | Usage |
|------------|-------|
| **claude-sonnet** (primary work) | Recon, architecture, threat-model, investigate, critic, review-file, review-filter, redteam, context-ingest |
| **claude-opus** (adversarial gates) | Phase adversary, validate (FP ladder), redteam-adversary, patch |
| **claude-haiku** (cheap tasks) | Pure-transcription implementer work, secondary low-importance passes |

## Configuration & Governance

- **`.coderabbit.yaml`** — 15KB PR review config with path rules and governance checks
- **`.pre-commit-config.yaml`** — prek hooks (doc-update guard + commit message check)
- **`.claude-plugin/marketplace.json`** — Marketplace manifest listing all plugins
- **`.env.example`** — Local OpenWiki environment template
- **`.openwikiignore`** — Read boundary paths for OpenWiki (separate from `.gitignore`)
- **`.cursor/rules/codeguard-1-hardcoded-credentials.mdc`** — Always-on Cursor rule against secrets

## Versioning

- Plugin versions follow semver, bumped automatically on shipping-file changes
- Bump rule: breaking change (`!`) → major, `feat` → minor, other types → patch
- Plugin version lives in `plugins/<name>/.claude-plugin/plugin.json`
- Root-level changes tracked in root `CHANGELOG.md`; plugin changes in `plugins/<name>/CHANGELOG.md`
- sec-overlay currently at version **1.69.15** (from PROJECT.md) — but plugin.json shows **1.122.0** (likely a more current release)
