---
phase: 4
slug: scale-resume-diff-output
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-20
validated: 2026-08-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Filled retroactively by validate-phase on 2026-08-21 from the four plan
> summaries and the live test suite.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (stdlib-only core; uv-managed venv) |
| **Config file** | `plugins/sec-overlay/skills/sec-overlay/helpers/pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_bundle.py tests/test_cli.py tests/test_review_coverage.py tests/test_review_comments.py tests/test_sarif.py` |
| **Full suite command** | `uv run pytest -q` (from `plugins/sec-overlay/skills/sec-overlay/helpers/`) |
| **Estimated runtime** | ~6 seconds for the phase files; full suite per the recorded baseline |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01 grouping | 01 | 1 | SCALE-01 | — | Deterministic bundle grouping; no file gains or loses review scope | unit | `uv run pytest -q tests/test_bundle.py` (14 tests: totality, order, deterministic unit_id) | ✅ | ✅ green |
| 04-01 focus rule | 01 | 1 | SCALE-01 | — | Widened `bundle_paths` focus rule threaded through `run_review` | unit | `uv run pytest -q tests/test_review_agent.py tests/test_review_tracer.py` | ✅ | ✅ green |
| 04-01 comment payload | 01 | 1 | OUT-01 | — | `review_comments.json` carries the 5-key payload plus the embedded manifest | unit | `uv run pytest -q tests/test_review_comments.py` (5 tests) | ✅ | ✅ green |
| 04-01 fingerprints | 01 | 1 | OUT-02 | — | SARIF `partialFingerprints` key on Path\|Category\|ExistingCode, message-independent | unit | `uv run pytest -q tests/test_sarif.py` (12 tests) | ✅ | ✅ green |
| 04-02 bounded flags | 02 | 2 | SCALE-02 | — | Out-of-range `--concurrency`/`--timeout`/`--max-git-procs` values are rejected, not clamped | unit | `uv run pytest -q "tests/test_cli.py" -k "concurrency or timeout or max_git_procs"` | ✅ | ✅ green |
| 04-02 pooled fetch order | 02 | 2 | SCALE-02 | — | Manifest entries keep serial file order despite uneven fetch delay | unit | `uv run pytest -q tests/test_cli.py::test_review_manifest_entries_preserve_file_order_despite_uneven_fetch_delay` | ✅ | ✅ green |
| 04-02 unit timeout | 02 | 2 | SCALE-02 | — | A timed-out unit fails every member file; the run seals `partial` | unit | `uv run pytest -q tests/test_cli.py::test_review_unit_timeout_fails_every_member_with_timeout_note tests/test_cli.py::test_review_unit_within_timeout_finishes_normally` | ✅ | ✅ green |
| 04-03 resume identity | 03 | 3 | SCALE-03 | — | A model or profile mismatch on resume is rejected before any write; the manifest byte-hash is unchanged | unit | `uv run pytest -q tests/test_review_coverage.py` (resume-identity tests) | ✅ | ✅ green |
| 04-03 SHA-pinned resume | 03 | 3 | SCALE-03 | — | A resumed run reads at the persisted head SHA; an unresolvable SHA fails loudly | unit | `uv run pytest -q tests/test_cli.py::test_review_resume_reads_at_persisted_head_sha_despite_moved_head tests/test_cli.py::test_review_resume_with_unresolvable_persisted_sha_fails_loudly` | ✅ | ✅ green |
| 04-04 seal-before-embed | 04 | 4 | OUT-01 | — | The embedded manifest seal matches the on-disk manifest for complete and partial runs | unit | `uv run pytest -q tests/test_cli.py::test_review_comments_embedded_manifest_seal_matches_on_disk_after_complete_run tests/test_cli.py::test_review_comments_embedded_manifest_seal_is_partial_after_partial_run` | ✅ | ✅ green |
| 04-04 `--model` surface | 04 | 4 | SCALE-03 | — | `--model` is a real CLI flag, forwarded to `run_review` and enforced on resume (exit 2 on change) | unit | `uv run pytest -q tests/test_cli.py::test_review_accepts_model_flag_and_forwards_it_to_run_review tests/test_cli.py::test_review_resume_with_changed_model_exits_2_via_main_entrypoint` | ✅ | ✅ green |
| 04-04 hung-fetch bound | 04 | 4 | SCALE-02 | — | A hung unit fetch cannot hold `run_review` past `--timeout`; git children carry `subprocess.run(timeout=...)` | unit | `uv run pytest -q tests/test_cli.py::test_review_returns_before_hung_unit_fetch_completes tests/test_cli.py::test_review_abandoned_unit_fetch_stops_at_the_unit_deadline tests/test_cli.py::test_review_production_git_calls_carry_subprocess_timeout` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new framework,
config, or stub files were needed; every test landed in the existing
`helpers/tests/` suite during phase execution.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none existed)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-08-21

---

## Validation Audit 2026-08-21

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All five requirements (SCALE-01, SCALE-02, SCALE-03, OUT-01, OUT-02) map to
green automated tests. The 8 phase test files ran together on 2026-08-21:
158 passed in 5.59s. This audit reconciled the template seeded by plan-phase;
the tests themselves shipped with plans 04-01 through 04-04 and needed no
additions.
