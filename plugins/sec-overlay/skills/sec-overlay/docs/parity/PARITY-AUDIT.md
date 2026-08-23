# PARITY-AUDIT — final disposition of every EXTRACTION.md item

This audit walks `docs/parity/EXTRACTION.md` row by row. Each item from THE ANALYSIS
(`analysis_ocr-vs-sec-overlay_20260822_1634.md`) gets one final disposition:

- **done** — implemented and verified this session, with `file:line` evidence.
- **already-done** — closed before this milestone; evidence cited.
- **rejected:<reason>** — a spec decision not to build it.
- **deferred:<reason + where>** — out of this milestone; the next step is named.
- **constraint** / **context** — a binding rule or informative note, not a work item.

Evidence paths are relative to `skills/sec-overlay/helpers/` unless prefixed. Verified
against branch `feat/ocr-parity-benchmark` at the current head. Zero items are dropped:
every EXTRACTION.md id appears below.

## Tier 0 — Measurement (M items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| M1 | done | `bench/tally.py:25-29` computes `f1 = 2PR/(P+R)`, `None` when undefined; rendered in headline, overall, and by-source rows. Task 1. |
| M2 | done | `bench/driver.py` `HeadlessDriver` + `reportable`; `bench/adapter.py` `CCSkillAdapter.scan` delegates, records failures, never fabricates. Task 3. |
| M3 | done | `bench/aacr_adapter.py` `aacr_entries(rows)` → `source="aacr"`, excluded from the real-confirmed headline; `bench/corpus.py:17` extends `SOURCES`. Task 5. |
| M3a | done | Judge statement published in the scorecard: `bench/tally.py:135-136` names `bench.judge` (deterministic match, then optional injected LLM judge). Task 5. |
| M3b | done | `bench/ocr_ingest.py` `ocr_findings(json_text)` maps `ocr review --format json` to benchmark-only CONFIRMED findings scored under the same judge. Task 5. |
| M3c | done | Same-judge caveat block in `bench/tally.py:137-139` and `bench/README.md` "Scope confound". Task 5. |
| M3d | done | AACR dataset inspected via the live Hugging Face viewer 2026-08-23; schema and caveats recorded in `bench/README.md:149-175`. Full-corpus category/label distribution stays marked unverified. Task 5. |
| M4 | done | `bench/corpus_seed/` ships ≥30 committed public entries (dogfood, dep-CVE, public-app, negatives); `test_bench.py::test_seed_corpus_has_min_entries` gates counts. Task 4. |
| M4a | done | `.github/workflows/sec-overlay-tests.yml` runs the offline detection gate on the two locked dogfood entries. Task 4. |
| M5 | done | `bench/run.py:151` `run_repeated`; `bench/tally.py:250` `aggregate_scorecards` (mean ± min/max per metric); writes `scorecard_agg.{json,md}`. Task 6. |
| M6 | done | `bench/tally.py:42` cost block (`tokens`, `wall_time_s`, `usd_per_confirmed_tp`); `run.py` captures wall-time and sums per-repo tokens; per-class FP-rate rows publish. Task 7. |

