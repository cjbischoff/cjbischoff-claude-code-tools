# Milestones

## v5.0 Hybrid Diff-Review Architecture (Shipped: 2026-08-22)

**Phases completed:** 7 phases, 30 plans, 116 tasks
**Stats:** 212 files changed, +38,296/−294 lines, 2026-08-17 through 2026-08-22
**Git range:** `a4731cb` through `758fe51`
**Closeout type:** override_closeout — 6 acknowledged Phase 06 tech-debt items
**Known verification overrides:** 6 (see STATE.md Deferred Items)

**Key accomplishments:**

- Baseline health proven: 4 ruff errors and 161 `ty` diagnostics fixed with real receipts; the frozen JSON contract stayed untouched (Phase 1).
- `sec-overlay review` CLI verb shipped a full diff pipeline: diffscope, file selection, sealed coverage manifest, hunk positioning, and phase gate — stdlib-only (Phase 2).
- Per-language rule resolution shipped: 8 rule docs, four-layer per-path resolution with a hard-reject rule-file safety gate, `security` and `general` review profiles, and a retract-only LLM reflection filter (Phase 3).
- Scale and resume shipped: bounded concurrency and timeouts, resume identity verification (same model, profile, and SHAs), diff-anchored comments, and SARIF fingerprint contracts (Phase 4).
- DIFF-04 gap closed: review artifacts now route through the git-ignored per-repo sidecar instead of leaking at `--root` (Phase 4.1).
- End-to-end verification and governed release: both review profiles ran on a real diff, audit criteria AUD-04/AUD-05 proven, `redteam`/`postflight` wired into `PHASE_TABLE`, every defect dispositioned, and all PRs merged after CodeRabbit review (Phases 5-6).

---
