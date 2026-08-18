---
phase: 3
slug: rule-matching-review-modes
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (stdlib-only project; no plugins beyond pytest itself) |
| **Config file** | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` |
| **Quick run command** | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/<file> -x -q` |
| **Full suite command** | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q` |
| **Estimated runtime** | ~10 seconds quick, ~45 seconds full |

Every command in this document runs from the repo root and changes into the helpers
directory first. `uv run` is required — the suite is not installed into the ambient
interpreter.

Static gates run beside the suite and share its sampling rate:
`cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run ruff check sec_overlay/ tests/ && uv run ty check`.

---

## Sampling Rate

- **After every task commit:** Run that task's `<automated>` command from the map below.
- **After every plan wave:** Run `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q` plus `uv run ruff check sec_overlay/ tests/ && uv run ty check`.
- **Before `/gsd-verify-work`:** Full suite green, plus `claude plugin validate .` from the repo root.
- **Max feedback latency:** 45 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | RULE-01, RULE-05, REV-02 | T-03-01, T-03-04, T-03-08 | Docs dir resolves from `__file__`, not CWD; reflection retracts only and fails open per file | integration (tracer) | `uv run pytest tests/test_review_tracer.py -x -q` | ✅ | ⬜ pending |
| 03-01-01 | 01 | 1 | RULE-01, RULE-05, REV-02 | — | N/A (static gates) | static | `uv run ruff check sec_overlay/ tests/ && uv run ty check` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | RULE-05 | T-03-SC | No dependency added; governance staged in the same commit | suite + hooks | `uv run pytest -q` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | RULE-05 | T-03-SC | Governance hooks accept the doc and version bump | hooks | `prek run --files plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | RULE-02 | T-03-09 | Global layer cannot widen resolution past the per-path fallthrough order | unit | `uv run pytest tests/test_rule_glob.py -k "layer or merge or order or idempot" -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | RULE-04 | T-03-09 | `--exclude` appends to, never replaces, the resolved exclude list | unit | `uv run pytest tests/test_rule_glob.py -k "filter or exclude" -x -q` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | RULE-04 | — | CLI surface parses without executing a run | smoke | `uv run python -m sec_overlay.cli review --help` | ✅ | ⬜ pending |
| 03-02-03 | 02 | 2 | RULE-03 | T-03-01, T-03-02, T-03-07 | Symlink resolve, repo-root boundary, extension allowlist, 512 KB cap — all four before read | unit (security) | `uv run pytest tests/test_rule_glob.py -k safety -x -q` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | RULE-02, RULE-03, RULE-04 | T-03-01, T-03-02 | Full module green after the safety gate lands | unit | `uv run pytest tests/test_rule_glob.py -q` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | RULE-05 | T-03-10, T-03-11 | Every map value resolves to a non-empty doc; no orphan doc or orphan entry | unit | `uv run pytest tests/test_rule_docs.py -q` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | RULE-05 | T-03-03 | No doc instructs the agent to set a status or severity | conformance | `uv run pytest tests/test_rule_docs.py -q` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | RULE-05 | T-03-11 | Index matches the shipped docs | suite | `uv run pytest -q` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | RULE-05 | — | Governance hooks accept the doc index and version bump | hooks | `prek run --files plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_docs/README.md plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json` | ✅ | ⬜ pending |
| 03-04-01 | 04 | 4 | REV-01 | T-03-12 | Disposition field placement decided before code, keeping `models.py` frozen | manual (checkpoint:decision) | — see Manual-Only Verifications | N/A | ⬜ pending |
| 03-04-02 | 04 | 4 | REV-01 | T-03-06, T-03-12, T-03-14 | Bypass limited to the five-class allowlist; gates C/D/E unconditional; unknown profile raises | unit | `uv run pytest tests/test_review_profiles.py -x -q` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 4 | REV-01 | — | N/A (static gates) | static | `uv run ruff check sec_overlay/ tests/ && uv run ty check` | ✅ | ⬜ pending |
| 03-04-03 | 04 | 4 | REV-01 | T-03-13, T-03-14 | Security profile reproduces pre-phase gate behavior exactly on the same fixture | regression | `uv run pytest tests/test_review_profiles.py -q` | ❌ W0 | ⬜ pending |
| 03-04-03 | 04 | 4 | REV-01 | T-03-14 | Whole suite green after the profile branch lands | suite | `uv run pytest -q` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 5 | REV-02 | T-03-04, T-03-15, T-03-16 | Retract-only; protected subjects vetoed mechanically; unknown id ignored | unit | `uv run pytest tests/test_reflection.py -x -q` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 5 | REV-02 | — | N/A (static gates) | static | `uv run ruff check sec_overlay/ tests/ && uv run ty check` | ✅ | ⬜ pending |
| 03-05-02 | 05 | 5 | REV-02 | T-03-05, T-03-08 | Every retraction and every fail-open skip is ledgered; zero case renders explicitly | unit | `uv run pytest tests/test_reflection.py -k "ledger or skip or zero" -q` | ❌ W0 | ⬜ pending |
| 03-05-02 | 05 | 5 | REV-02 | T-03-05 | Module green after the ledger and dispatch land | unit | `uv run pytest tests/test_reflection.py -q` | ❌ W0 | ⬜ pending |
| 03-05-03 | 05 | 5 | REV-03 | T-03-04 | A general-defect finding without a Tier-1 receipt never reaches `confirmed` | unit (security) | `uv run pytest tests/test_findings_gate.py -k general_defect -x -q` | ✅ | ⬜ pending |
| 03-05-03 | 05 | 5 | REV-03 | T-03-04 | Receipt gate remains sole authority on `confirmed` | unit | `uv run pytest tests/test_findings_gate.py -q` | ✅ | ⬜ pending |
| 03-06-01 | 06 | 6 | RULE-01, REV-02 | T-03-17, T-03-18 | Evidence stamped in code as `llm-claimed:review-agent`; model-supplied sources dropped; out-of-file comments discarded | unit (security) | `uv run pytest tests/test_review_agent.py -x -q` | ❌ W0 | ⬜ pending |
| 03-06-01 | 06 | 6 | RULE-01, REV-02 | — | N/A (static gates) | static | `uv run ruff check sec_overlay/ tests/ && uv run ty check` | ✅ | ⬜ pending |
| 03-06-02 | 06 | 6 | RULE-01 | T-03-17 | Agent prompt renders with no unfilled token and imports the shared anti-manipulation constants | contract | `uv run pytest tests/test_contracts.py tests/test_wiring.py -q` | ✅ | ⬜ pending |
| 03-06-03 | 06 | 6 | RULE-01, REV-01, REV-02 | T-03-19, T-03-21, T-03-22 | Missing, stale, and unparseable sources each ledger a skip and never abort the run | integration | `uv run pytest tests/test_review_live.py -x -q` | ❌ W0 | ⬜ pending |
| 03-06-03 | 06 | 6 | REV-01 | T-03-06 | `--profile general` reports a finding `--profile security` drops, on one real fixture diff | integration (criterion 4) | `uv run pytest tests/test_review_live.py -k "profile or split" -q` | ❌ W0 | ⬜ pending |
| 03-06-03 | 06 | 6 | RULE-01, REV-01, REV-02 | T-03-SC | Whole suite green with the live finding source wired | suite | `uv run pytest -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*File Exists: ✅ = the test file exists today · ❌ W0 = the plan's own first task creates it (see Wave 0 Requirements).*

