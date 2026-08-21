# Roadmap: cjbischoff-claude-code-tools

## Milestone: v5.0 Hybrid Diff-Review Architecture

## Overview

v4.0 (Baseline Health / Receipt-Backed Audit / Remediation) is superseded with zero
phases executed; its verification and release goals are absorbed below as Phases 1, 5,
and 6. This milestone first proves the delivered baseline is healthy, then builds the
diff-review pipeline in the spec's build order — diff acquisition and coverage,
positioning, rule matching, review verb and reflection filter, scale and output — and
finally proves both the whole-repo audit and the new diff review end to end before
remediating and shipping through governance. Every new module is stdlib-only and
TDD failing-test-first; models.py, evidence.py, and `fingerprint()` stay frozen.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Baseline Health Verification** - Prove the delivered marketplace and plugin baseline is healthy: validation, tests, hooks (completed 2026-08-17)
- [x] **Phase 2: Diff Pipeline & Positioning** - Deterministic diff acquisition, per-file coverage tracking, and hunk-anchored finding positioning (completed 2026-08-19)
- [x] **Phase 3: Rule Matching & Review Modes** - Per-language rule selection, the `review` verb's security/general profiles, and the retract-only reflection filter (completed 2026-08-19)
- [x] **Phase 4: Scale, Resume & Diff Output** - Semantic bundling, concurrency/resume limits, and the diff-anchored output payload (completed 2026-08-20)
- [x] **Phase 5: End-to-End Verification (Audit & Review)** - Drive full audit and review runs on a real target and verify honest, receipt-backed output (completed 2026-08-21)
- [ ] **Phase 6: Remediation and Governed Release** - Fix what the runs surfaced and ship through governance with the frozen contract intact

## Phase Details

### Phase 1: Baseline Health Verification

**Goal**: The maintainer can trust the delivered baseline — marketplace validation, quality gates, and governance hooks all pass today, before any new module is added
**Depends on**: Nothing (first phase)
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):

  1. `claude plugin validate .` exits clean for the marketplace manifest and the sec-overlay plugin
  2. sec-overlay's pytest suite passes, and ruff and ty report zero errors and zero warnings
  3. prek hooks are installed and `prek run` passes across the repo

**Plans**: 3/3 plans executed
**Wave 1**

- [x] 01-01-PLAN.md — Run all three gate families and capture receipts, versions, and a triage ledger

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Fix every triaged defect under governance, leaving the frozen contract untouched

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Re-run the gates green, write the fix ledger, and prove the phase constraints held

### Phase 2: Diff Pipeline & Positioning

**Goal**: Given a base/head ref pair, the harness deterministically identifies every changed file, tracks per-file review coverage, and confirms exact hunk-anchored finding locations without ever guessing a line
**Depends on**: Phase 1
**Requirements**: DIFF-01, DIFF-02, DIFF-03, DIFF-04, POS-01, POS-02, POS-03
**Success Criteria** (what must be TRUE):

  1. Ref arguments are validated against `^[A-Za-z0-9._/\-]+$` (leading `-` rejected) before any git subprocess call, and `diffscope.py` returns per-file `ChangedFile` records (path, old_path, status A/M/D/R, raw unified-diff text) pinned to resolved commit SHAs
  2. `file_select.py` deterministically splits changed files into reviewable and excluded-with-reason sets, excludes deleted files as `deleted`, and the agent cannot add or drop files from that list
  3. The coverage manifest carries one entry per reviewable file transitioning pending → in_review → done|failed, and a run cannot seal `complete` while any entry is `pending`; a `partial` terminal state names every unreviewed file
  4. `diffhunks.added_line_numbers()` and `line_in_hunk()` correctly classify added/context lines inside a hunk window, and `positioning.py` confirms a finding's location via hunk match → whole-file match → cross-file relocation, declining to `needs-position-review` (never guessing) on ambiguity or zero matches
  5. In review mode, `phase_gate.py` drops a finding whose confirmed line lies outside every changed hunk with reason `outside-diff`; the same finding is retained unchanged under the existing whole-file check in audit mode

**Plans**: 5/5 plans executed

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Tracer: one changed file reviewed end to end through every layer

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Ref validation, SHA pinning, extension allowlist, exclusion reasons, size cap

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Coverage manifest state machine and the unified-diff hunk parser

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-04-PLAN.md — Never-guess positioning ladder and needs-position-review visibility

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 02-05-PLAN.md — Review-mode position gate, drop ledger, and partial-seal exit code

**Notes**: The spec's coverage-manifest module collides in name with the already-shipped `helpers/sec_overlay/coverage.py` (a different, existing module). The plan for this phase must name the new manifest module distinctly (e.g. `review_coverage.py`) or explicitly extend the existing module — never silently overwrite it.

