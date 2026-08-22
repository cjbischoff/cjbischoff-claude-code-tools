---
phase: 1
slug: baseline-health-verification
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract, reconstructed retroactively from Phase 1 artifacts
> (01-01/02/03 PLAN and SUMMARY files, 01-VERIFICATION.md) on 2026-08-19.

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
`cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`.

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command from the map below.
- **After every plan wave:** Run the full suite plus the static gates.
- **Before `/gsd-verify-work`:** Full suite green (environmental exceptions excluded), plus `claude plugin validate .` from the repo root and from `plugins/sec-overlay/`.
- **Max feedback latency:** 45 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | VAL-01 | — | Marketplace manifest and every registered plugin validate cleanly | smoke | `claude plugin validate .` (repo root, then `plugins/sec-overlay/`) | ✅ | ✅ green |
| 01-01-02 | 01 | 1 | VAL-02 | — | Baseline receipts record real exit codes; no fabricated green | receipts | `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers pytest -q` | ✅ | ⚠️ 2 environmental (see Manual-Only) |
| 01-01-03 | 01 | 1 | VAL-03 | — | Governance hooks pass across the tree | hooks | `prek run --all-files` (repo root) | ✅ | ✅ green |
| 01-02-01 | 02 | 2 | VAL-02 | — | `ruff check` exits 0 with zero unaddressed findings | static | `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ruff check sec_overlay/ bench/ tests/` | ✅ | ✅ green |
| 01-02-02 | 02 | 2 | VAL-02 | — | `ty check` exits 0 (161 baseline diagnostics fixed) | static | `uv run --locked --directory plugins/sec-overlay/skills/sec-overlay/helpers ty check` | ✅ | ✅ green |
| 01-02-02 | 02 | 2 | VAL-02 | — | Non-dict subagent stage output returns a validation error, never raises (`_adapt_dict` / `_adapt_optional_dict`) | unit | `uv run pytest tests/test_stage_validate.py -x -q` (helpers dir) | ✅ | ✅ green |
| 01-03-01 | 03 | 3 | VAL-01, VAL-02, VAL-03 | — | Final receipts captured after last fix; baseline reds preserved | receipts | All six gate commands, re-run post-fix | ✅ | ✅ green (5/6; pytest carries the 2 environmental failures) |
| 01-03-02 | 03 | 3 | VAL-02 | — | Frozen contract untouched; every fix commit governance-compliant | integrity | `git diff <phase-start>..HEAD -- sec_overlay/models.py sec_overlay/evidence.py` (empty) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 stubs were needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bench corpus tests pass (`test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` and one sibling) | VAL-02 | The bench corpus and `rules/semgrep/` data are gitignored by deliberate choice; the tests cannot pass without local data | Restore the local corpus data, then run the full suite; expect 0 failures |
| `conventional-commit-msg` hook enforces commit format | VAL-03 | The hook declares `stages: [commit-msg]` and structurally cannot fire under `prek run --all-files` | Make a test commit with a malformed message; expect the hook to reject it |
| Remediation-route selection (proceed-as-triaged vs escalate-frozen) | VAL-01/02/03 | Governance judgment about the frozen-contract boundary; not classifiable by a test | Maintainer reviews the Triage Ledger in 01-VERIFICATION.md and selects a route |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or documented manual-only rationale
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none needed)
- [x] No watch-mode flags
- [x] Feedback latency < 45s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-19

---

## Validation Audit 2026-08-19

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

Gap resolved: `_adapt_dict` / `_adapt_optional_dict` rejection paths in
`sec_overlay/stage_validate.py` (added by Plan 02, previously untested). Three tests
added to `tests/test_stage_validate.py`; the file now runs 11 tests green, and
`ruff check` and `ty check` both pass.
