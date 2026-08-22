# Phase 5: End-to-End Verification (Audit & Review) - Pattern Map

**Mapped:** 2026-08-20
**Files analyzed:** 3 (this phase produces documentation artifacts only — no source code)
**Analogs found:** 3 / 3

## Scope Note

Phase 5 builds no new plugin code (per RESEARCH.md's Standard Stack: "No new libraries... phase adds no dependency"). Every file this phase creates is a Markdown evidence/governance artifact in `.planning/phases/05-end-to-end-verification-audit-review/`. There is no controller/service/component role to classify — the roles below are documentation roles (evidence-receipt, defect-ledger, verification-report), and the "data flow" is "run real CLI/agent pipeline, capture output, record it."

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|---------------|
| `05-*-receipt.md` (audit run + review run, per D-07) | evidence-receipt doc | command → exit code → decisive tail → version block | `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md` | exact (D-05/D-06/D-07 explicitly says "Phase 1 evidence format") |
| `05-DEFECTS.md` | defect-ledger doc | observed gap → severity → repro command → disposition | `01-01-SUMMARY.md`'s "Triage Ledger" pattern (frontmatter `coverage` block + narrative ledger rows) | role-match — same "every non-zero/anomalous result gets a disposition row" shape |
| `05-VERIFICATION.md` (produced downstream by `/gsd-verify-work`, not by this agent, but the planner should shape 05-PLAN.md tasks so this file's inputs are ready) | verification-report doc | six success criteria → evidence table → pass/gaps_found | `.planning/phases/04-scale-resume-diff-output/04-VERIFICATION.md` | exact — same "Observable Truths" + "Requirements Coverage" table shape, same honest gaps-not-hidden discipline (D-12) |

## Pattern Assignments

### `05-*-receipt.md` files (audit receipt, review-security receipt, review-general receipt)

**Analog:** `.planning/phases/01-baseline-health-verification/01-VERIFICATION.md` and its summary `01-01-SUMMARY.md`

**Required receipt shape** (per 01-CONTEXT D-05..D-07, reused verbatim by 05-CONTEXT's Claude's Discretion note):
- Exact command run (copy-pasteable, including `uv run --locked --directory <pkg> ...` style pinning — `01-01-SUMMARY.md:24`)
- Directory the command ran from
- Exit code
- Decisive output tail (not a full dump) — e.g. `01-01-SUMMARY.md:34`'s pattern of quoting the specific failing/passing line, not the whole log
- A version block (tool versions: `uv`, `git`, `python`, scanner versions) — mirrors RESEARCH.md's "Environment Availability" table, which the executor should re-run and paste, not restate from memory

**Sanitization overlay unique to Phase 5 (D-07, no analog needed — it's a subtraction rule, not a new pattern):**
Every receipt must drop anything that is a mando file path, code snippet, or finding body. Keep only: commands, exit codes, seal states (`CoverageManifest.seal()`'s `"complete"`/`"partial"`), headline counts, gate verdicts (`{"passed": true/false}` from `arch-gate.json`/`tm-gate.json`), and SHAs. This is the one place Phase 5's receipt format diverges from Phase 1's — Phase 1 had no external/sensitive-repo boundary to redact against.

**Example of the "decisive tail, not full dump" discipline to copy** (`01-01-SUMMARY.md:34`, verbatim pattern to follow, not to reuse content):
```
Recorded the real observed pytest failure ... instead of the stale documented
one ... which now passes — receipts follow the actual run, not prior
documentation
```
Translate for Phase 5: record the real observed `kb/receipts/<phase>.json` counts, `report.md` headline counts, and `coverage-ledger.json` completeness field from the actual mando run — never restate RESEARCH.md's predicted shape as if it were the observed one.

---

### `05-DEFECTS.md`

**Analog:** `01-01-SUMMARY.md`'s Triage Ledger (narrative rows) + its `coverage` frontmatter block (structured id/description/verification/status rows, `01-01-SUMMARY.md:41-70`)

**Row shape to copy** (adapt Triage Ledger's four dispositions — `environmental`/`code defect`/`config`/`no-fix-needed` — to D-11's two dispositions, `fixed-here`/`deferred`):

```markdown
| Defect | Severity | Repro Command | Disposition |
|--------|----------|----------------|-------------|
| <one-line defect, sanitized per D-07> | <blocker \| non-blocker> | <exact command that reproduces it, sanitized> | fixed-here \| deferred |
```

Each row needs the same rationale sentence style as `01-01-SUMMARY.md:34-37` ("Recorded the real observed X instead of Y, because Z") — state why the disposition was chosen, not just what it is.

**D-12 discipline (no analog needed — new rule):** a success-criterion failure on real output (e.g., a Tier-2-only finding reaches `confirmed`) is always a ledger row with disposition `deferred`, never a reason to re-run. Do not add a "re-ran and it passed" row that papers over the first observed failure.

---

### `05-VERIFICATION.md` (downstream artifact — shape planning tasks to feed it, per D-08)

**Analog:** `.planning/phases/04-scale-resume-diff-output/04-VERIFICATION.md`

**Structure to replicate:**
- Frontmatter: `phase`, `verified` (timestamp), `status` (`passed` | `gaps_found`), `score` (`n/6 must-haves verified`)
- `### Observable Truths` table: one row per AUD-01..AUD-06, `Status` column (`✓ VERIFIED` / `✗ GAP`), `Evidence` column citing the sidecar path and the exact field checked (e.g., `kb/coverage-ledger.json`'s `completeness` field — see `04-VERIFICATION.md:37` for the citation-density level to match)
- `### Requirements Coverage` table mapping AUD-01..AUD-06 to source plan and status
- `### Gaps Summary` — explicit `None` or a numbered list, matching `04-VERIFICATION.md:107-115`'s pattern of naming exactly which commits/checks closed each prior gap

**D-08 discipline:** every `Evidence` cell must cite what to check in the *live* mando sidecar (path + field), not paste sidecar content into this repo — same distinction Phase 1's receipts draw between "quote the tail" and "attach the log file."

---

## Shared Patterns

### Evidence format (all three doc types)
**Source:** `.planning/phases/01-baseline-health-verification/01-CONTEXT.md` D-05..D-08 (cited directly by 05-CONTEXT.md's Claude's Discretion section)
**Apply to:** every receipt, ledger row, and verification-report evidence cell this phase produces
**Rule:** exact command + exit code + decisive tail + version block. Never a narrative summary standing in for the actual command output.

### Sanitization gate (Phase 5-specific, no Phase 1 equivalent)
**Source:** 05-CONTEXT.md D-07
**Apply to:** every file this phase writes to this repo
**Rule:** before staging any Phase 5 file, grep it for mando-specific file paths, code snippets, and finding-body text; strip anything beyond commands/exit-codes/seal-states/counts/gate-verdicts/SHAs. This is a one-way rule (git history) — check before commit, not after.

### Honest-gap discipline (D-12)
**Source:** 05-CONTEXT.md D-12, mirrored in `04-VERIFICATION.md`'s "Gaps Summary" and `01-01-SUMMARY.md`'s Triage Ledger
**Apply to:** `05-DEFECTS.md` and the eventual `05-VERIFICATION.md`
**Rule:** a real failure is a logged row, not a re-run target. `04-VERIFICATION.md:107-115` shows the correct positive case (gaps genuinely closed by a later plan, named by commit) — do not imitate that closure narrative for a Phase 5 gap that was actually just re-run until it disappeared.

## No Analog Found

None. All three artifact types (receipt, ledger, verification report) have a direct precedent already in this repo's `.planning/phases/` tree.

## Metadata

**Analog search scope:** `.planning/phases/01-baseline-health-verification/`, `.planning/phases/02-diff-pipeline-positioning/`, `.planning/phases/04-scale-resume-diff-output/`
**Files scanned:** `01-VERIFICATION.md`, `01-01-SUMMARY.md`, `04-VERIFICATION.md` (read in full this session)
**Pattern extraction date:** 2026-08-20
