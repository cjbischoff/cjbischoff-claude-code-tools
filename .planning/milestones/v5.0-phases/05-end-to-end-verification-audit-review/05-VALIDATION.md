---
phase: 5
slug: end-to-end-verification-audit-review
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-20
validated: 2026-08-21
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_review_live.py tests/test_evidence.py tests/test_cvss.py tests/test_coverage_ledger.py -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers/`) |
| **Full suite command** | `uv run pytest -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers/`) |
| **Estimated runtime** | Quick subset ~2 seconds; full suite ~2 minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command.
- **After every plan wave:** Run the full suite command.
- **Before `/gsd-verify-work`:** The full suite must be green.
- **Max feedback latency:** 120 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | AUD-06 | — | Git subprocess runner scopes to `--root`, not process cwd | unit | `uv run pytest tests/test_review_live.py -q` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | AUD-06 | — | Profile split: security kept-set is a subset of general kept-set | unit | `uv run pytest tests/test_review_live.py -q` | ✅ | ✅ green |
| 05-02-01 | 02 | 1 | AUD-01 | — | Preflight reports vendored semgrep ruleset OK | integration | `uv run python -m sec_overlay.preflight` (exit 0) | ✅ | ✅ green |
| 05-02-02 | 02 | 1 | AUD-01 | — | All pipeline stages complete; working-tree fence holds | integration | `uv run pytest tests/test_cli_e2e.py -q` | ✅ | ✅ green |
| 05-03-01 | 03 | 1 | AUD-02 | — | No finding reaches `confirmed` on Tier-2-only evidence | unit | `uv run pytest tests/test_evidence.py tests/test_findings_gate.py tests/test_contracts.py -q` | ✅ | ✅ green |
| 05-03-02 | 03 | 1 | AUD-03 | — | `needs-deployment-testing` findings carry a positive `risk_score` and stay visible in the report headline | unit | `uv run pytest tests/test_redteam.py tests/test_report.py -q` | ✅ | ✅ green |
| 05-04-01 | 04 | 1 | AUD-04 | — | Deterministic gates pass; every CVSS vector is v4.0-only | unit | `uv run pytest tests/test_cvss.py -q` | ✅ | ✅ green |
| 05-04-02 | 04 | 1 | AUD-05 | — | Coverage ledger validates; explicit denominator; no unlogged zero-finding surface classes | unit | `uv run pytest tests/test_coverage_ledger.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

All automated commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.
Audit result 2026-08-21: 201 tests pass across the 9 mapped test files.

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 work was needed; the plugin ships a 113-file pytest suite that already exercises every automatable AUD behavior.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full `review` run on a real pinned external diff, both profiles | AUD-06 | Requires the external `mando` repo at pinned SHAs; runs outside this repo and its receipts need D-07 sanitization | Follow `05-01-review-security-receipt.md` and `05-01-review-general-receipt.md` |
| Full `/sec-overlay:audit` run on a pinned external target head | AUD-01 | Requires the external target repo, LLM reviewer dispatch, and the D-09-retained sidecar | Follow `05-02-audit-run-receipt.md` |
| Finding-integrity readback against the live retained sidecar | AUD-02, AUD-03 | Reads the D-09-retained external sidecar; the shipped validator has a write side effect, so it must be redirected to a scratch copy | Follow `05-03-finding-integrity-receipt.md` |
| Artifact and coverage readback against the live retained sidecar | AUD-04, AUD-05 | Reads the D-09-retained external sidecar; evidence map paths resolve only in that sidecar | Follow `05-04-artifact-coverage-receipt.md` |
| D-07 sanitization sign-off on committed receipts | AUD-01..AUD-06 | Judgment call on what counts as a leaked target-repo path or finding body; requires a human gate before commit | Run the receipt's `rg` sanitization gate, then review the diff by hand |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none existed)
- [x] No watch-mode flags
- [x] Feedback latency < 120s (quick subset runs in ~2s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-21

---

## Validation Audit 2026-08-21

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Retroactive audit (`/gsd-validate-phase 5`, State A). Every requirement AUD-01
through AUD-06 maps to green automated tests in the plugin suite for its
automatable behavior, plus a sanitized receipt for the live external-target
portion. The 5 manual-only rows above are inherent to this phase's design
(external pinned repo, D-07 sanitization, D-09 retention) and are documented,
not coverage gaps. Targeted run 2026-08-21: 201 tests, all pass.
