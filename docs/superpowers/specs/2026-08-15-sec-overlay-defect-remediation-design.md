# sec-overlay defect remediation — design

**Date:** 2026-08-15
**Status:** Draft for user review
**Branch:** `docs/sec-overlay-remediation-spec`
**Input:** `review_agentgateway/brainstorming/review_sec-overlay-issues_20260814_1507.md`
(57 issues, ISSUE-001 to ISSUE-057, from a full `agent-gateway` audit run)

---

## 1. Goal

Correct the 57 defects the `agent-gateway` review found in the `sec-overlay` plugin.
The plugin must reach three outcomes:

1. **Complete code coverage with accurate findings.** Independent agents on a stronger
   model family aggressively try to disprove every load-bearing claim. A finding a human
   acts on is dataflow-proven or is marked for a live test — never confirmed on a
   syntactic match alone.
2. **Artifacts a security engineer and a developer can act on.** The report, the SARIF
   file, and the red-team plan must be accurate, readable, and free of filler. A final
   independent agent reviews the shipped artifacts before the run ends.
3. **Controlled speed and token cost.** Deterministic methods and the plugin's existing
   tools do the mechanical work. Agents run only where judgment is required.

Goals 1 and 2 are primary. Goal 3 is secondary and never overrides 1 or 2.

## 2. Scope

- **In scope:** all 57 issues, grouped into the seven fix themes T1–T7 the review
  defines, plus one new capability (an artifact-review phase, §4.8) that goal 2 requires
  and no existing issue covers.
- **Out of scope:** any change to the model-family-diversity invariant, the tool-receipt
  safety contract, or the seven strengths the review's section E lists (§3.4). The
  harness never executes the target; it emits a plan a human runs.
- **Target of the fix:** the git-tracked source at
  `plugins/sec-overlay/skills/sec-overlay/`. The review cites the installed `0.2.1`
  cache; fixes land in source and ship through a version bump.

This one spec is intentionally large. It decomposes into several implementation plans at
the writing-plans stage (§7). The build order is T1 → T2/T3 → T4/T5 → T6/T7, because the
orchestration driver (T1) and the shared vocabularies (T2/T3) are the substrate every
later theme reads.

## 3. Constraints and invariants

### 3.1 Engineering constraints

- **Stdlib-only core.** No new runtime dependency without user sign-off. Dev
  dependencies stay `pytest`, `ruff`, `ty`.
- **TDD.** Every behavior change lands with a failing test first, then the fix. Security
  behavior (the receipt-tier gate) follows the security-fix order in the TDD rule: write
  the attack/regression test, confirm it fails on current code, then fix.
- **Governance.** Branch per change; Conventional Commits; docs track code in the same
  commit; a shipping-file change bumps `plugin.json` by commit type. Stage explicit
  paths only; never `--no-verify`.
- **Bench regression.** `helpers/bench/` locked positives must keep being detected. The
  receipt-tier change (§4.3) may move a locked positive from `confirmed` to
  `needs-deployment-testing`; that is a status change, not a detection loss. The bench
  assertions check detection, not terminal status — confirm this holds before landing
  T3, and adjust a bench assertion only if it over-asserts on status.

### 3.2 Model-family-diversity invariant (preserve)

Every load-bearing artifact is pressure-checked by an adversary on a stronger family
(opus) than the sonnet producer. The new artifact-review agent (§4.8) obeys this rule.
With only one family available, degrade to a fresh-context validator and log it.

### 3.3 Tool-receipt safety contract (preserve)

Adversarial reasoning alone demotes or downgrades a finding but never deletes a
tool-receipt-backed finding. Only a competing receipt deletes. This contract governs the
new artifact-review agent too: it can force a re-render or demote a claim; it cannot
delete a receipt-backed finding.

### 3.4 Do not regress (review section E / §0.11)

Preserve: the `redteam-plan.md` shape (authorization first, named unrunnable
preconditions, shell-variable payloads, five-key test blocks); the risk-sorted triage
table; finding history as an audit trail; the opus adversary passes; honest preflight;
the `CONTEXT.md` shape; and the C1 rework that locates a control before judging it.

---

## 4. Design

