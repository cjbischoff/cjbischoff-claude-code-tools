# Phase 5 Plan 4: Artifact-and-coverage receipt (AUD-04, AUD-05)

Sanitized per D-07 (one-way): no target-repo path below the repo root, no code
snippet, no diagram body, no threat description, and no finding body appears
below. The `.sec-overlay` sidecar path itself is permitted and required by
D-09. Every command below opens sidecar files for reading only.

## Target and scope

Real architecture, threat-model, and coverage artifacts from Plan 02's full
audit run, read back from the retained sidecar
`<target-repo-root>/.sec-overlay/mando-05-02-audit/`. Pinned pass SHA
`80e2abca4f0b53d056537e3281bf430089bbf7c8` (unchanged from Plans 02 and 03).
AUD-06's evidence below is read from the separate retained sidecar
`<target-repo-root>/.sec-overlay/mando-c4872e65/` (Plan 01's tracer run).

## Task 1 — AUD-04: deterministic gates and CVSS v4.0-only

### Gate verdicts

Command, run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```
uv run python -c "
import glob, json
for name in ('arch-gate', 'tm-gate'):
    hits = [p for p in glob.glob(f'<target-repo-root>/.sec-overlay/*/kb/gates/{name}.json')
            if '/mando-05-02-audit/' in p]
    d = json.load(open(hits[0])) if hits else None
    print(name, 'passed=', d.get('passed') if d else 'MISSING', 'errors=', len(d.get('errors', [])) if d else 'n/a')
"
```

Exit code: 0. Decisive tail:

```
arch-gate passed= True errors= 0
tm-gate passed= True errors= 0
```

**Deviation note:** the plan's own literal verify command globs
`kb/receipts/{arch-gate,tm-gate}.json`. That path exists but holds a
different artifact family — the generic per-phase bookkeeping receipt
written by `record_stage()` (`{"phase", "stdout", "artifacts", "counts"}`,
no `passed` key), not the deterministic gate verdict. The gate verdict
(`{"passed", "errors", "warnings"}`) is written by `driver.py`'s
`_write_gate()` helper to `kb/gates/{name}.json`. Corrected the glob before
running; see Deviations section below.

### Reproducible re-run of the composed deterministic checks

Both gates compose `diagram_gate.run_diagram_gate()` and
`ste_lint.lint_prose()`; `tm-gate` additionally composes
`artifact_gate.check_duplication()`. Re-ran all three directly against the
real artifact files rather than trusting the recorded JSON alone:

```
uv run python -m sec_overlay.diagram_gate \
  --architecture <target-repo-root>/.sec-overlay/mando-05-02-audit/architecture \
  --threat-model <target-repo-root>/.sec-overlay/mando-05-02-audit/threat-model \
  --require-threat-model
```
Exit code: 0. No violation lines printed.

```
uv run python -m sec_overlay.ste_lint <target-repo-root>/.sec-overlay/mando-05-02-audit/architecture/arc42.md
```
Exit code: 0. No violation lines printed.

```
uv run python -m sec_overlay.ste_lint <target-repo-root>/.sec-overlay/mando-05-02-audit/threat-model/threat-model.md
```
Exit code: 0. No violation lines printed.

```
uv run python -c "
from sec_overlay.artifact_gate import check_duplication
arc42 = open('<target-repo-root>/.sec-overlay/mando-05-02-audit/architecture/arc42.md').read()
tm = open('<target-repo-root>/.sec-overlay/mando-05-02-audit/threat-model/threat-model.md').read()
print('duplication_errors', len(check_duplication(arc42, tm)))
"
```
Exit code: 0. Decisive tail: `duplication_errors 0`.

All four reproductions returned zero violations, independently confirming
the recorded `passed=True` verdicts for both gates rather than merely
reading the stored JSON.

### CVSS v4.0-only scan

The plan's literal verify command globs `artifacts/*.md`. The sidecar's
`artifacts/` directory holds no Markdown files for this run (only
`review_ledger.json`, a review-mode artifact from a different plan) — that
glob alone would return a vacuous zero-vector count, which Edge E-08 forbids
being read as a clean pass. Scanned the real locations that carry CVSS
vectors instead: `threat-model/threat-model.md`, `report.md`,
`redteam-plan.md`, and every `findings/*.json` file.

```
uv run python -c "
import glob, re
pat = re.compile(r'CVSS:[0-9]\.[0-9]/')
sidecar = '<target-repo-root>/.sec-overlay/mando-05-02-audit'
files = (glob.glob(f'{sidecar}/threat-model/*.md')
         + glob.glob(f'{sidecar}/*.md')
         + glob.glob(f'{sidecar}/findings/*.json'))
tot = bad = 0
for f in files:
    hits = pat.findall(open(f, errors='ignore').read())
    tot += len(hits)
    bad += sum(1 for m in hits if not m.startswith('CVSS:4.0/'))
print('vectors', tot); print('non_v4_vectors', bad)
"
```

Exit code: 0. Decisive tail:

```
vectors 10
non_v4_vectors 0
```

**Result: AUD-04 holds on real output, non-vacuously.** Both `arch-gate` and
`tm-gate` recorded `passed=True` with 0 errors, independently reproduced by
re-running the four composed deterministic checks directly (0 violations
each). The CVSS scan found 10 real vectors across the threat model, report,
redteam plan, and finding files — none using a non-`CVSS:4.0/` prefix. A
non-zero total (10) rules out a vacuous pass.

## Task 2 — AUD-05: coverage denominator and coverage ledger

### Coverage denominator

The report's "Coverage & limitations" section states SAST coverage by
language as an explicit file count, not a qualitative claim:

```
rg -n -i 'coverage & limitations|coverage completeness' <target-repo-root>/.sec-overlay/mando-05-02-audit/report.md
```

Exit code: 0. Decisive tail: both section headers found. The table beneath
the first gives the per-language file counts; summed, they state an
explicit denominator of **515 files** (508 typescript + 7 javascript), with
"Dataflow coverage: 0% of counted source" naming those same 515 files as the
counted source. This reflects a whole-repository audit under default
excludes, consistent with D-03 and with the Plan 02 receipt's statement that
no narrowing scope argument was passed — a denominator smaller than the real
repository would indicate silent narrowing, and 515 is not artificially
small for this target.

### Coverage ledger validation

Command, run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```
uv run python -c "
import glob, json
from sec_overlay.coverage_ledger import validate_coverage_ledger
hits = [p for p in glob.glob('<target-repo-root>/.sec-overlay/*/kb/coverage-ledger.json')
        if '/mando-05-02-audit/' in p]
d = json.load(open(hits[0]))
surfaces = d['surfaces']
nfu = [s['id'] for s in surfaces if s.get('disposition') == 'needs_follow_up']
print('completeness', d.get('completeness'))
print('entries', len(surfaces))
print('needs_follow_up', len(nfu))
print('validate_errors', validate_coverage_ledger(d))
"
```

Exit code: 0. Decisive tail:

```
completeness partial
entries 8
needs_follow_up 5
validate_errors []
```

`completeness` reads `partial`, not `complete`, while 5 of 8 surfaces are
`needs_follow_up` — this is the ledger's designed non-contradictory state
(Edge E-09 only fires when `completeness` reads `complete` *and*
`needs_follow_up` is non-zero at the same time; that combination was not
observed here). The shipped `validate_coverage_ledger()` returned zero
errors.

### Zero-finding attack-surface cross-check

`kb/scan-profile.json`'s `attack_surface` list carries 9 entries, one of
which is `deps`. Reading `coverage_ledger.py`'s `build_coverage_ledger()`
source directly confirms `deps` is intentionally excluded from the
surface-completeness ledger by design (`classes = [c for c in
profile.get("attack_surface", []) if c != "deps"]`) — dependency findings
are tracked through the findings pipeline directly (a real
`deps`-class finding, `C-DEPS-0001`, exists and is already carried in
`05-DEFECTS.md` for its cosmetic rendering defect), not through the
attack-surface hunt ledger. Excluding `deps`, all 8 remaining classes
(`authn`, `authz`, `xss`, `crypto`, `ssrf`, `open-redirect`,
`business-logic`, `graphql`) have a ledger entry: 3 are `reported` (matching
the 3 non-dependency shipping findings) and 5 are `needs_follow_up`.
Unlogged zero-finding classes: **0**.

**Result: AUD-05 holds on real output, non-vacuously.** The report states an
explicit whole-repository denominator (515 files); the coverage ledger
validates cleanly against the shipped validator (0 errors); `completeness`
is `partial` with 5 `needs_follow_up` surfaces, consistent (no
`complete`/non-zero contradiction to ledger); and every non-`deps`
attack-surface class the run enumerated has a ledger entry — 0 unlogged.

## D-08 evidence map — all six phase criteria

For the downstream `/gsd-verify-work` verification report. Each row names a
sidecar path (relative to the target repo root) and the exact field to
check; no sidecar content is copied here.

| Criterion | Sidecar path | Field / check |
|---|---|---|
| AUD-01 | `.sec-overlay/mando-05-02-audit/state.json` | `stages` dict — 24/24 entries `done`; `git status --porcelain --untracked-files=no` empty in the target repo before/after |
| AUD-02 | `.sec-overlay/mando-05-02-audit/findings/*.json` | `status` field (bucket = `confirmed`); each member's `evidence_sources` passes `sec_overlay.evidence.confirms_alone()` unmodified |
| AUD-03 | `.sec-overlay/mando-05-02-audit/findings/*.json` and `report.md` | `status` field (bucket = `needs-deployment-testing`), `risk_score` field (non-null, positive); `report.md` "Needs runtime proof" headline count matches the bucket size |
| AUD-04 | `.sec-overlay/mando-05-02-audit/kb/gates/{arch-gate,tm-gate}.json` | `passed` field (both `true`), `errors` field (both empty); CVSS vector prefix across `threat-model/threat-model.md`, `report.md`, `redteam-plan.md`, `findings/*.json` (all `CVSS:4.0/`) |
| AUD-05 | `.sec-overlay/mando-05-02-audit/report.md` and `kb/coverage-ledger.json` | `report.md` "Coverage & limitations" table (file-count denominator); `coverage-ledger.json`'s `completeness` and `surfaces[].disposition` fields |
| AUD-06 | `.sec-overlay/mando-c4872e65/artifacts/coverage_manifest.json` and `.../artifacts/review_ledger.json` | `coverage_manifest.json`'s `seal` field (`complete`); `review_ledger.json`'s `review_source_skipped` / `review_findings` counts and `base_sha`/`head_sha` fields matching the diff range |

## Sanitization gate results (D-07)

```
rg -N '_hy/mando/' 05-04-artifact-coverage-receipt.md 05-DEFECTS.md | rg -v '_hy/mando/\.sec-overlay' | wc -l
```
Result: `0`.

```
rg -N '_hy/mando/' 05-*-receipt.md 05-DEFECTS.md 05-0*-PLAN.md | rg -v '_hy/mando/\.sec-overlay' | wc -l
```
Raw result: `9`. All 9 lines are inside `05-0{1,2,3,4}-PLAN.md`, and fall into
exactly two categories, both pre-existing, documented planner exceptions
rather than leaked content: (a) the `<automated>rg -N '_hy/mando/' ...`
verify-command text itself, which necessarily quotes the sanitization
pattern it checks for, and (b) the accompanying
`<!-- planner-discipline-allow: _hy/mando/ -->` comment each plan's
acceptance criteria already carries next to that same check. Filtering out
both categories:

```
rg -N '_hy/mando/' 05-*-receipt.md 05-DEFECTS.md 05-0*-PLAN.md \
  | rg -v '_hy/mando/\.sec-overlay' \
  | rg -v 'planner-discipline-allow' \
  | rg -v "<automated>rg -N '_hy/mando/'" \
  | wc -l
```
Result: `0`. No receipt, no `05-DEFECTS.md` row, and no plan-document prose
outside the self-quoted verify command contains an unpermitted target-repo
path.

## Fence and retention (D-08/D-09)

All commands above open sidecar files for reading only. No sidecar file was
deleted, overwritten, or pruned. Both retained sidecars
(`mando-05-02-audit`, `mando-c4872e65`) remain present and untouched, and
are retained per D-09 until v5.0 ships through Phase 6 and the milestone
audit.

## Environment

```
uv 0.11.32 (Homebrew 2026-07-23 x86_64-apple-darwin)
git version 2.55.0
Python 3.13.14
```

## Deviations discovered during this task

1. **Task 1's literal verify command path is wrong.** The plan's automated
   check globs `kb/receipts/{arch-gate,tm-gate}.json`. Those files exist but
   are the generic `record_stage()` bookkeeping receipt
   (`{"phase", "stdout", "artifacts", "counts"}`), not the deterministic
   gate verdict, so `.get('passed')` on them returns `None` for both names.
   The real gate verdict lives at `kb/gates/{name}.json`, written by
   `driver.py`'s `_write_gate()` helper. Corrected the glob before running.
   This is a bug in the plan's own verify command, not a target-pipeline
   defect — no `05-DEFECTS.md` row added for it (same pattern as Plan 03's
   Task 2 path correction).
2. **Task 1's literal CVSS-scan glob (`artifacts/*.md`) is vacuous for this
   run.** The sidecar's `artifacts/` directory holds no Markdown files (only
   `review_ledger.json`, a review-mode artifact from a different plan), so
   the literal glob would report `vectors=0, non_v4_vectors=0` — a result
   Edge E-08 explicitly forbids reading as a clean pass, since a zero total
   cannot be distinguished from "nothing was scanned." Scanned the real
   locations instead (`threat-model/*.md`, the sidecar-root `report.md` and
   `redteam-plan.md`, `findings/*.json`), which found 10 real vectors, all
   `CVSS:4.0/`. This is a bug in the plan's own verify command, not a
   target-pipeline defect — no `05-DEFECTS.md` row added for it.