## Tier 1 — Review-mode parity (P items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| P1a | done | `review_agent.py:101` `_render_sibling_diffs_block`, `{{SIBLING_DIFFS}}` largest-first with `omitted (token cap)` marker; `render_review_prompt(sibling_diffs, cap_tokens)` at `:121`. Task 10. |
| P1b | done | `bundle.py:142` `group_bundles(diffs=...)` with C/C++ header-impl and interface/impl stem pairing; `MAX_UNIT_TOKENS=50_000` split at `:48`. Deferred: `import_adjacency(graph_json)` grouping — SPEC-optional; review mode must not require `kb/graph.json`. Task 10. |
| P2 | done | 37 rule docs under `rules/rule_docs/` (27 ported with Apache-2.0 attribution + 5-family exclusion blocks); `rule_glob.py:56` `BUILTIN_PATH_RULE_MAP` = OCR 35 patterns + `**/*` catch-all in OCR order. Task 11. |
| P3 | done | `agents/review-plan.md` strict-JSON plan prompt; `cli.py:681` gates on `PLAN_LINE_THRESHOLD`; invalid plan falls open to a prompt without guidance. Task 14. |
| P4 | done | `review_budget.py` `estimate_review_cost`, `BudgetGate` look-ahead; `cli.py` `--token-budget`, `skipped(budget)`, `budget_exceeded`, exit 0 on partial. Task 12. |
| P4a | done | `review_budget.py:24` `FILE_BUDGET_FRACTION=0.8`; files over that fraction of the budget are excluded as `too-large-tokens`. Task 12. |
| P5 | done | `diffscope.py:97` `dirty_file_records`; `cli.py:969` `--workspace-dirty` and `--commit`; `cli.py:483` mutual-exclusion guard. Task 13. |
| P6 | done | `cli.py:323` `reflection_source` param replaces the literal `{}`; missing verdict → `ReflectionSkip` fail-open, protected classes refused. Task 9. |
| P7 | done | `sec_overlay/review_result.py` `write_review_result` emits the consolidated key set (findings, dropped, declines, retractions, skips, manifest, budget flag, tokens). Task 15. |
| P8 | done | `sec_overlay/background.py` `load_background` (1 MB cap, control-char strip, delimiter neutralization, `redactor.safe_for_prompt`); `cli.py` flags; `{{BACKGROUND}}` enveloped in the prompt. Task 16. |
| P9 | done | `calibrate.py:130` `_severity_for_score`; `:236` write-back with history event `calibrate:severity-downgraded` on the downgrade branch. Task 2. |

## Tier 2 — Product shell (S items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| S1 | done | `plugins/sec-overlay/action.yml` composite action; `sec_overlay/pr_poster.py` stdlib `urllib` client with severity routing (critical/high inline, medium/low summary), `event: COMMENT`. Correction logged: actionlint substituted by a Ruby YAML parse (EXTRACTION §5). Task 18. |
| S2 | done | `cli.py:942` `sessions` parser with `list`/`show` over the sidecar `state.json` + review ledger; `--severity` filter. Task 19. |
| S3 | done | `ASSURANCE_CASE.md` (trust boundaries, countermeasures with `file:line`, Saltzer–Schroeder, OWASP/CWE, CI checks); citation walk in `test_docs_invariants.py`. Task 17. |
| S4 | done | `cli.py:953` `rules check <path>`; `cli.py:904` `difflib.get_close_matches` did-you-mean hook. Task 20. |

## Milestone 4 / Tier 3 — Press the advantage

| Id | Disposition | Evidence |
|----|-------------|----------|
| T3a | done | `cli.py` `--tier` (`fast`/`assured`) recorded in manifest and result; fast skips the plan phase. Task 21. |
| T3b | done | `bench/tally.py` per-class FP-rate rows publish in the "By class" table (REQ-M6/T3b). Task 7. |
| T3c | done | `bench/tally.py:47` `verified_fix_rate`; verified-fix block over confirmed real true-positives; `run.py` plumbs per-repo findings. Task 22. |
| T3d | done | `bench/tally.py:177` `_coverage_honesty` over per-run `kb/coverage-ledger.json`; unsupported-coverage-claim rate. Task 23. |
| T3e | done | `bench/aacr_adapter.py:33` `_source` tags security-category rows `aacr-security`; `bench/corpus.py:17` registers the slice; `tally` emits it via `by_source`. Task 24. |
| T3f | done | Covered by M5 variance (`aggregate_scorecards`). |
| T3g | deferred | CVSS-vs-human-triage agreement. The analysis conditions it on "once corpus exists"; single-maintainer adjudication has no second annotator (`bench/README.md:78-88`), so no agreement statistic is invented. Revisit when a multi-annotator corpus exists. |
| T3h | done | `fixed`/`verified-static` counts in the headline table via the same `verified_fix_rate` mechanism (`bench/tally.py:47,87`). Task 22. |

