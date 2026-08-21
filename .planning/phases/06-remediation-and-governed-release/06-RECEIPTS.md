# Phase 6 Plan 5 — Real Dispatch Receipt and E-12 Subset Verdict

Sanitized per D-09 (locked in Task 1 as `d09-as-written`): commands, exit codes, seal states,
headline counts, the subset verdict, and SHAs only. No target-repo path below repo root (the
`.sec-overlay` sidecar path is the one named exception, per D-09), no code excerpt, no finding
body. Category-level breakdown (defect-class / rule-id counts) is included at the executor's
discretion, per Task 1's resolution — these are generic taxonomy terms, not target-repo-specific
information.

## Task 1 — boundary decision

Resolved as `d09-as-written`: the receipt may contain commands, exit codes, seal states,
headline counts, the subset verdict, and SHAs — exactly D-09 as locked. Category-level
breakdown (defect class / rule ID counts, not file paths) stays at executor discretion. Applied
throughout this document.

## Dispatch mechanism — deviation from literal `SKILL.md` dispatch (Rule 4)

The executor agent's available toolset carries no Task/subagent-dispatch capability, so it
could not itself spawn the 14 per-file `review-file` subagents `SKILL.md`'s review-mode
dispatch step calls for. This was raised as a blocking checkpoint (two options: the
orchestrator dispatches via its own Agent-tool access, or the executor self-performs the
review in-session with the deviation disclosed). The orchestrator selected the first option and
performed the dispatch directly:

- The executor ran `--prepare` (plain CLI, profile-independent) to render the 14 per-file
  prompts and compute the 14 deterministic agent labels.
- The orchestrator spawned 14 fresh-context `sonnet` `review-file` subagents — one per rendered
  prompt, diff-only input, no repository access — and persisted each subagent's raw response as
  a recorded agent return (`record_agent_return`) under the executor's chosen workspace, keyed
  by the same 14 deterministic labels `--prepare` had already computed.
- The executor then ran both consume passes (no `--prepare` flag) against those recorded
  returns.

This is real per-file reviewer dispatch — 14 independent model calls, one per reviewable file,
each returning genuine `code_comment` or `task_done` verdicts — not a mocked or stubbed
substitute for `SKILL.md`'s intended mechanism.

## Environment

- `uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)`
- `git version 2.55.0`
- `Python 3.13.14`

