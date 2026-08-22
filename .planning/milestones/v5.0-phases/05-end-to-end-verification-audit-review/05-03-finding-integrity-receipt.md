# Phase 5 Plan 3: Finding integrity receipt (AUD-02, AUD-03)

Sanitized per D-07 (one-way): no target-repo path below the repo root, no
code snippet, no finding title, message, or body appears below. The
`.sec-overlay` sidecar path is permitted and required by D-09. All readback
commands below are read-only against the live sidecar; the one write-capable
call (`validate_findings`) was redirected to a scratch copy — see Task 1.

## Target and scope

Real findings from Plan 02's audit run, read back from the retained sidecar
`<target-repo-root>/.sec-overlay/mando-05-02-audit/findings/*.json` (4 real
findings, no fixtures). Pinned pass SHA `80e2abca4f0b53d056537e3281bf430089bbf7c8`
(unchanged from Plan 02).

## Task 1 — AUD-02: receipt ladder on real findings

Command, run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```
uv run python -c "
import glob, json
from sec_overlay.evidence import confirms_alone
paths = sorted(glob.glob('<target-repo-root>/.sec-overlay/*/findings/*.json'))
paths = [p for p in paths if '/mando-05-02-audit/' in p]
findings = [json.load(open(p)) for p in paths]
confirmed = [f for f in findings if f.get('status') == 'confirmed']
ladder_pass = [f for f in confirmed if confirms_alone(f.get('evidence_sources') or [])]
ladder_fail = [f for f in confirmed if not confirms_alone(f.get('evidence_sources') or [])]
print('confirmed=', len(confirmed))
print('ladder_pass=', len(ladder_pass))
print('ladder_fail=', len(ladder_fail))
"
```

Exit code: 0. Decisive tail:

```
confirmed= 1
ladder_pass= 1
ladder_fail= 0
```

**Result: AUD-02 holds on real output, non-vacuously.** The confirmed bucket
is non-empty (1 finding); every member of it passes `confirms_alone()` — the
shipped, unmodified predicate from `evidence.py`, not a hand-rolled tier
check. Zero ladder failures, so no violation exists to record and no
identifier/status/evidence-source-name listing is required by this task's
own acceptance criteria (that listing is only for violations).

Separately, the shipped schema/invariant validator was also run, redirected
away from the live sidecar to avoid its write side effect on `receipt_tier`
mismatch (`findings_gate.validate_findings()` conditionally rewrites a
finding's stored `receipt_tier` field, which would violate D-09's retention
prohibition if run directly against the live sidecar). The 4 real finding
JSON files were copied to a scratch directory outside this repo and outside
the target repo; a `Workspace(findings_dir_override=<scratch-copy>)` pointed
`validate_findings()` at the copy only. Exit/result: `errors returned = 0`.
MD5 checksums of the 4 live sidecar finding files were recorded before and
after this call and are identical, confirming the live sidecar was not
touched.

## Task 2 — AUD-03: runtime-dependent findings carry real risk and stay visible

Command, run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```
uv run python -c "
import glob, json
paths = sorted(glob.glob('<target-repo-root>/.sec-overlay/*/findings/*.json'))
paths = [p for p in paths if '/mando-05-02-audit/' in p]
findings = [json.load(open(p)) for p in paths]
ndt = [f for f in findings if f.get('status') == 'needs-deployment-testing']
null_scores = [f for f in ndt if f.get('risk_score') is None]
zero_scores = [f for f in ndt if f.get('risk_score') == 0]
positive_scores = [f for f in ndt if f.get('risk_score') and f.get('risk_score') > 0]
print('ndt=', len(ndt))
print('null_scores=', len(null_scores))
print('zero_scores=', len(zero_scores))
print('positive_scores=', len(positive_scores))
"
```

Exit code: 0. Decisive tail:

```
ndt= 3
null_scores= 0
zero_scores= 0
positive_scores= 3
```

Report visibility check (corrected path — see Deviations below):

```
rg -n 'Needs runtime proof|needs-runtime' <target-repo-root>/.sec-overlay/mando-05-02-audit/report.md
```

Exit code: 0. Decisive line: `Needs runtime proof: 3` (headline), plus 6
supporting per-row occurrences of `needs-runtime` in the triage table and
detail list.

**Result: AUD-03 holds on real output, non-vacuously.** The
needs-deployment-testing bucket is non-empty (3 findings); every member
carries a positive `risk_score` (field name: `risk_score`), zero null, zero
zero-valued. The report's headline count (3) matches the computed bucket
size (3) exactly — no mismatch. The bucket is visibly rendered in the
report, under the pipeline's designed human-readable labels
("Needs runtime proof" headline, "needs-runtime" per-row status) rather than
the literal enum string `needs-deployment-testing` — this is the report
renderer's intended design (`report.py`), not a suppression or omission.

## Fence and retention (D-08/D-09)

All commands above open sidecar files for reading only, except the one
explicitly-redirected `validate_findings()` call in Task 1, whose scratch
redirection and pre/post MD5 comparison are documented above. No sidecar
file was deleted, overwritten, or pruned. Both retained sidecars
(`mando-05-02-audit`, `mando-c4872e65`) remain present and untouched.

## Environment

```
uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)
git version 2.55.0
Python 3.13.14
```

## Deviations discovered during this task

1. **Task 2's literal verify command path is wrong.** The plan's automated
   check assumes `report.md` lives under a sidecar `artifacts/` subdirectory;
   in the real sidecar, `report.md` lives at the sidecar root, and
   `artifacts/` holds only `review_ledger.json` (a review-mode artifact from
   a different plan). Corrected the glob to the sidecar root before running.
   This is a bug in the plan's own verify command, not a target-pipeline
   defect — no `05-DEFECTS.md` row added for it.
2. **The literal string `needs-deployment-testing` does not appear in
   `report.md` by design**, not because the bucket is hidden. `report.py`
   renders that status under human-readable labels ("Needs runtime proof",
   "needs-runtime") everywhere in the shipped report — confirmed by
   inspecting the renderer. Re-ran the visibility check against the actual
   design labels instead of the literal enum string; the headline count
   check above confirms the bucket is genuinely visible, not folded away.
3. **`evidence_sources` values for the 3 needs-deployment-testing findings
   embed real target-repo relative file paths** (e.g. `read:<path>:<line
   range>`, `ripgrep:<pattern>:<match description>`), not bare tool names.
   Task 1's acceptance criteria only requires quoting evidence-source names
   for ladder violations, of which this run has zero, so none are quoted
   here. This receipt deliberately does not reproduce any `evidence_sources`
   string for the needs-deployment-testing bucket, because doing so would
   place a target-repo file path below the repo root into this repo's
   history, violating D-07 regardless of the plan's framing that such names
   are safe. The single confirmed finding's evidence source
   (`sca:osv:<advisory-id>` shape — a pure tool/advisory identifier with no
   path) would have been safe to quote if needed; it was not needed either,
   since the ladder-failure count is 0.

## 05-DEFECTS.md

No new rows added. Both AUD-02 and AUD-03 passed with zero violations on
real output — there is nothing to disposition. The ledger remains at 9 rows
from Plan 02.
