# Phase 2: Diff Pipeline & Positioning - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 02-diff-pipeline-positioning
**Areas discussed:** Coverage module naming, diffscope extension shape, Exclusion policy, Decline & drop visibility

---

## Coverage module naming

| Option | Description | Selected |
|--------|-------------|----------|
| New review_coverage.py | Distinct module, zero risk to the shipped audit-mode coverage.py | ✓ |
| Extend coverage.py | One coverage concept in one file, higher regression risk | |
| You decide | Claude picks at planning time | |

**User's choice:** New `review_coverage.py`.

| Option | Description | Selected |
|--------|-------------|----------|
| artifacts/ as JSON | coverage_manifest.json in the run's artifacts/ directory, incremental writes | ✓ |
| In-memory + final emit | State in process, file only at seal time | |

**User's choice:** Persist at `artifacts/coverage_manifest.json`.

| Option | Description | Selected |
|--------|-------------|----------|
| Module-enforced strict | review_coverage.py owns transitions; illegal moves raise | ✓ |
| Advisory states | Driver writes states freely; only the seal check is hard | |

**User's choice:** Module-enforced strict transitions.

| Option | Description | Selected |
|--------|-------------|----------|
| partial only on failures | partial seals only when every non-done entry is failed and named | ✓ |
| partial covers pending too | An interrupted run may seal partial with pending files | |

**User's choice:** `partial` only on failures; any `pending` entry blocks sealing.

---

## diffscope extension shape

| Option | Description | Selected |
|--------|-------------|----------|
| Additive, keep old API | ChangedFile + changed_file_records() beside existing functions | ✓ |
| Migrate callers to new API | One API, but touches shipped audit callers | |

**User's choice:** Additive extension; existing callers untouched.

| Option | Description | Selected |
|--------|-------------|----------|
| ValueError + CLI exit 2 | Validation raises in diffscope; cli.py exits 2 with one-line message | ✓ |
| CLI-only validation | Only cli.py validates; library callers unguarded | |

**User's choice:** ValueError in the module, exit 2 at the CLI.

| Option | Description | Selected |
|--------|-------------|----------|
| Resolve once at run start | rev-parse both refs after validation; all calls use pinned SHAs | ✓ |
| Resolve per call | Symbolic refs each call; a moving branch skews the run | |

**User's choice:** Resolve once at run start; SHAs recorded in the manifest.

| Option | Description | Selected |
|--------|-------------|----------|
| Review new path, keep old_path | R records carry path=new, old_path=old; review the new path | ✓ |
| Treat rename as delete+add | --no-renames; loses rename context | |

**User's choice:** Review the new path; keep `old_path` on the record.

---

## Exclusion policy

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode OCR mirror | allowed_ext.go list as a module constant | ✓ |
| Config-file driven | Allowlist from a config file; adds unneeded surface | |

**User's choice:** Hardcoded OCR-mirror allowlist constant.

| Option | Description | Selected |
|--------|-------------|----------|
| Binary files | Reason `binary` | ✓ |
| Lockfiles/generated | Default-exclude globs, reason `generated` | ✓ |
| Size cap | Oversized diffs excluded | ✓ |

**User's choice:** All three exclusion categories (multi-select).

| Option | Description | Selected |
|--------|-------------|----------|
| Excluded as too-large, named | Over 5000 diff lines: reason `too-large`, named, never in manifest | ✓ |
| Marked failed, not excluded | Oversized file enters manifest as failed; run seals partial | |

**User's choice:** Excluded as `too-large`, named in output.

| Option | Description | Selected |
|--------|-------------|----------|
| Lock five reasons | Closed enum: deleted, binary, generated, not-allowlisted, too-large | ✓ |
| Open vocabulary | Free strings | |

**User's choice:** Closed reason enum, test-asserted.

---

## Decline & drop visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Report section + JSON | Dedicated report section plus JSON state needs-position-review | ✓ |
| JSON only | Machine output only; human report omits declines | |

**User's choice:** Report section + JSON.

| Option | Description | Selected |
|--------|-------------|----------|
| Listed with reason | Per-finding dropped ledger (path, line, outside-diff) in report + JSON | ✓ |
| Count only | Aggregate count without detail | |

**User's choice:** Per-finding dropped-findings ledger.

| Option | Description | Selected |
|--------|-------------|----------|
| Nonzero exit + named files | partial exits nonzero (suggested 3), names every failed file | ✓ |
| Exit 0 + warning text | Scripted callers would treat partial as success | |

**User's choice:** Nonzero exit with named files.

---

## Claude's Discretion

- Internal manifest JSON schema fields beyond {file, state, SHAs}
- Hunk-parser data structures and positioning window sizes
- Exact default-exclude glob list
- Module implementation order and test fixture strategy

## Deferred Ideas

- CLI flag to override the 5000-line size cap — belongs with Phase 4's flag surface