### 4.1 T1 — one `audit` driver (root of 001, 002, 006, 007, 030, 038, 039, 044, 045, 047, 050, 051, 053)

**Decision:** add `sec_overlay.cli audit --target <T>` — a deterministic sequencer that
owns phase order, preconditions, and resumability. It does **not** own agent invocation.
The orchestrator still spawns each independent subagent, which keeps the disproving
agents independent and keeps the driver stdlib-only and deterministic.

The driver:

1. **Runs every deterministic phase in a fixed order** and calls the six tested-but-
   unwired modules (ISSUE-051), including `factcheck` (ISSUE-047) and `redactor` (a
   security control). It runs `demote_noise` and `reconcile_plan` as ordered steps, not
   optional calls (ISSUE-006), and runs the noise/clustering step before report so the
   clone set collapses (ISSUE-007).
2. **Gates advancement on preconditions.** A phase advances only when the prior phase's
   declared artifacts exist **and** `record_stage` ran. This kills the silent partial
   run (ISSUE-038) and guarantees the review phases (critic → judge → validate → trace,
   red-team adversary, artifact-review) are never skipped.
3. **Halts loudly on a missing output.** No artifact, no advance, visible error — this
   traces a lost subagent (ISSUE-015) instead of a run that "looks unstarted."
4. **Prints the exact next agent dispatch** — the prompt name plus token substitution —
   when the next phase is an agent phase. The orchestrator supplies the model call.
5. **Is resumable.** Phase state persists; a re-run skips completed phases. `verify`
   costs 128 s and `prefilter` 137 s in this run — never pay them twice (goal 3).
6. **Places `findings_gate` right after investigate** (ISSUE-044), not six phases late,
   so a schema-invalid finding fails before dedupe (ties to ISSUE-041).
7. **Runs independent phases without a false serial dependency** (ISSUE-030) where the
   phase-state graph shows no artifact dependency between them.

`SKILL.md:104` and `CLAUDE.md:56` are corrected to the real `begin_pass(Workspace, sha)`
signature (ISSUE-002). The patch prompt receives the full class set for a multi-class
input, not one class token (ISSUE-050). The `trace` phase, which writes `reachability`
correctly, becomes a required phase in the driver, not optional (ISSUE-045). A dropped
class's candidates are surfaced, not orphaned: the driver calls
`unrouted_candidate_classes` and spawns general triage when non-empty (ISSUE-039).

**Phase-state model.** Each phase declares `name`, `inputs` (artifact paths that must
exist to start), `outputs` (artifact paths that must exist to finish), `kind`
(`deterministic` or `agent`), and `record_stage` key. The driver reads this table,
checks inputs, runs or prints, checks outputs, records the stage. The table is the single
source of phase order — the prose ladder in `SKILL.md` becomes documentation of the
table, not the authority.

**Verify honesty (ISSUE-053).** `verify` cannot dynamically verify an agent-found
finding with no runnable reproduction; it writes `static-only` after 128 s. The driver
records verify's real capability per finding: a finding with no reproduction is routed to
`needs-deployment-testing`, not left implying a dynamic check ran.

### 4.2 T2 — one ref parser and one shared schema (024, 025, 026, 028, 035, 040, 041, 046)

**Decision:** the producer prompt and the gate share one reference parser and one schema.

- **Ref parser.** Parse `path:line[-range]`, then treat any trailing text as an optional
  human hint, stripped before resolution (ISSUE-024, ISSUE-028). Today `_parse_ref`
  splits on the last colon and rejects a valid `file line hint` reference as one long
  filename.
- **Schema.** Add the required recon output the schema omits (ISSUE-025). Validate a
  finding against the schema at the gate so a schema violation fails there instead of
  crashing dedupe (ISSUE-041).
- **Recon gate.** Require a non-comment code reference to establish an attack surface — a
  comment line must not (ISSUE-026).
- **Render check.** A prompt render fails loudly if any `{{token}}` is unfilled
  (ISSUE-040), which also protects the patch prompt (ISSUE-050).
- **Evidence vocabulary told to agents.** Inject the receipt-tier set and the
  shipping-status set into every agent prompt as a `references/prompt-constants.md` block
  (ISSUE-046), so the closed vocabulary is no longer a secret the agent must guess.
