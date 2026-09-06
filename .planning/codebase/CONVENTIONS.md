# Coding Conventions

**Analysis Date:** 2026-09-05

## Language & Style

### Python

- **Line length:** 100 characters (enforced by Ruff)
- **Target version:** Python 3.12 (enforced by Ruff `target-version = "py312"`)
- **Imports:** Absolute imports only (project convention, enforced in CLAUDE.md)
- **Formatters:** Ruff (linter + formatter)
- **Type checker:** `ty` (configured in `pyproject.toml` with `fixtures` and `rules` excluded)
- **Test frameworks:** pytest (all tests in `tests/` directory at package root)
- **No runtime dependencies:** The `sec_overlay` package is deliberately stdlib-only. No third-party imports in shipping code (dev dependencies only: pytest, ruff, ty).

### Shell (bash)

- Hook scripts at `scripts/hooks/` (commit-msg-check.sh, pre-commit-check.sh)
- OpenWiki history digest at `scripts/openwiki-history-digest.sh`
- Must not reference paths outside the script's own plugin directory (constraint from CLAUDE.md)

### Markdown

- Every directory in the Directory Guide has its own `README.md`
- CLAUDE.md files must stay under 200 lines
- AGENTS.md carries an OpenWiki-region block (`<!-- OPENWIKI:START -->` ... `<!-- OPENWIKI:END -->`)
- Skill SKILL.md is the authoritative reference for the audit pipeline

## Code Quality Constraints

| Rule | Detail | Enforcement |
|------|--------|-------------|
| Max function length | ≤100 lines | CODE_REVIEW.md convention |
| Max complexity | ≤8 (McCabe) | CODE_REVIEW.md convention |
| Imports | Absolute only | CLAUDE.md governance |
| Runtime deps | Zero (`dependencies = []`) | ADR-2026-08-04 |
| TDD | Failing test first | PROJECT.md convention |
| Git staging | Explicit path staging only (no `git add -A`, `git add .`, `git commit -a`, no `--no-verify`) | CLAUDE.md governance |

## Naming Conventions

- **Branch names:** `<type>/<short-kebab-description>` — e.g. `feat/poc-reproducer-retry`, `fix/hook-grace-period`
- **Commit types:** `feat` · `fix` · `chore` · `docs` · `style` · `refactor` · `perf` · `test`
- **Commit format:** `<type>(<optional-scope>): <imperative summary, under 50 chars>` — body wrapped at 72 chars explaining why, optional footer
- **Breaking changes:** `!` after type/scope plus `BREAKING CHANGE:` footer
- **Plugin version:** Semver derived from commit type (breaking → major, `feat` → minor, other → patch)
- **Test files:** `test_<module>.py` in `tests/` directories
- **Skills:** All executable logic under `skills/<name>/scripts/`, not in `SKILL.md`

## Error Handling Patterns

### Audit Pipeline

The sec-overlay pipeline uses an **exit-code-based** error signaling in the Python CLI:

- Exit 0: Clean run, `complete` coverage seal
- Exit 2: Invalid ref, unsafe rule file, or `--model` mismatch on resume
- Exit 3: One or more files could not be reviewed (fail open — partial results returned)

### Phase Adversary Pattern

Analysis phases end with an adversary gate:
1. Deterministic pre-check (`phase_gate.run_phase_checks`) rejects hard-unresolvable citations
2. Surviving claims run through an independent opus adversary
3. Only battle-tested claims flow forward

### Reflection Filter (fail open)

Review-mode reflection pass:
- A file with no recorded verdict → `ReflectionSkip` (keeps its findings, never silently drops)
- A file whose reflection pass raises → `ReflectionSkip` (fail open per D-15)
- Protected subject retractions are refused (hard-coded veto, never silent per D-14)

### Deterministic-first gating

- These always run before any LLM phase: `phase_gate.run_phase_checks`, `diagram_gate`, `ste_lint`
- A diagram gate violation halts the pipeline (producer re-scopes and regenerates once)
- Receipt-based confirmation: no finding reaches `confirmed` without a mechanical tool receipt

## Security Conventions

- **`PROTECTED_SUBJECT_CLASSES`** — Hardcoded veto in reflection filter; no verdict can override it
- **Tool-receipt bar** — Evidence bar never bypassed for Tier-2-only evidence
- **Workspace isolation** — Review/audit artifacts resolve under `<target>/.sec-overlay/<slug>/` sidecar, never at `<target>` itself
- **CodeQL trusted config** — Runs only on `codeql_config_trusted`; unsupported/untrusted configs skipped and logged
- **Secrets detection** — First-party module (`sec_overlay.secrets`); enforced by `.cursor/rules/` and pre-commit hooks

## Git & Commit Practices

- No direct commits to `main` (repository ruleset blocks pushes to main; requires PR)
- Pre-commit hooks: `prek install` activates them
- CodeRabbit review wait: Open PR, wait for CodeRabbit's walkthrough comment, then merge
- Branch must be deleted after merge
- Plugin version bumps happen in the same commit as shipping-file changes (not a separate version commit)

## Documentation Patterns

- **Changelog routing:** Plugin-only → plugin CHANGELOG.md; root-only → root CHANGELOG.md; mixed → both
- **Folder README rule:** A commit that changes a tracked file inside a folder with a README.md must update that README.md in the same commit
- **Exemption:** A commit staging only a plugin's own CHANGELOG.md is exempt from the folder README requirement
- **ADR format:** Decision / Context / Alternatives / Reasoning / Trade-offs / Supersedes
- **Markdown checkboxes:** Completed items use `✓`, not `[x]`
