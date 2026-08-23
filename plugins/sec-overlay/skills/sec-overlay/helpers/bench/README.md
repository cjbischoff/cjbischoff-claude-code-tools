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
  `CCSkillAdapter` is the documented seam for a native SDK driver.
- `run.py` — orchestrates clone/scan/judge/tally; resumable via a findings cache;
  exit 1 if any locked finding regressed.

## Run
```bash
# grade workspaces the operator scanned by driving the CC skill:
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
# or drive a scanner binary (future Go build):
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --binary "sec-overlay-go scan"
```

## Corpus
`corpus_seed/` is seeded from this project's real session findings (confirmed = locked
positives; correctly-rejected leads = negatives; one dep-CVE). Grow it every time the
harness confirms/rejects a real finding — that is Layer B.

`corpus_seed/absence.json` locks the absence-rule pair. Both positives must stay
detected. The negative must stay silent. Never edit a corpus entry to force a
pass. A `locked` positive that goes undetected is a rule defect, not a corpus one.

Grading the absence pair needs a scanned workspace or `--binary`. `WorkspaceAdapter`
only reads findings. It runs no scan. An empty `--workspaces` directory therefore
reports `recall=0.0` for these entries. That is an empty input, not a rule
regression.

The run also exits 1, because a locked positive counts as regressed. Do not gate
CI on that exit status without a pre-scanned workspace. To check the rules alone,
run `semgrep scan --config rules/absence fixtures/absence_repo` from `helpers/`.

Scorecard metrics include F1 (`2PR/(P+R)`, `None` when precision or recall is
undefined or both are zero) in `overall`, per-source, and headline rows (REQ-M1).

## Headless driver (REQ-M2)

`driver.py` shells a headless agent run per corpus target (`DEFAULT_ARGV_TEMPLATE`:
`claude -p <instruction> --permission-mode acceptEdits`, `{target}`/`{workspace}`
substituted). `CCSkillAdapter` wraps it: drive, then grade the workspace with
`reportable`. A failed run records `{target, error}` on `driver.failures` and yields
zero findings for that target — never fabricated results. `bench.run`'s per-target
findings cache makes interrupted benchmark runs resumable.
