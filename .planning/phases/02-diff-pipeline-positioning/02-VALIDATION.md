---
phase: 2
slug: diff-pipeline-positioning
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
validated: 2026-08-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` |
| **Quick run command** | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/<task test files> -q` |
| **Full suite command** | `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q` |
| **Estimated runtime** | ~2 seconds (phase files), ~27 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` pytest command
- **After every plan wave:** Run the plan's combined pytest command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DIFF-04 | — | N/A (checkpoint decision) | manual | — | — | ✅ |
| 02-01-02 | 01 | 1 | DIFF-01 | — | Artifacts dir created inside workspace only | unit | `uv run pytest tests/test_workspace.py -q` | ✅ | ✅ green |
| 02-01-03 | 01 | 1 | DIFF-01, DIFF-02, POS-03 | T-02 | Refs resolved to SHA before use (TOCTOU close) | tracer | `uv run pytest tests/test_review_tracer.py tests/test_diffscope.py tests/test_phase_gate.py -q` | ✅ | ✅ green |
| 02-02-01 | 02 | 2 | DIFF-01, DIFF-02 | T-02 | Invalid ref rejected, exit 2 contract | unit | `uv run pytest tests/test_diffscope.py tests/test_cli.py -q` | ✅ | ✅ green |
| 02-02-02 | 02 | 2 | DIFF-03 | — | Allowlist + default-exclude globs deterministic | unit | `uv run pytest tests/test_file_select.py -q` | ✅ | ✅ green |
| 02-02-03 | 02 | 2 | DIFF-03 | — | Closed exclusion-reason enum, size cap enforced | unit | `uv run pytest tests/test_file_select.py tests/test_diffscope.py -q` | ✅ | ✅ green |
| 02-03-01 | 03 | 3 | DIFF-04 | T-02-05 | Illegal manifest transitions raise; seal never lies | unit | `uv run pytest tests/test_review_coverage.py -q` | ✅ | ✅ green |
| 02-03-02 | 03 | 3 | POS-01 | — | Stdlib-only hunk parser, pure frozen dataclass | unit | `uv run pytest tests/test_diffhunks.py -q` | ✅ | ✅ green |
| 02-03-03 | 03 | 3 | DIFF-04, POS-01 | — | Manifest and parser hold under tracer path | integration | `uv run pytest tests/test_review_coverage.py tests/test_diffhunks.py tests/test_review_tracer.py -q` | ✅ | ✅ green |
| 02-04-01 | 04 | 4 | POS-02 | — | Exact consecutive matching, no fuzzy fallback | unit | `uv run pytest tests/test_positioning.py -q` | ✅ | ✅ green |
| 02-04-02 | 04 | 4 | POS-01, POS-02 | — | Four-rung ladder declines instead of guessing | unit | `uv run pytest tests/test_positioning.py -q` | ✅ | ✅ green |
| 02-04-03 | 04 | 4 | POS-02 | — | Every decline surfaced in report and ledger | unit | `uv run pytest tests/test_report.py tests/test_report_split.py -q` | ✅ | ✅ green |
| 02-05-01 | 05 | 5 | POS-03 | — | Review gate drops out-of-diff findings; audit path untouched | unit | `uv run pytest tests/test_phase_gate.py -q` | ✅ | ✅ green |
| 02-05-02 | 05 | 5 | POS-03 | — | Drops and declines both land in report and ledger | unit | `uv run pytest tests/test_report.py tests/test_report_split.py -q` | ✅ | ✅ green |
| 02-05-03 | 05 | 5 | DIFF-03, DIFF-04 | T-02-05 | Seal maps to exit codes 0/2/3; unfinished files named | unit | `uv run pytest tests/test_cli.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 work was needed;
pytest and the test package predate this phase.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Coverage manifest location and shape decision | DIFF-04 | Checkpoint decision gate (02-01-01), a human choice, not a code behavior | Confirm `artifacts/review_coverage.json` shape matches 02-01-PLAN.md Task 1 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none existed)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-17

---

## Validation Audit 2026-08-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 7 requirements (DIFF-01..04, POS-01..03) map to green tests. Phase test files
run 304 tests, all pass. The full suite shows 2 failures outside this phase's
scope: `test_bench.py::test_seed_corpus_is_valid` and
`test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`. Neither
touches a Phase 2 requirement or file.
