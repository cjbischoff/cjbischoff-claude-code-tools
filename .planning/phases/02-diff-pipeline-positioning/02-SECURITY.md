---
phase: 02
slug: diff-pipeline-positioning
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-17
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI argv -> `diffscope` | Operator-supplied `--base` / `--head` reach a `git` argv | ref strings (untrusted) |
| `git` stdout -> parsers | Path and status text parsed into records and glob-matched | path text (tool-reported) |
| Repo working tree -> `positioning` | File content read to confirm a claimed finding location | source text (read-only) |
| Agent-claimed finding -> `resolve_position` / review gate | Model output; locations unverified until gated | finding claims (untrusted) |
| Run artifact dir -> Phase 4 | `coverage_manifest.json` and `review_ledger.json` are resume and audit inputs | run state (local) |
| Manifest seal -> CLI exit code | Exit code is what CI and the operator's shell trust | process status |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Tampering | `diffscope.validate_ref` | high | mitigate | Anchored allowlist `^(?!-)[A-Za-z0-9._/~-]+$` (`diffscope.py:9`); `ValueError` before any subprocess; `--` separator in every git argv; leading-dash/empty/space/semicolon/backtick/dollar cases tested (`test_diffscope.py:72-85`) | closed |
| T-02-02 | Tampering | `diffscope.resolve_ref_sha` | medium | mitigate | Both refs resolved to SHAs at run start (`cli.py:117-118`); test asserts every `rev-parse` precedes the first `diff` and raw refs never reach `diff` argv (`test_diffscope.py:175-193`); raises on nonzero returncode (fix `b00d0c1`) | closed |
| T-02-03 | Denial of Service | `file_select.partition` size cap | medium | mitigate | Strict `>` against `DEFAULT_MAX_DIFF_LINES` (5000); wired into CLI via `diff_line_counts`/`binary_paths` (fix `3dbf975`, `cli.py:124-129`); both cap boundaries tested | closed |
| T-02-04 | Information Disclosure | `CoverageManifest` content | low | accept | Manifest stores paths, states, notes, SHAs only — never diff or file content; written inside the local run root | closed |
| T-02-05 | Repudiation | `CoverageManifest.seal` | high | mitigate | `seal()` raises `CoverageTransitionError` on any `pending`/`in_review` entry or empty manifest; `complete` requires every entry `done`; `partial` names each failed entry | closed |
| T-02-06 | Tampering | path handling in `file_select`/`positioning` | medium | mitigate | git-reported paths used read-only for allowlist/glob decisions; only write targets are `ws.artifacts` paths built from the workspace root (`workspace.py`) | closed |
| T-02-07 | Spoofing | rename record path assignment | medium | mitigate | R/C status assigns `path`=new, `old_path`=old (`diffscope.py:89-90`); review runs on the new path's hunks; rename tests (`test_diffscope.py:112-138`) | closed |
| T-02-08 | Repudiation | exclusion reason vocabulary | high | mitigate | `EXCLUSION_REASONS` five-member frozenset; `ExcludedFile.__post_init__` raises outside it; test walks every produced exclusion (`test_file_select.py:171`) | closed |
| T-02-09 | Tampering | `CoverageManifest` transitions | high | mitigate | Single `_ALLOWED_TRANSITIONS` table gates every state change; `CoverageTransitionError` names path, current state, rejected target; nothing outside the class edits the JSON | closed |
| T-02-10 | Tampering | manifest and ledger persistence | medium | mitigate | `_atomic_write`: mkstemp-in-destination-directory then `os.replace`, temp unlinked on `BaseException`; used by `review_coverage._persist` and `report.write_review_ledger` | closed |
| T-02-11 | Tampering | `parse_hunks` line classification | high | mitigate | Ignore-until-first-header rule; CRLF normalised via `splitlines()`; no-newline marker skipped; asserted by tests | closed |
| T-02-12 | Denial of Service | `parse_hunks` on a large body | low | accept | T-02-03's 5000-line cap runs in `file_select.partition` before any diff text reaches the parser | closed |
| T-02-13 | Spoofing | `resolve_position` match strictness | high | mitigate | Exact consecutive line comparison with whitespace strip only; zero `difflib` references repo-wide; no tolerance window, nearest-line fallback, or confidence score | closed |
| T-02-14 | Repudiation | `PositionResult` field validation | high | mitigate | `__post_init__` forbids a `needs-position-review` result carrying a line number; closed reason vocabularies (`test_positioning.py:68-93`) | closed |
| T-02-15 | Repudiation | decline visibility | high | mitigate | `run_review` wires gate declines into `write_report(ws, dropped=…, position_reviews=…)` (`cli.py:148-149`, fix `f0427d7`); zero-decline case still emits report section and ledger (test `test_review_writes_ledger_and_report_with_zero_drops_and_declines`) | closed |
| T-02-16 | Tampering | markdown table injection via snippet | medium | mitigate | Pipes escaped, CR/LF collapsed in snippet cells (`report.py:653`, `test_report.py:925-930`); reachable from the production review path since fix `f0427d7` | closed |
| T-02-17 | Information Disclosure | snippet content in artifacts | low | accept | Snippet is source text the operator already has read access to, written inside the local run root; required to make a decline actionable | closed |
| T-02-18 | Repudiation | silent finding loss | high | mitigate | Every drop becomes a `DroppedFinding` in the report section and `artifacts/review_ledger.json` from the same `write_report` call (fix `f0427d7`); markdown drop-row count equals ledger drop count (test `test_review_ledger_drop_count_matches_markdown_drop_rows`) | closed |
| T-02-19 | Spoofing | drop vs decline conflation | high | mitigate | `review_position_gate` returns kept/dropped/declines as separate lists; declines carry `PositionResult` (fix `2ab4cb5`); a `needs-position-review` finding appears in neither kept nor drop list (`test_phase_gate.py:394`) | closed |
| T-02-20 | Tampering | audit-mode regression | high | mitigate | `findings_gate.py` untouched across phase 02 (last commit `090b8f9` pre-dates the phase); no new `_line_in_range` call site; pre-existing gate tests pass unmodified | closed |
| T-02-21 | Repudiation | exit code masking an incomplete run | high | mitigate | Distinct branches: exit 2 invalid ref, exit 0 complete seal, exit 3 partial seal (`cli.py:120-156`); each code has its own test | closed |
| T-02-22 | Tampering | hunk-boundary off-by-one | high | mitigate | Half-open interval `hunk_for_line`; first/last changed lines kept, immediately-before/after dropped (`test_phase_gate.py:349-374`) | closed |
| T-02-23 | Information Disclosure | drop records in report | low | accept | Drop rows carry path, line, rule id — metadata the operator already reads, written inside the local run root; required to make a drop auditable | closed |
| T-02-SC | Tampering | npm/pip/cargo installs | high | accept | Zero installs in the phase; `pyproject.toml` `dependencies = []` verified directly at audit time | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-04 | Manifest stores metadata only (paths, states, notes, SHAs); no new disclosure surface beyond operator read access | plan register (02-01-PLAN.md) | 2026-08-17 |
| AR-02-02 | T-02-12 | Upstream 5000-line cap bounds parser input; no second cap needed | plan register (02-03-PLAN.md) | 2026-08-17 |
| AR-02-03 | T-02-17 | Snippet is source text the operator already reads; required for actionable declines | plan register (02-04-PLAN.md) | 2026-08-17 |
| AR-02-04 | T-02-23 | Drop rows carry operator-readable metadata only; required for auditable drops | plan register (02-05-PLAN.md) | 2026-08-17 |
| AR-02-05 | T-02-SC | Phase installs zero packages; `dependencies = []` asserted by test and verified at audit | plan register (all plans) | 2026-08-17 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-17 | 24 | 21 | 3 (T-02-15, T-02-18 blocking; T-02-16 non-blocking) | gsd-security-auditor (ASVS L1) |
| 2026-08-17 | 24 | 24 | 0 | orchestrator re-verification after fix `f0427d7` (wiring confirmed at `cli.py:148-149`; 16/16 CLI tests pass, full suite 1026 passed) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-17
