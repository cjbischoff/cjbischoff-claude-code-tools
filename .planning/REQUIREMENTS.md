# Requirements: cjbischoff-claude-code-tools — Milestone v5.0

**Defined:** 2026-08-16
**Core Value:** The marketplace never ships an unverified claim: every plugin passes
validation, every release follows governance, and every confirmed sec-overlay finding
is receipt-backed.

Source: the hybrid diff-review specification
(`spec_sec-overlay-improvement_20260816_0920.md`) plus the carried-over verification
goals from the superseded v4.0 milestone. Design invariants: stdlib-only core, frozen
models.py/evidence.py contract, receipt gate as the sole authority on `confirmed`.

## v5.0 Requirements

### Validation (VAL)

- [x] **VAL-01**: `claude plugin validate .` passes for the marketplace manifest and
  every registered plugin

- [x] **VAL-02**: sec-overlay quality gates pass — pytest green, ruff and ty clean,
  zero warnings

- [x] **VAL-03**: prek hooks are installed and `prek run` passes repo-wide

### Diff Pipeline (DIFF)

- [x] **DIFF-01**: A maintainer can run `python -m sec_overlay.cli review` against a
  base/head ref pair; refs are validated against `^[A-Za-z0-9._/\-]+$` with leading
  `-` rejected, and all reads pin to resolved commit SHAs

- [x] **DIFF-02**: `diffscope.py` returns per-file `ChangedFile` records carrying
  path, old_path, status (A/M/D/R), and the raw unified-diff text

- [x] **DIFF-03**: `file_select.py` deterministically splits changed files into
  reviewable and excluded (with reasons); deleted files are excluded as `deleted`,
  and the agent cannot add or drop files from the list

- [x] **DIFF-04**: The coverage manifest holds one entry per reviewable file with
  states pending → in_review → done|failed; a run cannot seal `complete` while any
  entry is `pending`, and a `partial` terminal state names unreviewed files

### Positioning (POS)

- [x] **POS-01**: `diffhunks.py` parses unified diffs with stdlib only and exposes
  `added_line_numbers(file)` and `line_in_hunk(file, line)`

- [x] **POS-02**: `positioning.py` confirms a finding's location via hunk match, then
  whole-file match, then cross-file relocation; ambiguity or zero matches yields a
  decline routed to `needs-position-review`, never a guessed line

- [x] **POS-03**: In review mode, `phase_gate.py` drops a finding whose confirmed line
  is outside every changed hunk with reason `outside-diff`; whole-repo audit mode
  keeps the existing whole-file check

### Rule Matching (RULE)

- [x] **RULE-01**: `rule_glob.py` matches lower-cased paths against ordered PathRules
  with brace expansion and `**`-aware globbing; first match wins, else the default
  rule

- [x] **RULE-02**: Rule resolution layers apply first-non-empty: `--rule` path →
  project `.sec-overlay/rule.json` → global `~/.sec-overlay/rule.json` → built-in
  rules; `--exclude` appends to the resolved exclude list

- [x] **RULE-03**: Rule-file reads resolve symlinks, require the resolved path under
  repo root, restrict extensions to `.md`/`.txt`/`.markdown`, and cap size at 512 KB

- [x] **RULE-04**: A rule entry with `merge_system_rule: true` concatenates built-in
  and user rule text under fixed headers instead of replacing

- [x] **RULE-05**: Per-language rule docs ship for go, java, python, php, rust,
  ts/js/tsx/jsx, kotlin, swift, and default, each covering NPE, thread-safety,
  injection (XSS/SQLi), resource leaks, and error-swallowing with explicit exclusions

### Review Modes (REV)

- [x] **REV-01**: `review --profile security` reproduces current gate behavior
  exactly; `--profile general` reports general defects the security gates A/B would
  drop, with gates C/D/E still applied

- [x] **REV-02**: The reflection filter runs per file after positioning and the hunk
  gate, retracts only, fails open on LLM error, and encodes the protected-subject
  vetoes; it can never produce a `confirmed` disposition

- [x] **REV-03**: The mechanical-receipt gate remains the sole authority on
  `confirmed`; general-defect findings without a Tier-1 receipt ship as
  `unconfirmed`/`needs-deployment-testing`

### Scale and Resume (SCALE)

- [x] **SCALE-01**: `bundle.py` deterministically groups locale/config siblings and
  impl/test pairs into single review units, one file per unit as fallback, documented
  as a sec-overlay addition beyond OCR

- [x] **SCALE-02**: `--concurrency` (default 8), per-bundle `--timeout` (default
  10m), and `--max-git-procs` (default 16) bound execution; a timed-out bundle marks
  its files `failed` and the run terminal state becomes `partial`

- [ ] **SCALE-03**: Resume validates identity before any agent spawn — an implicit
  model or profile change is rejected with nothing persisted, and file reads stay
  pinned to sealed commit SHAs

### Output (OUT)

- [x] **OUT-01**: Diff-review mode emits a diff-anchored comment payload
  `{path, line, side, existing_code, content}` alongside the existing SARIF,
  markdown, and per-finding files, with the coverage manifest included