---

## Wave 0 Requirements

No separate Wave 0 plan is needed. pytest, ruff, and ty are already configured and the
existing suite is green, so the framework rung is covered. Each missing test file is created
by the first task of the plan that needs it, under TDD — the failing test is written before
the module it covers.

- [ ] `tests/test_rule_glob.py` — created by 03-02 Task 1 (RULE-02, RULE-03, RULE-04)
- [ ] `tests/test_rule_docs.py` — created by 03-03 Task 1 (RULE-05)
- [ ] `tests/test_review_profiles.py` — created by 03-04 Task 2 (REV-01)
- [ ] `tests/test_reflection.py` — created by 03-05 Task 1 (REV-02)
- [ ] `tests/test_review_agent.py` — created by 03-06 Task 1 (RULE-01, REV-02)
- [ ] `tests/test_review_live.py` — created by 03-06 Task 3 (RULE-01, REV-01, REV-02)

Already present: `tests/test_review_tracer.py`, `tests/test_findings_gate.py`,
`tests/test_review_coverage.py`, `tests/test_contracts.py`, `tests/test_wiring.py`, and
`tests/conftest.py` with the shared fixture-repo helpers plans 03-04 and 03-06 reuse.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Placement of the general-defect class and the non-receipt disposition field | REV-01, REV-03 | A `checkpoint:decision` (03-04 Task 1) resolving RESEARCH Open Question 1; a naming choice constrained by the frozen `models.py` contract cannot be decided by a test | Read the options in 03-04 Task 1, confirm `models.py` and `evidence.py` are untouched by every option, then reply with the selected option id. Everything downstream of the choice is covered by `tests/test_review_profiles.py` and `tests/test_findings_gate.py`. |

Every other phase behavior has an automated command in the map above.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
