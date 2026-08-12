# sec-overlay improvements from the lumedeodorant review

**Date:** 2026-08-12
**Status:** Approved for implementation
**Branch:** `feat/sec-overlay-review-improvements`

## Goal

Add four improvements to the `sec-overlay` plugin. Each one closes a gap found
during a comparison of two runs on the `lumedeodorant` repository: an older
`sec-harness` run and a current `sec-overlay` run.

The four improvements are:

1. Per-stage token accounting and a run self-score (I3).
2. Systemic finding clustering (I1).
3. External-boundary confidence disposition (I2).
4. SARIF completeness with rule metadata and suppressed leads (I4).

Build order: I3, then I1, then I2, then I4. I3 comes first because it makes every
later change measurable.

## Background

A review compared two runs against `lumedeodorant`:

- `sec-overlay` ran against commit `b215b91` (current HEAD).
- `sec-harness` ran against commit `948fd7a`, dated 11 days earlier.

The review found four concrete gaps. Each maps to one improvement below.

1. **Token spend could not be measured.** `helpers/sec_overlay/cost.py` has the
   full accounting machinery (`record_agent`, `aggregate_by_phase`,
   `estimate_cost_usd`), but `CampaignState.budget` stayed `{}` in both runs. The
   orchestrator never called `record_agent`.
2. **Finding-count inflation.** `sec-overlay` reported 20 findings; 12 were the
   same authorization pattern across 12 different subscription routes.
   `helpers/sec_overlay/dedupe.py` merges only exact `(file, line, cls)`
   collisions, so 12 findings in 12 files never merged. Adversarial verification
   could not confirm any of the 12 alone, yet they are one systemic risk.
3. **External-dependency confidence.** Two of the 12 findings were unconfirmable
   because the ownership check may live in the un-vendored
   `@lumedeodorant/account-portal-core` package. The pipeline had no way to record
   "confidence capped: the sink crosses into an un-ingested package," so these
   landed as flat medium findings.
4. **SARIF drops leads.** `helpers/sec_overlay/sarif.py` always emits `rules: []`.
   `helpers/sec_overlay/report.py` (documented at line 321) restricts SARIF to
   `confirmed`/`fixed`, so 17 of 20 findings never reached SARIF. A consumer that
   reads SARIF saw 15% of the findings.

## Method

Each improvement follows the plugin's existing ladder and TDD rule. Every helper
change ports a failing test first, then the implementation to green. All paths
below are relative to `plugins/sec-overlay/skills/sec-overlay/`.

The two decisions taken during design:

- **I1 is recorded, not report-only.** Machine consumers (the I3 self-score, SARIF,
  per-repo memory) read finding records, not `report.md`. Report-only clustering
  would leave the inflation in every machine consumer. Clustering reuses the
  existing `duplicate_of` primary-election pattern.
- **I4 defaults to suppressed-full.** All reportable findings reach SARIF;
  `needs-deployment-testing` findings carry a SARIF `suppressions` entry, so a
  compliant gate still gates on `confirmed`/`fixed` only. This is a visible change
  to SARIF output on upgrade — recorded in the CHANGELOG.

## I3 — Per-stage token accounting and self-score

**Change points:**

- `SKILL.md` orchestration: after each subagent return, call
  `cost.record_agent(state, phase, model, tokens)` next to the existing
  `record_agent_return`. Tokens come from the subagent result usage.
- If the harness does not surface per-subagent token usage, record agent count and
  output bytes as a proxy, labelled as a proxy, never as a measured token figure.
- `helpers/sec_overlay/report.py`: add a "Run economics" section — tokens by phase,
  model mix, and the USD figure explicitly labelled an estimate.
- `postflight`: write a self-score object to `state.json` — reported count,
  confirmed-vs-needs-runtime ratio, cluster count, rejected count, and
  external-boundary count.

**Invariant:** the self-score reads finding records after the gate, so its counts
match `findings.json` exactly.

**Tradeoff:** token counts depend on the harness surfacing usage. The proxy
fallback keeps the section honest when usage is absent.

## I1 — Systemic finding clustering

**Constraint:** do not delete the sibling findings. Each route is a distinct sink
and individually exploitable if the check is truly missing. Group, do not drop.

**Change points:**

- New no-LLM pass `sec_overlay.cluster`, run after `dedupe`. Group active findings
  by `(cls, sink_symbol)` where `sink_symbol` is resolved from the graph
  (`graph.json`). A group of 3 or more sites elects a `cluster_primary` using the
  same severity-then-id rule dedupe already uses, and stamps `cluster_id` on all
  members.