- [x] **OUT-02**: SARIF fingerprints use `Path|Category|ExistingCode` excluding
  message text

### Audit Integrity (AUD)

- [ ] **AUD-01**: A full `/sec-overlay:audit` run completes end to end on a real
  target repo, with per-phase receipts written and the working-tree fence intact

- [ ] **AUD-02**: Every finding with status `confirmed` cites a mechanical tool
  receipt; Tier-2-only or syntactic-match evidence never reaches `confirmed`

- [ ] **AUD-03**: Runtime-dependent findings land in `needs-deployment-testing` with a
  real risk score, visible in report headline counts

- [ ] **AUD-04**: Architecture and threat-model artifacts pass the deterministic gates
  (Mermaid caps, derivation headers, STE lint) and score with CVSS v4.0 only

- [ ] **AUD-05**: The audit report states its coverage denominator; every
  attack-surface class without a finding has a logged coverage-ledger entry

- [ ] **AUD-06**: A full `review` run (both profiles) completes end to end on a real
  diff, with the coverage manifest sealed and positioning-confirmed line numbers

### Release Governance (REL)

- [ ] **REL-01**: Every defect observed in the verification runs is fixed or given a
  written disposition, with models.py/evidence.py and `fingerprint()` identity
  unchanged, asserted by tests

- [ ] **REL-02**: Every change ships through governance — branch, Conventional
  Commit, semver bump plus CHANGELOG entry in the same commit, PR merged only after
  CodeRabbit's walkthrough comment

- [ ] **REL-03**: `helpers/pyproject.toml` dependencies stay empty — zero new runtime
  dependencies across all new modules

## v2 Requirements

Deferred to a future milestone. Tracked but not in the current roadmap.

### Growth (GROW)

- **GROW-01**: A second plugin is onboarded from `docs/templates/plugin/` and passes
  the same validation and governance bar

- **GROW-02**: `claude plugin validate .` runs as an automated gate (prek hook or CI)
  instead of a manual step

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Anthropic SDK / direct API dependency | Rejected by ADR-2026-08-04; stdlib-only core |
| External multi-repo check registry | Deferred by ADR-2026-08-04; in-repo bundles only |
| Correlation write-back or member re-scanning | Spec B pins the correlation layer read-only |
| Edits to models.py / evidence.py | Frozen JSON contract, byte-mirrored by a Go port |
| Mixing CVSS v3.1 and v4.0 | Ruling R2 pins v4.0 harness-wide, no mixing |
| Re-implementing delivered baseline features | All 50 ingested docs are delivered work |
| Reflection filter replacing the receipt ladder | Spec §6 pins compose-under, not replace |
| Reusing content/regex `rule_matcher.py` for path globs | Spec §4.1 pins a separate module |

## Open Design Notes

- The spec names a new `coverage.py`, but `helpers/sec_overlay/coverage.py` already
  exists. The roadmap or phase plan must rename the new module (for example
  `review_coverage.py`) or extend the existing one.

- `**`-aware globbing needs `pathlib.PurePath.full_match` (Python 3.13) or a small
  custom matcher; the chosen floor must be stated in the plugin docs.

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VAL-01 | Phase 1 | Complete |
| VAL-02 | Phase 1 | Complete |
| VAL-03 | Phase 1 | Complete |
| DIFF-01 | Phase 2 | Complete |
| DIFF-02 | Phase 2 | Complete |
| DIFF-03 | Phase 2 | Complete |
| DIFF-04 | Phase 2 | Complete |
| POS-01 | Phase 2 | Complete |
| POS-02 | Phase 2 | Complete |
| POS-03 | Phase 2 | Complete |
| RULE-01 | Phase 3 | Complete |
| RULE-02 | Phase 3 | Complete |
| RULE-03 | Phase 3 | Complete |
| RULE-04 | Phase 3 | Complete |
| RULE-05 | Phase 3 | Complete |
| REV-01 | Phase 3 | Complete |
| REV-02 | Phase 3 | Complete |
| REV-03 | Phase 3 | Complete |
| SCALE-01 | Phase 4 | Complete |
| SCALE-02 | Phase 4 | Complete |
| SCALE-03 | Phase 4 | Pending |
| OUT-01 | Phase 4 | Complete |
| OUT-02 | Phase 4 | Complete |
| AUD-01 | Phase 5 | Pending |
| AUD-02 | Phase 5 | Pending |
| AUD-03 | Phase 5 | Pending |
| AUD-04 | Phase 5 | Pending |
| AUD-05 | Phase 5 | Pending |
| AUD-06 | Phase 5 | Pending |
| REL-01 | Phase 6 | Pending |
| REL-02 | Phase 6 | Pending |
| REL-03 | Phase 6 | Pending |

Coverage: 32/32 v1 requirements mapped. No orphans, no duplicates.

---
*Requirements defined: 2026-08-16*
*Last updated: 2026-08-16 for milestone v5.0 roadmap creation*
