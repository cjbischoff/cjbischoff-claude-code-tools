# OCR Parity + Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement every requirement in `docs/parity/SPEC.md` — measurement foundation first, then review-mode parity, then shell, then advantage metrics.

**Architecture:** All code lands in `skills/sec-overlay/helpers/` (stdlib-only Python). New behavior goes in new modules or additive functions; `models.py`/`evidence.py` are frozen. LLM dispatch stays in `SKILL.md`; the Python core only prepares prompts and consumes recorded returns.

**Tech Stack:** Python ≥3.12 stdlib, pytest, ruff, ty. External binaries (`claude`, `git`, `gh`) are shelled with injectable runners.

**Spec:** `plugins/sec-overlay/skills/sec-overlay/docs/parity/SPEC.md` (traceability to `docs/parity/EXTRACTION.md`).

## Global Constraints

- stdlib-only runtime; no new dependencies (C1).
- `models.py`, `evidence.py` frozen — extend via new modules (C2).
- Per requirement: RED commit (failing test) then GREEN commit (fix) (C3).
- Never weaken FP ladder, tool-receipt gate, family diversity, retract-only reflection (C4).
- Docs update in the same commit; new documented constants get a `test_docs_invariants.py` assertion (C5).
- Every commit staging a file in a folder with a tracked `README.md` also stages that README; every plugin commit stages `plugins/sec-overlay/CHANGELOG.md`; GREEN commits bump `plugin.json` version by Conventional-Commit semver (repo hooks).
- Milestone order: M → P → S → T3. Milestone-2+ commit messages record a before/after benchmark delta (C6).
- All test/lint commands run from `skills/sec-overlay/helpers/`: `uv run pytest tests/<file> -q`, `uv run ruff check`, `uv run ty check`.
- Git commits run from the repo root (`helpers/` contains an unrelated nested `.git`).

---

## Milestone 1

### Task 1: REQ-M1 — F1 in tally
**Files:** Modify `helpers/bench/tally.py` (`_metrics`, `to_markdown`); Test `helpers/tests/test_bench.py` (append).
**Produces:** `_metrics(...)["f1"]: float | None`; markdown F1 lines.
- [ ] RED: `test_f1_computed` — results with tp=3, fn=1, fp=1 (P=0.75, R=0.75) assert `abs(m["f1"] - 0.75) < 1e-9`; `test_f1_none_when_undefined` — empty results assert `m["f1"] is None`. Commit `test(sec-overlay): add failing f1 scorecard tests`.
- [ ] GREEN: in `_metrics`, `f1 = 2*precision*recall/(precision+recall) if precision is not None and recall is not None and (precision+recall) else None`; render in headline + Overall + by-source rows. Update `bench/README.md`. Commit `feat(sec-overlay): compute f1 in bench scorecard`.

### Task 2: REQ-P9 — judge severity write-back
**Files:** Modify `helpers/sec_overlay/calibrate.py`; Test `helpers/tests/test_calibrate.py` (append).
**Produces:** after `run_calibrate`, a finding with `judge_verdict in ("severity-inflated","downgrade")` has `f.severity` lowered to the band of its post-downgrade `risk_score` plus history event `calibrate:severity-downgraded {from,to}`.
- [ ] RED: build a CONFIRMED finding, `severity=CRITICAL`, `judge_verdict="downgrade"`, low derived score; after calibrate assert `f.severity != Severity.CRITICAL` and history event present; second test: no verdict → severity unchanged. Commit.
- [ ] GREEN: add `_severity_for_score(score) -> Severity` (documented band map, inverse of `_severity_floor`); apply write-back inside the existing downgrade branch. Same-commit docs: `helpers/sec_overlay/README.md` calibrate row, `test_docs_invariants.py` assertion for the band map if documented as constants. Commit.

