# 05-01 Task 2 — General-profile review receipt

Sanitized per D-07: commands, exit codes, seal states, counts, gate verdicts, and SHAs only.
No target-repo paths below repo root (the sidecar path itself is the one exception, per
D-09), no code snippets, no finding bodies.

## SHAs (read back from `05-01-review-security-receipt.md`, not re-resolved)

- Base SHA (full): `5f477d8c140c5b85f6c307a42d7afe96541efbfb`
- Head SHA (full): `d06ce30d328e41b9f258d3cb19964a57d0facd37`

## Command

```
uv run python -m sec_overlay.cli review \
  --base 5f477d8c140c5b85f6c307a42d7afe96541efbfb \
  --head d06ce30d328e41b9f258d3cb19964a57d0facd37 \
  --root <target-repo-root> \
  --profile general
```

Run from `plugins/sec-overlay/skills/sec-overlay/helpers`, same defaults as Task 1
(`--concurrency` 8, `--timeout` 600, `--max-git-procs` 16).

## Deviation from Task 1's invocation (Rule 3 — auto-fixed blocking issue)

Running this command with the identical invocation shape as Task 1 (no environment override)
against the same target repo failed with exit code `2` and `error: resume rejected: profile
changed from 'security' to 'general'` — `review_coverage.check_resume_identity`
(`sec_overlay/review_coverage.py:197-220`) rejects any run whose profile differs from a
prior manifest already recorded at that target's one sidecar path, and the `review`
subcommand exposes no `--workspace` override (only `audit` does). This is by design
(SCALE-03 identity pinning prevents a resumed run from silently switching profile
mid-review) — it is not a bug, but it blocked running two profiles against one target's
single sidecar as literally as Task 1's invocation.

Fix: set `SEC_OVERLAY_HOME` for this one command to a durable, target-adjacent path
distinct from the default (`<target-repo-root>/.sec-overlay-general`, sibling to the
default `.sec-overlay/`, outside the target's tracked tree, self-git-ignored by a
`.gitignore` the tool writes into the new memory base). `repo_memory.repo_slug` still
resolves to the same identity-derived slug under that base, so the general run's workspace
is `.sec-overlay-general/mando-c4872e65/` — same slug as Task 1's `.sec-overlay/mando-c4872e65/`,
confirming both runs target the identical repo identity. Task 1's original sidecar workspace
was never touched, read, or overwritten by this fix (D-09 retention preserved).

## Result

- Exit code: `0`
- Decisive tail: no stdout/stderr output on success; the manifest seal state below is the
  decisive signal.
- Sidecar path: `.sec-overlay-general/mando-c4872e65/` (relative to target repo root)
- Coverage manifest seal: `complete`
- Coverage manifest SHA read-back: `base_sha`/`head_sha` match the diff range above exactly
- Reviewable file count: 14, excluded file count: 1 — identical partition to Task 1 (same
  SHA range, same `file_select.py` logic; the excluded file is the same `.mdc` file,
  `not-allowlisted`)
- Kept (live) findings: 0
- Dropped findings: 0
- Review-source disposition: all 14 reviewable files landed in `review_source_skipped`,
  same as Task 1 and for the same reason (D-13/D-15) — see Task 1's receipt.

## Subset comparison (D-06/D-10 profile-superset contract)

- Security-kept finding set size: 0
- General-kept finding set size: 0
- General-unique count (general-kept, not in security-kept): 0
- Security-kept-but-general-dropped count: 0 — **no superset violation observed.** The
  empty-set case is a vacuous pass (∅ ⊆ ∅), not a substantive confirmation of the
  superset property; see `05-DEFECTS.md` for the E-12 flagged-assumption note this
  implies for Phase 6, which must confirm the contract against a run with non-zero
  findings on both profiles.
