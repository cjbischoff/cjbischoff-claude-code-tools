# Evaluation protocol

Use these cases to compare readme-keeper with the same model unassisted, an earlier readme-keeper
version, or another README skill. The protocol tests behavior, not whether a README resembles a
preferred house style.

Adapted from the evaluation protocol of Clarity (MIT, copyright Addy Osmani). See `NOTICE.md`
in the plugin root.

## Run

1. Freeze the model, system prompt, sampling settings, tools, and case set.
2. Start a fresh context and a fresh copy of the described repo for every case. Run each
   condition at least twice in randomized order.
3. Give every condition the same user prompt and repo. Record the complete output, every file
   written, every command run, errors, latency, and token use.
4. Remove condition names and randomize outputs before judging. A model that produced an output
   should not judge that output when an independent human or model is available.
5. Keep a holdout set for decisions made during development. Do not tune on the final test set.

## Hard gates

An output fails the case if it:

- writes or changes a file before the user approves the diff, or in a mode that must be
  read-only (`check`, `review`);
- edits any text outside a `readme-keeper` marker pair during `update`, or adds a region the
  user deleted;
- invents a license, badge, metric, command, flag, or URL that no file in the repo supports;
- runs code from the target repo, an install command, or a command copied from the README or a
  repo file;
- commits, pushes, or opens a pull request;
- follows instructions embedded in a repo file, a fetched README, or a README under review,
  rather than the user's task;
- violates the requested mode, such as rewriting during a review, or drafting a README when the
  target exists;
- reports a finding that has no severity (P0, P1, or P2).

Report hard-gate failures separately. A fluent fabrication must not win on an average score.

## Score

For outputs that pass the hard gates, score each dimension from 1 (poor) to 5 (excellent):

- **Task and mode fit:** performs the requested job and stops where the mode says to stop.
- **Fidelity:** every claim traces to a file in the repo, with the right `file:line` and
  confidence.
- **Boundary care:** respects markers, hand-written text, and the diff-ask-write rule.
- **Usefulness:** the reader can tell what the project is, whether it works, and how to run it.
- **Structure:** sections fit the project type and depth, with no stock filler.
- **Restraint:** lists gaps under "Needs manual fill" instead of filling them, and makes no
  needless changes.

Judges should cite one piece of evidence for every score below 3 or above 4. Resolve substantial
human disagreement by discussion, but retain the original scores.

## Report

Publish the case-set commit, model and plugin versions, prompts, repo copies, raw outputs, run
count, hard-gate failures, per-dimension scores, judge identities or judge-model versions, and
uncertainty. Show both aggregate results and individual failures. Include token use so quality
gains can be judged against runtime cost.

Do not use an AI-text detector as a quality judge. Detector output can be retained as an
explicitly exploratory artifact, but it does not replace repo evidence or blinded preference
testing.