## Part 2.3 measurement-critique requirements (R items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| R1 | done | Reproducible one-command run documented in `bench/README.md:90-101`; satisfied by M2 (driver) + M3b (OCR under same judge). Task 8. |
| R2 | done | Hit criterion published: `bench/README.md:126` states F1 definition; judge match rule named in the scorecard (M3a). Task 8. |
| R3 | done | `bench/README.md:78` "Annotation protocol" states single-maintainer adjudication and disagreement handling, with no invented inter-annotator statistic. Task 8. |
| R4 | done | Scope confound stated (`bench/README.md:103`); OCR graded under the identical judge (M3b). Task 8. |
| R5 | done | Covered by M5. |
| R6 | already-done | `bench/corpus.py` supports `kind=negative`; kept. |
| R7 | done | Covered by T3e. |

## Part 3.4 weaknesses (W items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| W1 | done | Corpus populated (M4). |
| W2 | done | Driver landed (M2). |
| W3 | done | F1 landed (M1). |
| W4 | done | Live reflection wired (P6). |
| W5a | already-done | `phase_gate.py:31` `_parse_ref` handles `file:line — prose`. |
| W5b | already-done | `calibrate.py:29` `_SCOREABLE` includes `needs-deployment-testing`. |
| W5c | already-done | `repo_memory.py:93-98` includes subpath in the slug. |
| W5d | done | Judge severity write-back (P9). |
| W5e | already-done | `report.py` NDT section foregrounded above confirmed. |
| W6 | constraint | `tests/test_docs_invariants.py` CI-guarded; every new documented constant gets an assertion. Binding DoD rule. |
| W7 | done | 37 rule docs (P2). |

## Part 4 gap-matrix rows (G items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| G18 | rejected: TUI/editor extension is a separate product | SPEC disposition G18. Terminal UX, viewer TUI, and VS Code extension are out of scope for a harness; no code shell added. |
| G19 | rejected: multi-provider not applicable by design | SPEC disposition G19. The harness pins model-family diversity; multi-provider presets contradict that gate. |
| G20 | rejected: delegation mode low value | SPEC disposition G20. OCR's whole product is the delegate; sec-overlay's value is the adversarial ladder. |
| G21 | deferred: deliberate MCP routing, revisit after first benchmark | SPEC disposition G21. Routing external MCP tools into the review loop is deferred until the first benchmark measures where a gap exists. |
| G2 | done | Addressed by the T3a fast tier (token-comparable row). |
| G13 | context | Cost accounting — sec-overlay already wins; no action. |
| G14/15/16/23–27/30/33/34 | context | Advantage inventory; feeds T3 publishing + S3. |

## Part 1.7 fine detail (D items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| D1 | done | OCR token-estimate shape encoded in `review_budget.py` constants; asserted in `test_docs_invariants.py`. Task 12. |
| D2 | already-done | `reflection.py` `PROTECTED_SUBJECT_CLASSES` ports OCR's protected list. |
| D3 | done | Plan-skip threshold `PLAN_LINE_THRESHOLD` (P3). Task 14. |
| D4 | done | Manifest item states and failure classes consumed by the P4 manifest entries. Task 12. |
| D5 | done | Exit-code contract: partial-budget run exits 0 (P4). Task 12. |
| D6 | rejected: no cross-comment dedup in review mode | OCR itself lacks it; sec-overlay's dedup runs in the audit pipeline (`dedupe.py`), not review mode. Noted as an opportunity, not built. |
| D7 | context | OCR sends diffs unredacted; cited as a sec-overlay advantage in S3 + comparison. Folded into S3. |
| D8 | constraint | OCR review-mode bundling claim is false (`agent.go:673` per-file); P1 is described as sec-overlay-original, never a port. Refuted-claim guard. |
| D9 | done | OCR Action posts every review as `event: COMMENT`; severity routing is placement only — mirrored in `pr_poster.py` (S1). Task 18. |
| D10 | done | Per-file token estimate added to prepare output under P4. Task 12. |

