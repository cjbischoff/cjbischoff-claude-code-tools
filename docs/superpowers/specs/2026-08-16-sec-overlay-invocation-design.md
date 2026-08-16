# Design — a driven invocation path for sec-overlay

**Status.** Design only. Approved 2026-08-16. No plugin file changes until an implementation plan is approved.
**Plugin.** sec-overlay (installed 1.30.3). Source under `plugins/sec-overlay/`.
**Evidence base.** One full 20-stage run over a 382-file Go repo; 70 numbered observations in
`review_sec-overlay-harness_20260814_1258.md`; the prior spec `spec_sec-overlay-invocation_20260815_0949.md`.
**Scope choices.** A1 (one command) · B1 (thin driver module) · C1 (receipts + fence + O-65 only) · D1
(inferred roles shown at the confirm step).

---

## Problem

The plugin has no `commands/` directory. Invocation is skill-only: a human or main agent reads `SKILL.md`
and hand-drives all 20 stages — substituting about nine tokens per agent spawn, remembering `record_stage`
after each phase, and persisting each agent return. Six of the seven defects in the run's final round are
consequences of that hand-driving, not of the analysis code.

The correlation layer is worse. `sec_overlay/correlate/` is a complete deterministic package — manifest,
ingest, three edge builders, re-threshold, mermaid, SARIF, artifact skeletons — with a working CLI at
`python -m sec_overlay.correlate --manifest <p> --out <p>`. The string `correlate` appears nowhere in
`SKILL.md`. The capability has no documented caller.

This design adds one command and one small driver module that reach both.

## Goals

1. One command audits one repo, or audits several repos and correlates them.
2. No hand token-substitution, no remembered `record_stage`.
3. No stage advances without a receipt on disk.
4. An audit never writes into the tree it is auditing.
5. Multi-repo correlation reaches the existing core, infers roles, and drops unified docs into the
   directory the command runs from.

## Non-goals

Named so the omission is deliberate, not an oversight. Each is tracked for a separate coverage-family
design.

- Concept-enumeration recall (O-23, O-24, O-25, O-26, O-28, O-39, O-43, O-45).
- Wiring / upward-reachability check (O-47).
- Type-vs-syntax reasoning (O-48, O-49).
- Input-contract / fail-open family (O-37, O-40, O-55).
- Post-stage-7 dedupe and finding state (O-46, O-50, O-51, O-52, O-54); report exit code (O-57).
- Scoring and disposition (O-30, O-32, O-53, O-70).
- Anchor-content gate (O-59) and verify fallback (O-60, O-61) — cheap, but detection-side, so grouped
  with the coverage design.

---

## Section 1 — Command surface and routing (A1)

One command file, `plugins/sec-overlay/skills/sec-overlay/commands/audit.md`:

```
/sec-overlay:audit <repo> [<repo> ...]
```

Routing:

1. Count the repo arguments.
2. **One repo** — run the single-repo audit and stop. No correlation, no CWD output. The existing
   pipeline, driven instead of hand-run.
3. **Two or more repos** — audit each repo, then correlate. Before correlation, stop and confirm with the
   operator (Section 4).

No `correlate` subcommand and no manifest argument. The member list comes from the repo arguments; the
manifest is an internal artifact the driver synthesizes (Section 3), never operator-authored.

**Trade-off.** A stand-alone re-correlate is not a separate command. To re-correlate, re-run `audit` with
the same repos: each per-repo audit resumes from its last receipt, so only correlation re-runs. Accepted,
because it removes the manifest-authoring step.

---

## Section 2 — The driver (B1) and the fixes it carries (C1)

New module `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/run.py`, three functions.

| Function | Job | Closes |
|----------|-----|--------|
| `write_env(ws, target, scope)` | Resolve the ~9 substitution tokens once; write `run.env` in the workspace. Agent phases read tokens from there. | ~30 hand substitutions; wrong-root risk |
| `receipt(ws, phase, stdout, artifacts, counts)` | Write `kb/receipts/<phase>.json` after every phase, including phases that print nothing. `record_stage` runs only after the receipt exists. | O-67 (silent gate), O-69 (stdout-only counts) |
| `fence(target, baseline)` | Re-check `git status --porcelain` against the run's opening snapshot; any delta stops the run and names the file. | O-68 (writes into the audited tree) |

One edit outside `run.py`: `agents/redteam-adversary.md` writes its verdicts to
`kb/gates/redteam-adversary.json`, not the path the renderer overwrites with `verdicts: {}` on every
render. One writer per path. Closes O-65.

**Not in this design:** O-59 anchor gate, O-60/61 verify fallback (Non-goals).

**Trade-off.** `run.py` is new code with tests, versus prose-only instructions in the command file. It is
the smaller long-run cost: the review shows the hand-driven path re-introduces O-67 and O-68 every run.

### Driver loop (single repo)

1. **Open.** Resolve the workspace via `RepoMemory(<target>)`. Call `run_status()` for
   `{finished, resumable, next_phase, stages_done}`. Snapshot `git status --porcelain` on the target as
   the fence baseline. `write_env` once.
2. **Loop** from `next_phase` to the end: run the phase, capture stdout verbatim, `fence`, `receipt`,
   then `record_stage`.
3. **Close.** `postflight`, then print the receipt index.