- `references/finding.schema.json`: add two optional nullable fields — `cluster_id`
  (string) and `affected_sites` (array). The `cluster_primary` carries
  `affected_sites`; members carry `cluster_id`. Additive and optional, like the
  existing `duplicate_of` — existing readers ignore unknown fields.
- `helpers/sec_overlay/report.py`: render a cluster as one section with a sites
  table. `select_reportable` counts the cluster as one headline item.

**Guards against over-merging:**

- Require the same `cls` AND the same sink symbol from the graph.
- Never cluster a finding already `confirmed`. Clustering applies to the
  `raw`/`needs-deployment-testing` tier only, where the 12-way pattern lives.

**Invariant:** every member of a cluster shares one `cluster_id`; exactly one
member per cluster is the primary and carries `affected_sites`; no `confirmed`
finding is ever a non-primary member.

## I2 — External-boundary confidence disposition

**Change points:**

- `agents/validate.md` and `agents/trace.md`: when a dataflow sink resolves into a
  dependency that is not in the ingested source set, set
  `reachability.blocker = "external-boundary"` and record the package name in
  `preconditions`.
- Add a `completeness_tier` value `external-unverifiable`. `report.py` renders a
  distinct bucket, "Leads — pending external-dependency verification," separate
  from source-provable leads.
- `helpers/sec_overlay/calibrate.py`: cap `risk_score` for `external-boundary`
  findings so they cannot present as a confirmed medium.
- `kb/scan-scope.json`: add an ingested-package manifest so the boundary check is
  deterministic, not guessed.

**Invariant:** a finding whose sink crosses into a package absent from the ingested
manifest is never reported as `confirmed`; it is a lead in the external bucket.

**Tradeoff:** the check needs the ingested-package manifest. Without it, the stage
cannot tell an un-ingested dependency from a first-party module, so the manifest is
a prerequisite for this improvement.

## I4 — SARIF completeness

**Change points:**

- `helpers/sec_overlay/sarif.py`: populate `driver.rules` from the `rule_id`/`cls`
  set, with `asvs_ids` and `codeguard_ids` as rule properties. Unconditional and
  strictly additive.
- `helpers/sec_overlay/report.py`: emit `needs-deployment-testing` findings as SARIF
  results with `suppressions: [{"kind": "inSource", "justification": "needs runtime
  proof"}]`. Keep `confirmed`/`fixed` unsuppressed. This is the new default.
- Add a `scan_options` flag to restore the old confirmed-only output for consumers
  that do not honor suppressions.

**Invariant:** SARIF results marked with a `suppressions` entry are exactly the
`needs-deployment-testing` findings; `confirmed`/`fixed` findings carry no
suppression.

**Tradeoff:** default SARIF content changes on upgrade — a previously clean
dashboard shows suppressed leads. A naive consumer that counts `results[]` length
blindly sees a higher count. The `scan_options` flag is the escape hatch.

## Governance

- Branch: `feat/sec-overlay-review-improvements`. No direct commits to `main`.
- I1's schema addition is additive and optional — a `feat`, not a `feat!`.
- I4's default SARIF change is a behavior change — call it out in the CHANGELOG
  `### Changed` group.
- Each commit updates `README.md` and adds a `CHANGELOG.md` entry. Commits inside a
  Directory Guide folder update that folder's `README.md` too.
- Do not bump the plugin `version` field — the user bumps it manually per release.

## Test-harness note (not a plugin change)

The review could not cleanly attribute run differences because the two runs used
different commits (`b215b91` vs `948fd7a`, 11 days apart). Any future A/B of the
plugin must pin both runs to the same target SHA. Record this in the bench README
when the eval harness is next touched.

## Success criteria

1. A run populates `state.json` `budget.records`; `report.md` shows a Run economics
   section; `postflight` writes a self-score. (I3)
2. A repeat of the 12-way authz pattern produces one clustered headline finding
   with a 12-site table, not 12 findings. (I1)
3. A finding whose sink crosses into an un-ingested package appears in the external
   bucket with a capped `risk_score`, never as a confirmed medium. (I2)
4. SARIF emits populated `driver.rules`; `needs-deployment-testing` findings appear
   as suppressed results; `confirmed`/`fixed` are unsuppressed; the confirmed-only
   flag restores prior output. (I4)

## Out of scope

- Any change to the cross-repo `correlate` layer.
- Runtime/dynamic verification of `needs-deployment-testing` leads.
- A plugin `version` bump.
- Building the eval harness itself; the note above is a reminder for when it is
  next touched.
