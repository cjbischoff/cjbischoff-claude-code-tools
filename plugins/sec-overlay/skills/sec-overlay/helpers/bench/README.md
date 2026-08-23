# bench — sec-overlay evaluation harness (dev-only)

Measures and locks in detection quality. Not part of the shipped harness. Three layers:

- **Layer A — detection benchmark.** A labelled corpus (positives to find, negatives
  to stay silent on) → clone@commit (or scan a local checkout) → scan via a swappable
  adapter → judge → precision/recall segmented by source & class.
- **Layer B — regression corpus.** Corpus entries have a `lifecycle`; a `locked`
  positive that stops being detected is a hard failure (`scorecard.regressed`).
- **Layer C — contract/wiring tests.** Live in the main suite
  (`tests/test_contracts.py`, `tests/test_wiring.py`) — prompt↔schema drift, backend
  reachability. Deterministic, no LLM.

## Modules
- `corpus.py` — `CorpusEntry`/`Corpus`, `load_corpus(dir)`. Entry = `{finding_id, kind
  (positive|negative), source (real-confirmed|dep-cve|synthetic|public-app), cls,
  repo_url|local_path, commit, file, line, description, lifecycle, package, cve}`.
- `judge.py` — `deterministic_match` (class+file+line-proximity+fingerprint; CVE for
  deps) then an optional injected `llm_judge` for fuzzy/root-cause credit.
- `tally.py` — precision/recall by source & class, FP-rate from negatives, regressions;
  `Scorecard.to_markdown()`/`to_dict()`. Synthetic recall is never blended into the
  headline (real-confirmed only).
- `adapter.py` — `ScanAdapter` protocol. `BinaryAdapter` drives a scanner binary (the
  Go migration); `WorkspaceAdapter` grades an already-scanned workspace (CC-skill flow);
  `CCSkillAdapter` is the documented seam for a native SDK driver. Two readers select
  what a `WorkspaceAdapter` grades: `reportable` (confirmed/fixed — the confirmation
  gate, default) and `tier1_detected` (any-status findings backed by a Tier-1 receipt —
  detection grading, never touches `reportable`).
- `run.py` — orchestrates clone/scan/judge/tally; resumable via a findings cache;
  exit 1 if any locked finding regressed. `--grade-mode {real,detection}` picks the
  reader (default `real`); `--only-local` skips http clone targets for an offline gate.
  `--repeats N` runs the benchmark N times into `run-<n>/` and writes an aggregate
  `scorecard_agg.{json,md}` (mean ± range per metric) via `run_repeated` (REQ-M5).
  Each run captures wall-time and sums per-repo token totals from every
  `workspaces/*/state.json` budget (via `sec_overlay.cost`), passing a `cost`
  record to `tally` so the scorecard carries cost/latency columns (REQ-M6).
- `tally.py` — also `aggregate_scorecards(cards)`: mean/min/max per metric
  (precision, recall, f1, fp_rate) across repeated runs; skips `None` metrics.
  `tally(..., cost=...)` attaches a cost block (`tokens`, `wall_time_s`,
  `usd_per_confirmed_tp` = USD estimate / real-confirmed TP, `None` when no TP);
  `to_markdown` renders a "Cost & latency (estimates)" section, and per-class
  FP-rate rows already publish in the "By class" table (REQ-M6, T3b).
  `tally(..., findings_by_id=...)` attaches a verified-fix block
  (`fixed`, `confirmed`, `rate` = (`FIXED` ∪ `verified-static`) / confirmed
  true-positives) and a headline markdown row; `run.py` plumbs the per-repo
  findings in, and the rate stays absent when no fix data is supplied (REQ-T3c/T3h).
- `aacr_adapter.py` — `aacr_entries(rows)` maps AACR review-dataset rows to
  `source="aacr"` corpus entries (excluded from the real-confirmed headline).
- `ocr_ingest.py` — `ocr_findings(json_text)` parses `ocr review --format json` into
  benchmark-only CONFIRMED findings tagged `llm-claimed:ocr` (never harness findings).

## Run
```bash
# grade workspaces the operator scanned by driving the CC skill (confirmation):
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
# or drive a scanner binary (future Go build):
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --binary "sec-overlay-go scan"
# offline detection-regression gate (CI): a deterministic scan never CONFIRMS, so grade
# whether a Tier-1 receipt located each locked ground-truth finding instead.
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench \
  --workspaces <dir> --grade-mode detection --only-local
```

`.github/workflows/sec-overlay-tests.yml` runs the last form: it smoke-scans
`fixtures/vulnerable_repo` into a workspace, then gates on the two `locked` dogfood
entries staying detected. Detection mode exists because `reportable` returns nothing
for a deterministic-only scan (confirmation needs the adversarial LLM pass) — the
confirmation gate stays unchanged and cannot run in CI.

## Annotation protocol

