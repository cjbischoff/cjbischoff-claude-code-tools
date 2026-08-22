---
phase: 06
slug: remediation-and-governed-release
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-21
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

The register was authored at plan time: all five plans carry a `<threat_model>` block.
The audit verified each mitigation against the implementation at HEAD; one gap
(T-06-02-06, medium) was found open and fixed in the same audit session via PR #28
(commit `a2802d8`, merge `fbe7945`), then re-verified.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI argv to `run_review` | `--root` / `--workspace` are operator paths crossing into path resolution and subprocess `cwd` | filesystem paths |
| `PHASE_TABLE` to `run.drive()` | the table is the sole authority on which audit phases run | phase sequencing |
| Finding data to rendered report | package identifiers interpolate into markdown a human acts on | finding metadata |
| Frozen Python contract to its port | `models.py`/`evidence.py` define a JSON shape a second implementation mirrors | finding schema |
| Target sidecar to this repository | audit output about a third-party codebase crosses into a public repo via git history | sanitized receipts only |
| Reviewer subagent to consume step | model-generated per-file returns are untrusted parser input | review tool-call JSON |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01-01 | Denial of Service | `run_review` root handling | low | mitigate | `cli.py` guard exits 2 before any workspace or git call | closed |
| T-06-01-02 | Tampering | `--workspace` path resolution | medium | mitigate | resolved only through `load_paths(workspace=...)`, no second resolver | closed |
| T-06-01-03 | Elevation of Privilege | resume-identity guard | high | mitigate | guard runs on both workspace branches; pinned by `test_review_workspace_override_permits_a_second_profile_without_weakening_the_resume_guard` | closed |
| T-06-01-04 | Information Disclosure | stderr message content | low | mitigate | exit-2 message names only the operator's own value | closed |
| T-06-01-05 | Repudiation | governance commits | medium | mitigate | unbroken 1.69.0→1.69.11 version/CHANGELOG chain, hooks never bypassed | closed |
| T-06-01-SC | Tampering | npm/pip/cargo installs | high | accept | no install task; `dependencies = []` asserted by test | closed |
| T-06-02-01 | Tampering | `PHASE_TABLE` order | high | mitigate | `test_original_phase_order_is_preserved` (literal 22-name list) | closed |
| T-06-02-02 | Repudiation | `artifact-gate` halt attribution | medium | mitigate | `redteam` placed before `artifact-gate`; `test_redteam_precedes_the_artifact_gate` | closed |
| T-06-02-03 | Elevation of Privilege | double-registering `redteam` | medium | mitigate | `test_redteam_is_not_a_deterministic_action` | closed |
| T-06-02-04 | Denial of Service | postflight action error handling | low | accept | no try/except added — propagation is the sibling-action norm | closed |
| T-06-02-05 | Information Disclosure | prior-context artifact | low | accept | `postflight.py` untouched by the plan (empty diff) | closed |
| T-06-02-06 | Spoofing | doc-to-code phase-order drift | medium | mitigate | `test_claude_md_phase_order_tracks_phase_table` (added post-audit, PR #28 `a2802d8`) pins doc-named phases to `PHASE_TABLE` relative order | closed |
| T-06-02-SC | Tampering | npm/pip/cargo installs | high | accept | no install task; asserted empty | closed |
| T-06-03-01 | Spoofing | deps Fix line | medium | mitigate | `rsplit('@', 1)[0] or pkg` pinned by 5 identifier-shape tests | closed |
| T-06-03-02 | Tampering | package-identifier truncation | medium | mitigate | pure string slice, no shell/path/import sink | closed |
| T-06-03-03 | Elevation of Privilege | red-team prompt prose | high | mitigate | prose matches `wants_runtime()`'s real two-way predicate; code-derived doc guard | closed |
| T-06-03-04 | Tampering | agent prompt constant blocks | high | mitigate | `prompt-constants.md` byte-identical (empty diff across plan commits) | closed |
| T-06-03-05 | Spoofing | ruleset-setup docs | medium | mitigate | tree-walking `test_no_live_doc_claims_a_git_submodule_that_does_not_exist` | closed |
| T-06-03-06 | Repudiation | test-suite explanation | low | mitigate | README correctly attributes the miss to the monkeypatched runner | closed |
| T-06-03-SC | Tampering | npm/pip/cargo installs | high | accept | no install task; asserted empty | closed |
| T-06-04-01 | Tampering | frozen contract modules | high | mitigate | sha256 source digests in `test_frozen_contract.py`, 6/6 pass | closed |
| T-06-04-02 | Repudiation | `fingerprint()` output | high | mitigate | 3 golden-value cases (full/minimal/permuted) | closed |
| T-06-04-03 | Information Disclosure | profile gate | high | mitigate | single-element + boundary subset probes | closed |
| T-06-04-04 | Repudiation | vacuous E-12 verdict | high | mitigate | vacuity assertion separate from subset assertion | closed |
| T-06-04-05 | Tampering | new runtime dependency | high | mitigate | test reads live `pyproject.toml` via `tomllib`, asserts `[]` | closed |
| T-06-04-06 | Tampering | uncommitted perturbation | medium | mitigate | clean `git status` on `sec_overlay/`; full suite green | closed |
| T-06-04-07 | Denial of Service | over-broad identity guard | low | mitigate | guard names exactly the two required modules, no directory walk | closed |
| T-06-04-SC | Tampering | npm/pip/cargo installs | high | accept | no install task; the plan asserts the absence | closed |
| T-06-05-01 | Information Disclosure | committed receipts | high | mitigate | D-09 boundary decided at a blocking checkpoint; receipt re-read against prohibitions before staging | closed |
| T-06-05-02 | Information Disclosure | target checkout path | high | mitigate | `<target-repo-root>` placeholder throughout; only SHAs recorded | closed |
| T-06-05-03 | Repudiation | E-12 verdict | high | mitigate | verdict and vacuity recorded as two separate facts with both set sizes | closed |
| T-06-05-04 | Repudiation | dispatch proof | high | mitigate | `review_source_skipped: 0` recorded beside Phase 5's `14` — the count flip is the proof | closed |
| T-06-05-05 | Tampering | Phase 5 workspace | high | mitigate | sidecar digest match before/after the run | closed |
| T-06-05-06 | Elevation of Privilege | resume-identity guard | high | mitigate | guard untouched; isolation achieved via `--workspace` override; sidecar survival is the evidence | closed |
| T-06-05-07 | Tampering | reviewer returns as parser input | medium | accept | consume step's existing seal/position/reflection/receipt gates are the controls; exercised and recorded | closed |
| T-06-05-08 | Repudiation | closure claim | medium | mitigate | four criteria addressed individually with citations in `06-DEFECTS.md` | closed |
| T-06-05-SC | Tampering | npm/pip/cargo installs | high | accept | no install task; REL-03 re-asserted by running the existing test | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-01-SC, T-06-02-SC, T-06-03-SC, T-06-04-SC, T-06-05-SC | No plan installs anything; `pyproject.toml` `dependencies` stays `[]` and is asserted empty by a live-read test, so the supply-chain legitimacy gate has no input. | maintainer (plan-time disposition) | 2026-08-21 |
| AR-06-02 | T-06-02-04 | Postflight action gets no try/except: exception propagation is the existing behavior of every sibling deterministic action; swallowing would hide real faults. | maintainer (plan-time disposition) | 2026-08-21 |
| AR-06-03 | T-06-02-05 | `postflight.py` content rules unchanged — the plan changed when the action runs, not what it records. | maintainer (plan-time disposition) | 2026-08-21 |
| AR-06-04 | T-06-05-07 | Model-generated reviewer returns stay untrusted input; the consume step's existing seal, position, reflection, and receipt gates are the controls, exercised live in Plan 06-05. | maintainer (plan-time disposition) | 2026-08-21 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-21 | 35 (+2 SC-consolidated rows counted per-plan: auditor tallied 37) | 36 | 1 (T-06-02-06, medium, non-blocking) | gsd-security-auditor (sonnet), ASVS L1 |
| 2026-08-21 | 35 | 35 | 0 | orchestrator re-verification after PR #28 landed the T-06-02-06 standing test |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-21