### Phase 3: Rule Matching & Review Modes

**Goal**: The review verb selects the right per-language checklist for every file, runs in security or general-defect scope on command, and never lets an LLM judgment override the mechanical receipt gate
**Depends on**: Phase 2
**Requirements**: RULE-01, RULE-02, RULE-03, RULE-04, RULE-05, REV-01, REV-02, REV-03
**Success Criteria** (what must be TRUE):

  1. `rule_glob.py` resolves a file's rule via ordered, brace-expanded, `**`-aware PathRules (first match wins, else the default rule), through four-layer resolution (`--rule` path → project `.sec-overlay/rule.json` → global `~/.sec-overlay/rule.json` → built-in), with `--exclude` appended to the resolved exclude list and `merge_system_rule: true` concatenating built-in and user text under fixed headers instead of replacing
  2. Rule-file reads resolve symlinks, require the resolved path under repo root, restrict extensions to `.md`/`.txt`/`.markdown`, and reject files over 512 KB
  3. Per-language rule docs exist for go, java, python, php, rust, ts/js/tsx/jsx, kotlin, swift, and default, each naming NPE, thread-safety, injection (XSS/SQLi), resource-leak, and error-swallowing checks with explicit exclusions
  4. `review --profile security` on a diff reproduces existing gate A-E behavior exactly; `--profile general` on the same diff additionally surfaces NPE/thread-safety/XSS/SQLi findings that gates A/B would have dropped, with gates C/D/E still enforced
  5. The reflection filter runs once per file after positioning and the hunk gate, retracts findings only, fails open on LLM error, and cannot itself produce a `confirmed` disposition; a general-defect finding without a Tier-1 mechanical receipt ships as `unconfirmed`/`needs-deployment-testing`, never `confirmed`

**Plans**: 7/7 plans executed (03-07 is gap closure from 03-VERIFICATION.md)
**Wave 1**

- [x] 03-01-PLAN.md — Wave 1 (tracer): end-to-end review of one Python file through its rule doc and the reflection filter

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Wave 2: four-layer rule resolution, merge_system_rule, file filter, and the rule-file safety gate

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-03-PLAN.md — Wave 3: the seven remaining per-language rule docs and their conformance test

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 03-04-PLAN.md — Wave 4: security and general profiles with the same-fixture no-regression proof (has a decision checkpoint)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 03-05-PLAN.md — Wave 5: reflection prompt, protected-subject veto, never-silent ledger, and the receipt-gate disposition ladder

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 03-06-PLAN.md — Wave 6: per-file review-agent dispatch that feeds the resolved rule doc in and real findings out

**Wave 7** *(gap closure, blocked on Wave 6 completion)*

- [x] 03-07-PLAN.md — Wave 7 (gap closure): report reflection survivors in the ledger and route apply_profile through the D-12 disposition ladder

**Notes**: `**`-aware globbing needs `pathlib.PurePath.full_match` (Python 3.13) or a small custom matcher. State the chosen floor explicitly in the plugin docs — check the plugin's actual supported interpreter range before assuming Python 3.13 is available; if it is not, ship the custom matcher.

### Phase 4: Scale, Resume & Diff Output

