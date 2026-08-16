# /sec-overlay:audit

Audit one repository, or audit several and correlate them.

## Usage

    /sec-overlay:audit <repo> [<repo> ...]

## Routing

1. Count the repo arguments.
2. **One repo** — drive the single-repo audit and stop. No correlation, no CWD output.
3. **Two or more repos** — drive each repo's audit, then correlate.

## Single repo

Drive the audit from `helpers/` using `sec_overlay.run.drive()`:

    cd plugins/sec-overlay/skills/sec-overlay/helpers
    uv run python -c "from sec_overlay.run import drive; print(drive('<repo>', config='rules/smoke.yaml'))"

The driver writes `run.env` once, and fences the tree and writes a receipt before
each stage. When it prints a `NEXT AGENT PHASE` block, run that agent prompt, then
re-invoke `drive` to resume from the first phase without a receipt.

## Multiple repos

1. Drive each repo's audit in turn (each resumes from its own receipts).
2. Infer each repo's role from its `kb/scan-profile.json` (`sec_overlay.run.infer_role`).
3. **Confirm** with the operator: the repo count, each repo's inferred role, and that
   correlation will write unified docs into the current directory. A wrong role is the
   cue to abort and correct.
4. On go, synthesize the manifest (`sec_overlay.run.synthesize_manifest`), write it into
   the correlation workspace, and run the existing core:

       uv run python -m sec_overlay.correlate --manifest <synth> --out "$PWD"

5. Output lands in the current directory: `ARCHITECTURE.md`, `THREAT_MODEL.md`,
   `REDTEAM.md`, `FINDINGS.md`, plus `edges.json`, `verdicts.json`, `report.sarif`.

A barrier whose enforcer repo the operator did not include is emitted as a
`coverage-gap`, never a clean result.
