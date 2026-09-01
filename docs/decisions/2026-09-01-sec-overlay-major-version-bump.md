## Decision: deleting the `factcheck` phase makes the defect-repair build a major version bump, and sec-overlay offers no resume-across-version guarantee.

## Context

The sec-overlay defect-repair spec found `factcheck` implemented, documented, and unreachable. No
phase row ran it, so no run ever produced a `fact-checked` verification value. REQ-42 removes the
capability instead of finishing it.

The removal crosses the plugin's public contract in four places:

1. The phase name `factcheck`, which an operator could name in a stage ledger.
2. The CLI-callable module `helpers/sec_overlay/factcheck.py`.
3. The documented prompt `agents/factcheck.md`, and its row in `agents/README.md`.
4. The `verification` enum value `fact-checked`, removed from `evidence.py`'s
   `VERIFICATION_VALUES`, from `models.py`'s docstring, and from
   `references/finding.schema.json`.

REQ-40 and REQ-43 also reorder the phase table. `redteam` moves before `report`, and `validate-fix`
becomes a phase between `patch` and `verify`.

## Alternatives considered

- Finish `factcheck` by writing the missing producer — rejected. The producer would have to observe
  agent token spend, which the orchestrator reports and the driver does not measure. Finishing the
  phase means writing a consumer nothing asks for.
- Keep the module and the prompt, and only remove the unreachable phase row — rejected. That leaves
  a CLI entry point and a documented prompt for a capability no run reaches, which is the same
  defect in a smaller form.
- Keep `fact-checked` in the `verification` enum as an accepted-but-unproduced value — rejected. A
  closed enum that admits a value no phase writes is a schema that lies about the data it describes.
- Delete all four surfaces and bump the plugin to a major version — selected.

## Reasoning

A stage ledger is worth reading only when every key in it names a phase that ran. Deleting the four
surfaces together costs a planned feature and buys that property. The code stays in git history at
`b79e6ec^`, so nothing is unrecoverable.

The bump is major because each of the four surfaces was reachable from outside the plugin. A caller
of `factcheck.py`, a workspace carrying a `fact-checked` verification value, or a schema validator
pinned to the old enum all break. Semver's answer to a removed public surface is a major bump, and
the commit carries a `BREAKING CHANGE:` footer.

## Trade-offs accepted

- A workspace resumed from a 1.x run carries stage keys in the old phase order and re-runs phases.
  This is accepted, because no resume-across-version guarantee exists today. No code reads a stored
  version to decide what to skip.
- A finding whose stored `verification` is `fact-checked` now fails schema validation. No run
  produced that value, so no real workspace holds one, but a hand-edited fixture would.
- `models.py` and `evidence.py` are byte-pinned by `helpers/tests/test_frozen_contract.py`, and both
  changed. Their sha256 digests were recomputed per that test's stated procedure. **The separate Go
  port must receive the identical two-file change by hand.** This obligation is recorded in
  `b79e6ec`'s commit body and is not discharged by this branch.

## Supersedes

none
