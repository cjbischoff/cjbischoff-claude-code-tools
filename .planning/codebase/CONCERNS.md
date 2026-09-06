# Technical Debt & Concerns

**Analysis Date:** 2026-09-05

## Current State

Per PROJECT.md (2026-08-22): **Zero known tech debt.** All six Phase 06 items were cleared in v5.1 (PRs #32, #33). Zero deferred items, zero open blockers. The project is awaiting the next milestone definition.

## Previously Cleared Items (v5.1, 2026-08-22)

| Item | Type | Resolution |
|------|------|------------|
| ruff `I001` in `test_cli.py:778` | Lint error | Fixed in LINT-01 (PR #32) |
| `test_rule_glob.py:231` — missing `--workspace` assertion | Test gap | Added in TEST-01 (PR #32) |
| WR-01 tests don't prove guard runs before git | Test gap | Fixed in TEST-02 (PR #32) |
| CLI-legend block not audited for further misorderings | Doc gap | Audited in DOC-01 (PR #33) |
| Pipeline diagram misses `selfscore`/`artifact-gate`/`artifact-review` | Doc gap | Fixed in DOC-02 (PR #33) |
| `CLAUDE.md` phase order list missing `selfscore` entry | Doc gap | Fixed in DOC-03 (PR #33) |
| Ingest WARNING (ING-01): kb-redesign design doc/upstream spec | Conflict | Closed — design doc affirmed as authority (PR #33) |

## Deferred Items (Next Milestone Candidates)

### GROW-01 — Second Plugin Onboarding
- Deferred to v2: 2026-08-16 and 2026-08-22 (twice)
- Template exists at `docs/templates/plugin/` with `{{PLACEHOLDER}}` markers
- No candidate plugin named
- **Risk:** Stale template — markers may drift from actual `marketplace.json`/`plugin.json` formats

### GROW-02 — Automated Plugin Validation Gate
- Deferred to v2: 2026-08-16 and 2026-08-22
- Run `claude plugin validate .` as an automated prek hook or CI gate
- Currently a manual step in the release process
- **Risk:** Manual step can be forgotten; a broken plugin manifest ships unnoticed

## Architectural Concerns

### Size & Complexity
- **sec-overlay SKILL.md** is 736 lines — hard to navigate, cross-references many sub-components
- **helpers/tests/README.md** is 112KB — likely auto-generated or excessively verbose
- **helpers/sec_overlay/README.md** is 113KB — same concern
- **plugin CHANGELOG.md** is 145KB — very long; may benefit from truncation or summary
- **Root CLAUDE.md** is under 200 lines (good — hard limit enforced)
- **Root README.md** is comprehensive at 9.4KB (reasonable for a marketplace README)

### Frozen Contracts
- `models.py` and `evidence.py` are **frozen** — byte-mirrored by a parallel Go port
- `fingerprint()` identity never changes
- Any bug in these files requires coordination with the Go port; cannot be fixed independently
- This is a deliberate constraint but carries risk if a bug is discovered in the frozen interface

### Dependency on External CLI Tools
- The sec-overlay audit pipeline depends on external binaries (`semgrep`, `codeql`, `osv`) being installed on the system
- `preflight.py` can skip missing backends, but this silently reduces coverage
- CodeQL requires per-language query packs to be downloaded separately — a missing pack silently drops dataflow coverage for that language

### Agent Prompt Maintenance
- 20+ agent prompt files in `agents/` — all reference specific model tiers (sonnet, opus)
- If Anthropic deprecates/changes model behavior, all prompts may need updating
- The adversarial validation pattern doubles LLM costs (two models per phase)

## Security Concerns

### CodeQL Trusted Config
- CodeQL runs only on a `codeql_config_trusted` — unsupported configs are silently skipped
- Risk: user thinks CodeQL is scanning but it's logged in a `skipped` list they may not read
- **Mitigation:** Skipped backends are logged in `prefilter.py` output with reasons

### Workspace Isolation
- Review/audit artifacts resolve under `<target>/.sec-overlay/<slug>/` sidecar
- The sidecar slug derives from the workspace path — different spellings of the same path create orphan sidecars
- **Mitigation:** CLAUDE.md warns about this and requires identical --workspace values across all invocations

### Reflection Filter Fail-Open
- `PROTECTED_SUBJECT_CLASSES` is hardcoded — no human override mechanism if it needs updating
- Fail-open (ReflectionSkip keeps all findings) may hide bugs in the reflection system — user never sees a failure, they just get more findings

## Performance Concerns

### Large-Codebase Scalability
- The full audit pipeline runs 14+ phases, many with LLM subagents
- The `--concurrency` cap (default 8, max 128) limits parallel dispatch, but a large codebase (thousands of files) will still require significant LLM token spend
- Phase 5 E2E verification ran on a 515-file coverage denominator — larger targets may increase cost linearly

### Token Costs
- The adversary pattern (sonnet producer → opus adversary) doubles every analysis phase's cost
- `scan_options.adversary_depth = gate-by-exception` reduces this but requires careful judgment
- No USD cost estimation is shown by default — it's an opt-in estimate call

## Integration Risks

### OpenWiki CI Dependency
- `.github/workflows/openwiki-update.yml` requires `ANTHROPIC_API_KEY` repository secret
- If the secret expires or is misconfigured, the wiki falls out of date silently
- Local `--update` requires environment variables — easy to forget `OPENWIKI_TELEMETRY_DISABLED` and `DO_NOT_TRACK`

### CodeRabbit Rate Limits
- Incremental reviews pause after 2 reviewed commits
- Manual review needed via `@coderabbitai review` for additional passes
- `abort_on_close: false` means reviews finish after PR merge — findings arrive after the fact

## Documentation Drift Risk
- OpenWiki wiki is generated from source — but only refreshed weekly or on manual dispatch
- If source changes significantly between refreshes, the wiki is stale
- `.openwikiignore` must be kept in sync with source changes or content is missed
