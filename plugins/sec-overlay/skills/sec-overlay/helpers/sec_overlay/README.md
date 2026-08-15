# `sec_overlay/` — the Python core package

The deterministic pipeline package: SAST orchestration, the tool-receipt gate, finding identity,
scoring, reporting, campaign state, and per-repo memory. Stdlib-only (no runtime dependencies).

**The authoritative, grouped module map lives in [`../README.md`](../README.md#sec_overlay--module-map-grouped-by-job)** — that
table lists every module by job and is kept current with the code. This file is the in-package
entry point; read the parent map for the full inventory.

- Package layout: ~72 modules at the top level, plus the `correlate/` subpackage (cross-repo
  correlation — see the parent map's `sec_overlay/correlate/` section).
- Two in-code invariants enforced here: the tool-receipt gate (`evidence.py` + `findings_gate.py`)
  and never-silent backends (`prefilter.py`). See [`../README.md`](../README.md#the-two-invariants-in-code).
- CLI-callable modules (`python -m sec_overlay.<module>`) are listed in the parent map.

When a module here changes, update the module map in [`../README.md`](../README.md) **and** this
pointer if the package layout changed — in the same commit (enforced by the pre-commit hook).

`cost.py` gained `aggregate_by_model` (per-model token totals, alongside the existing
`aggregate_by_phase`), feeding `report.py`'s "Run economics" section — see the module map entry.

`models.py`'s `Finding` gained `cluster_id` (systemic-cluster id) and `affected_sites` (member
sites on a cluster primary) — additive, nullable fields that round-trip through `to_dict`/
`from_dict`.

`selfscore.py` (new) computes the per-run self-score from workspace findings and persists it to
`CampaignState.budget["self_score"]` — see the module map entry. `build_self_score` now also
returns a `shipping` count over the full `evidence.SHIPPING_STATUSES` set, alongside the
narrower `reported` count (`confirmed`/`fixed` only) it retains for backward continuity.

`evidence.py` gained a shared tier/status vocabulary: `TIER1_RECEIPTS`/`TIER2_RECEIPTS` (partition
`_MECHANICAL`), `SHIPPING_STATUSES`, `RUNTIME_DISPOSITIONS`, and the `receipt_tier()`/
`confirms_alone()` predicates — a single source of truth for later modules that need to know
whether a source can confirm a finding alone.

`models.py`'s `Finding` gained `receipt_tier: int | None` — an additive, nullable field that
round-trips through `to_dict`/`from_dict`. It holds the value `evidence.receipt_tier()` derives
once a gate stamps it; `None` before that.

`cluster.py` (new) groups ≥3 same-class, same-sink `raw` findings into one systemic cluster,
run after dedupe and before the critic/gate ladder — see the module map entry.

`report.py` gained `collapse_clusters`, which reduces each systemic cluster to one representative
finding (highest-risk member, or the elected primary if present) before the confirmed and
needs-runtime buckets are counted and rendered; `render_ndt` renders an affected-sites table when
the finding carries `affected_sites`.

**Breaking:** `findings_gate.validate_findings` now enforces the tier model instead of the
old "any mechanical receipt confirms" rule. It stamps `Finding.receipt_tier` (the lowest —
strongest — tier among `evidence_sources`, via `evidence.receipt_tier`), rejects a
`confirmed`/`fixed` finding unless `evidence.confirms_alone` is true (a Tier-1 receipt), and
rejects any `runtime_disposition` outside `evidence.RUNTIME_DISPOSITIONS`. A ripgrep-only
receipt — previously sufficient for SAST-unsupported languages — now fails the gate; route
that finding to `needs-deployment-testing` instead. `driver._act_findings_gate` raises
`PhaseHalt` when the gate returns any error, so a rejected finding now halts the phase
instead of passing through silently.

`scope.py` (new) checks `is_external_package(pkg, ws)` against `kb/scan-scope.json`'s
`ingested_packages` list, so a sink that resolves into an un-ingested dependency can be flagged as
outside the scanned source — returns `False` (not external) when no manifest exists, so the check
never invents a boundary — see the module map entry.

`calibrate.py` gained `_EXTERNAL_CAP` (3) and `_is_external_boundary`: a finding whose
`reachability.blocker == "external-boundary"` has its `risk_score` capped at 3 (below the medium
floor of 4) and `completeness_tier` set to `"external-unverifiable"`, so it can never present as a
confirmed medium regardless of claimed severity.

`report.to_markdown` partitions the needs-runtime bucket further: findings with
`completeness_tier == "external-unverifiable"` render in their own "Leads — pending
external-dependency verification" section (via `render_ndt`), separate from the source-provable
needs-runtime section, so a capped external-boundary lead is never conflated with an in-repo
needs-runtime finding.

`sarif.py` gained `_rules()`, populating `driver.rules` from the finding set (de-duplicated by
`rule_id`, `cls` as `name`, `asvs_ids`/`codeguard_ids` as `properties`) — additive only, `results`
unchanged — see the module map entry.

`sarif.to_sarif` gained a `suppressed` parameter: findings in that list get a `suppressions:
[{"kind": "inSource", "justification": "needs runtime proof"}]` entry on their SARIF result, others
carry none. `report.write_report` now defaults to passing all reportable findings plus
`needs-deployment-testing` findings as `suppressed` (behavior change on upgrade — SARIF used to
carry confirmed/fixed only); `confirmed_only=True` (CLI: `--confirmed-only`) restores the prior
confirmed/fixed-only SARIF with no suppressions.

`calibrate.py`, `selfscore.py`, `sarif.py`, and `report.py` are `ruff format`-clean as of the
review-improvements branch; keep them that way (run `ruff format` before committing edits here).

`phases.py` (new) is the ordered phase table (`PhaseSpec`, `PHASE_TABLE`) plus pure sequencer
helpers (`missing_inputs`, `outputs_present`, `next_actionable_phase`) the audit driver walks —
see the module map entry.

`driver.py` (new) is the audit sequencer: deterministic-phase runner, loud halt, agent-dispatch
printer. `run_deterministic_phase` checks a `PhaseSpec`'s inputs, runs its registered
`DETERMINISTIC_ACTIONS` entry, checks its outputs, then calls `record_stage` — raising
`PhaseHalt` if an input or output artifact is missing. `AuditContext` carries the workspace,
target, config, pinned SHA, and lazily-loaded `ScanProfile` an action needs. `render_dispatch`
returns the printable block for an agent phase — prompt file plus `{{TARGET}}`/`{{WORKSPACE}}`/
`{{SHA}}` substitutions, plus an optional `{{ATTACK_CLASS}}` line when called with `classes=` —
with no side effects; the orchestrator runs the model. It raises if called on a deterministic
phase (`prompt is None`). At the `investigate` phase, `run_audit` reads `agents_to_spawn` from
`kb/scan-profile.json`, widens it with `partition.reconcile_plan` (recon-omitted classes), passes
the reconciled list to `render_dispatch(classes=...)`, and appends `unrouted_triage_dispatch`'s
block — naming any candidate class still unrouted after reconciliation, with its count — so a
`security-other`/`unknown` leftover never silently drops out of triage. `patch` gets the same
reconciled class list passed to `render_dispatch(classes=...)` (no triage block, unlike
`investigate`) — a multi-class run's fixes are no longer dispatched with one class token.

`DETERMINISTIC_ACTIONS` is now fully populated: `prefilter` → `prefilter.run_prefilter`,
`findings-gate` → `findings_gate.validate_findings`, `dedupe` → `dedupe.dedupe_findings`,
`calibrate` → `calibrate.calibrate_findings`, `verify` → `verify.verify_findings`
(a `static-only` re-verify routes the finding to `needs-deployment-testing`, never leaves it
`confirmed` implying a dynamic check passed; only `verified-static` promotes to `fixed`),
`demote-noise` → `partition.demote_noise`, `report` → `report.write_report`, `selfscore` →
`selfscore.write_self_score`. `run_audit(ctx)` walks `PHASE_TABLE` from the first phase not yet
`done`: runs deterministic phases in place, and for an agent phase auto-advances only when it has
an output path that is *not also* one of its inputs (several agent phases — `investigate`,
`critic`, `judge`, `validate`, `trace`, `patch` — declare the same `findings_dir` callable as both
input and output, so the dir's mere presence never counts as "this phase ran"); otherwise it
returns `render_dispatch(...)` and stops. Returns `"AUDIT COMPLETE"` once every phase is `done`.
`cli.py` exposes this as its `audit` subcommand (`python -m sec_overlay.cli audit --target <T>
--config <rules> [--workspace <WS>] [--sha <sha>]`): resolves the workspace the same way `scan`
does and prints `run_audit`'s return value. It does **not** call `state.begin_pass` (C1 fix,
0.10.1) — `audit` is re-invoked repeatedly across a single pass (the orchestrator runs an agent
phase, then calls `audit` again to advance), and `begin_pass` wipes `state.stages` and bumps
`pass_number` whenever any stage is recorded, which would livelock the six `findings_dir`-in/out
agent phases and inflate `pass_number` by one per call. Pass lifecycle is owned solely by the
campaign supervisor, which calls `begin_pass` once before the first `audit` invocation, mirroring
the `scan` path (`scan` has never called `begin_pass`).

`driver.py`'s `run_audit` also now guards its direct `scan-profile.json` read at the
investigate/patch branch (M1, 0.10.1): an absent or malformed file raises `PhaseHalt` instead of
an unhandled `FileNotFoundError`/`JSONDecodeError`, matching the "loud halt" contract every other
phase gate honors.

`redteam.py`'s `_above_bar` is now coverage-first: a critical/high/medium finding above the risk
floor earns a manual test directive regardless of receipt strength — a missing tool receipt no
longer withholds the runtime test that would settle it (it still sorts later via `receipts`
rendering `_no tool receipt (verify carefully)_` in the directive block). The dead
`redteam:prime-manual-test` history branch (no producer ever wrote that event) is removed.

`redactor.py` and `factcheck.py` are now wired into the driver (ISSUE-047, ISSUE-051).
`render_dispatch` passes its composed block through `redactor.safe_for_prompt` before returning —
a security control that guarantees no dispatch block the orchestrator prints can carry a
high-confidence secret. `factcheck` is a new deterministic phase between `trace` and `calibrate`,
declared with no inputs/outputs so a hard gate never halts the run before Plan B's fact-check
agent exists: `_act_factcheck` reads `kb/verdicts.json` if present, applies each entry via
`factcheck.apply_verdict` (validated first with `factcheck.validate_verdict`), and no-ops silently
when the file is absent.

`phase_gate.py`'s `_parse_ref` (ISSUE-024/028) now anchors a citation with a leading-match regex
(`_REF_ANCHOR`) instead of `rsplit(":", 1)`, so a trailing human hint after the line or range
(`foo.py:42 in the handler`) is stripped instead of failing the ref to resolve. A bare path with
no colon-line, or a colon whose first tail token isn't numeric, still returns `(ref, None)`.
