# 05-01 Task 1 — Security-profile review receipt

Sanitized per D-07: commands, exit codes, seal states, counts, gate verdicts, and SHAs only.
No target-repo paths below repo root (the `.sec-overlay` sidecar path is the one exception,
per D-09), no code snippets, no finding bodies.

## Command

```
uv run python -m sec_overlay.cli review \
  --base 5f477d8c140c5b85f6c307a42d7afe96541efbfb \
  --head d06ce30d328e41b9f258d3cb19964a57d0facd37 \
  --root <target-repo-root> \
  --profile security
```

Run from `plugins/sec-overlay/skills/sec-overlay/helpers`. `--concurrency`, `--timeout`, and
`--max-git-procs` left at shipped defaults (8 / 600 / 16).

## Environment

- `uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)`
- `git version 2.55.0`
- `Python 3.13.14`

## Diff range

- Base SHA (full): `5f477d8c140c5b85f6c307a42d7afe96541efbfb`
- Head SHA (full): `d06ce30d328e41b9f258d3cb19964a57d0facd37`
- Target repo HEAD before and after run: `80e2abca4f0b53d056537e3281bf430089bbf7c8` (unchanged;
  `git status --porcelain --untracked-files=no` empty both before and after — target tree
  untouched)

## Result

- Exit code: `0`
- Decisive tail: no stdout/stderr output on success; the manifest seal state below is the
  decisive signal, not console output.
- Sidecar path: `.sec-overlay/mando-c4872e65/` (relative to target repo root, per D-09)
- Coverage manifest seal: `complete`
- Coverage manifest SHA read-back: `base_sha`/`head_sha` match the diff range above exactly
- Reviewable file count: 14 (all reached state `done`)
- Excluded file count: 1
  - Excluded file's extension is `.mdc`. `.mdc` is absent from `ALLOWED_EXTENSIONS`
    (`sec_overlay/file_select.py:26-38`), so `partition_changed_files` routes it out with
    reason `not-allowlisted` (`sec_overlay/file_select.py:193-196`). Total changed files in
    the diff range: 15 (14 reviewable + 1 excluded).
- Kept (live) findings: 0
- Dropped findings: 0
- Positioning-decline count: 0 (vacuous — no findings existed to attempt positioning on)
- Review-source disposition: all 14 reviewable files landed in `review_source_skipped`
  (`review_ledger.json` → `review_source_skipped: 14`, `review_findings: 0`). This is the
  correct, by-design outcome for a CLI-only invocation of `review`: per D-13,
  `review_agent.py` only renders prompts and parses responses — `SKILL.md` owns per-file
  `review-file` subagent dispatch, which this tracer task's `<action>` never invokes. Per
  D-15, a missing agent return is ledgered identically to a stale ref pair or an unparseable
  response — "a reviewer failure, never a coverage failure" — and does not block `seal()`.
  AUD-06's completion criteria (`05-RESEARCH.md`) ground the run's "done" state in
  `CoverageManifest.seal()` and `review_findings.apply_profile()`, not in genuine LLM-authored
  findings, so this is expected and is not a defect.

## Deviation discovered during this task

While preparing to run this command, a real cwd-scoping bug was found and fixed under Rule 1
(auto-fix bugs) before this receipt was recorded — see `05-DEFECTS.md` for the ledger entry
and the plugin's own changelog for the shipped fix. The receipt above reflects the run made
*after* that fix landed.