(Same environment Phase 5's `05-01-review-security-receipt.md` recorded.)

## Diff range

- Base SHA (full): `5f477d8c140c5b85f6c307a42d7afe96541efbfb`
- Head SHA (full): `d06ce30d328e41b9f258d3cb19964a57d0facd37`
- These match the plan's expected range exactly — no discrepancy row needed against D-07.
- Target repo HEAD before and during and after every command below: `80e2abca4f0b53d056537e3281bf430089bbf7c8` (unchanged); `git status --porcelain --untracked-files=no` empty throughout — target tree untouched by this session.
- Total changed files in range: 15 (14 reviewable, 1 excluded — same partition Phase 5 recorded: the excluded file's extension, `.mdc`, is absent from `ALLOWED_EXTENSIONS`).

## Reviewer run configuration

- Model: `sonnet` (all 14 dispatched subagents and both consume-pass invocations)
- Concurrency: `8` (shipped default, `DEFAULT_CONCURRENCY`; no `--concurrency` override passed)
- Timeout: `600` seconds (shipped default, `DEFAULT_TIMEOUT_SECONDS`; no `--timeout` override passed)

## Command 1 — prepare (profile-independent, run once)

```
uv run python -m sec_overlay.cli review \
  --base 5f477d8c140c5b85f6c307a42d7afe96541efbfb \
  --head d06ce30d328e41b9f258d3cb19964a57d0facd37 \
  --root <target-repo-root> \
  --workspace <scratch-workspace-security> \
  --prepare
```

Run from `plugins/sec-overlay/skills/sec-overlay/helpers`.

- Exit code: `0`
- Output: 14 rendered per-file prompts + a `review_plan.json` recording each file's
  deterministic agent label, written under `<scratch-workspace-security>/runs/`.
- This step is profile-independent — the same prepared prompt set is valid input to either a
  security-profile or a general-profile consume pass.

## Command 2 — security-profile consume

```
uv run python -m sec_overlay.cli review \
  --base 5f477d8c140c5b85f6c307a42d7afe96541efbfb \
  --head d06ce30d328e41b9f258d3cb19964a57d0facd37 \
  --root <target-repo-root> \
  --workspace <scratch-workspace-security> \
  --profile security
```

- Exit code: `0`
- Decisive tail: no stdout/stderr output on success; the coverage manifest seal state is the
  decisive signal.
- Coverage manifest seal: `complete`
- Coverage manifest SHA read-back: `base_sha`/`head_sha` match the diff range above exactly
- Coverage manifest `model`/`profile`: `sonnet` / `security`
- Reviewable file count: 14 (all reached state `done`)
- Review-source disposition: `review_source_skipped: 0` — every one of the 14 reviewable files
  received a genuine recorded reviewer return this run. Contrast with Phase 5's
  `05-01-review-security-receipt.md`, which recorded `review_source_skipped: 14` /
  `review_findings: 0` for the identical 14-file set, because that tracer task's `<action>`
  never invoked per-file dispatch at all (`SKILL.md` owns dispatch; the CLI-only invocation
  alone cannot produce it). This run is the first in this milestone where all 14 files carry a
  real dispatched reviewer return rather than a skip.
- Findings-ledger headline counts: `review_findings: 0` (kept), `dropped: 5`
- Dropped-finding category breakdown: 2 `resource-leak`, 3 `null-dereference` — all 5 dropped
  with reason `gate-b` (gate B: "no security impact"), per `review_findings.apply_profile()`.
  Under the security profile, every gate-marked (A–E) finding drops unconditionally; general
  defect classes carry no exception under this profile.

## Command 3 — copy recorded returns into a fresh general workspace

The 14 recorded reviewer-return files (`runs/<agent-label>.txt`) were copied byte-for-byte from
`<scratch-workspace-security>` into a fresh `<scratch-workspace-general>` workspace.
`sha256sum` over both `runs/` directories confirmed the copy is byte-identical. No `--prepare`
was re-run and no subagent was re-dispatched for this step — the general-profile consume pass
below reads the same 14 recorded returns the security-profile pass already read, satisfying the
plan's requirement that the subset verdict be computed over one identical reviewer output set,
not two independently dispatched runs.

## Command 4 — general-profile consume (same recorded returns, copied)

```
uv run python -m sec_overlay.cli review \
  --base 5f477d8c140c5b85f6c307a42d7afe96541efbfb \
  --head d06ce30d328e41b9f258d3cb19964a57d0facd37 \
  --root <target-repo-root> \
  --workspace <scratch-workspace-general> \
  --profile general
```

- Exit code: `0`
- Coverage manifest seal: `complete`
- Coverage manifest SHA read-back: `base_sha`/`head_sha` match the diff range above exactly
- Coverage manifest `model`/`profile`: `sonnet` / `general`
- Reviewable file count: 14 (all reached state `done`)
- Review-source disposition: `review_source_skipped: 0` (same 14 recorded returns consumed)
- Findings-ledger headline counts: `review_findings: 5` (kept), `dropped: 0`
- Kept-finding category breakdown: 2 `resource-leak`, 3 `null-dereference` — all 5 kept with
  disposition `unconfirmed`, per `findings_gate.disposition_without_receipt` (both classes are
  static-checkable, not runtime-dependent, so neither ships `needs-deployment-testing`).

## Consume order

1. Prepare (once, profile-independent).
2. Security-profile consume, against the 14 dispatched returns as originally recorded.
3. Byte-for-byte copy of the same 14 returns into a fresh workspace.
4. General-profile consume, against the copied — not re-dispatched — returns.

## E-12 subset verdict

- Security-kept set size: `0`
- General-kept set size: `5`
- Subset relation: security-kept ⊆ general-kept — `∅ ⊆ {5 ids}` — **holds (True)**.
- Vacuity: **not vacuous.** A vacuous verdict is an empty-vs-empty comparison (∅ ⊆ ∅) that
  passes trivially without exercising the profile gate at all — Phase 5's exact defect
  (`review_source_skipped: 14` both profiles, 0 kept either side). This run's general-kept set
  is non-empty (5), so the comparison is a genuine demonstration that `apply_profile()`
  discriminates: the same 5 raw findings, dispatched once, are correctly dropped under the
  security profile (gate B, unconditional-under-security) and correctly kept under the general
  profile (both defect classes are members of `GENERAL_DEFECT_CLASSES`). The profile-superset
  contract (security-kept ⊆ general-kept) is demonstrated on live, non-degenerate data, not
  merely asserted.
- Plan 04 deterministic backstop (D-08): not invoked — D-08's backstop is the fallback evidence
  for a vacuous outcome; this run produced a non-vacuous result directly, so the live result
  itself is the primary evidence per the plan's flagged-assumption resolution.

## Phase 5 sidecar isolation

- Phase 5's existing sidecar, `.sec-overlay/mando-c4872e65/` (target-repo-relative path,
  disclosed per the D-09 exception), was not written to by any command in this receipt — all
  four commands above target `<scratch-workspace-security>` / `<scratch-workspace-general>`,
  both outside the target repository tree entirely.
- `coverage_manifest.json` digest inside that sidecar was read before and after this session's
  full command sequence and is identical both times (SHA-1 digest match; digest value withheld
  per the no-code/no-artifact-content sanitization boundary — the fact of the match, not the
  digest's use as a security control, is the receipt).

## Plugin-tree diff check

`git diff --stat HEAD -- plugins/` — empty (0 lines). This plan writes no code; no `plugins/`
file is modified, and no plugin `version` bump applies.

## Governance receipt

See `06-DEFECTS.md` (Task 3) for the 5-row shipping/governance table covering all four shipping
PRs plus this plan's deliberate zero-shipping-file row.
