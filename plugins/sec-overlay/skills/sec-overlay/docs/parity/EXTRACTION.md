# EXTRACTION — inventory of THE ANALYSIS (analysis_ocr-vs-sec-overlay_20260822_1634.md)

Source document: `/Users/christopher/Tools/open-code-review/analysis_ocr-vs-sec-overlay_20260822_1634.md`.
Analysis baseline: sec-overlay at repo commit `0a65ee9`. Re-verification baseline: current
`main` (merge `1aedb2e`, after PR #35). Every row below carries a re-verified status against
the current source, not the analysis baseline.

Extraction passes run: **3** (A: inventory, B: cross-check, C: adversarial). Pass C added
zero rows, so extraction stopped at 3 passes.

- Rows added on Pass A: 58.
- Rows added on Pass B (marked `missed-on-pass-A`): 12 (D6, D7, D9, D10, X1–X8).
- Rows added on Pass C: 0.

Verification-status vocabulary: `confirmed` (re-verified against current source this
session, file:line cited), `repo-doc-sourced` (from sec-overlay or OCR docs, not
independently re-derived), `refuted` (the analysis itself refuted it — Part 6.5),
`external` (off-repo, not inspectable locally).

Status vocabulary: `open` (needs work), `partial` (some of it landed since `0a65ee9`),
`already-done` (closed since `0a65ee9`, evidence cited), `constraint` (binding rule, not a
work item), `context` (informative, no work), `disposition-required` (no spec requirement;
spec must state why).

## Tier 0 — Measurement (M items, analysis Part 6 + Part 7 Milestone 1)

| Id | Item | Analysis section | Analysis file:line targets | Claim verification | Current status + evidence |
|----|------|------------------|---------------------------|--------------------|---------------------------|
| M1 | Add F1 (`2PR/(P+R)`, zero-division-safe) to `Scorecard`, `to_markdown`, `to_dict` | Part 6 M1; Part 3.4 §3; Part 7 §1 | `helpers/bench/tally.py` | confirmed | open — no `f1` token in `bench/tally.py` |
| M2 | Replace `CCSkillAdapter.scan()` `NotImplementedError` with a headless driver (`claude -p` or Agent SDK); resumable, per-repo cache, failure = skip + record, never fabricate | Part 6 M2; Part 3.4 §2; Part 7 §3 | `helpers/bench/adapter.py` | confirmed | open — `bench/adapter.py:67,78` still raises |
| M3 | `bench/aacr_adapter.py`: AACR-Bench rows → `CorpusEntry`, own source label, never blended into `real-confirmed` headline | Part 6 M3; Part 7 §5 | new `helpers/bench/aacr_adapter.py` | confirmed (absence) | open — no such file in `bench/` |
| M3a | Publish the matching rule (judge); if an LLM judge is added, its prompt is a versioned artifact | Part 6 M3 caveat; Part 2.3 §2 | `helpers/bench/judge.py` | confirmed | partial — deterministic judge exists (`judge.py`); not yet published in scorecard output |
| M3b | Runner mode that scores OCR's own JSON output under the identical judge; one table tool × {F1, P, R, FP-rate, tokens, wall-time} | Part 6 M3; Part 7 §5 | new runner code | confirmed (absence) | open |
| M3c | Encode caveat: cross-tool numbers comparable only under the same judge | Part 6 M3 caveat | scorecard text | confirmed | open |
| M3d | Inspect the AACR dataset before building the adapter (contents never inspected by the analysis) | Part 6.5 external caveat | Hugging Face `Alibaba-Aone/aacr-bench` | external | open — mandatory investigation task |
| M4 | Populate corpus ≥30 entries: locked positives from confirmed findings, negatives from correctly-rejected leads, ≥3 dep-CVEs, ≥5 public-app entries (OWASP Juice Shop/WebGoat pinned commits) | Part 6 M4; Part 3.4 §1; Part 7 §4 | `helpers/bench/corpus_seed/` | confirmed | partial — 3 entries (`corpus_seed/absence.json`, tracked); 27+ needed |
| M4a | Wire `bench.run` into CI as regression gate (exit 1 on locked-miss) | Part 6 M4; Part 7 §4 | repo CI | confirmed (absence) | open — no test workflow in `.github/workflows/` |
| M5 | ≥3 runs per benchmark config; report mean ± range | Part 6 M5; Part 2.3 §5; Part 7 §6 | bench runner + scorecard | confirmed (absence) | open |
| M6 | Token/latency columns in scorecard from `cost.py` records; `$ / confirmed-TP` derived column | Part 6 M6; Part 7 §6 | `helpers/sec_overlay/cost.py`, `bench/tally.py` | confirmed | open — `tally.py` has no token/latency columns |

## Tier 1 — Review-mode parity (P items, Part 6 + Part 7 Milestone 2)

| Id | Item | Analysis section | Analysis file:line targets | Claim verification | Current status + evidence |
|----|------|------------------|---------------------------|--------------------|---------------------------|
| P1a | Sibling-diff visibility: include sibling diffs (or on-request excerpts) in the review-file prompt for files in the same bundle | Part 6 P1; Part 4 row 4b; Part 7 §8 | `review_agent.py:60-61` (analysis cite) | confirmed — bare paths still rendered at `review_agent.py:56-60` (`- {p}`) | done (Task 10) — `render_review_prompt(sibling_diffs=..., cap_tokens=...)` renders `{{SIBLING_DIFFS}}` largest-first with `omitted (token cap)` marker + `(diff included below)` annotation; `cli.run_review` prepare passes unit-mate diffs. Deferred: single-file units get non-mate sibling diffs only under REQ-P4's budget (Task 12) |
| P1b | Real dispatch-time bundling: extend groups (basename-stem pairs, header/impl, interface/impl, test/subject, import-adjacency from `graph.py`); one subagent per bundle; cap bundle token size | Part 6 P1; Part 4 row 4; Part 7 §8 | `bundle.py`, `graph.py` | confirmed | done (Task 10) — added C/C++ header-impl (`.h/.c`, `.hpp/.cpp`) + interface/impl stem (`svc.ts`/`svc.impl.ts`) pairing and `MAX_UNIT_TOKENS=50_000` first-fit split (`group_bundles(diffs=...)`). Deferred: `import_adjacency(graph_json)` grouping (SPEC-optional; review mode must not require `kb/graph.json`) |
| P2 | Rule docs 9 → 36; priority order terraform, yaml, github_workflows, github_config, package_json, cargo_toml, pom_xml, composer_json, build_gradle, c, cpp, protobuf, graphql, prisma, json, properties, nix, bicep, then the rest; Apache-2.0 attribution per file; glob added to `BUILTIN_PATH_RULE_MAP` same commit | Part 6 P2; Part 3.4 §7; Part 4 row 5; Part 7 §9 | `rules/rule_docs/`, `rule_glob.py` | confirmed | done — Task 11: 27 docs ported (attribution + 5-family blocks), map = OCR 35 patterns + `**/*`, exact order; 197 rule tests green |
| P3 | Optional per-file plan phase above a line threshold; plan JSON injected into the review-file prompt; skip below threshold (OCR: `agent.go:1230-1236`) | Part 6 P3; Part 4 row 6; Part 1.7; Part 7 §12 | review prepare path | confirmed (absence) | open |
| P4 | Hard token budget for review mode: OCR estimate shape (`estimate.go:55-68`), look-ahead dispatch gate, `skipped(budget)` manifest entries, `budget_exceeded` in output, exit 0 on partial; keep audit-mode soft semantics | Part 6 P4; Part 4 rows 3+12; Part 1.7; Part 7 §10 | `profile.py:42`, review dispatch | confirmed — `token_budget` appears only in `profile.py:42` docstring | open |
| P4a | Token-aware large-file guard (OCR drops files over 80% of model context) vs current 5000-line cap | Part 4 row 3; Part 1.2 §2 | `file_select.py` | confirmed | open — `file_select.py` caps by line count only |
| P5 | Review input modes: `--commit <sha>` and dirty-workspace review (staged+unstaged+untracked) | Part 6 P5; Part 4 row 1; Part 7 §11 | `cli.py` review args | confirmed — no such flags at `cli.py:630-634` | open |
| P6 | Wire live reflection: replace literal `{}` with real review-filter verdicts; keep fail-open `ReflectionSkip` + `PROTECTED_SUBJECT_CLASSES` | Part 6 P6; Part 3.4 §4; Part 4 row 8; Part 6.5; Part 7 §7 | `cli.py:553`, `reflection.py:257-259` | confirmed — `cli.py:553` passes literal `{}` | open |
| P7 | Consolidated `review_result.json`: status, findings with severity/rule, skips, retractions, ledger, budget flag, manifest, per-phase tokens (mirror OCR `output.go:283-301`) | Part 6 P7; Part 4 row 17; Part 7 §13 | new module | confirmed (absence) | open — `review_ledger.json` + `review_comments.json` exist separately; no consolidated file |
| P8 | `--background` / `--background-file` with OCR sanitization (size cap, control-char strip, delimiter-smuggle guard) + `redactor.safe_for_prompt` | Part 6 P8; Part 4 row 31; Part 7 §14 | `cli.py`, `redactor.py` | confirmed (absence) | open |
| P9 | Judge severity write-back (bug): `severity-inflated`/`downgrade` must produce a visible downgraded severity (write-back with history entry, or derived-severity rendering) | Part 6 P9; Part 3.4 §5d; Part 6.5; Part 7 §2 | `calibrate.py:214-227` | confirmed — current code lowers `risk_score` with history event, never writes `f.severity` (`calibrate.py:214-236`) | open |

## Tier 2 — Product shell (S items, Part 6 + Part 7 Milestone 3)

| Id | Item | Analysis section | Targets | Claim verification | Current status |
|----|------|------------------|---------|--------------------|----------------|
| S1 | GitHub Action + PR comment poster; severity routes inline-vs-summary like OCR's `post-review-comments.js`; SARIF slots into code-scanning upload | Part 6 S1; Part 4 row 22; Part 1.7 (always `event: COMMENT`); Part 7 §15 | new `action.yml` + poster | confirmed (absence) | open |
| S2 | `sessions list/show` rendering over the sidecar + review ledgers | Part 6 S2; Part 4 row 14 context; Part 7 §17 | `cli.py`, `repo_memory.py` | confirmed (absence) | open — only `memory --target` exists |
| S3 | `ASSURANCE_CASE.md` for the harness: trust boundaries (repo text → prompts [envelope + redactor], subagent writes [write-guard], target never executed/modified), countermeasures cited with file:line; OCR's shape: actors, boundaries, threats, Saltzer–Schroeder, OWASP/CWE, CI checks | Part 6 S3; Part 4 row 28; Part 1.6; Part 7 §16 | new doc | confirmed (absence) | open |
| S4 | `did-you-mean` flag suggestions + `rules check <file>` debug command (`rule_glob` has the resolver) | Part 6 S4; Part 4 row 32; Part 1.1; Part 7 §17 | `cli.py`, `rule_glob.py` | confirmed (absence) | open |

## Milestone 4 / Tier 3 — Press the advantage

| Id | Item | Analysis section | Claim verification | Current status |
|----|------|------------------|--------------------|----------------|
| T3a | Fast review tier: position gate + reflection + receipt gate only, no critic/validate; token-comparable row vs OCR's 385K; full ladder stays as "assured" tier | Part 6 risk §2; Part 7 §18 | confirmed (absence) | open |
| T3b | Publish FP-rate on negatives, per class | Tier 3; Part 7 §18 | confirmed | partial — `tally.py` computes `fp_rate`; per-class publishing + headline placement open |
| T3c | Verified-fix rate (`fixed`/`verified-static` proportion) in scorecard | Tier 3; Part 7 §18 | confirmed (absence) | open |
| T3d | Coverage-honesty audit: unsupported-coverage-claim rate per run | Tier 3; Part 7 §18 | confirmed (absence) | open |
| T3e | Security slice: AACR ground truth filtered to security-category issues; publish both tools' scores | Tier 3; Part 2.3 §6; Part 7 §18 | external (depends M3d) | open |
| T3f | Variance bars in published table | Tier 3 (= M5) | — | covered by M5 |
| T3g | CVSS/risk score-vs-human-triage agreement | Tier 3 | confirmed (absence) | open — analysis conditions it on "once corpus exists" |
| T3h | `fixed`/`verified-static` counts in the headline table | Tier 3 | confirmed (absence) | open (same mechanism as T3c) |

## Part 2.3 measurement-critique requirements (binding on sec-overlay's own benchmark)

| Id | Requirement | Analysis section | Status |
|----|-------------|------------------|--------|
| R1 | Reproducible from the repo: harness code, scoring script, repo/PR list, one-command run | Part 2.3 §1 | open — satisfied via M2 + M3b + a documented run command |
| R2 | Hit criterion defined and published | Part 2.3 §2 | partial — `judge.py` defines it (class + file + line ≤ 12 + fingerprint, CVE-match for deps); publishing in the scorecard is open |
| R3 | Inter-annotator story for our own corpus: annotation protocol, adjudication, disagreement handling stated | Part 2.3 §3 | open |
| R4 | Non-confounded comparison: state the scope confound; grade OCR under the identical judge | Part 2.3 §4 | open — via M3b + report text |
| R5 | Variance, repeated runs | Part 2.3 §5 | = M5 |
| R6 | Negative entries in the corpus | Part 2.3 §6 context; Part 2.4 | already-done — `corpus.py` supports `kind=negative`; keep |
| R7 | Security-specific slice | Part 2.3 §6 | = T3e |

## Part 3.4 weaknesses (each mapped or dispositioned)

| Id | Weakness | Mapping | Status + evidence |
|----|----------|---------|-------------------|
| W1 | Bench corpus empty | M4 | partial (3 entries) |
| W2 | No automatic driver | M2 | open |
| W3 | No F1 | M1 | open |
| W4 | Live reflection not wired in review mode | P6 | open |
| W5a | `phase_gate._parse_ref` rejects `file:line — prose` | fixed pre-analysis | already-done — `phase_gate.py:31` `_parse_ref` handles it (analysis confirmed at `0a65ee9`) |
| W5b | calibrate skips `needs-deployment-testing` | fixed pre-analysis | already-done — `calibrate.py:29` `_SCOREABLE` includes NDT |
| W5c | `repo_slug` monorepo collision | fixed pre-analysis | already-done — `repo_memory.py:93-98` includes subpath |
| W5d | Judge severity write-back | P9 | open |
| W5e | `report.md` renders confirmed/fixed only; NDT-heavy repo reads near-clean | partially mitigated per analysis | already-done — `report.py:175` `render_ndt`, `:278` NDT never folded, `:346` NDT count line; NDT section foregrounded above confirmed |
| W6 | Documentation drift recurring bug class | constraint | already-managed — `tests/test_docs_invariants.py` CI-guarded; every new documented constant gets an assertion (binding DoD rule) |
| W7 | Rule coverage 9 vs 36 | P2 | done — 36 rule docs (27 ported Task 11); `BUILTIN_PATH_RULE_MAP` = OCR 35 patterns + `**/*` |

## Part 4 gap-matrix rows not already covered by M/P/S/T3 (disposition-required)

| Id | Row | OCR capability | Disposition demand |
|----|-----|----------------|--------------------|
| G18 | Row 18 | Text/terminal UX: ANSI output, suggestion diffs, viewer TUI, VS Code extension | disposition-required |
| G19 | Row 19 | Multi-provider LLM (24 presets, 3 protocols) | disposition-required (analysis: "n/a by design; skip") |
| G20 | Row 20 | Delegation mode (LLM-free rule+file handoff) | disposition-required (analysis: "low value; its whole product is the delegate") |
| G21 | Row 21 | Deliberate MCP external-tool routing into the review loop | disposition-required |
| G2 | Row 2 | Whole-repo scan speed/cost ("OCR on speed/cost") | addressed by T3a fast tier |
| G13 | Row 13 | Cost accounting — sec-overlay already wins | context, no action |
| G14/15/16/23–27/30/33/34 | Rows where sec-overlay wins or ties | advantage inventory | context — feeds Tier 3 publishing + S3 |

## Part 1.7 fine detail (Pass A rows D1–D5, D8; Pass B rows D6, D7, D9, D10)

| Id | Detail | Use | Status |
|----|--------|-----|--------|
| D1 | OCR token-estimate formula: `diffTokens + 2000 + 400 + (diffTokens + 2000)×7 + 700×7` (`estimate.go:55-68`) | input to P4 estimate shape | spec input |
| D2 | OCR reflection protected subjects list (memory safety, concurrency, linkage, behavioral change, unused parameters) | already ported | already-done — `reflection.py` `PROTECTED_SUBJECT_CLASSES` (D-16) |
| D3 | OCR plan-skip threshold: `insertions + deletions < PlanModeLineThreshold` | input to P3 | spec input |
| D4 | OCR manifest item states (`selected, completed, reused, failed, waived`) + failure classes (`provider, timeout, cancelled, configuration, input, budget, panic, unknown`) | vocabulary input to P4 manifest entries | spec input |
| D5 | OCR exit-code contract: non-zero only for run-level failure or all-items-failed; budget stop with coverage exits 0 | input to P4 | spec input |
| D6 | *(missed-on-pass-A)* OCR has no cross-comment dedup in review mode (scan only) | sec-overlay opportunity note | disposition-required |
| D7 | *(missed-on-pass-A)* OCR sends diffs to providers unredacted (`manifest.go:650-687` is the only sanitizing) | cite as sec-overlay advantage in S3 + comparison table | folded into S3 + T3 publishing |
| D8 | OCR review-mode bundling claim is FALSE (README marketing; `agent.go:673` dispatches per file) | P1 marketing counter; never describe P1 as "porting OCR's bundling" | spec input (refuted-claim guard) |
| D9 | *(missed-on-pass-A)* OCR GitHub Action posts every review as `event: "COMMENT"`; severity routing is inline-vs-summary placement only | input to S1 spec | spec input |
| D10 | *(missed-on-pass-A)* OCR preview struct has counts + will-review/exclude-reason only; no rules, no token estimates | sec-overlay `--prepare` may exceed it (add per-file token estimate to prepare output under P4) | folded into P4 |

## Pass B additions from Parts 1, 2, 5 (X rows, all missed-on-pass-A)

| Id | Item | Analysis section | Disposition demand |
|----|------|------------------|--------------------|
| X1 | OCR mid-loop memory compression (`llmloop/compression.go`) | Part 1.2 §5 | disposition-required |
| X2 | OCR two retry layers + `RetryCollector` human-readable retry report | Part 1.4 | disposition-required |
| X3 | OCR `session comments` severity/category filters | Part 1.1 | folded into S2 scope decision |
| X4 | OCR non-GitHub CI recipes (GitLab, Bitbucket, Gerrit, GitFlic, Codeup) | Part 1.5 | disposition-required |
| X5 | OCR npm per-platform binary distribution + VS Code extension | Part 1.5 | folded into G18 disposition |
| X6 | OCR provider wizard TUI (~2968 lines) + `ocr llm test` probe | Part 1.1 | folded into G19 disposition |
| X7 | OCR severity enum inconsistency (3-level plan scale vs 4-level tool enum) + no numeric confidence | Part 1.3 | context — sec-overlay advantage; feeds comparison table |
| X8 | OCR blog-post internal numbers (20k MAU, <5% FP, ~80% merged) are self-reported, not the benchmark | Part 2.1 | context — never cite as benchmark |

## Part 6.5 Verification Ledger rows

| Id | Ledger entry | Handling |
|----|--------------|----------|
| V1 | Refuted: "OCR bundles related files in review mode" | spec guard — P1 described as sec-overlay-original, never a port |
| V2 | Refuted: "all dogfooding defects open" (3 of 4 fixed) | reflected in W5a–W5c already-done rows |
| V3 | Refuted: "OCR Action escalates by severity" | reflected in D9 (S1 spec input) |
| V4 | Refuted: "~24k lines" (measured 27,538) | context only |
| V5 | Confirmed set (empty corpus, adapter, no F1, reflection `{}`, budget unenforced, missing review inputs, OCR unredacted) | re-verified this session; statuses above |
| V6 | Repo-doc-sourced (medium confidence): test counts, OCR corpus construction claims, CHANGELOG ~line cites | carry the confidence label; never restate as verified |
| V7 | External: AACR dataset contents uninspected; hit criterion undocumented | M3d mandatory investigation task |

## Honest risk assessment (Part 6, binding on the plan)

| Id | Risk | Plan encoding |
|----|------|---------------|
| HR1 | Recall risk: gate ladder may crush recall on AACR general defects | first AACR run uses `--profile general`; iterate with `fp_feedback` + P2 rule docs before publishing |
| HR2 | Token cost of the adversarial ladder | T3a fast tier for the token-comparable row |
| HR3 | Judge selection bias | publish the judge (M3a), run OCR through it (M3b), accept losses it reports |

## Binding constraints (Part 7 + skill CLAUDE.md, not work rows)

1. `helpers/` stays stdlib-only; SAST binaries shelled, never imported.
2. `models.py` and `evidence.py` are sha256-frozen contracts; extend via new modules.
3. TDD: RED failing-test commit, then GREEN fix commit, per item.
4. Never weaken the FP ladder, tool-receipt gate, model-family diversity, or retract-only reflection.
5. Docs and code do not drift: same-commit doc updates; `test_docs_invariants.py` assertion for every new documented constant.
6. Milestone order M → P → S → advantage; measurement first; Milestone-2+ items record a before/after benchmark delta in the commit message.
7. If a measured result contradicts THE ANALYSIS, record the correction in the run report; never bend the corpus or judge.
8. Completion report includes the final scorecard next to OCR's published row (F1 25.10% / precision 33.90% / 385K tokens, Claude-4.6-Opus).

## Re-verification notes (Step 2 of the mission)

Rows re-verified stale relative to the analysis (closed between `0a65ee9` and current `main`):

1. Part 3.4 §1 "corpus_seed contains only a README" — stale: `absence.json` (3 entries) now exists and is git-tracked; skill `CLAUDE.md` §1 "corpus is gitignored" is itself now partially stale.
2. Part 4 row 4 "dispatch is one file per subagent" — stale: SCALE-01 `bundle.py` `ReviewUnit` dispatch landed (impl/test + locale/config pairs); P1b reduced from open to partial.
3. Part 3.4 §5e report NDT rendering "partially mitigated" — now fully rendered (`report.py` NDT section foregrounded above confirmed).
4. helpers README test counts moved (analysis said ~1,285/108; README now claims 98 files/954 tests in one place and 78/575 in another — repo-doc drift, both repo-doc-sourced).

All other analysis file:line cites for sec-overlay re-resolved at current source without drift
(`adapter.py:67,78`, `cli.py:553`, `profile.py:42`, `calibrate.py:214-236`,
`review_agent.py:56-60`, `cli.py:630-634`).

## Corrections logged during implementation (constraint 7)

1. REQ-M4 (seed corpus): `absence.json` held two `lifecycle: locked` synthetic
   positives on `fixtures/absence_repo`. A deterministic-only CI scan cannot
   CONFIRM (confirmation needs the adversarial LLM pass), and the absence rules
   are not part of the smoke-scan detection gate, so a `locked` status there
   would regress the offline gate for a reason unrelated to detection quality.
   Both entries were changed to `open`. The two `locked` positives now live only
   in `dogfood.json` at `fixtures/vulnerable_repo` (`secrets` app.py:9, `sqli`
   app.py:18), which the smoke scan does exercise. This corrects the corpus to
   what the CI gate can actually assert; it does not weaken any confirmation gate.

2. REQ-P4 (token budget), naming: the plan text implied one `estimate_tokens`
   would grow into the budget projection. That would overload the raw size
   primitive `bundle.py` and `review_agent.py` already share (`len // 4`) with a
   plan-loop cost formula, changing every existing caller's meaning. Instead
   `estimate_tokens` stays the raw primitive and a new
   `estimate_review_cost(diff_text)` holds the projection. Same numbers as the
   plan; the split keeps the shared primitive stable.

3. REQ-P4 dispositions (rows carried in this plan):
   - P4a (per-file over-cap exclusion): DONE — files over `FILE_BUDGET_FRACTION`
     (0.8) of the budget are excluded as `too-large-tokens` before review.
   - D1/D4/D5/D10 (budget constants and the plan-loop cost shape): DONE —
     `PLAN_PROMPT`, `PLAN_OUT`, `ROUNDS`, `ROUND_OUT`, `FILE_BUDGET_FRACTION`,
     `BUDGET_SKIP_NOTE` in `review_budget.py`; asserted in
     `tests/test_docs_invariants.py`.
   - P1a (single-file units get non-mate sibling diffs under budget): the
     Task-10 deferral is re-dispositioned to DONE — bounded by the Task-12
     budget rather than pending it.
   - Bench: no-op — `bench.run` grades the audit pipeline, not review mode.