### Task 3: REQ-M2 — headless driver
**Files:** Create `helpers/bench/driver.py`; Modify `helpers/bench/adapter.py` (CCSkillAdapter delegates); Test `helpers/tests/test_bench_driver.py`.
**Produces:** `HeadlessDriver(argv_template: list[str], *, runner=subprocess.run, timeout=3600)`; `CCSkillAdapter(driver=None)` — `scan(repo_path, workspace)` runs the driver (template tokens `{target}`, `{workspace}`) then returns `reportable(workspace)`; a nonzero exit or exception returns `[]` and appends `{"target","error"}` to `driver.failures`; per-target cache handled by `bench.run`'s existing findings cache.
- [ ] RED: fake runner asserts substituted argv; failure recorded, no raise, empty list; success path reads a seeded workspace finding. Commit.
- [ ] GREEN: implement; default argv template documented in `bench/README.md` (`claude -p <review prompt> --permission-mode acceptEdits ...` shape). Commit.

### Task 4: REQ-M4 — corpus ≥30 + CI gate
**Files:** Modify `helpers/bench/corpus_seed/` (new JSON files: `dogfood.json`, `dep_cves.json`, `public_apps.json`, `negatives.json`); Create `.github/workflows/sec-overlay-tests.yml`; Test `helpers/tests/test_bench.py` (append).
- [x] RED: `test_seed_corpus_has_min_entries` — `load_corpus(corpus_seed)` ≥30, validates clean, ≥3 `dep-cve`, ≥5 `public-app`, ≥1 negative, ≥1 locked. Commit. (`50664a1`)
- [x] GREEN: 30 committed public entries; detection-grading path (`tier1_detected` + `--grade-mode detection` + `--only-local`, `reportable` untouched); CI workflow smoke-scans fixtures and gates on the two locked dogfood entries; docs updated; absence.json locked→open correction logged in `docs/parity/EXTRACTION.md`. Commits `9eab7c8` (plugin) + `198e932` (CI workflow + root docs).

### Task 5: REQ-M3 — AACR adapter + judge publishing
**Files:** Create `helpers/bench/aacr_adapter.py`, `helpers/bench/ocr_ingest.py`; Modify `helpers/bench/tally.py` (headline guard already excludes non-real sources — add test), `helpers/bench/README.md`; Test `helpers/tests/test_aacr_adapter.py`.
**Produces:** `aacr_entries(rows: list[dict]) -> list[CorpusEntry]` (`source="aacr"` — extend `SOURCES` tuple in `corpus.py`); `ocr_findings(json_text: str) -> list[Finding]` mapping `ocr review --format json` comments to `Finding` (status CONFIRMED for judging, evidence `llm-claimed:ocr` — benchmark-only objects, never harness findings); scorecard markdown gains judge-statement + same-judge caveat block.
- [x] Investigate AACR dataset (M3d): fetch dataset card/schema; record findings in `bench/README.md`; if unreachable, document the assumed row shape and mark untested. (schema from live HF viewer 2026-08-23; full-corpus `category`/`label` distribution unverified — noted in `bench/README.md`)
- [x] RED: fixture AACR rows → entries with source `aacr`; tally test proves `aacr` results never move `_real` headline; `ocr_ingest` fixture JSON → findings with file/line/severity. Commit. (`test_aacr_adapter.py`)
- [x] GREEN: implement both; append judge statement text to `Scorecard.to_markdown`. Commit. (`aacr_adapter.py`, `ocr_ingest.py`, `SOURCES += ("aacr",)`, same-judge block in `tally.py`)

### Task 6: REQ-M5 — variance
**Files:** Modify `helpers/bench/run.py` (`--repeats`), `helpers/bench/tally.py` (`aggregate_scorecards(cards: list[Scorecard]) -> dict` mean ± min/max for P/R/F1/FP-rate); Test `helpers/tests/test_bench.py` (append).
- [x] RED: three synthetic scorecards → mean/range asserted. Commit.
- [x] GREEN: implement; `run.py` loops repeats into `run_dir/run-<n>/`, writes `scorecard_agg.{json,md}`. Commit.

