# Phase 6: Remediation and Governed Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-21
**Phase:** 6-Remediation and Governed Release
**Areas discussed:** Fix vs disposition line, E-12 re-verification, Agent-dispatched review scope, Release & merge shape

---

## Fix vs disposition line

| Option | Description | Selected |
|--------|-------------|----------|
| Wire into PHASE_TABLE | Add redteam/postflight as real PHASE_TABLE/DETERMINISTIC_ACTIONS entries | ✓ |
| Docs-only | State that redteam/postflight are always manual module calls | |
| You decide | Claude picks during planning | |

**User's choice:** Wire into PHASE_TABLE.

| Option | Description | Selected |
|--------|-------------|----------|
| Align prose to code | Rewrite agents/redteam.md to the actual 2-way split | ✓ |
| Implement 3-way in code | Extend wants_runtime() to allow exemption | |
| You decide | Claude picks during planning | |

**User's choice:** Align prose to code.

| Option | Description | Selected |
|--------|-------------|----------|
| Add --workspace to review | Mirror audit's flag | ✓ |
| Disposition: env var is the way | Document SEC_OVERLAY_HOME as the mechanism | |
| You decide | Claude picks during planning | |

**User's choice:** Add --workspace to review.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix all fixable | WR-01, deps template, both doc corrections; dispositions for D-05 mixing criterion and tracer non-dispatch | ✓ |
| Code fixes only, docs dispositioned | Fix WR-01 and deps template only | |
| You decide | Claude triages each row | |

**User's choice:** Fix all fixable.

---

## E-12 re-verification

| Option | Description | Selected |
|--------|-------------|----------|
| Real dispatched review on mando | Full SKILL.md-driven per-file reviewer, both profiles | ✓ |
| Seeded diff with known findings | Deterministic but synthetic evidence | |
| Test-level harness | Pytest-only subset assertion | |

**User's choice:** Real dispatched review on mando.

| Option | Description | Selected |
|--------|-------------|----------|
| Pytest harness backstop | Deterministic apply_profile subset test added regardless of live outcome | ✓ |
| Try another diff | Re-select until findings appear | |
| Ledger it again | Another honest deferral | |

**User's choice:** Pytest harness backstop.

| Option | Description | Selected |
|--------|-------------|----------|
| New findings-biased diff | Fresh diff tuned for finding yield | |
| Reuse Phase 5 SHA range | Same base..head for direct comparability | ✓ |
| You decide | Planner picks | |

**User's choice:** Reuse Phase 5 SHA range.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep D-07/D-08 as-is | Sanitized receipts here; full artifacts in mando sidecar | ✓ |
| Loosen for subset proof | Also commit anonymized fingerprints | |

**User's choice:** Keep D-07/D-08 as-is.

---

## Agent-dispatched review scope

| Option | Description | Selected |
|--------|-------------|----------|
| One evidenced run, both profiles | Receipts prove dispatch; no new features | ✓ |
| Run + dispatch hardening | Also fix any dispatch defects surfaced | |
| Minimal: whatever E-12 needs | Stop at first non-empty finding set | |

**User's choice:** One evidenced run, both profiles.

| Option | Description | Selected |
|--------|-------------|----------|
| Same ladder as Phase 5 | Run-blockers fixed in-phase; rest ledgered in 06-DEFECTS.md | ✓ |
| Fix everything surfaced | Every new defect gets a fix | |
| Ledger everything new | No new fixes beyond planned rows | |

**User's choice:** Same ladder as Phase 5.

| Option | Description | Selected |
|--------|-------------|----------|
| Fresh workspace via new --workspace | Land the flag first, run into a fresh Phase 6 workspace | ✓ |
| SEC_OVERLAY_HOME override again | Reuse the Phase 5 workaround | |
| You decide | Planner sequences it | |

**User's choice:** Fresh workspace via new --workspace.

| Option | Description | Selected |
|--------|-------------|----------|
| Planner's call | Pick run settings from Phase 4 bounded-run evidence and CLI defaults | ✓ |
| Match Phase 5 invocation exactly | Identical flags to the tracer run | |

**User's choice:** Planner's call.

---

## Release & merge shape

| Option | Description | Selected |
|--------|-------------|----------|
| Few thematic PRs | Group fixes by theme; ~4 CodeRabbit waits | ✓ |
| One PR per fix | Maximum isolation; 8+ review waits | |
| One release PR | Single large mixed diff | |

**User's choice:** Few thematic PRs.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix branches off milestone branch | Fork from and merge back into docs/milestone-v5-diff-review; milestone merges to main once at close | ✓ |
| Fix branches straight to main | Each thematic PR targets main | |
| You decide | Planner picks | |

**User's choice:** Fix branches off milestone branch.

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated identity-guard test | One citable assertion for models.py/evidence.py/fingerprint() identity | ✓ |
| Existing suite suffices | Rely on current behavioral coverage | |
| You decide | Planner checks and adds only if missing | |

**User's choice:** Dedicated identity-guard test.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-commit by CC type | feat bumps minor, fixes/docs bump patch, same-commit bump + CHANGELOG | ✓ |
| Single minor at phase end | One batched bump | |

**User's choice:** Per-commit by CC type.

---

## Claude's Discretion

- Exact PR grouping within the thematic shape.
- Reviewer run configuration (--model, --concurrency, --timeout) for the dispatched run.
- Identity-guard test mechanism (checksum vs AST vs golden fingerprint fixture).
- Receipt document structure, following the Phase 1 evidence format.

## Deferred Ideas

None — discussion stayed within phase scope.