3. **Task 2's literal verify command path is wrong**, in the same way as
   Plan 03's Task 2 finding: the plan's second automated check globs
   `.../artifacts/report.md`, but `report.md` lives at the sidecar root;
   `artifacts/` holds only `review_ledger.json` (a review-mode artifact from
   a different plan). Corrected the glob to the sidecar root before running.
   No `05-DEFECTS.md` row added — this is a plan-document issue, already
   documented once in Plan 03's ledger-equivalent deviation and reproduced
   here rather than duplicated as a new row.
4. **`scan-profile.json`'s `attack_surface` list appears to have one more
   entry than the coverage ledger — not a gap.** The scan profile lists 9
   attack-surface classes including `deps`; the coverage ledger has 8
   entries. Reading `build_coverage_ledger()`'s source confirmed this is
   deliberate: `deps` is excluded from the surface-completeness ledger by
   design, because dependency findings are tracked through the findings
   pipeline directly rather than through the attack-surface hunt ledger (a
   real `deps`-class finding, `C-DEPS-0001`, already exists and is carried
   in `05-DEFECTS.md`). Re-verified against the source before concluding
   this was a coverage gap; it is not. No `05-DEFECTS.md` row added.

## 05-DEFECTS.md

No new rows added. Both AUD-04 and AUD-05 passed on real output: both gate
verdicts are `true` with 0 errors, all 10 real CVSS vectors are `CVSS:4.0/`,
the report states an explicit 515-file denominator, the coverage ledger
validates with 0 errors, and every non-`deps` zero-finding attack-surface
class has a logged entry. The four items above are executor/plan-document
verify-command corrections and one re-verified non-gap, not target-pipeline
defects — the ledger remains at 9 rows from Plan 02, unchanged by this plan.
