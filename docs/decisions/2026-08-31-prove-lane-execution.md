## Decision: sec-overlay may execute target-derived code in one opt-in phase, `prove`, and nowhere else.

## Context

sec-overlay held a single invariant across all 27 phases: the harness reads the target and never
runs it. The static-to-runtime bridge was `redteam-plan.md`, a plan a human runs by hand. REQ-30 of
the sec-overlay improvements spec asks the harness to prove a finding by running it, so a confirmed
finding can carry a reproduction instead of a static receipt alone.

Running target-derived code reverses the invariant. The reversal is broad-impact: it changes what
the harness is permitted to do to a machine, and every later phase inherits the result.

## Alternatives considered

- Attach proof to the existing `redteam` phase — rejected. That prompt's charter is explicit
  no-execution. Folding execution into it makes the charter unreadable and gives no way to switch
  execution off.
- Attach proof to a `verify` agent prompt — rejected. No such prompt exists; verification is
  deterministic Python.
- Add a top-level `ScanProfile` field for the flag — rejected. `ScanProfile.from_dict` calls
  `cls(**d)`, so an unknown top-level key raises. The flag lives in the existing `scan_options`
  dict instead.
- Add a new `prove` phase behind `scan_options.prove_findings`, default off — selected.

## Reasoning

One phase owns the reversal, so the invariant still reads as a single sentence with one named
exception. The flag defaults off, so an operator opts in per run and a target that cannot be built
degrades to today's behaviour rather than failing. The phase is skipped by the driver when the flag
is off, so a default run costs no model dispatch and writes no file.

Soundness is bounded by three conditions that must hold together. The agent drove a real entrypoint,
the class has a wrapper-decidable oracle, and the oracle observed the effect. A slice-only proof
attaches a human-runnable harness and stays `needs-runtime`. `sqli` and `authz` route to a human-run
harness, because their oracles need a provisioned backend.

Containment is structural, not advisory. Every build and every run happen under `ws.repro`, outside
the target tree. The oracle is a stdlib loopback HTTP collector, so a proof needs no network egress
and the lane adds no dependency.

## Trade-offs accepted

- The harness can now run code on the operator's machine. There is no sandbox and no network
  namespace on darwin; containment rests on the out-of-tree build root and the prompt's hard rules.
- `evidence.py` stays byte-identical for the D-15 frozen-contract test, so the reproduction receipt
  vocabulary lives in `prove.py`. A `reproduction`-only confirmed finding leaves `receipt_tier`
  null and takes `runtime_disposition` `static-settled`.
- A proof bypasses the Tier-1 tool-receipt requirement. The bypass is narrower than a Tier-1
  receipt in one way and wider in another: it needs an observed effect, but it trusts the agent's
  report of what it ran.

## Supersedes

none