**Goal**: Large changesets stay bounded and resumable, and every shipped finding carries a diff-anchored, positioning-confirmed location
**Depends on**: Phase 3
**Requirements**: SCALE-01, SCALE-02, SCALE-03, OUT-01, OUT-02
**Success Criteria** (what must be TRUE):

  1. `bundle.py` deterministically groups locale/config siblings and impl/test pairs into single review units (one file per unit as fallback), documented in the skill docs as a sec-overlay addition beyond OCR
  2. `--concurrency` (default 8), per-bundle `--timeout` (default 10m), and `--max-git-procs` (default 16) bound execution; a timed-out bundle marks its files `failed` and the run's terminal state becomes `partial`
  3. Resume validates model/profile identity before spawning any agent — an implicit change is rejected with nothing persisted — and every file read stays pinned to the sealed commit SHAs
  4. Diff-review mode emits a diff-anchored comment payload (`path, line, side, existing_code, content`) per finding alongside the existing SARIF, markdown, and per-finding files, with the coverage manifest included
  5. SARIF fingerprints key on `Path|Category|ExistingCode`, excluding message text

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Bundle grouping, diff-anchored comment payload, and content-only SARIF fingerprints (SCALE-01, OUT-01, OUT-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Bounded concurrency, per-bundle timeout, git process cap, and timeout-to-partial sealing (SCALE-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-03-PLAN.md — Resume identity validation before any write, and SHA-pinned resumed reads (SCALE-03)

**Wave 4** *(gap closure — blocked on Wave 3 completion)*

- [x] 04-04-PLAN.md — Seal before embedding the manifest, give `--model` a CLI surface, and bound wall-clock time on a hung fetch (OUT-01, SCALE-02, SCALE-03)

### Phase 04.1: Close gap: DIFF-04 — review sidecar workspace isolation (INSERTED)

**Goal:** Reviewing a repo writes nothing into that repo's tracked working tree — `run_review` resolves its workspace through `RepoMemory.for_target(root)` to the `<target>/.sec-overlay/<slug>/` sidecar, exactly as `scan` and `audit` already do, with a regression test pinning the convention
**Requirements**: DIFF-04
**Depends on:** Phase 4
**Plans:** 1/1 plans complete

Plans:

- [x] 04.1-01-PLAN.md — Re-root `run_review` onto the per-repo sidecar, re-root every test assertion that encoded the bug, and land it as one governed commit

### Phase 5: End-to-End Verification (Audit & Review)

**Goal**: Both pipelines — whole-repo audit and diff review — prove themselves end to end on a real target, with every claim receipt-backed and every gap logged rather than hidden
**Depends on**: Phase 4
**Requirements**: AUD-01, AUD-02, AUD-03, AUD-04, AUD-05, AUD-06
**Success Criteria** (what must be TRUE):

  1. A full `/sec-overlay:audit` run completes end to end on a real target repo; per-phase receipts are written and the working-tree fence holds throughout
  2. Every finding with status `confirmed` cites a mechanical tool receipt; no Tier-2-only or syntactic-match finding reaches `confirmed`
  3. Runtime-dependent findings land in `needs-deployment-testing` with a real risk score, visible in report headline counts rather than hidden
  4. Architecture and threat-model artifacts pass the deterministic gates (Mermaid caps, derivation headers, STE lint) and score with CVSS v4.0 only
  5. The audit report states its coverage denominator, and every attack-surface class without a finding has a logged coverage-ledger entry
  6. A full `review` run in both profiles completes end to end on a real diff, with the coverage manifest sealed and every reported line positioning-confirmed

**Plans**: 4/4 plans executed

Plans:
**Wave 1**

- [x] 05-01-PLAN.md — Tracer: run the diff-review pipeline end to end on a real diff in both profiles, seal the manifest, and establish the sanitized receipt format and defect ledger (AUD-06)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02-PLAN.md — Close the vendored semgrep ruleset gap, then drive the audit through every PHASE_TABLE stage on the pinned target head (AUD-01)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 05-03-PLAN.md — Read finding integrity back from the audit sidecar: the Tier-1 receipt ladder and runtime-dependent risk scoring (AUD-02, AUD-03)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 05-04-PLAN.md — Read artifact gates and coverage back: deterministic gates, CVSS v4.0 only, coverage denominator, and the coverage ledger (AUD-04, AUD-05)

### Phase 6: Remediation and Governed Release

**Goal**: Every defect the verification runs surfaced is fixed or dispositioned, and every fix ships through the repo's own governance with zero frozen-contract regressions
**Depends on**: Phase 5
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):

  1. Every defect logged during Phase 5's verification runs has a merged fix or a written disposition
  2. models.py, evidence.py, and `fingerprint()` identity are unchanged after fixes, asserted by the test suite
  3. Each fix lands on a branch with a Conventional Commit, semver bump, and CHANGELOG entry in the same commit, merged only after CodeRabbit's walkthrough comment posts
  4. `helpers/pyproject.toml` dependencies stay empty across every new module — zero new runtime dependencies

**Plans**: 3/5 plans executed

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — CLI fixes: WR-01 root guard as the phase tracer, `review --workspace`, PR governance rail established

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-02-PLAN.md — Pipeline wiring: `redteam` and `postflight` into `PHASE_TABLE` and `DETERMINISTIC_ACTIONS`, docs reconciled

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06-03-PLAN.md — Output and doc corrections: deps-finding package name, red-team prompt two-way split, two false doc claims

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 06-04-PLAN.md — Guards: frozen-contract identity, `fingerprint()` golden values, empty dependency table, profile-subset edge probes

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 06-05-PLAN.md — Dispatched run, E-12 evidence, sanitized receipts, defect ledger, phase close

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Baseline Health Verification | 3/3 | Complete    | 2026-08-17 |
| 2. Diff Pipeline & Positioning | 5/5 | Complete    | 2026-08-19 |
| 3. Rule Matching & Review Modes | 7/7 | Complete    | 2026-08-19 |
| 4. Scale, Resume & Diff Output | 4/4 | Complete    | 2026-08-20 |
| 5. End-to-End Verification (Audit & Review) | 4/4 | Complete    | 2026-08-21 |
| 6. Remediation and Governed Release | 3/5 | In Progress|  |