The internal corpus is labeled by a single maintainer. Each entry records a ground
truth (`kind` positive/negative, `cls`, `file`, `line`) tied to a public advisory,
a dep-CVE lockfile, or a synthetic fixture. Adjudication is single-maintainer: one
person decides each label; there is no second annotator and no inter-annotator
agreement statistic, and none is invented. When the deterministic judge disagrees
with a label — a positive it cannot match, or a negative it flags — the maintainer
resolves it by correcting the corpus entry or the rule, and records the correction
in `docs/parity/EXTRACTION.md`. Labels are never edited to force a pass (see
`corpus_seed/README.md`).

## Reproducing the benchmark

One command reproduces the benchmark end to end over the committed seed corpus:

```bash
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
```

It clones each target at its pinned commit (or scans a local checkout), judges every
finding under one judge, and writes `scorecard.{json,md}`. `--repeats N` runs it N
times and adds `scorecard_agg.{json,md}` (mean ± range). See the `## Run` section for
the binary and offline-detection variants.

## Scope confound

The scorecard states a scope confound, and any cross-tool comparison inherits it: a
deterministic file selection reviews less code, so a lower token count partly measures
doing less, not doing better. A token gap is not a pure efficiency signal. When a
cross-tool run grades OCR, OCR is scored under the same judge (REQ-M3.3); the losses
it reports are accepted and published unedited.

## Corpus
`corpus_seed/` ships committed (public entries only — see `corpus_seed/README.md`).
The two `locked` positives live in `dogfood.json` at `fixtures/vulnerable_repo`
(`secrets` app.py:9, `sqli` app.py:18) — both semgrep-detectable, so the CI detection
gate can assert them. Grow the corpus every time the harness confirms/rejects a real
finding — that is Layer B. Never edit a corpus entry to force a pass. A `locked`
positive that goes undetected is a rule defect, not a corpus one.

Grading any positive needs a scanned workspace or `--binary`. `WorkspaceAdapter`
only reads findings. It runs no scan. An empty `--workspaces` directory therefore
reports `recall=0.0` and the run exits 1 (a locked positive counts as regressed). Do
not gate CI on that exit status without a pre-scanned workspace. To check the absence
rules alone, run `semgrep scan --config rules/absence fixtures/absence_repo` from
`helpers/`.

Scorecard metrics include F1 (`2PR/(P+R)`, `None` when precision or recall is
undefined or both are zero) in `overall`, per-source, and headline rows (REQ-M1).

## Headless driver (REQ-M2)

`driver.py` shells a headless agent run per corpus target (`DEFAULT_ARGV_TEMPLATE`:
`claude -p <instruction> --permission-mode acceptEdits`, `{target}`/`{workspace}`
substituted). `CCSkillAdapter` wraps it: drive, then grade the workspace with
`reportable`. A failed run records `{target, error}` on `driver.failures` and yields
zero findings for that target — never fabricated results. `bench.run`'s per-target
findings cache makes interrupted benchmark runs resumable.

## External datasets and cross-tool judging (REQ-M3)

Two optional adapters let the bench compare against outside data. Neither feeds the
harness; both stay inside the bench oracle.

### AACR review dataset (`aacr_adapter.py`)

`aacr_entries(rows)` maps rows from the `Alibaba-Aone/aacr-bench` code-review dataset
to `CorpusEntry` objects tagged `source="aacr"`. That source is excluded from the
real-confirmed headline, so AACR rows never move the parity number (`tally` guard).

Dataset shape, read from the live Hugging Face viewer on 2026-08-23 (one `default`
subset, one `train` split, 2,150 rows). Row columns:

| column | type | meaning |
|--------|------|---------|
| `project_main_language` | string | repo primary language |
| `pr_url`, `pr_source_commit`, `pr_target_commit` | string | pull-request coordinates |
| `pr_change_line_count` | int64 | diff size |
| `pr_category` | string | pull-request kind (e.g. "Bug Fix") |
| `is_ai_comment` | bool | true = model-authored review comment |
| `source_model` | string | model name when `is_ai_comment`; empty otherwise |
| `note` | string | the review-comment text |
| `path` | string | file the comment targets |
| `side` | string | diff side ("right") |
| `from_line`, `to_line` | int64 | comment line span |
| `category` | string | comment class |
| `context` | string | "File Level" / "Diff Level" / "Repo Level" |
| `label` | int64 | ground-truth flag |

Caveats — the viewer preview covered about 100 of 2,150 rows. In that preview:
`category` held only "Code Defect", "Maintainability and Readability", and
"Performance"; no distinct "Security" category value was observed (only three
case-insensitive "security" text hits across the whole scraped page). `label` showed
only the value 1. The full-corpus distinct-value distribution for `category` and
`label` is unverified — the parquet was not loaded in this environment. The T3e
security slice (Task 24) must re-check whether a Security category exists before it
depends on one.

### OCR cross-tool findings (`ocr_ingest.py`)

`ocr_findings(json_text)` parses the JSON that `ocr review --format json` emits
(top level `{"comments": [...], ...}`; each comment `{path, content, start_line,
end_line, severity?, category?}`) into benchmark-only `Finding` objects. Each carries
status CONFIRMED (so the judge scores it) and evidence source `llm-claimed:ocr`.
These objects exist only to score OCR through the same judge; they are never harness
findings and never satisfy the tool-receipt gate.
