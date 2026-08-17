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

The driver writes `run.env` once, pins the pass SHA, and — before each deterministic
stage — fences the tree against the pass baseline and writes a receipt. When it prints
a `NEXT AGENT PHASE` block, run that agent prompt so it writes its declared outputs,
then close the phase with `advance` (it fences the tree, writes the receipt, and records
the stage):

    uv run python -c "from sec_overlay.run import advance; advance('<repo>', '<phase>')"

Then re-invoke `drive` to continue to the next phase. Resume is stage-based: `drive`
picks up at the first phase with no recorded stage.

## Multiple repos

1. Drive each repo's audit in turn (each resumes from its own recorded stages).
2. Infer each repo's role from its `kb/scan-profile.json` (`sec_overlay.run.infer_role`).
3. **Confirm** with the operator: the repo count, each repo's inferred role, and that
   correlation will write unified docs under the current directory (in `artifacts/`). A
   wrong role is the cue to abort and correct.
4. On go, synthesize the manifest (`sec_overlay.run.synthesize_manifest`), write it into
   the correlation workspace, and run the existing core:

       uv run python -m sec_overlay.correlate --manifest <synth> --out "$PWD"

5. Output lands under the current directory: `ARCHITECTURE.md`, `THREAT_MODEL.md`,
   `REDTEAM.md`, `FINDINGS.md`, and `report.sarif` in `<cwd>/artifacts/`; the raw
   `edges.json`, `verdicts.json`, and `product.json` at `<cwd>` itself.

A barrier whose enforcer repo the operator did not include is emitted as a
`coverage-gap`, never a clean result.