## Pass B additions (X items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| X1 | rejected: mid-loop memory compression | OCR-specific loop optimization; sec-overlay uses per-phase workspaces, not a single long loop. No equivalent need. |
| X2 | rejected: two retry layers + retry report | The harness dispatches parallel agents in waves with safe re-dispatch (skill CLAUDE.md §2); a separate retry collector adds no signal. |
| X3 | done | `sessions show --severity` filter folded into S2. Task 19. |
| X4 | rejected: non-GitHub CI recipes | GitLab/Bitbucket/Gerrit recipes are distribution surface, not harness capability. S1 ships the GitHub composite action only. |
| X5 | rejected: npm per-platform binary + VS Code extension | Folded into the G18 rejection (separate product). |
| X6 | rejected: provider wizard TUI + `llm test` probe | Folded into the G19 rejection (multi-provider not applicable). |
| X7 | context | OCR severity-enum inconsistency; sec-overlay advantage — feeds the comparison table. |
| X8 | context | OCR blog-post internal numbers are self-reported; never cited as a benchmark. |

## Part 6.5 Verification Ledger (V items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| V1 | constraint | "OCR bundles related files in review mode" refuted; P1 described as sec-overlay-original. Honored in P1a/P1b + D8. |
| V2 | already-done | "all dogfooding defects open" refuted; reflected in W5a–W5c already-done rows. |
| V3 | done | "OCR Action escalates by severity" refuted; reflected in D9 → S1. |
| V4 | context | "~24k lines" refuted (27,538 measured); context only. |
| V5 | done | Confirmed set (empty corpus, adapter, no F1, reflection `{}`, budget unenforced, missing review inputs, OCR unredacted) all closed — see M/P rows above. |
| V6 | context | Repo-doc-sourced medium-confidence claims carry the confidence label; never restated as verified. |
| V7 | done | AACR dataset inspected (M3d); hit criterion documented (R2). |

## Honest risk assessment (HR items)

| Id | Disposition | Evidence |
|----|-------------|----------|
| HR1 | mitigated | Recall risk: first AACR run uses `--profile general`; P2 rule docs and `fp_feedback` iterate before publishing. Mitigation is in place; the risk stays real until a full AACR run measures recall. |
| HR2 | mitigated | Token cost of the adversarial ladder addressed by the T3a fast tier (token-comparable row). |
| HR3 | mitigated | Judge-selection bias: judge published (M3a), OCR run through it (M3b), reported losses accepted. |

## Binding constraints (Part 7)

All eight EXTRACTION.md constraints held through implementation:

1. `helpers/` stayed stdlib-only; SAST binaries shelled, never imported.
2. `models.py` and `evidence.py` unchanged (sha256-frozen); all new behavior in new modules.
3. TDD RED-then-GREEN commit pairs per item.
4. FP ladder, tool-receipt gate, model-family diversity, retract-only reflection never weakened.
5. Same-commit doc updates; `test_docs_invariants.py` assertions for new documented constants.
6. Milestone order M → P → S → advantage held.
7. Corrections logged in `EXTRACTION.md` "Corrections logged during implementation" (5 entries). No corpus or judge bent to match THE ANALYSIS.
8. Completion report carries the final scorecard next to OCR's published row — see the completion report.

## Stale re-verification rows (EXTRACTION §"Re-verification notes")

Four analysis cites went stale between `0a65ee9` and the current branch. All are documented
in EXTRACTION.md and require no further work:

1. "corpus_seed contains only a README" — stale; the seed now ships ≥30 entries (M4).
2. "dispatch is one file per subagent" — stale; `bundle.py` `ReviewUnit` dispatch landed (P1b).
3. Report NDT rendering "partially mitigated" — now fully rendered (W5e).
4. helpers README test counts — repo-doc drift, both figures repo-doc-sourced.