### Task 7: REQ-M6 — tokens/latency/$ columns + per-class FP publishing
**Files:** Modify `helpers/bench/run.py` (per-repo wall-time capture; optional token totals read from each workspace's `state.json` budget via `cost.py` aggregation), `helpers/bench/tally.py` (columns `tokens`, `wall_time_s`, `usd_per_confirmed_tp` labeled estimate); Test append.
- [x] RED: synthetic run record with tokens/time → columns in `to_dict`/markdown; per-class fp-rate rows already exist — assert they render in the published table section. Commit.
- [x] GREEN: implement. Commit.

### Task 8: REQ-R3 + REQ-R1/R4 — protocol + reproducibility docs
**Files:** Modify `helpers/bench/README.md` (annotation protocol, adjudication, one-command reproduce, scope-confound statement); Modify `helpers/tests/test_docs_invariants.py` (assert sections exist).
- [x] RED: docs-invariants test for the three section headings. Commit. GREEN: write sections. Commit.

## Milestone 2 (each GREEN commit records before/after bench delta from `python -m bench.run` over the internal corpus)

### Task 9: REQ-P6 — wire live reflection
**Files:** Modify `helpers/sec_overlay/reflection.py` (add `recorded_verdict_source(ws, *, base, head)`), `helpers/sec_overlay/cli.py` (`reflection_source` param + `--prepare-reflection` mode rendering `agents/review-filter.md` prompts from post-profile kept findings into `runs/reflection_prompts/`), `SKILL.md` (dispatch step); Test `helpers/tests/test_reflection.py`, `helpers/tests/test_cli_review.py` (append).
**Produces:** verdict envelope `{"base","head","verdict": {id: analysis}}` recorded under agent label `review-filter-<agent_label(path)>`; missing/mismatched → raise → existing `ReflectionSkip` fail-open path.
- [x] RED: recorded verdict retracts non-protected finding end to end through `run_review`; protected class refused; missing verdict → `ReflectionSkip` in ledger (not silent keep-all). Commit. (`6550299`)
- [x] GREEN: implement; replace `{}` at the `apply_verdict` call with `reflection_source(record.path)`. Docs: cli docstring, module READMEs, SKILL.md step. Commit. Bench delta: no-op — REQ-P6 changes review mode only; `bench.run` grades the audit pipeline (`--binary`/`--workspaces`), which this change does not touch. Regression proof is the full suite (1395 passed), including `test_bench.py`.

### Task 10: REQ-P1 — sibling diffs + richer bundling
**Files:** Modify `helpers/sec_overlay/review_agent.py` (`render_review_prompt(..., sibling_diffs: dict[str,str] | None, cap_tokens: int)`), `helpers/sec_overlay/bundle.py` (header/impl + stem-pair rules; optional `import_adjacency(graph_json)` grouping; `MAX_UNIT_TOKENS` split), `helpers/sec_overlay/cli.py` prepare path; Tests append to `test_review_agent.py`, `test_bundle.py`.
- [x] RED: prompt includes sibling diff fenced blocks; oversized sibling truncates with `omitted (token cap)` marker; `.h/.c` pair groups; token cap splits a unit. Commit. (`de8a8b0`)
- [x] GREEN: implemented. `estimate_tokens` landed in new `review_budget.py` (Task 12 reuses it); `render_review_prompt(sibling_diffs, cap_tokens)` + `{{SIBLING_DIFFS}}` token; `group_bundles(diffs=, max_unit_tokens=)` C-pair/impl-stem/split; `cli.run_review` prepare passes unit-mate diffs. Deferred (EXTRACTION P1a/P1b): single-file non-mate siblings → Task 12 budget; `import_adjacency` (SPEC-optional). Bench delta: no-op — `bench.run` grades the audit pipeline, not review mode (Task 9 convention). Commit.

### Task 11: REQ-P2 — rule docs 9 → 36
**Files:** Create 27 docs under `skills/sec-overlay/rules/rule_docs/` (analysis priority order); Modify `helpers/sec_overlay/rule_glob.py` (`BUILTIN_PATH_RULE_MAP` globs, OCR order); Test `helpers/tests/test_rule_glob.py` (count, attribution line `Adapted from open-code-review (Apache-2.0)`, map→doc resolution).
- [x] RED: count/attribution/resolution tests. Commit. (`2b10606`)
- [x] GREEN: ported 27 docs from OCR `rule_docs/` with attribution line + 5-family exclusion blocks; `BUILTIN_PATH_RULE_MAP` = OCR's 35 patterns + `**/*` catch-all, exact order; updated `rules/rule_docs/README.md`, `helpers/sec_overlay/README.md`. All 197 rule tests + full 1541 suite/ruff/ty green. Bench delta: no-op — `bench.run` grades the audit pipeline, not review mode (Task 9 convention).

### Task 12: REQ-P4 — hard token budget + token-aware guard
**Files:** Create `helpers/sec_overlay/review_budget.py` (`estimate_tokens(diff_text) -> int` using OCR shape constants `PLAN_PROMPT=2000, PLAN_OUT=400, ROUNDS=7, ROUND_OUT=700`; `BudgetGate(budget)` with `.admit(estimate) -> bool` look-ahead); Modify `cli.py` (`--token-budget`, skip-marking `skipped(budget)`, `budget_exceeded` flag, prepare per-file estimates), `file_select.py` (token-variant too-large exclusion when budget set); Tests `test_review_budget.py` + append `test_cli_review.py`, `test_docs_invariants.py` (constants).
- [x] RED: estimator formula test; gate admits until projected breach then refuses all; run_review with tiny budget seals partial, exit 0, manifest notes `skipped(budget)`, result flag true. Commit.
- [x] GREEN: implement. Commit.

### Task 13: REQ-P5 — `--commit` + `--workspace-dirty`
**Files:** Modify `helpers/sec_overlay/diffscope.py` (`dirty_file_records(root, runner)` staged+unstaged+untracked; commit mode reuses `resolve_ref_sha(f"{sha}^")`), `cli.py` (flags, mutual exclusion, resume identity records mode); Tests append `test_diffscope.py`, `test_cli_review.py`.
- [x] RED: fixture repo — commit mode diffs `sha^..sha`; dirty mode lists staged+unstaged+untracked records; `--commit` with `--base` exits 2. Commit.
- [x] GREEN: implement. Commit.

### Task 14: REQ-P3 — per-file plan phase
**Files:** Create `skills/sec-overlay/agents/review-plan.md` (strict-JSON plan prompt, severity-ordered `issues[]`); Modify `review_agent.py` (`render_plan_prompt`, `{{PLAN_GUIDANCE}}` token in `render_review_prompt`), `cli.py` (`--plan`, threshold `PLAN_LINE_THRESHOLD = 100` documented, prepare writes plan prompts; consume injects recorded plan JSON, fail-open skip); Tests append.
- [x] RED: below threshold no plan prompt; above threshold prompt written; recorded plan text appears in review prompt; invalid plan → prompt without guidance + recorded skip. Commit.
- [x] GREEN: implement; docs-invariants pin threshold; agents/README row. Commit.

### Task 15: REQ-P7 — consolidated `review_result.json`
**Files:** Create `helpers/sec_overlay/review_result.py` (`write_review_result(ws, *, findings, dropped, declines, retractions, skips, manifest, budget_exceeded, tokens, base, head, model, profile, tier) -> Path`); Modify `cli.py` (call last); Test `test_review_result.py`.
- [x] RED: zero-finding and populated runs produce the full documented key set. Commit.
- [x] GREEN: implement via `workspace._atomic_write`. Commit.

### Task 16: REQ-P8 — background context
**Files:** Create `helpers/sec_overlay/background.py` (`load_background(text|path) -> str`: 1 MB cap → `ValueError`, control-char strip, envelope-delimiter neutralization, then `redactor.safe_for_prompt`); Modify `cli.py` (flags), `review_agent.py` (`{{BACKGROUND}}` in prompt inside envelope), `agents/review-file.md`; Tests `test_background.py` + append.
- [x] RED: cap exit 2; control chars stripped; secret aborts (`SecretsPresent`); prompt contains enveloped text. Commit.
- [x] GREEN: implement. Commit.

## Milestone 3

### Task 17: REQ-S3 — ASSURANCE_CASE.md
**Files:** Create `skills/sec-overlay/ASSURANCE_CASE.md`; Test append `test_docs_invariants.py` (citation file:line resolution walk + `ste_lint` clean).
- [x] RED: invariants test for required sections + resolvable citations. Commit. GREEN: write the case. Commit.

### Task 18: REQ-S1 — GitHub Action + poster
**Files:** Create `plugins/sec-overlay/action.yml`, `helpers/sec_overlay/pr_poster.py` (stdlib `urllib` GitHub API client; severity routing critical/high → inline, medium/low → summary; `event: COMMENT`); Test `test_pr_poster.py` (fake transport).
- [x] RED: routing + payload tests. Commit. GREEN: implement; actionlint the yml. Commit.

### Task 19: REQ-S2 — sessions list/show
**Files:** Modify `cli.py` (subcommands over sidecar `state.json` + review ledger; `show` takes `latest` or slug, `--severity` filter); Test append `test_cli_review.py` or new `test_sessions.py`.
- [x] RED: fixture sidecar → list row; show renders counts + filter. Commit. GREEN: implement. Commit.

### Task 20: REQ-S4 — rules check + did-you-mean
**Files:** Modify `cli.py` (`rules check <path>` printing doc + layer; argparse error hook via `difflib.get_close_matches`); Test append.
- [x] RED: resolver output test; misspelled subcommand names nearest. Commit. GREEN: implement. Commit.

## Milestone 4

### Task 21: REQ-T3a — fast/assured tiers
**Files:** Modify `cli.py` (`--tier`, recorded in manifest/result; fast skips plan + reflection-prepare requirement? No — fast keeps reflection, skips plan and marks tier for benchmark labeling; assured = full); Test append.
- [ ] RED: tier recorded; fast path skips plan even with `--plan`. Commit. GREEN: implement. Commit.

### Task 22: REQ-T3c/T3h — verified-fix rate
**Files:** Modify `helpers/bench/tally.py` (`verified_fix_rate` when run records carry fix data) + `run.py` plumb; Test append.
- [ ] RED/GREEN as above. Commits.

### Task 23: REQ-T3d — coverage-honesty rate
**Files:** Modify `helpers/bench/run.py` (read each workspace's `kb/coverage-ledger.json`; a run claiming complete with open surfaces = unsupported claim), `tally.py` column; Test append.
- [ ] RED/GREEN. Commits.

### Task 24: REQ-T3e — security slice
**Files:** Modify `helpers/bench/aacr_adapter.py` (security-category tag → `cls` mapping; slice label `aacr-security` in tally by_source seg); Test append.
- [ ] RED/GREEN. Commits.

### Task 25: Final — PARITY-AUDIT.md + smoke benchmark + completion report
- [ ] Run full test suite, ruff, ty; run `python -m bench.run` over internal corpus (deterministic adapter) for the final scorecard.
- [ ] Write `docs/parity/PARITY-AUDIT.md` walking EXTRACTION.md row by row.
- [ ] Re-read THE ANALYSIS against the audit; fix gaps.
- [ ] Completion report with pass counts, stale rows, scorecard vs OCR's published row.
