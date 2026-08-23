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
