# evals

Behavioral eval cases for the readme-keeper plugin. This folder is for development only. It is
not part of the user-facing behavior of the plugin, and it needs no API key and no CI.

| File | Purpose |
|---|---|
| `cases.json` | 15 cases for `create`, `update`, `check`, and `review`, including the `--research`, `--style fancy`, `--score`, and `--install-ci` flags. Each case has an `id`, `mode`, `category`, `prompt`, `input`, `requirements`, and `prohibitions`. A case may also have a `followup` string. |
| `JUDGE.md` | The judging protocol: run rules, hard gates, 1-5 scores, and the report format. Adapted from Clarity (MIT, Addy Osmani). |

Requirements are semantic. Judge the meaning of the output, not its exact wording.

## Manual run

The run is manual. No script calls a model.

1. Install the plugin locally: `claude --plugin-dir plugins/readme-keeper`.
2. Pick a case from `cases.json`. Build the small repo that the case `input` describes in a
   scratch directory, and open a fresh session there. Do not reuse a session or a repo copy
   between cases.
3. Send the case `prompt`, then give the case `input` as the repo state. If the case has a
   `followup`, wait for the first reply, then send the `followup` text as the second user turn.
4. Save the complete output and the list of files that changed.
5. Judge the output against the case `requirements` and `prohibitions` and the hard gates and
   scores in `JUDGE.md`. A hard-gate failure fails the case.
6. Record the case `id`, the model, the plugin version, the hard-gate result, and the scores.
7. Repeat for every case. To compare conditions, run each case again without the plugin, then
   judge the outputs blind.

The test `tests/test_evals.py` checks only that `cases.json` is well formed.
