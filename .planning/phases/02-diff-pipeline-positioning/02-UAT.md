---
status: complete
phase: 02-diff-pipeline-positioning
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md]
started: 2026-08-19T18:30:00Z
updated: 2026-08-19T18:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Excluded file handling
expected: Review over a diff touching a generated or non-allowlisted file excludes that file with a named reason (deleted/binary/generated/not-allowlisted/too-large); the run completes and exits 0.
result: pass
evidence: Temp repo diff (uv.lock, img.png, ok.py) — excluded [('img.png','binary'),('uv.lock','not-allowlisted')], reviewable ['ok.py'], exit 0.

### 2. Zero reviewable files exits 0
expected: A review whose diff contains zero reviewable files (all excluded) exits 0 (vacuous success) instead of crashing on an empty coverage manifest.
result: pass
evidence: Diff containing only uv.lock and img.png (both excluded) — review exits 0, no crash.

### 3. Invalid ref rejection
expected: `sec-overlay review --base <invalid-ref> --head HEAD` exits 2 with a clear error before any file selection or manifest work; a leading-dash ref is rejected.
result: pass
evidence: `--base not-a-real-ref` prints "error: unresolvable ref: 'not-a-real-ref'" and exits 2; `--base --` rejected with usage, exits 2.

### 4. Report and review ledger outputs
expected: After a review run, the markdown report contains a "Position review required" section and a "Dropped Findings" section (headings present even when empty), and `artifacts/review_ledger.json` exists with `position_reviews` and `dropped` keys.
result: pass
evidence: report.md has "## Dropped findings" (line 13) and "## Position review required" (line 18) with explicit none lines; review_ledger.json contains position_reviews and dropped keys.

### 5. Review CLI exits 0 and seals complete on single-file diff
expected: `sec-overlay review --base <sha> --head <sha>` on a single-changed-file diff exits 0 and seals the coverage manifest `complete`
result: pass
source: automated
coverage_id: D1

### 6. diffscope resolves refs to SHAs first
expected: `diffscope` resolves both refs to SHAs before any other git call and returns `ChangedFile` records
result: pass
source: automated
coverage_id: D2

### 7. file_select.partition splits without importing Finding
expected: `file_select.partition` splits changed files into reviewable/excluded without importing `Finding`
result: pass
source: automated
coverage_id: D3

### 8. Coverage manifest completeness invariant
expected: Coverage manifest holds one entry per reviewable file, both resolved SHAs, and raises rather than sealing over an unfinished entry
result: pass
source: automated
coverage_id: D4

### 9. Stdlib-only unified diff hunk parser
expected: `diffhunks.parse_hunks`/`added_line_numbers` parse a unified diff with stdlib only
result: pass
source: automated
coverage_id: D5

### 10. Position gate drops outside-diff findings
expected: `phase_gate.review_position_gate` drops a finding whose confirmed line falls outside the diff, keeps an in-hunk finding, and leaves the audit-mode gate untouched
result: pass
source: automated
coverage_id: D6

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