- **Semantic gap (ISSUE-035) stays split by design.** The deterministic gate proves a
  reference *resolves*. Whether it *means* what the prose claims is the opus
  phase-adversary's job. This matches the deterministic-first, agent-for-judgment
  boundary set in T1 — do not try to make the deterministic gate judge meaning.

### 4.3 T3 — one shipping-status set and one receipt-tier model (003, 048, 054, 055, 057)

**Decision:** two shared definitions, read by every gate, filter, red-team bar, and
selfscore.

- **Receipt-tier model (ISSUE-003).** Split `_MECHANICAL` into two tiers, recorded on the
  finding so a reader sees proof strength.
  - **Tier 1 — confirms alone:** `codeql`, `semgrep`, `sca`, `secrets`. Each is
    proof-complete for its finding shape (a dataflow path, a vulnerable version, a live
    secret).
  - **Tier 2 — corroborates only:** `ripgrep`, `structural-index`, `ast-grep`. These
    locate code; they do not prove reachability.
  - A Tier-2-only finding cannot reach `confirmed`. It routes to
    `needs-deployment-testing`. This is forced by goal 1 plus the safety contract
    (§3.3): a syntactic match plus LLM reasoning must not confirm.
- **Shipping-status set.** `confirmed`, `fixed`, `needs-deployment-testing`, read by the
  receipt gate (ISSUE-048), the fact-check filter (ISSUE-057), the red-team bar
  (ISSUE-054), and selfscore. Today each reads its own narrower subset; that mismatch is
  the root of the four issues.
- **`runtime_disposition` gets an enum and a gate (ISSUE-055).** The field is free text
  today; the agent wrote the literal `"neither"` on 6 of 25 findings and no gate caught
  it. Define an enum (`needs-runtime`, `static-settled`, `unassessed`) and reject an
  out-of-vocabulary value at the gate.
- **Red-team bar — coverage-first (ISSUE-054).** Every `needs-deployment-testing`
  finding gets a full manual test directive, not a one-line bullet. The plan grows from
  ~11 to ~21 directives; it stays risk-sorted so the highest-value directives read first.
  Drop the `has_receipt` conjunct from the severity clause — a missing receipt sorts a
  directive later, it does not withhold the test that would settle the finding. Delete
  the dead `redteam:prime-manual-test` hatch or give an agent prompt that writes it; a
  branch no caller reaches misleads a reader.

**Tradeoff accepted:** more findings land in `needs-deployment-testing` and the plan is
longer. This is the accuracy-and-coverage cost the user chose over a shorter,
less-complete artifact.

### 4.4 T4 — a route-to-control table derived once (016, 027, 029, 031, 036, 037, 049)