Resume falls out of steps 1–2 sharing `run_status()`: an interrupted run restarts at the first phase with
no receipt, not at phase 0.

---

## Section 3 — Role inference and manifest synthesis (net-new)

The correlation core needs a manifest whose members each carry a `role` from the closed set
`rbac-source`, `service-enforcer`, `infra` (`correlate/manifest.py:9`). No inference exists today. A new
function infers one role per repo from its `kb/scan-profile.json`, which recon already produces.

| Role | Signal in scan-profile |
|------|------------------------|
| `rbac-source` | `subsystems` / `frameworks` / `attack_surface` name authentication or authorization machinery: auth, rbac, iam, policy, interceptor, middleware, identity |
| `service-enforcer` | the profile exposes network request handlers: gRPC/HTTP services, network entrypoints in `attack_surface` |
| `infra` | everything else, and the default when the signal is ambiguous |

The `infra` default is deliberate. A wrong `rbac-source` label fabricates a `control-enforces` edge, which
drives a false promote or demote verdict in `rethreshold`. Under-correlating is logged as a
`coverage-gap`; over-correlating produces a wrong finding. Signal-over-noise wins, and D1 (Section 4) lets
the operator correct a wrong role before correlation runs.

Inference lives in `run.py` beside the driver. The driver writes the synthesized manifest into the correlation workspace, then calls the existing
`python -m sec_overlay.correlate --manifest <synth> --out <cwd>` unchanged. `member_key` is
`<slug>#<scan_scope>`, so two sub-services of one monorepo remain distinct members.

**Trade-off.** Inference is a heuristic and will mislabel some repos. It is stated, surfaced at the confirm
step, and correctable — not silent.

---

## Section 4 — Multi-repo flow and CWD output (D1)

1. Audit each repo in turn (Section 1); each resumes from its own receipts.
2. After the last audit, infer each repo's role (Section 3).
3. **Confirm.** Print: the repo count, each repo's inferred role, and that correlation will write unified
   docs into the current directory. Wait for the operator. A wrong role is the cue to abort and correct.
4. On go, synthesize the manifest and run `correlate --out <cwd>`.
5. Output lands in the current directory: `ARCHITECTURE.md`, `THREAT_MODEL.md`, `REDTEAM.md`,
   `FINDINGS.md`, plus `edges.json`, `verdicts.json`, `report.sarif`. The narrative agents
   (`correlate-combiner`, `cross-repo-adversary`) fill and adversary-check the narrative slots.
6. Receipt and fence apply once for the correlation step too.

`rethreshold` emits a `coverage-gap` verdict for any barrier whose enforcer repo the operator did not
include; the combiner renders those as open. A missing repo never becomes a clean result.

### Why correlation earns its place

A large share of a single repo's unresolved findings turn on facts in sibling repos — does an interceptor
authenticate the services, is a handler panic recovered per request. `control_enforces_edges` links an
`rbac-source` member's control to a `service-enforcer` member's unguarded sink; `rethreshold` promotes,
demotes, or gaps the finding on that edge. The capability existed in the plugin with no way to reach it.

---

## Section 5 — Verification

The properties under test are the fence, the receipt, the O-65 split, role inference, and routing.

1. **Fence.** Run one phase, `touch <target>/x`; the next fence check stops the run and names `x`.
2. **Receipt.** Run the findings gate through the driver; `kb/receipts/findings-gate.json` exists with
   non-empty `counts` though the stage prints nothing.
3. **O-65.** Render the plan, then run the adversary; `kb/gates/redteam.json` still carries the plan and
   `kb/gates/redteam-adversary.json` carries the verdicts.
4. **Role inference.** Unit test over sample scan-profiles maps to the expected role, including the
   ambiguous → `infra` default.
5. **Routing.** Unit test on argument count: one repo → audit only; N repos → audit each then correlate.

Every executable change ships its test in the same commit (repo governance).

---

## Section 6 — Governance and distribution

- **Version.** Shipping-file changes (`commands/`, `agents/`, `helpers/`) bump the plugin `version`. This
  is a `feat`, so a minor bump in `plugins/sec-overlay/.claude-plugin/plugin.json`.
- **Docs-track-code.** The same commit updates each touched folder's `README.md`: a new `commands/README.md`,
  plus `agents/README.md` and `helpers/README.md`. The plugin `CHANGELOG.md` gets an entry.
- **Branching.** Branch per change, Conventional Commits, stage explicit paths only, PR, wait for
  CodeRabbit's walkthrough comment before merge.
- **Distribution.** This adds a working-tree fence and a driver that shells out per stage — a change to the
  harness's own trust boundary. If these changes are published rather than kept local, `security-review` is
  available and worth running against the diff first. Operator's call; it is not run unasked.

---

## What gets built

| Item | Kind | Replaces |
|------|------|----------|
| `commands/audit.md` | new command + 20-row stage table | ~30 hand substitutions, remembered `record_stage` |
| `commands/README.md` | new folder README | — |
| `helpers/sec_overlay/run.py` | `write_env`, `receipt`, `fence` | operator memory |
| role-inference function (in `run.py`) | scan-profile → role | the manifest-authoring step |
| Edit `agents/redteam-adversary.md` | one path string | the O-65 collision |
| Tests for driver, inference, routing | new | — |

Not built, deferred to the coverage-family design: everything under Non-goals.
