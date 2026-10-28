# evals

Behavioral eval cases for the plainspoken skill. This folder is for development only. It is not
part of the user-facing behavior of the plugin, and it needs no API key and no CI.

| File | Purpose |
|---|---|
| `cases.json` | 19 cases: 11 adapted from Clarity (MIT) and 8 new cases for `brief` and `rewrite`. Each case has an `id`, `mode`, `category`, `prompt`, `input`, `requirements`, and `prohibitions`. |
| `JUDGE.md` | The judging protocol: run rules, hard gates (including the `brief` fixed-format gate), 1-5 scores, and the report format. |

Requirements are semantic. Judge the meaning of the output, not its exact wording.

## Manual run

The run is manual. No script calls a model.

1. Install the plugin locally: `claude --plugin-dir plugins/plainspoken`.
2. Pick a case from `cases.json`. Open a fresh session for it. Do not reuse a session between
   cases.
3. Send the case `prompt`, then paste the case `input` as the source text.
4. Save the complete output.
5. Judge the output against the case `requirements` and `prohibitions` and the hard gates and
   scores in `JUDGE.md`. A hard-gate failure fails the case.
6. Record the case `id`, the model, the plugin version, the hard-gate result, and the scores.
7. Repeat for every case. To compare conditions, run each case again without the plugin, then
   judge the outputs blind.

The test `tests/test_evals.py` checks only that `cases.json` is well formed.