**Decision:** derive a route-to-control table once (deterministic, from the graph and
the structural index) and check each phase's output against it. A missing route, control,
or entrypoint is a **logged gap** carrying `reason` and `next_step`, never dropped
(serves goal 1's completeness bias).

- Recon must summarise the external route table it exists to summarise (ISSUE-027).
  Architecture must report all controls the table holds, not one of four (ISSUE-029).
  Threat-model must keep every entrypoint its own input described (ISSUE-036).
- Doc coverage is recorded: documents discovered vs documents read, with a warning when
  the ratio is low (ISSUE-016, ISSUE-021). C1 read 3 of 200 documents and recorded
  nothing.
- The recon agent plan is checked against the classifier; unrouted candidate classes
  spawn a general-triage agent so the agent set is not under-planned (ISSUE-031, wired by
  the T1 driver).
- **Class extensions (ISSUE-037, ISSUE-049) — fallback now.** 11 of 17 planned classes
  have no extension file. Make investigate and patch **degrade gracefully to the base
  prompt and log the gap**, so no class is ever silently unhandled. Coverage is preserved
  immediately. Authoring the 11 extensions is tracked as a separate follow-on, not
  blocked inside this spec.

### 4.5 T5 — fact-check over every shipping status + a reachability pre-check (004, 005, 017, 018, 019, 020, 023, 032, 033, 042, 056)

**Decision:** the fact-check pass reads the full shipping-status set (not just
`confirmed`), and every red-team payload and every citation gets a reachability
pre-check.

- An agent's return text must be written to an artifact; the driver's precondition gate
  requires the finding file to exist, so a finding cannot live only in chat (ISSUE-017).
- Deterministic citation resolution rejects an empty `line: 1` anchor and a citation that
  does not resolve (ISSUE-018, ISSUE-019). C1 control findings go through the same
  evidence and anchor requirements as any other finding, written by code, not by hand
  (ISSUE-023).
- Reconcile runs after any context rewrite so findings do not drift from a rewritten
  context (ISSUE-020, wired by the driver).
- Prefilter skips its own sidecar output directory (ISSUE-032) — add the workspace dir to
  `_SKIP_DIRS`.
- Cross-session false-positive feedback keys on the content fingerprint, not the
  workspace path, so it survives a workspace rename (ISSUE-033).
- Cross-class dedupe compares the structured fingerprint (`rule_id | cls |
  enclosing-symbol`), not free text, and same-line duplicates no longer leak (ISSUE-042,
  ISSUE-005).
- CodeQL must actually attach a receipt when it runs; investigate why it produced 9
  entries across 134 findings and fix the pack/config path (ISSUE-004, ties to the
  preflight pack check).
- The red-team producer traces a payload source→sink through the target's own input
  validation before emitting it; a payload it cannot trace is marked an unrunnable
  precondition, not shipped as a live test (ISSUE-056). This is the reachability
  pre-check applied to payloads.

### 4.6 T6 — per-finding fields for the constant sections + a split, risk-sorted report (009, 010, 011, 012, 013, 022, 052)

**Decision — the three constant report sections (ISSUE-052, P0):** delete two, collect
one.

- Ship §1, §2, §3, §5, §7 (summary, data flow, evidence/receipts, severity,
  remediation) — each carries real per-finding data today.
- **Delete §6 (Confirmed Attack Scenario) and §8 (Testing).** Both restate §2 and §7. A
  "Confirmed Attack Scenario" heading whose body is a constant misleads a reader who
  quotes headings; the run confirmed no scenario.
- **Add `impact` as one required `Finding` field**, rendered in its own section and gated
  non-empty in `findings_gate`. Impact is the one section a security engineer needs and
  cannot derive from the data flow. The artifact-review agent (§4.8) checks it is not
  filler.

**Decision — report length (ISSUE-009):** split into an executive report plus per-finding
detail, risk-sorted.

- The T1 clustering fix removes ~32% of the 2701-line file (the log-injection clone set)
  for free; re-measure after.
- `report.md` stays short (target ~150 lines): the bottom line in **words** ("1 critical,
  1 high, 32 medium, 9 low" — ISSUE-010, not `1/1/32/9`), a risk-sorted triage table with
  a real short **title** column (ISSUE-011, no mid-word truncation), the top shipping
  findings in full, and links to the rest.
- Per-finding detail for the ~25 shipping findings goes to `findings/<ID>.md` — markdown a
  developer reads, not raw JSON. The 70 informational findings stay in JSON behind a
  linked index.
- The body orders by **risk score, not status**.
- Prefilter findings are renamed from `C-####` to their class prefix after classification
  (ISSUE-013). The context diagram obeys its own style rule (ISSUE-022).
- The coverage ledger requires `reason` and `next_step` on any `needs_follow_up`
  disposition; the gate rejects a bare label (ISSUE-012, ties to T4).

### 4.7 T7 — per-phase timing and token records + a selfscore that reads the shipping set (008, 014, 015, 021, 034, 043)

**Decision:** the driver records per-phase wall-clock; agents self-report token spend in
their output envelope (a deterministic phase has no tokens). Selfscore reads the
shipping-status set (ties to T3).

- No phase runs untimed and no agent phase runs untracked (ISSUE-014); the run stops
  reporting no timing and no token spend.
- A lost subagent is traced by the driver's loud halt on a missing artifact (ISSUE-015).
- `provenance.docs_read` counts the documents actually read (ISSUE-021, ties to
  ISSUE-016).
- Two self-checks that report success while checking nothing are made to assert a real
  condition or deleted (ISSUE-034) — the same dead-code shape as ISSUE-051.
- The critic, which rejected nothing in two runs (ISSUE-043), gets a real rejection
  criterion or is flagged for removal, since judge and validate already filter. This is a
  measurement task: instrument the critic's reject rate first (now possible under the new
  telemetry), then decide.
- Flat risk scores (ISSUE-008) trace to upstream severity inputs, not the scorer; fix at
  the calibrate input, not the scorer.

### 4.8 New — an independent artifact-review phase (goal 2)

**Decision:** add a final `artifact-review` agent (opus, a different family from the
sonnet report producer) plus a deterministic `artifact_gate` companion, after `report`
and `redteam`.

- **`artifact_gate` (deterministic, runs first).** Mechanically checks the cheap things
  before the agent spends tokens: no constant or placeholder section survives, no triage
  cell is truncated, every shipping finding has a per-finding detail file and a red-team
  directive, every rendered claim cites a finding that exists. A failure here is fixed by
  a re-render, not by the agent.
- **`artifact-review` agent (opus, judgment).** Reads the rendered `report.md`,
  `report.sarif`, and `redteam-plan.md` against the findings they cite and flags: a claim
  the findings do not support, a section that is unreadable, a shipped finding with no
  test path, filler in the `impact` field. Its verdict can demote a claim or force a
  re-render.
- **Safety contract (§3.3) binds it:** it cannot delete a tool-receipt-backed finding.
  Only a competing receipt deletes.
- The driver runs `artifact_gate` → `artifact-review` as gated phases; the run does not
  finish until both pass or their findings are recorded.

---

## 5. Data model and interface changes

- `Finding` gains `impact: str` (required, gated non-empty) and a receipt-tier record
  (Tier 1 / Tier 2) derived from its `evidence_sources`.
- `runtime_disposition` becomes an enum (`needs-runtime`, `static-settled`,
  `unassessed`), gated.
- New shared constants: `SHIPPING_STATUSES = {confirmed, fixed,
  needs-deployment-testing}` and `TIER1_RECEIPTS` / `TIER2_RECEIPTS`, imported by every
  gate, filter, red-team bar, selfscore, and the T2 prompt-constant block.
- New CLI: `sec_overlay.cli audit`. New modules: the phase-state table/driver, and
  `artifact_gate`. New agent prompt: `agents/artifact-review.md`.
- Corrected docs: `SKILL.md` and `CLAUDE.md` `begin_pass` signature; the four folder
  READMEs track every code change in the same commit (enforced).

## 6. Testing strategy

- **TDD per behavior.** Each issue's fix lands with a failing test first. The receipt-tier
  gate follows the security-fix order: an attack test (a Tier-2-only finding must not
  reach `confirmed`) that fails on current code, then the fix.
- **Contract tests stay green.** `tests/test_contracts.py` (prompt↔schema drift) and
  `tests/test_wiring.py` (silent-backend regression) must pass; the wiring test is
  extended to assert the six previously-unwired modules are now called by the driver.
- **Bench regression.** Locked positives keep being detected after the receipt-tier
  change; a locked positive that moves to `needs-deployment-testing` is still detected.
- **Driver ordering test.** A phase whose input artifact is missing must halt the driver
  loudly; a completed phase must be skipped on resume.
- **Artifact-gate test.** A report with a constant section, a truncated cell, or a
  shipping finding with no directive must fail `artifact_gate`.

## 7. Decomposition into plans

This spec becomes several implementation plans, built in dependency order:

1. **Plan A — T1 driver + phase-state table** (001, 002, 006, 007, 030, 038, 039, 044,
   045, 047, 050, 051, 053, 015). The substrate everything else needs.
2. **Plan B — T2 parser/schema + T3 status/receipt vocabularies** (024, 025, 026, 028,
   035, 040, 041, 046, 003, 048, 054, 055, 057). The shared definitions.
3. **Plan C — T4 coverage table + T5 accuracy/provenance** (016, 027, 029, 031, 036, 037,
   049, 004, 005, 017, 018, 019, 020, 023, 032, 033, 042, 056).
4. **Plan D — T6 report split + T7 telemetry + artifact-review phase** (009, 010, 011,
   012, 013, 022, 052, 008, 014, 021, 034, 043, plus the new phase).

Each plan gets its own version bump and CHANGELOG entry per governance. The version
increment is derived from each plan's commit types; the CLI addition and the report
split are `feat` (minor), the status-set unification is a contract change and is called
out as breaking (`!` / major) if it changes a shipped finding's status semantics.

## 8. Traceability — all 57 issues

| Issue | P | Theme | Where fixed |
|---|---|---|---|
| 001 | P1 | T1 | §4.1 audit driver |
| 002 | P2 | T1 | §4.1 begin_pass signature |
| 003 | P1 | T3 | §4.3 receipt tiers |
| 004 | P2 | T5 | §4.5 CodeQL receipt |
| 005 | P2 | T5 | §4.5 dedupe same-line |
| 006 | P1 | T1 | §4.1 noise gate ordered |
| 007 | P1 | T1 | §4.1 clustering before report |
| 008 | P3 | T7 | §4.7 calibrate input |
| 009 | P1 | T6 | §4.6 report split |
| 010 | P2 | T6 | §4.6 counts in words |
| 011 | P2 | T6 | §4.6 title column |
| 012 | P2 | T6 | §4.6 ledger reason/next_step |
| 013 | P3 | T6 | §4.6 class-prefix IDs |
| 014 | P2 | T7 | §4.7 timing/tokens |
| 015 | P1 | T1/T7 | §4.1 loud halt |
| 016 | P1 | T4 | §4.4 doc coverage recorded |
| 017 | P1 | T5 | §4.5 artifact-written findings |
| 018 | P1 | T5 | §4.5 citation resolution |
| 019 | P2 | T5 | §4.5 anchor check |
| 020 | P2 | T5 | §4.5 reconcile on rewrite |
| 021 | P3 | T7 | §4.7 docs_read count |
| 022 | P2 | T6 | §4.6 diagram style |
| 023 | P2 | T5 | §4.5 control findings by code |
| 024 | P1 | T2 | §4.2 ref parser |
| 025 | P2 | T2 | §4.2 recon schema field |
| 026 | P1 | T2 | §4.2 non-comment reference |
| 027 | P1 | T4 | §4.4 route table |
| 028 | P1 | T2 | §4.2 ref parser hint |
| 029 | P1 | T4 | §4.4 all controls |
| 030 | P2 | T1 | §4.1 no false serial dep |
| 031 | P2 | T4 | §4.4 agent-plan check |
| 032 | P1 | T5 | §4.5 skip sidecar |
| 033 | P1 | T5 | §4.5 fingerprint-keyed feedback |
| 034 | P2 | T7 | §4.7 real self-checks |
| 035 | P1 | T2 | §4.2 semantic gap split |
| 036 | P1 | T4 | §4.4 entrypoint retained |
| 037 | P2 | T4 | §4.4 class-ext fallback |
| 038 | P0 | T1 | §4.1 driver + preconditions |
| 039 | P1 | T1 | §4.1 unrouted candidates |
| 040 | P3 | T2 | §4.2 render check |
| 041 | P1 | T2 | §4.2 schema at gate |
| 042 | P1 | T5 | §4.5 structured dedupe |
| 043 | P2 | T7 | §4.7 critic criterion |
| 044 | P1 | T1 | §4.1 gate ordering |
| 045 | P2 | T1 | §4.1 trace required |
| 046 | P1 | T2 | §4.2 vocabulary in prompts |
| 047 | P1 | T1 | §4.1 factcheck wired |
| 048 | P1 | T3 | §4.3 gate reads shipping set |
| 049 | P1 | T4 | §4.4 class-ext reaches patch |
| 050 | P2 | T1 | §4.1 patch multi-class |
| 051 | P1 | T1 | §4.1 six modules wired |
| 052 | P0 | T6 | §4.6 constant sections |
| 053 | P1 | T1 | §4.1 verify honesty |
| 054 | P1 | T3 | §4.3 coverage-first bar |
| 055 | P1 | T3 | §4.3 disposition enum |
| 056 | P1 | T5 | §4.5 payload reachability |
| 057 | P1 | T3 | §4.3 factcheck shipping set |

Tally: 2 P0, 31 P1, 20 P2, 4 P3 — all 57 mapped.

## 9. Open items for follow-on (not blocking this spec)

- Author the 11 missing class-extension files (T4 tracks a graceful fallback now).
- Decide the critic's fate after its reject rate is instrumented (ISSUE-043).
