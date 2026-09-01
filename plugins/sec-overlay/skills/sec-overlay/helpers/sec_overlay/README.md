# `sec_overlay/` — the Python core package

The deterministic pipeline package: SAST orchestration, the tool-receipt gate, finding identity,
scoring, reporting, campaign state, and per-repo memory. Stdlib-only (no runtime dependencies).

**The authoritative, grouped module map lives in [`../README.md`](../README.md#sec_overlay--module-map-grouped-by-job)** — that
table lists every module by job and is kept current with the code. This file is the in-package
entry point; read the parent map for the full inventory.

- Package layout: ~73 modules at the top level, plus the `correlate/` subpackage (cross-repo
  correlation — see the parent map's `sec_overlay/correlate/` section).
- Two in-code invariants enforced here: the tool-receipt gate (`evidence.py` + `findings_gate.py`)
  and never-silent backends (`prefilter.py`). See [`../README.md`](../README.md#the-two-invariants-in-code).
- CLI-callable modules (`python -m sec_overlay.<module>`) are listed in the parent map.

When a module here changes, update the module map in [`../README.md`](../README.md) **and** this
pointer if the package layout changed — in the same commit (enforced by the pre-commit hook).

`workspace.py`'s `read_findings`/`write_findings` now round-trip a finding's unknown JSON keys
(REQ-27): `read_findings` stashes any key absent from `Finding.__dataclass_fields__` on the
returned instance (in sorted order, for a deterministic merge) and warns on stderr naming the
preserved keys; `write_findings` merges them back into the dumped record before writing. This
never touches `models.py`, so the frozen Go-port mirror (D-15) and its sha256 pin are unaffected.

`workspace.py` gains `finding_counts(ws)` (REQ-13, folds in REQ-23), returning
`{"findings", "findings_in", "findings_out"}` — `findings_in` is every finding file,
`findings_out` is the `evidence.SHIPPING_STATUSES` subset, and `findings` repeats
`findings_in` for the pre-REQ-13 consumer. `run.py`'s two receipt writers (`drive`'s
`on_complete`, `advance`) call it instead of glob-counting `findings/F-*.json` — no real
finding id starts `F-`, so every receipt recorded zero. `driver._write_gate` and
`artifact_gate.run_artifact_gate` merge the same two keys into their gate JSON payload, so a
gate receipt records counts, not only `passed`.

`detection_coverage.py`'s `generate()` now emits a dependency-internal sink row in the
rule-sources table — see the module map entry in [`../README.md`](../README.md) for the
full contract.

`rule_gaps.py`'s `emit_semgrep_rule` takes a new `safe_option` keyword. With it, the emitted
rule is an absence rule: it fires only on a construction missing the named safe option. Its
id then sits under `sec-overlay.absence.` instead of `sec-overlay.`. Without it, behavior is
unchanged.

`dependency_sinks.py` (new) loads and validates `../references/dependency-sinks.json` — the
catalog of dependencies whose own code holds a sink — and exposes `catalog_ids()` for later
receipt-id validation, plus `match_manifests()`/`matched_classes()` to check a target repo's
manifests against the catalog. `manifest_paths()` returns the declaring manifest per matched
entry, relative to the target root, so a recall claim can cite a ref the reader can open. See the module map entry in [`../README.md`](../README.md) for
the full contract and the CLI-callable list for its `list`/`match` subcommands.

`review_findings.py` (new, REV-01) adds the review-profile gate `apply_profile` — see the
module map entry in [`../README.md`](../README.md) for the full contract; `cli.py`'s
`run_review` and `report.py`'s `write_report`/`write_review_ledger` now thread its
`ReviewFinding` output through, both documented at the same map entries.

`review_result.py` (new, REQ-P7) adds `write_review_result`, the consolidated per-run
`artifacts/review_result.json` writer — `cli.py`'s `run_review` calls it last on both consume
exits. See the module map entry in [`../README.md`](../README.md) for the full key contract.

`run_review` takes a `tier` argument (`--tier fast|assured`, default `assured`, REQ-T3a). The
`fast` tier skips the plan half — the `--prepare --plan` step returns without emitting
`plan_manifest.json` — while `assured` runs the full chain. The tier is recorded in both
`review_result.json` and its `CoverageManifest` (`review_coverage.py` now carries `tier` through
`__init__`/`to_dict`/`from_dict`).

`pr_poster.py` (new, REQ-S1) is the stdlib GitHub pull-request review poster — `route_findings`
splits critical/high (inline) from the rest (summary), `build_review_payload` builds a `COMMENT`
review, and `post_review` POSTs it with an injectable transport. The composite `action.yml` at
the plugin root invokes it. See the module map entry in [`../README.md`](../README.md).

`sessions.py` (new, REQ-S2) renders read-only over the per-repo sidecar — `session_rows` and
`render_rows` list one row per slug (pass, sha, finding counts), `resolve_session` picks `latest`
by mtime or a slug, and `session_detail`/`render_detail` show stages plus a ledger summary with a
`--severity` finding filter. Wired as `cli.py`'s `sessions list|show` subcommand. See the module
map entry in [`../README.md`](../README.md).

`background.py` (new, REQ-P8) adds `load_background`, sanitizing developer-supplied background
context before it enters a review prompt — a 1 MB `BACKGROUND_MAX_BYTES` cap, control-character
strip, envelope-delimiter neutralization, a hard secret abort, then `redactor.safe_for_prompt`.
`review_agent.render_review_prompt` gains a `background` kwarg; `cli.py`'s `review` gains
`--background`/`--background-file`. See the module map entry in [`../README.md`](../README.md).

`workspace.py`'s `Workspace` now coerces `str` path arguments via a hand-written `__init__`
instead of a dataclass `__post_init__` — the stored fields stay `Path`-typed, but the
constructor accepts `str | Path` so `Workspace('<path>')` (as agent-authored prompts write it)
type-checks under `ty` as well as running correctly. No behavior change.

`kb.py` gained the arc42/threat-model tree path helpers (`arch_dir`/`arc42_path`/
`container_diagram_path`, `threat_dir`/`threat_model_path`/`dfd_path`), replacing the old
`kb/architecture.md` and `kb/THREAT_MODEL.md` single-file paths; `kb_status` now reports
`arc42_path`/`threat_model_path` existence. `workspace.py`'s `Workspace.ensure()` now also
creates `architecture/runtime-view/` and `threat-model/attack-sequences/` under the workspace
root. `kb.py`'s now-dead `entities_dir` (no remaining callers once the prompts stopped reading
`kb/entities/`) was removed.

New module `cvss4_data.py`: CVSS v4.0 MacroVector lookup table (270 entries) and interpolation
tables (`MAX_COMPOSED`, `MAX_SEVERITY`), vendored verbatim from FIRST's official calculator
(BSD-2-Clause). Data only, no logic — Task 2 builds the v4.0 scoring engine on it.

`cvss.py` rewritten to CVSS v4.0: `cvss40_base(vector)` ports the MacroVector/interpolation
algorithm from `cvss_score.js` against `cvss4_data.py`'s tables (base metrics only — E/CR/IR/AR
fixed at their spec worst-case defaults, no environmental/threat support); `offensive_priority`
keeps its 3.1 branch order verbatim. `CVSS:3.x` input now raises `ValueError`.

`calibrate.py` re-pointed to `cvss40_base` (was `cvss31_base`, removed in the v4.0 migration) at
its import and both call sites; `risk_score`/`priority` derivation shape is unchanged. The
`Finding.cvss_vector` docstring in `models.py` now says "CVSS v4.0" to match.

`cvss.py`'s `_parse` now raises `ValueError` when a Threat (`E`) or Environmental (`CR`/`IR`/`AR`/
`M*`) metric is present with a value other than `X` (Not Defined) — this engine scores base
metrics only; `calibrate.py` records a `calibrate:cvss-unparseable` history event before falling
back to the heuristic score on any unparseable vector.

New module `artifact_gate.py` (§4.8): `run_artifact_gate(ws)` checks a finished run's own
artifacts — report.md free of stale constant sections and over-long triage cells, every shipping
finding has a `findings/<ID>.md` detail file and a red-team directive, every triage-table ID
resolves to a finding, and `CONTEXT.md`'s mermaid diagram stays at ≤10 nodes (ISSUE-022). Writes
`kb/gates/artifact-gate.json`; runs before the opus artifact-review adversary, never deletes
findings. `check_duplication(arc42_text, tm_text)` flags a threat-model heading that restates an
arc42 heading, or a structure heading (e.g. "Building Block View") appearing in the threat-model
doc at all; `run_artifact_gate` calls it only when both `architecture/arc42.md` and
`threat-model/threat-model.md` exist.

`context.py` gained `doc_coverage()` to compare documents discovered vs read and flag a low read ratio. The `load()` function now accepts optional `repo_root` and `scan_scope` parameters to populate `provenance["docs_discovered"]` at load time (wiring by downstream caller) — see the module map entry.

`stage_validate.py`'s `validate_stage` now raises `ValueError` for a stage with no registered
validator instead of silently passing, and `prefilter.py`'s `run_prefilter` gained a
`strict: bool = True` parameter plus a new `_raise_on_incomplete_backends` helper: a planned SAST
backend left in `skipped_reasons` or `failed` now raises `RuntimeError` instead of returning a
silent partial result (ISSUE-034). Pass `strict=False` only for a deliberately partial run. A
`"disabled"` skip reason is excluded from the raise — a profile turning a backend off on purpose
is a planning decision, not a coverage hole (R14).

`context.py` also gained `cited_source_docs()` (every `source_doc` an item or its history cites); `stage_validate.py`'s `_validate_context` now appends an error when a cited doc is absent from `provenance["docs_read"]` (ISSUE-021).

`stage_validate.py`'s `_VALIDATORS` dict now routes every entry through `_adapt_dict`/
`_adapt_optional_dict`, two small factories that isinstance-check the stage payload before
delegating to the real validator. Previously only `_validate_runtime_test` guarded against a
non-dict stage output; the other validators would raise `AttributeError` on malformed subagent
JSON instead of returning a validation error. No behavior change for well-formed input.

`findings_gate.py` gained `validate_citations(ws, root, *, statuses=None)`, a resolver-backed
citation/anchor check: it rejects any finding at a gated status (default
`evidence.SHIPPING_STATUSES`) whose `file:line` does not resolve against `root`, reusing
`phase_gate.resolve_ref`. A `line: 1` anchor is rejected only when it fails to resolve, so a real
top-of-file finding survives while a placeholder anchor on a missing file does not. Control
findings from `context.control_findings` inherit the check since they land in the same finding
files. `driver._act_findings_gate` calls it alongside `validate_findings` and folds both error
lists into the same `PhaseHalt`.

`cost.py` holds `record_timing`/`aggregate_timings_by_phase`, summing per-phase wall-clock
seconds recorded in `CampaignState.budget["timings"]` (ISSUE-014) — see the module map entry.
`write_report` folds `aggregate_timings_by_phase` into the economics dict as `by_phase_seconds`,
and `to_markdown` renders it as a "Wall-clock by phase, seconds" list in "Run economics" when
present. Token and USD accounting was removed at REQ-46: the harness never surfaced a
subagent's usage, so those tables always rendered empty.

`models.py`'s `Finding` gained `cluster_id` (systemic-cluster id) and `affected_sites` (member
sites on a cluster primary) — additive, nullable fields that round-trip through `to_dict`/
`from_dict`.

`selfscore.py` (new) computes the per-run self-score from workspace findings and persists it to
`CampaignState.budget["self_score"]` — see the module map entry. `build_self_score` now also
returns a `shipping` count over the full `evidence.SHIPPING_STATUSES` set, alongside the
narrower `reported` count (`confirmed`/`fixed` only) it retains for backward continuity.

`build_self_score` gained `critic_viable`, `critic_rejected`, and `critic_reject_rate` (0.0 with
no critic events), counted from `critic:viable`/`critic:rejected` history events across all
findings (ISSUE-043) — measurement only, nothing gates on the rate.

`evidence.py` gained a shared tier/status vocabulary: `TIER1_RECEIPTS`/`TIER2_RECEIPTS` (partition
`_MECHANICAL`), `SHIPPING_STATUSES`, `RUNTIME_DISPOSITIONS`, and the `receipt_tier()`/
`confirms_alone()` predicates — a single source of truth for later modules that need to know
whether a source can confirm a finding alone.

`evidence.py`'s `TIER2_RECEIPTS` also holds `dependency-catalog`, the receipt for a finding
whose sink lives inside a dependency's own code. A catalog match proves the dependency is
declared. It does not prove the sink is reached, so the receipt stays Tier 2 like `ripgrep`
and `ast-grep` — it locates a finding and never confirms one alone.

`findings_gate.validate_findings` now rejects a `dependency-catalog:<id>` receipt whose
`<id>` is absent from `dependency_sinks.catalog_ids()`. Without this check, free text after
the colon would read as a receipt with no real entry behind it.

`models.py`'s `Finding` gained `receipt_tier: int | None` — an additive, nullable field that
round-trips through `to_dict`/`from_dict`. It holds the value `evidence.receipt_tier()` derives
once a gate stamps it; `None` before that.

`models.py`'s `Finding` also gained `impact: str = ""` — the concrete consequence of exploitation,
rendered as the report's Impact section. `findings_gate.validate_findings` rejects a
`SHIPPING_STATUSES` finding whose `impact` is blank; non-shipping findings may stay blank.

`report.py`'s `render_finding` §4 Impact now renders that real `f.impact` text (falling back to
`"(impact not recorded)"` when blank) instead of a boilerplate sentence. The constant §6 Confirmed
Attack Scenario and §8 Testing blocks are deleted — both always emitted identical fixed prose
regardless of the finding (ISSUE-052); section numbering (`sev_no`/`fix_no`) is unchanged.

`cluster.py` (new) groups ≥3 same-class, same-sink `raw` findings into one systemic cluster,
run after dedupe and before the critic/gate ladder — see the module map entry.

`dedupe.py`'s same-line pass now keys on `(file, line, cls)` alone when `dataflow` is empty,
so two dataflow-less findings at the same site collapse regardless of message wording
(ISSUE-042); a non-empty `dataflow` still extends the key. `correlate/edges.py`'s
`_RECURRENCE_STATUSES` is now `evidence.SHIPPING_STATUSES` rather than a separate literal
(ISSUE-005).

`report.py` gained `collapse_clusters`, which reduces each systemic cluster to one representative
finding (highest-risk member, or the elected primary if present) before the confirmed and
needs-runtime buckets are counted and rendered; `render_ndt` renders an affected-sites table when
the finding carries `affected_sites`.

`report.py`'s bottom-line `Confirmed:` line now renders counts in words (`"1 critical, 1 high, 2
medium, 1 low"`, zero counts omitted, `"none"` when all zero) instead of a digit ratio
(`"1/1/2/1"`) (ISSUE-010).

`report.py` gained `_short_title(text, limit=72)`, trimming the triage table's `what` column to a
word boundary with a trailing `…` instead of cutting mid-word at a fixed 80-character slice
(ISSUE-011).

**Breaking:** `findings_gate.validate_findings` now enforces the tier model instead of the
old "any mechanical receipt confirms" rule. It stamps `Finding.receipt_tier` (the lowest —
strongest — tier among `evidence_sources`, via `evidence.receipt_tier`), rejects a
`confirmed`/`fixed` finding unless `evidence.confirms_alone` is true (a Tier-1 receipt), and
rejects any `runtime_disposition` outside `evidence.RUNTIME_DISPOSITIONS`. A ripgrep-only
receipt — previously sufficient for SAST-unsupported languages — now fails the gate; route
that finding to `needs-deployment-testing` instead. `driver._act_findings_gate` raises
`PhaseHalt` when the gate returns any error, so a rejected finding now halts the phase
instead of passing through silently.

**REQ-47:** `scope.py` is deleted — `is_external_package` had no caller. `scanscope.py`'s
`rel_to_root` helper is deleted too, for the same reason; the module now exposes only
`ScanScope`, `resolve`, `write_scope`, and `load_scope` — see the module map entry.

`calibrate.py` gained `_EXTERNAL_CAP` (3) and `_is_external_boundary`: a finding whose
`reachability.blocker == "external-boundary"` has its `risk_score` capped at 3 (below the medium
floor of 4) and `completeness_tier` set to `"external-unverifiable"`. `calibrate_findings` also
demotes a `CONFIRMED` external-boundary finding to `NEEDS_DEPLOYMENT_TESTING` (REQ-41) — the prior
rule lived only in the `validate` prompt, which cannot see the `trace`-phase blocker set after it
runs — so the finding can never present as confirmed regardless of claimed severity.

`report.to_markdown` partitions the needs-runtime bucket further: findings with
`completeness_tier == "external-unverifiable"` render in their own "Leads — pending
external-dependency verification" section (via `render_ndt`), separate from the source-provable
needs-runtime section, so a capped external-boundary lead is never conflated with an in-repo
needs-runtime finding.

`report.py` gained `write_finding_details(ws, findings, patch_statuses=None)`, which writes one
Markdown file per finding to `ws.findings_dir/<ID>.md` (full `render_finding`/`render_ndt` body).
`to_markdown` no longer inlines the "Needs runtime proof" or "Confirmed (source-provable)"
sections — it renders a risk-ordered "## Detail" link list pointing at `findings/<ID>.md` instead,
so `report.md` stays short while the full evidence stays one click away. `write_report` calls
`write_finding_details` after writing `report.md` so the linked files always exist.

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
`PHASE_TABLE` now opens with `route-census` (deterministic, no inputs, output `_route_census` —
`kb/route-census.json`). It runs before `recon` so the census reads only the target's source,
never recon's own output — see the module map entry. `PHASE_TABLE` runs `redteam` (agent,
`agents/redteam.md`, input `_findings_dir`, output `_redteam_plan` — `reports/redteam-plan.md`)
right after `demote-noise` and before `report` (REQ-40): `report` names `redteam-plan.md` in its
rendered output, so `report` now also declares `_redteam_plan` as an input, and the driver gates
on it existing before `report` may start. `selfscore` and `prove` still follow `report`, then
`artifact-gate` (deterministic, input `_report`/`_sarif`, output `_artifact_gate_json`) —
`artifact_gate.run_artifact_gate` still hard-requires `redteam-plan.md` to exist (D-01) — then
`artifact-review` (agent, `agents/artifact-review.md`, input `_artifact_gate_json`, output
`_artifact_review_json`), and finally `postflight` (deterministic, input
`_artifact_review_json`, output `context.prior_context_path` — `kb/prior_context.json`), the
durable cross-scan distillation that closes the pipeline.

`report.py` (REQ-40) no longer probes the filesystem for `redteam-plan.md`; the caller now states
whether the run produced one. `render_ndt`, `_ndt_next_actions`, `write_finding_details`, and
`write_report` all take a `has_redteam_plan` keyword — `render_ndt`/`_ndt_next_actions`/
`write_finding_details` default it `True` (the common case), `write_report` defaults it `False`
(the review-mode case with no redteam phase); `write_report` no longer needs a probe because
`driver._act_report` passes `has_redteam_plan=True`, guaranteed by `report`'s new
`_redteam_plan` input declaration. `cli.py`'s two review-mode call sites (`run_semgrep`,
`run_review`) keep the `False` default, correctly, since neither runs a redteam phase.

`report.main()` (REQ-40 fix round 1) is the one exception to the no-probe rule above. The CLI
entry point has no caller and so no phase context, and it had been passing no `has_redteam_plan`
to `write_report`, silently taking the `False` default and omitting the pointer even when
`redteam-plan.md` existed. `main()` now probes the file on disk itself, since a CLI boundary is
the single place in this module where a filesystem read stands in for a caller.

`architecture` now outputs `_arc42`/`_container` (`kb.arc42_path` /
`kb.container_diagram_path`, i.e. `architecture/arc42.md` + `architecture/container-diagram.mmd`,
not the old `kb/architecture.md`), immediately followed by the deterministic `arch-gate` row
(input those same two paths, output `_arch_gate_json` — `kb/gates/arch-gate.json`). `threat_model`
now outputs `_tm_doc`/`_dfd` (`kb.threat_model_path` / `kb.dfd_path`, i.e.
`threat-model/threat-model.md` + `threat-model/dfd.mmd`, not the old `kb/THREAT_MODEL.md`) and
takes `_arch_gate_json` as its input — the threat model cannot start until the architecture gate
passed — followed by the deterministic `tm-gate` row (output `_tm_gate_json` —
`kb/gates/tm-gate.json`).

`driver.py` (new) is the audit sequencer: deterministic-phase runner, loud halt, agent-dispatch
printer. `run_deterministic_phase` checks a `PhaseSpec`'s inputs, runs its registered
`DETERMINISTIC_ACTIONS` entry (timed with `time.perf_counter` and recorded via
`cost.record_timing` before `record_stage`, ISSUE-014), checks its outputs, then calls
`record_stage` — raising `PhaseHalt` if an input or output artifact is missing. `AuditContext`
carries the workspace,
target, config, pinned SHA, and lazily-loaded `ScanProfile` an action needs. `render_dispatch`
returns the printable block for an agent phase — prompt file plus `{{TARGET}}`/`{{WORKSPACE}}`/
`{{SHA}}` substitutions, plus an optional `{{ATTACK_CLASS}}` line — a compact JSON array of
class keys — when called with `classes=` — with no side effects; the orchestrator runs the
model. It raises if called on a deterministic
phase (`prompt is None`). `_act_route_census` calls `route_census.census(ctx.target)` and
`write_census` to persist `kb/route-census.json`. This action registers under `"route-census"`
in `DETERMINISTIC_ACTIONS` and runs before the `recon` dispatch. At the `investigate` phase, `run_audit` reads `agents_to_spawn` from
`kb/scan-profile.json`, widens it with `partition.reconcile_plan` (recon-omitted classes, plus —
via `target_root=ctx.target` — every attack class of a matched dependency-sink catalog entry),
passes the reconciled list to `render_dispatch(classes=...)`, and appends `unrouted_triage_dispatch`'s
block — naming any candidate class still unrouted after reconciliation, with its count — so a
`security-other`/`unknown` leftover never silently drops out of triage. `patch` gets the same
reconciled class list passed to `render_dispatch(classes=...)` (no triage block, unlike
`investigate`) — a multi-class run's fixes are no longer dispatched with one class token.

`DETERMINISTIC_ACTIONS` is now fully populated: `prefilter` → `prefilter.run_prefilter`,
`findings-gate` → `findings_gate.validate_findings`, `dedupe` → `dedupe.dedupe_findings`,
`calibrate` → `calibrate.calibrate_findings`, `verify` → `verify.verify_findings`
(a `static-only` re-verify routes the finding to `needs-deployment-testing`, never leaves it
`confirmed` implying a dynamic check passed; only `verified-static` promotes to `fixed`;
`verify_patch` returns a named cause from `VERIFY_CAUSES` — not a verification value —
which `verify_findings` maps to a legal `Finding.verification` value through
`_CAUSE_TO_VERIFICATION`, recording `verify:cause:<cause>` in the finding's history;
`verify_findings` resolves its own `config` scalar through `verify.resolve_configs(ws, config)`
before the loop, so every finding is re-scanned against the semgrep rulesets `recon` planned in
`kb/scan-profile.json`, not an unrelated caller-supplied path; `verify_patch`'s `config` parameter
now accepts a list too, and `_check` OR-combines a `_file_has_hit` call per config for the
semgrep backend, running codeql/sca once regardless of the list),
`demote-noise` → `partition.demote_noise`, `report` → `report.write_report`, `selfscore` →
`selfscore.write_self_score`, `artifact-gate` → `_act_artifact_gate` (calls
`artifact_gate.run_artifact_gate`, raising `PhaseHalt` naming every error when the gate rejects the
run's own artifacts), `arch-gate` → `_act_arch_gate`, `tm-gate` → `_act_tm_gate`, `postflight` →
`_act_postflight` (calls `postflight.run_postflight(ctx.ws, ctx.sha, target=ctx.target)`, which
distills the finished scan into `kb/prior_context.json` and records its own stage — D-01). Passing
`target` lets `run_postflight` derive its own drift set: it diffs the prior context's pinned SHA
against this pass's SHA in `ctx.target`'s working tree, drops prior items on any file that moved,
and keeps the rest — no caller computes `changed_files` by hand (REQ-45). `changed_files` raises
`ValueError` when `git diff --name-only` exits non-zero, naming the operation and both revisions:
a missing prior SHA would otherwise produce an empty drift set, and every stale prior conclusion
would survive. Both `arch-gate`/`tm-gate`
run `diagram_gate.run_diagram_gate` over `architecture/` (and `threat-model/` where present) plus
`ste_lint.lint_prose` over their doc, write `{"passed", "errors", "warnings"}` to
`kb/gates/<name>.json` via the shared `_write_gate` helper, and raise `PhaseHalt` naming every
error; `_act_tm_gate` additionally runs `artifact_gate.check_duplication` against `arc42.md` and
calls `run_diagram_gate(..., require_threat_model=True)` so a missing `dfd.mmd` is a gate error
instead of the silently-optional default. `redteam` and `artifact-review` are agent phases with no
registered action — each auto-advances once its declared output artifact exists
(`reports/redteam-plan.md`, `kb/gates/artifact-review.json`), same as any other output-only agent
phase. `run_audit(ctx)` walks `PHASE_TABLE` from the first phase not yet
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

`redteam.py`'s `discriminate` now gates payloads on reachability (ISSUE-056): a new
`payload_runnable(f)` returns `True` only when a finding carries a non-empty `dataflow` trace or a
`reachability` dict with `reachable is True`; an above-bar needs-runtime finding that fails this
check routes to a new `"unrunnable"` bucket instead of the manual plan — an untraceable payload is
a precondition to test for, not a live directive. `render_plan` renders this bucket as its own
`## Unrunnable preconditions (payload not traceable)` plan section (and folds its `open_questions`
into "Questions to ask") so these findings are surfaced, never silently dropped; `write_plan`'s
returned summary carries an `"unrunnable"` count alongside the other buckets.

`redactor.py` is wired into the driver (ISSUE-051). `render_dispatch` passes its composed block
through `redactor.safe_for_prompt` before returning — a security control that guarantees no
dispatch block the orchestrator prints can carry a high-confidence secret.

REQ-42 removed the `factcheck` phase (ISSUE-047), the `sec_overlay.factcheck` module, and the
`agents/factcheck.md` prompt. The phase's only input, `kb/verdicts.json`, had no producing phase,
so `_act_factcheck` no-opped on every run and the `fact-checked` verification value had no writer.

`phase_gate.py`'s `_parse_ref` (ISSUE-024/028) now anchors a citation with a leading-match regex
(`_REF_ANCHOR`) instead of `rsplit(":", 1)`, so a trailing human hint after the line or range
(`foo.py:42 in the handler`) is stripped instead of failing the ref to resolve. A bare path with
no colon-line, or a colon whose first tail token isn't numeric, still returns `(ref, None)`.

`profile.py`'s `_REQUIRED` (ISSUE-025) now includes `attack_surface_evidence`, matching
`scan-profile.schema.json`'s `required` — `subsystems` stays optional in both.

`phase_gate.py`'s new `attack_surface_gate` (ISSUE-026) rejects a recon `attack_surface` key
whose evidence refs are absent, unresolved, or resolve only to comment lines — a comment is a
claim about code, not proof it executes. Reuses `resolve_ref`/`is_comment_line`; kept separate
from `run_phase_checks` so architecture/context claims citing a comment aren't over-rejected.

`prompts.py` (new, ISSUE-040) adds `render_prompt(template, subs)`, substituting `{{KEY}}` tokens
and raising `ValueError` naming every `{{TOKEN}}` left unfilled — the orchestrator renders each
agent dispatch prompt through it so a hand-substitution gap (a literal `{{ATTACK_CLASS}}`)
fails before the model runs instead of silently reaching it.

`coverage_ledger.py`'s `build_coverage_ledger` now stamps its own `needs_follow_up` surfaces with
a `reason`/`next_step` too (previously bare), matching the shape `route_control.py`'s gap dicts
already used; `validate_coverage_ledger` rejects a `needs_follow_up` surface missing either field.

`route_control.py` (new, ISSUE-027/029/036) derives one route-to-control table
(`build_route_control_table`) and checks recon, architecture, and threat-model output against it
(`check_recon_routes`, `check_census_routes`, `check_architecture_controls`,
`check_threat_entrypoints`, `check_catalog_classes`). The table prefers the code-derived census:
it calls
`route_census.load_census(ws)` by default, or takes a `census=` list of `RouteSite` directly, and
stamps `"source": "route-census"` on the table. Without a census, it falls back to
`kb/scan-profile.json`'s `entrypoints`, stamping `"source": "scan-profile"`. The fallback path is
unchanged. Recon-derived routes still work when a target has no ripgrep-visible framework.
A missing route, control, or entrypoint is never dropped: each check returns a `needs_follow_up`
gap dict with `reason`/`next_step`, and `record_route_gaps` appends those gaps into
`kb/coverage-ledger.json`'s `surfaces`, demoting `completeness` to `partial` so the ledger's own
"complete forbids needs_follow_up" invariant still holds after the append.

`check_catalog_classes(entries, profile)` reports every `dependency_sinks.SinkEntry` class the
recon profile's `attack_surface` never named. A matched dependency, such as OPA, hides its sink
inside its own Rego policy calling `http.send`. A first-party scan misses it, so recon can omit
the whole class with no signal. Each gap row names the catalog entry and sink so a reviewer can
read why the class applies.

`phase_gate.py`'s `recall_claims(ws, profile, *, target_root)` (new) is the first caller of
`check_census_routes` and `check_catalog_classes` for the recall adversary
(`agents/recall-adversary.md`). It builds one `{"id", "refs"}` claim per deterministic omission. A census route gap keeps
the route's own `file:line` as its ref. A catalog-class gap points at the manifest that declares
the package, from `dependency_sinks.manifest_paths()`, since the adversary resolves a ref from
the target root. Every claim carries a ref by construction, since an
unrefable omission gives the adversary nowhere to look. It imports `dependency_sinks`,
`route_census`, and `route_control` at module level — none of the three imports back from
`phase_gate`, so no import cycle exists.

`check_architecture_controls`/`check_threat_entrypoints` match a control or entrypoint via
`_mentions`, a word-bounded (alphanumeric-neighbor guard) check, not substring. A token that is part
of a longer word (`auth` inside `authorization`) is still flagged as a gap for those two checks.
`check_census_routes` also calls `_mentions`, but against the recon profile's whole JSON blob rather
than one field. A profile field carrying the route path as a prefix, such as a filename in free
text, suppresses the gap. This is the check that closes the circularity. A route the code registers
but recon never named now surfaces as a gap.

`route_census.py` (new) derives a route inventory straight from source, via ripgrep over
`references/route-frameworks.json`'s framework patterns, so `route_control.py`'s table can read
something recon did not produce. `census()` returns `[]` when ripgrep exits nonzero or matches
nothing. A missing ripgrep binary raises `FileNotFoundError`, because preflight owns binary
availability — `preflight.py`'s `TOOLS` list now includes `rg` as a required entry.
`write_census(ws, sites)` persists the result to `kb/route-census.json`, and
`load_census(ws)` reads it back as `RouteSite` records, returning `[]` when the file is absent or
holds invalid JSON. The module map entry in [`../README.md`](../README.md) has the full contract.
CLI-callable.

`class_ext.py` (new) provides `class_extension_status(classes, classes_dir)` to check which
investigate/patch extension files exist; absent classes are logged as gaps so coverage is never
silently lost. Uses an alias map (e.g., sqli/cmdi/xss → injection.md) to count coarse files.

`sast.py` now excludes `.sec-overlay`, `.git`, `.venv`, and `node_modules` directories from
semgrep scans via `_SKIP_DIRS` tuple and `--exclude` flags, preventing audit findings on the
harness's own sidecar output.

`prefilter.py`'s candidate-id assignment moved into `_assign_candidate_ids`, which now numbers
ids per attack class (`C-SQLI-0001`, `C-XSS-0001`, ...) instead of one global `C-0001..`
sequence, so ids carry the class and never collide across rulesets (ISSUE-013).

`mermaid_index.py` (new) — `index_mermaid(text)` line-oriented parser for Mermaid flowchart,
sequence, and C4 diagrams, returning a `DiagramIndex` (nodes, edges, subgraphs, participants,
messages, store_ids, has_style). Not a grammar: extracts only what the diagram gate checks;
raises `ValueError` on an unrecognized diagram header. Feeds the upcoming diagram gate (Task 2).

New module `diagram_gate.py` — deterministic hard gate over generated Mermaid diagrams
(`check_diagram`, `run_diagram_gate`, `CAPS`, `SEQ_CAPS`): per-type node/participant/message
caps, ≤4-word edge labels, DFD trust-boundary-subgraph requirement, derivation provenance
(`%% derived-from:` header + sha256 freshness, no element/participant absent from the source),
legend-required styling, and orphan-detail nodes — scoped to `container`/`component`/`dfd` only,
never `context` or `sequence` (context actors are by design often degree-1). CLI-callable —
see the module map entry.

`mermaid_index.py` also gained a fix for an edge whose source node carries its own inline
bracket label on the same line (`web[Web] --> api[API]`) — previously produced zero edges for
that shape — and its C4 parser now adds `Person(...)`/`*_Ext(...)` ids to `store_ids` too,
orphan-exempt alongside `ContainerDb`/`SystemDb`/`*Queue`.

Crash-path hardening round: `_INLINE_LABEL_SKIP` in `mermaid_index.py` only spanned single-bracket
shapes and missed multi-char forms like `q{{Queue}}` — widened to one bracket-class alternation
covering `[[`, `((`, `{{`, `[(`, `([`, and bare `[`/`(`/`{`. In `diagram_gate.py`, `_provenance`
crashed with `FileNotFoundError` when the derived-from source file didn't exist (a missing
`container-diagram.mmd`, or an attack sequence whose header names an unknown parent, hitting
`_attack_parent`'s `MISSING-PARENT` placeholder); it now reports `"derived-from source ... not
found"` and returns instead of calling `read_bytes()`. `check_diagram`'s parse of the source
diagram (for element/participant-diff checks) is now wrapped in `try/except ValueError`, reporting
`"source ... unparseable: ..."` instead of an uncaught traceback.

`mermaid_index.py`'s flowchart edge scan now tries `_FLOW_EDGE_MID` (`a -- some label --> b`)
before the piped-label `_FLOW_EDGE` regex, fixing a defect where the label text itself was
misread as a phantom source node and `a`/`b` were silently dropped from `nodes`.

New module `ste_lint.py` — a deterministic linter for the checkable structural subset of
ASD-STE100: sentence >25 words, semicolon in prose, and paragraph >6 sentences are errors; a
4+ word capitalized run mid-sentence (noun-cluster suspicion) and a sentence repeating " then "
are warnings. Fenced code blocks, mermaid blocks, headings, table separator rows, inline code
spans, and URLs are exempt; table free-text cells are linted. `lint_prose(text) -> (errors,
warnings)` is the entry point; the CLI (`python -m sec_overlay.ste_lint <files...>
[--require-frontmatter]`) exits 1 on any error and additionally requires the literal
`ASD-STE100` string somewhere in the file when `--require-frontmatter` is passed.

`ste_lint.py` fix round: an unterminated code fence used to silently drop every line after it
from linting with no signal at all — `_prose_blocks` now returns `(blocks, errors)` and reports
an `"unbalanced code fence"` error when the file ends still inside a fence, so a real violation
hidden behind a stray opening fence no longer passes clean. Sentence splitting (`_split_sentences`)
now only breaks at `[.!?]` followed by a capitalized word, and folds the split back onto its
clause when the preceding token is a known abbreviation (`e.g.`, `i.e.`, `etc.`, `vs.`, `cf.`,
`approx.`, `viz.`, `al.`) — an abbreviation no longer fractures a paragraph into a false
"over 6 sentences" or hides a genuinely over-length sentence by chopping it in two.

Diagram-gate parsing-gap round: `mermaid_index.py`'s flowchart edge scan matched only the first
`-->` on a line, so a chained edge (`a --> b --> c`) recorded `a→b` and silently dropped `b→c` —
the scan now restarts each search at the matched destination's position, walking every hop on the
line. The sequence-diagram regexes (`_PARTICIPANT`, `_SEQ_MSG`) rejected hyphenated ids
(`auth-api`) — `_PARTICIPANT`'s id class now allows `-`, and `_SEQ_MSG`'s source-id match is
non-greedy so it backtracks to the shortest id that still lets the arrow class match, instead of
swallowing the arrow's leading dash. `diagram_gate.py` gained `_node_label_errors`: a node's
bracket label over 4 words is now an error (bare-id nodes with no bracket label are exempt), and
`run_diagram_gate` takes a keyword-only `require_threat_model` flag — when set, a missing
`dfd.mmd` becomes a gate error instead of a silently-skipped optional diagram (CLI:
`--require-threat-model`).

New module `run.py` — driver helpers for a sec-overlay audit run; first addition is `fence(target,
baseline, *, runner=subprocess.run)`, which raises `WorkingTreeFenceError` naming the delta lines
when `git status --porcelain` output differs from the captured baseline.

`run.py` gained `receipt(ws, phase, *, stdout="", artifacts=None, counts=None)`, which writes
`<ws.kb>/receipts/<phase>.json` (keys `phase`, `stdout`, `artifacts`, `counts`) and returns the
path — so no stage advances without a receipt on disk.

`run.py` gained `write_env(ws, target, scope, sha)`, which writes `<ws.root>/run.env` with
`TARGET`, `WORKSPACE`, `SHA`, `SCAN_SCOPE`, and `REPO_ROOT` resolved once — agent phases read the
tokens from this file instead of the orchestrator re-substituting them by hand on every spawn.

`run.py` gained `infer_role(profile: ScanProfile) -> str`, which maps a `ScanProfile`'s
`subsystems`/`frameworks`/`attack_surface` to one of `sec_overlay.correlate.manifest.ROLES`
(`rbac-source` → `service-enforcer` → `infra` default) for correlation-manifest synthesis.

`run.py` gained `synthesize_manifest(product, members) -> dict`, which wraps `members` under
`product` and raises `ValueError` when `sec_overlay.correlate.manifest.validate_manifest` rejects
the result — building the `product.json`-shaped dict `python -m sec_overlay.correlate` consumes.

`run.py` gained `drive(target, config, *, scope=".", workspace=None, runner=subprocess.run,
table=PHASE_TABLE) -> str`, the single-repo audit loop. It opens or resumes the sidecar
`Workspace` (via `_target_workspace`, which delegates to `RepoMemory.for_target`), pins the SHA,
calls `state.begin_pass` on a fresh workspace, snapshots the `git status --porcelain` baseline,
writes `run.env` once, then calls `driver.run_audit` with an `on_complete` callback. That callback
fences the tree (`fence`) and writes a receipt (`receipt`) before every `record_stage` — `driver.py`
now accepts this `on_complete: Callable[[str], None] | None` hook on both `run_deterministic_phase`
and `run_audit`, invoking it immediately before each stage is recorded so a receipt always exists
before its stage counts as done (O-67 ordering).

`run.py`'s baseline is now persisted at `<ws.kb>/fence-baseline` via the private
`_load_baseline(ws, target, runner)`, captured once at pass start and read back on every resume —
so a resumed `drive` fences against the pre-audit tree, not a fresh snapshot that would already
contain an agent phase's write; `drive` also now stays pinned to `state.active_sha` on resume
instead of re-reading HEAD. `run.py` gained `advance(target, phase, *, workspace=None,
runner=subprocess.run) -> Path`, the closing call for the six agent phases (`drive` never
auto-advances past them): it loads the persisted baseline, fences, writes a receipt, and calls
`campaign.record_stage`.

`workspace.py`'s `Workspace` gained an `artifacts` property (`self.root / "artifacts"`) for
review-mode run state — the coverage manifest and review ledger the new `review` CLI mode writes.
It is never routed through `reports_dir`: review-mode run state is not a report. `ensure()` now
also creates it.

Four new modules wire the `sec-overlay review` tracer path — one changed file, one hunk, one
finding through the full pipeline: `diffhunks.py` (`parse_hunks`/`added_line_numbers`/
`line_in_hunk`), `file_select.py` (`partition` — path-shaped, never imports `Finding`),
`positioning.py` (`resolve_position` — decline discipline, never a fuzzy match presented as
exact), and `review_coverage.py` (`CoverageManifest`, sealing `complete`/`partial`, raising
rather than sealing over a `pending`/`in_review` entry). `diffscope.py` (additive:
`validate_ref`/`resolve_ref_sha`/`changed_file_records`/`file_diff_text`) and `phase_gate.py`
(additive: `review_position_gate`) gained the ref/file and gate layers respectively — every
pre-existing symbol in both is unchanged. `cli.py` gained the `review` subparser and
`run_review`, matching the existing `scan`/`memory`/`audit` structure. Tracer scope only:
batching, exit codes 2/3, the full extension allowlist, and the diff-line size cap land in a
later plan. `models.py` and `evidence.py` — the frozen milestone contracts — are untouched; no
new runtime dependency. See the module map entries.

`diffscope.py` and `cli.py` reached full ref-validation behavior: the allowlist pattern now
also permits `~` (so `HEAD~1`-style ancestor refs validate), `changed_file_records` parses the
full `--name-status` vocabulary including renames and copies (both carry `old_path`), and two
new functions — `file_diff_line_count` and `binary_paths` — give `file_select.partition` its
size-cap and binary inputs. `cli.py`'s `review` branch now catches a `ValueError` from ref
resolution and exits `2` with one stderr line naming the ref, without laundering any other
`ValueError` in the run into the same exit code. `resolve_ref_sha` itself now raises that
`ValueError` when `git rev-parse --verify` exits non-zero (CR-02): a syntactically valid but
nonexistent ref used to resolve to `""` instead of raising, silently defeating the exit-2 path
this paragraph describes.

`file_select.py`'s `ALLOWED_EXTENSIONS` is now the full 86-extension allowlist ported from
open-code-review's `supported_file_types.json`, and a new `DEFAULT_EXCLUDE_GLOBS` tuple (40
fnmatch-compatible patterns, brace-expanded from the OCR source's 34) drives a new
`_is_generated(path)` check. `partition` now normalizes a git-quoted non-ASCII path
(`_normalize_path`) before matching, lowercases the extension, and orders its checks deleted →
generated → not-allowlisted; binary detection and the diff-line size cap land in a later task
of the same plan. `fnmatch` approximates `doublestar`'s `**` (no true zero-or-more-segment
matching) — the parametrised glob test in `tests/test_file_select.py` holds that gap honest.

`file_select.py`'s `EXCLUSION_REASONS` is now enforced, not just documented: `ExcludedFile`
raises `ValueError` in `__post_init__` for any reason outside the closed set. `partition` gained
`diff_line_counts`, `binary_paths`, and `max_diff_lines` (default `DEFAULT_MAX_DIFF_LINES` =
5000, D-11) keyword parameters, all defaulting to no-op values so a caller that omits them still
works. The full check order is now deleted → binary → generated → not-allowlisted → too-large; a
file at exactly the cap is reviewable. No `--max-diff-lines` CLI flag exists — a cap override is
deferred to Phase 4.

`cli.py`'s `run_review` now computes `diff_line_counts` (via `file_diff_line_count`, one call per
changed file) and `binary_paths` before calling `partition`, and passes both through (CR-03): the
tracer-path call left both kwargs at their no-op defaults, so an oversized or binary file stayed
`reviewable` instead of landing in `selection.excluded` with reason `too-large`/`binary`.
`run_review`'s docstring now states plainly that batching and exit codes 2/3 are implemented,
not future work (WR-02) — only finding-source integration remains pending.

`review_coverage.py`'s `CoverageManifest` reached full behavior (DIFF-03): a single
`_ALLOWED_TRANSITIONS` table gates every state change, `seal()` now raises `CoverageTransitionError`
(a `RuntimeError`, per the plan's Artifacts spec) on an empty manifest — sealing `complete` with
nothing reviewed is a T-02-05 violation, not a vacuous pass — and `cli.py`'s `run_review` gained an
early `if not selection.reviewable: return 0` before `seal()` so a diff with zero reviewable files
exits cleanly instead of hitting that new raise (Rule 1 fix, caused by this same change).

`diffhunks.py` reached full behavior (DIFF-04): `Hunk` is now a frozen dataclass with
`tuple`-typed `added`/`deleted`/`context` fields, built through an internal mutable `_MutableHunk`
builder during the parse loop and frozen on hunk close, so `parse_hunks` is provably pure. Line
splitting moved from `str.replace("\r\n", "\n").split("\n")` to `str.splitlines()`, fixing a real
bug where a diff ending in a newline produced a spurious trailing empty context line. New
`hunk_for_line(hunks, line) -> Hunk | None` and module constant `NO_NEWLINE_MARKER`.

`positioning.py` reached full behavior (POS-01, POS-02): `resolve_position` now runs a
four-rung ladder in order — hunk match in the claimed file (`exact`), whole-file match in the
claimed file (`relocated`/`whole-file-match`), match in exactly one other changed file
(`relocated`/`cross-file-match`), else decline (`needs-position-review`/`no-hunk-match`) — and
stops at the first rung producing exactly one match; two or more matches at any rung decline
(`ambiguous-multiple-matches` or `cross-file-ambiguous`) instead of picking one. An absent or
whitespace-only snippet declines (`no-snippet`) before any rung runs. `PositionResult` gained a
`snippet` field (default `None`, backward-compatible), carried on every result including
declines, so a report can show the claim without a second lookup. `phase_gate.py`'s
`review_position_gate` gained an optional `file_text_by_path` parameter (default `None`, which
disables the ladder's whole-file and cross-file rungs) to match `resolve_position`'s new
five-argument signature — a Rule 3 fix for the signature this same plan's earlier task changed.

`report.py` gained two additive functions (D-13, POS-02), wired into neither `to_markdown` nor
`write_report` — plan 02-05 does that wiring once the drop ledger exists.
`render_position_review_section(results: list[PositionResult]) -> str` renders one
`## Position review required` markdown table, one row per declined result (claimed path,
claimed line, snippet, reason), with pipe characters escaped and newlines collapsed in the
snippet cell so a decline can never corrupt the table into a hidden row; an empty list still
renders the heading plus an explicit none-required line.
`write_review_ledger(ws, *, position_reviews, dropped) -> Path` writes
`artifacts/review_ledger.json` (via the same `_atomic_write` shape as `review_coverage.py`)
with `position_reviews`/`dropped` keys always present, each `position_reviews` entry carrying
`state: "needs-position-review"`. A separate artifact rather than a `findings.json` state,
since `models.py`'s `FindingStatus` enum has no review-position member and adding one would
break the Go port's byte mirror. Both functions ship in plan 02-04, task 3.

Plan 02-05, task 1 replaced `phase_gate.py`'s `review_position_gate` with the shape POS-03
needs: a three-way split into `(kept, dropped, declines)` instead of the earlier two-way
`(kept, dropped)`. A finding declines (`needs-position-review`) when the ladder cannot resolve
it at all; every other finding is checked against `diffhunks.hunk_for_line` at its RESOLVED
position (not its claimed one, since a relocated match can land outside every hunk's range) —
inside a hunk keeps the finding at that resolved position, outside drops it with reason
`outside-diff`. `DroppedFinding` now carries `path`, `line`, `rule_id`, and `reason` instead of
a bare `finding_id`, and `DROP_REASONS` is a frozen set of the reason(s) the gate can emit —
currently just `outside-diff`; `UNRESOLVED_POSITION_REASON` was removed (WR-01) since the gate
never assigned it — a decline goes to `declines`, never `dropped`, so there was no second reason
to reserve. The gate never mutates an input finding: a relocated keep copies the finding to its resolved
position with `copy.copy`, so calling the gate twice on the same input is idempotent. `declines`
entries are the `positioning.PositionResult` `resolve_position` returned (not the raw `Finding`) —
that is the shape `report.write_report(..., position_reviews=...)` already requires.

Plan 02-05, task 2 wires those drops into the human and machine reports. `report.py` gained
`DROPPED_FINDINGS_HEADING` and `render_dropped_findings_section(dropped)`, matching the heading
level, table style, and none-dropped fallback `render_position_review_section` already used for
declines. `to_markdown` now takes `dropped` and `position_reviews` arguments and renders both
sections unconditionally, right after the findings body — an empty run states none-dropped
rather than omitting the section, for the same reason a declined finding is never silently
dropped. `write_report` takes the same two arguments and threads them into both `to_markdown`
and `write_review_ledger` from a single call, so the markdown table and the JSON ledger can
never disagree about what was dropped in one run.

Plan 02-05, task 3 wires the coverage manifest's seal to `run_review`'s exit code (D-15). The
per-file loop now wraps `parse_hunks(file_diff_text(...))` in a `try`/`except`: on success the
file transitions `pending` -> `in_review` -> `done` as before; on any exception the file
transitions to `failed` with the exception text as its `note`, and the loop moves to the next
file rather than aborting the run. A `complete` seal (including a diff with zero reviewable
files) returns 0; a `partial` seal — one or more `failed` files — prints one "unfinished file"
line per non-`done` entry, read through `manifest.entries()`, naming its path, state, and note,
then returns 3. The pre-existing exit-2 ref-validation path is unaffected — it runs before the
manifest exists at all. No `--max-diff-lines` override flag and no `logging` import: both stay
out of scope for this milestone.

Plan 03-06, task 3 wires the recorded review-agent returns into `run_review` as the review-mode
finding source, closing the last gap noted above (`file_text_by_path` and a real position-gate
snippet). `diffscope.py` gained `file_text_at_ref(path, ref, *, runner) -> str`, matching the
module's existing injectable-runner convention (`git show <ref>:<path>`, empty string if the path
did not exist at that ref) — every pre-existing symbol in the module is unchanged. `run_review`
now builds `file_text_by_path` alongside `hunks_by_path`/`diff_text_by_path` in its per-file loop,
then, before calling `review_position_gate`, sets each live finding's `evidence` field itself from
the real file text at the finding's claimed line — never from the agent's own claim (the
`code_comment` tool has no snippet field at all; D-13's tool-receipt discipline never trusts an
LLM's claim of code content). This makes the position gate's whole-file "relocated" rung reachable
for the first time in a live run, so a finding claimed outside every diff hunk is now correctly
dropped with reason `outside-diff` instead of declining earlier as `no-snippet`. The gate chain
order is unchanged: position gate → `review_findings.apply_profile` → `reflection.apply_verdict`
→ the receipt gate.

`cli.py`'s `run_review` closed the last gap in the drop/decline wiring (T-02-15, T-02-18):
task 2/3 above wired the gate's output into `to_markdown`/`write_review_ledger`, but
`run_review` itself still discarded `review_position_gate`'s returned `(kept, dropped,
declines)` tuple and never called `report.write_report` — so no review-mode run actually
produced `report.md`'s drop/decline sections or `artifacts/review_ledger.json`, in production
or in the zero-drop/zero-decline case. `run_review` now captures `dropped`/`declines` and calls
`write_report(ws, dropped=dropped, position_reviews=declines)` right after the gate call —
before the reviewable/seal exit-code branches, so both a `0` (complete seal, including zero
reviewable files) and a `3` (partial seal) run write both outputs from the same gate call. The
exit-2 ref-validation path returns before the gate runs at all and is unaffected.

Two new modules wire rule-doc resolution and reflection into the review tracer (Phase 3 plan
01). `rule_glob.py` (`expand_braces`, `glob_match`, `resolve_rule_doc`, `builtin_rule_docs_dir`)
ports OCR's brace-expansion + `**`-aware segment matcher to stdlib-only Python (case-insensitive,
first-match-wins over `BUILTIN_PATH_RULE_MAP`, falling back to `rules/rule_docs/default.md`); the
docs dir resolves from `Path(__file__)`, never cwd. `reflection.py` (`apply_verdict`,
`build_payload`) is a retract-only LLM-verdict filter mirroring `evidence.py`'s "code decides, not
the LLM's claim" discipline — a verdict can only remove a finding the code submitted, never add or
rank one, and `PROTECTED_SUBJECT_CLASSES` is a hardcoded veto no verdict can override. `report.py`
gained `reflection_retractions`/`reflection_skips` keyword params on `write_review_ledger`/
`write_report`, added to the same ledger dict (`reflection_retractions`, `reflection_skipped`) —
no second artifact file. `cli.py`'s `run_review` gained `--profile` (`security`/`general`,
reserved for a later plan), resolves each reviewable file's rule doc, and runs its kept findings
through `apply_verdict` inside a `try`/`except` that records a `ReflectionSkip` and fails open on
error rather than aborting the run.

Phase 3 plan 05 (Task 1) adds the prompt and verdict-validation half of that filter.
`render_reflection_prompt` renders the new `agents/review-filter.md` prompt wholesale via
`sec_overlay.prompts.render_prompt`, substituting only `{{PATH}}`/`{{DIFF}}`/`{{COMMENTS}}`.
`validate_verdict` parses the LLM's raw JSON tool-call response and raises `ReflectionResponseError`
on invalid JSON, an unnamed tool, or a `report_incorrect_comments` id outside what the file's
payload actually submitted — reading only the named tool, `comment_ids`, and `analysis`, so an
extra field (severity, message, a would-be new finding) is silently ignored. `apply_verdict` now
records a refused protected-class retraction (`REFUSED_REASON`) in the same `retractions` list as
an applied one (`RETRACTED_REASON`) rather than dropping it — the finding still survives in `kept`,
but the attempt is never silent (D-14).

Phase 3 plan 05 (Task 2) closes the never-silent ledger's markdown-rendering half (D-15).
`report.py` gains `render_reflection_skipped_section`/`REFLECTION_SKIPPED_HEADING`, mirroring
`render_reflection_retractions_section`'s pattern — a table of `path`/`reason`/`error` per
`ReflectionSkip`, or "No file was skipped." when empty, rendered unconditionally so a run with
zero skips still shows the section rather than omitting it. `to_markdown` gains a
`reflection_skips` keyword param and now calls both retraction and skip renderers back to back;
`write_report` passes `reflection_skips` through to `to_markdown` (it already reached
`write_review_ledger`). SKILL.md's "Diff-scoped review" section documents the dispatch: a
`review-filter` subagent renders `render_reflection_prompt`, returns a verdict `validate_verdict`
parses, and `apply_verdict` retracts.

REQ-P6 wires that filter live. `reflection.py` gains `reflection_label(path)` — a `review-filter-`
prefixed label distinct from `review_agent.agent_label` so a file's review return and its reflection
verdict never collide on disk — and `recorded_verdict_source(ws, *, base, head)`, a closure reading
each file's verdict envelope (`{"base", "head", "verdict"}`) recorded under that label. It mirrors
`review_agent.recorded_return_source`'s error contract: a missing verdict, invalid JSON, a base/head
mismatch, or a non-dict `verdict` all raise `ValueError`, so a stale verdict can never retract this
run's finding. `cli.py`'s `run_review` gained `reflection_source` (defaults to
`recorded_verdict_source`) and a `--prepare-reflection` mode that, after the profile runs, renders
one `review-filter` prompt per file with kept findings under `runs/reflection_prompts/<label>.md`
and writes `runs/reflection_plan.json`. The consume run applies each file's recorded verdict; any
`ValueError` lands in the existing per-file `ReflectionSkip` fail-open path (D-15) — never a silent
keep-all.

Phase 3 plan 05 (Task 3) attaches the D-12 receipt-gate disposition ladder to
`findings_gate.py`, beside the existing `confirms_alone` check it leaves untouched.
`STATIC_CHECKABLE_CLASSES` (`null-dereference`, `error-swallowing`, `resource-leak`,
`injection`) and `RUNTIME_DEPENDENT_CLASSES` (`thread-safety`) partition
`review_findings.GENERAL_DEFECT_CLASSES` exactly — a module-level assert enforces the union
and the empty intersection, so a sixth class added there without a matching entry here fails
at import time rather than silently landing in neither set. `disposition_without_receipt`
maps a general-defect class with no Tier-1 receipt to `unconfirmed` or
`needs-deployment-testing` and raises `ValueError` on anything else — it never touches
`FindingStatus`; `unconfirmed` stays a plain `review_findings` string, not a member of the
frozen enum `models.py` byte-mirrors for the Go port.

Phase 3 plan 02 (Task 1) expands `rule_glob.py`'s built-in-only resolution into RULE-02's four-layer
resolver. `ProjectRuleEntry`/`ProjectRule` mirror OCR's `rule.json` shape byte-for-byte (D-06):
an ordered `entries` list (`path` glob, `rule` text, `merge_system_rule` bool) plus `include`/
`exclude` lists Task 2's whole-layer filter selection consumes — never per-path resolution.
`load_project_rule(path, repo_root)` reads a layer defensively (`None` when absent, following
`exclusions.load_exclusions`'s idiom) and resolves each entry's `rule` file at load time through
`read_rule_file_safe` (Task 3's safety gate, below). `match_project_rule_entry(layer,
path)` is the per-path fallthrough building block — first entry in JSON array order whose pattern
matches wins. `resolve_rule_doc` now takes an optional `RuleResolution` and walks
`[custom, project, global]` before falling back to the built-in map, deciding independently per
path; an entry with `merge_system_rule` routes through `merge_with_system_rule(builtin_text,
user_text)`, which reproduces OCR's `## System-Specific Rules (Mandatory)` /
`## User-Specific Rules (Mandatory)` header format across all three empty-input cases. Per-path
fallthrough and Task 2's whole-layer filter selection are deliberately separate functions with
separate loops — the phase's single highest-risk mis-implementation is collapsing them into one.

Task 2 adds the whole-layer filter and the two CLI flags it powers. `build_file_filter(layers)`
walks `[custom, project, global]` and returns the first layer whose `include` or `exclude` is
non-empty — lower-cased at build time (D-04) — skipping a layer where both are empty rather than
selecting it as an empty filter; `None` when no layer qualifies. It shares no loop or helper with
`match_project_rule_entry`: one answers per-path, the other picks one whole layer, and the two
never call each other. `build_resolution(rule_path, excludes, repo_root)` assembles all three
layers — mirroring OCR's `NewResolver`, the custom (`--rule`) and global layers resolve a relative
`rule` field against their OWN file's directory (`Path(rule_path).parent`, `_global_rule_path()
.parent`), while only the project layer resolves against `repo_root` — then calls
`build_file_filter` and appends the lower-cased CLI `--exclude` values to whichever filter comes
back (or builds an excludes-only `FileFilter` when no layer had one). `cli.py`'s `review`
subparser gained `--rule` (single path) and `--exclude` (repeatable); `run_review` calls
`build_resolution` once, passes the `RuleResolution` into `resolve_rule_doc` for each reviewable
file, and narrows `selection.reviewable` by the resulting `FileFilter` before the manifest loop —
`dataclasses.replace` rebuilds the frozen `Selection` rather than mutating it — so an excluded
file never enters coverage accounting.

Task 3 adds RULE-03's hard-reject rule-file safety gate. `read_rule_file_safe(path, repo_root)`
runs a fixed check order — `Path.resolve(strict=True)` to collapse symlinks, extension check
against `ALLOWED_RULE_EXTENSIONS` (`.md`/`.txt`/`.markdown`) on the RESOLVED path's suffix so a
`.md` symlink pointing at a `.yaml` target is caught, `Path.is_relative_to` containment against
the resolved `repo_root`, then a capped `open("rb")` read of at most `MAX_RULE_FILE_BYTES + 1`
(524288 + 1) bytes rejecting anything over the cap before any UTF-8 decode — and raises
`RuleSafetyError` naming the path and reason on any violation, never falling through to another
layer. `_entry_rule_path(rule, repo_root)` joins a layer's relative `rule` field the same way
`build_resolution` already did in Task 2; `read_rule_file_safe` itself does no relative-path
resolution, only symlink resolution. Three deliberate divergences from OCR's `system_rules.go`,
documented in the function's docstring: the boundary check runs against the RESOLVED path
(stronger than OCR's pre-resolution check, closing a symlink-escape gap OCR has), a violation is
always a hard raise rather than OCR's warn-and-fallthrough, and the size cap is enforced on the
read itself (TOCTOU-safe) rather than via a separate `stat` call, measured in bytes not
characters. `cli.py`'s `run_review` catches `RuleSafetyError` around both `build_resolution` and
the per-file `resolve_rule_doc` call, prints the message to stderr, and returns exit code 2 — the
gate's `repo_root` is exactly whatever base `load_project_rule` was already passed for that layer
(true `repo_root` for the project layer, the layer's own config file's parent directory for
custom/global), not a separately threaded true project root, since a global config under
`~/.sec-overlay/` is essentially never nested under an arbitrary project's `repo_root`.

REQ-S4 adds `resolve_with_layer(path, resolution)`, a thin sibling of `resolve_rule_doc` that
returns a `(layer, text)` pair — the winning layer label (`custom`/`project`/`global`, or
`custom+builtin` etc. when the entry merges the system rule, else `builtin`) alongside the resolved
doc text. `cli.py`'s `rules check <path> --root` prints that pair for one path, so a maintainer can
see which layer a rule came from without running a review. The top-level parser is a
`_SuggestingParser`: on an argparse "invalid choice" error it appends a `difflib.get_close_matches`
"Did you mean '<x>'?" line before the standard exit-2, so a misspelled subcommand names the nearest
valid one.

Phase 3 plan 03 (Task 1) extends `BUILTIN_PATH_RULE_MAP` from its single `python.md` entry to
nine, mirroring OCR's `system_rules.json` pattern strings and doc filenames exactly (D-02): one
entry per built-in language plus a trailing `"**/*": "default.md"` catch-all, so `default.md` is
a reachable, testable map value like every other doc instead of a fallback living outside the
map (`_resolve_builtin_or_default`'s post-loop fallback keeps working unchanged, since the
catch-all matches everything the fallback did). `REQUIRED_RULE_SECTIONS` names the five defect
families every built-in doc must cover, in the fixed order `python.md` established; a sibling
`RULE_SECTION_SYNONYMS` dict carries the accepted per-language heading wording for each family
(a Rust doc says panic/unwrap where a Java doc says null pointer) as data, not scattered test
logic — `tests/test_rule_docs.py` drives every assertion from these two constants and the map
itself, never a hardcoded filename list.

The OCR-parity plan (Task 11, REQ-P2) grows `BUILTIN_PATH_RULE_MAP` from nine docs to 36,
matching OCR's full 35-pattern `system_rules.json` set (plus the trailing `**/*` catch-all) in
exact order: manifests (`pom.xml`, `package.json`, `Cargo.toml`, ...), config (`.properties`,
`.json`, `.yaml`, `.github/**`), templates (FreeMarker, Astro, MyBatis mapper/DAO XML), and the
remaining languages (C/C++, Protobuf, GraphQL, Prisma, Terraform, Bicep, Nix, Haskell, Julia,
Nim, ArkTS, gettext `.po`/`.pot`). Each new doc under `rules/rule_docs/` was adapted from OCR's
Apache-2.0 sources and carries an `Adapted from open-code-review (Apache-2.0)` attribution line;
`tests/test_rule_glob.py` asserts the 27 ported docs are mapped, attributed, and resolve for a
representative path each (first-match order matters: `.github/workflows/**` before `.github/**`,
`pom.xml`/`package.json`/... before the generic `**/*.{json,json5}`).

Phase 3 plan 06 (Task 1) adds the review-file agent seam, mirroring `reflection.py`'s
render/parse-only discipline (no subprocess, no network client, no model SDK — `SKILL.md` owns
dispatch, D-13). `review_agent.py`'s `render_review_prompt` renders `agents/review-file.md`
(Task 2's file, not this one's) for a single file's review pass; `parse_review_response` is the
REV-03 elevation-of-privilege backstop — every finding it builds carries `REVIEW_AGENT_CLAIM`
(`evidence.as_llm_claim("review-agent")`) as its only evidence source and `FindingStatus.RAW`,
both fixed in code rather than read from the model's response, so `evidence.confirms_alone` is
false for every agent-authored finding regardless of what the response claims. A `code_comment`
naming a path other than the one under review is discarded and counted, never converted —
the Strict Focus Rule enforced mechanically, not only asked for in the prompt.

Phase 3 plan 07 (Task 1) closes a gap in that same gate chain (REV-02): `run_review`'s
reflection loop read its per-file selection from the position gate's `_kept` list and then
discarded `apply_verdict`'s returned kept half entirely, so a retraction never actually
removed anything from the reported `review_findings` — the retracted finding still shipped
in the ledger next to its own `RETRACTED_REASON` entry. The loop now selects each reviewable
file's findings from `apply_profile`'s kept output (`review_findings`, not `_kept`), passes
the inner `Finding` objects (`.finding`) to `apply_verdict`, and accumulates every retracted
id (submitted ids minus the ids `apply_verdict` returned as kept) into one `retracted_ids` set
across the loop. After the loop, `review_findings` is rebound to the entries whose
`.finding.id` is not in `retracted_ids` — filtering the original list, never reconstructing it
by union, so a finding on a path the loop never visits (absent from `selection.reviewable`)
stays in place instead of being silently dropped (D-14). A per-file `apply_verdict` failure
still records a `ReflectionSkip` and contributes no retracted ids, so that file's findings
survive untouched (fail-open, D-15) without affecting any other file's retractions.

Phase 3 plan 07 (Task 2) closes the other REV-03 gap: `apply_profile` hardcoded
`UNCONFIRMED_DISPOSITION` for every kept finding, so `findings_gate.disposition_without_receipt`
(the D-12 ladder above) was dead code and a kept thread-safety finding never shipped
`needs-deployment-testing`. `apply_profile` now calls `disposition_without_receipt(defect_class)`
for every kept finding whose `classify` result is not `None`, and keeps the
`UNCONFIRMED_DISPOSITION` fallback only for a kept finding `classify` returns `None` for (a
gate-unmarked finding outside the general-defect allowlist). The import is function-local inside
`apply_profile` — `findings_gate` already imports `GENERAL_DEFECT_CLASSES` and both disposition
constants from this module at module level, so a module-level reverse import would cycle.

Phase 4.1 plan 01 fixes DIFF-04: `cli.py`'s `run_review` used to construct `Workspace(args.root)`
directly, writing every review artifact at the bare `--root` instead of the per-repo sidecar
`scan` and `audit` already use. `run_review` now resolves its workspace through
`RepoMemory.for_target(root, runner=r).workspace`, the same call `_target_workspace` makes for
`audit`, threading the same `r = runner or subprocess.run` default the rest of the function
already used. `build_resolution` and `render_review_prompt` still take the bare `root` — they
never touched the workspace, only the rule/prompt resolution paths — so they are unchanged.
Every test in `test_review_live.py`, `test_review_tracer.py`, and `test_rule_glob.py` that reads
back a review artifact now resolves it through the same sidecar rather than joining `tmp_path`
directly, so a passing test proves the production path, not the bug.

Phase 4 plan 01 (Task 1, tracer) adds two new modules and extends `sarif.py`, wired end to end
through `cli.run_review` — see the module map entries in [`../README.md`](../README.md) for the
full contract. `bundle.py` is SCALE-01's grouping unit (`ReviewUnit`, `group_bundles`); this
plan's grouping is the degenerate one-unit-per-file case only, called on `selection.reviewable`
downstream of `file_select.partition`. `review_comments.py` is OUT-01's diff-anchored comment
writer (`DiffComment`, `comment_from_finding`, `write_review_comments`), called once after
`write_report` with `CoverageManifest.to_dict()`'s own dict, writing
`artifacts/review_comments.json`. `sarif.py` gained `_sarif_fingerprint` + the `FINGERPRINT_KEY`
constant: every SARIF result now carries a `partialFingerprints` entry keyed on
`file|cls|evidence.strip()`, deliberately excluding `message` so a wording tweak does not churn
result identity, and deliberately not reusing `fingerprint.fingerprint()` (a different identity
contract).

Phase 4 plan 01 (Task 2) gives `group_bundles` its real grouping semantics, replacing Task 1's
degenerate one-unit-per-file placeholder: an impl/test pair (`foo.py`/`test_foo.py`,
`foo.go`/`foo_test.go`, `foo.ts`/`foo.test.ts` or `foo.spec.ts`) and locale/config siblings in the
same directory (`en.json`/`fr.json`, `config.dev.yaml`/`config.prod.yaml`) now share one
`ReviewUnit`; every file a rule does not claim still falls back to its own single-member unit, so
no path is ever dropped. The fallback key strips a `test`/`tests` directory segment before
comparing, so this repo's own `tests/test_foo.py` convention pairs with a root-level `foo.py`.
`parse_review_response` gained a keyword-only `bundle_paths: frozenset[str] | None = None`
parameter widening the Strict Focus Rule from "this exact path" to "any member of the reviewing
unit" — a kept comment is now attributed to *its own* claimed path (`Finding.file`,
`_stable_finding_id`), not the outer `path`, since a multi-file unit's comment may name any
member. `bundle_paths=None` (the default) keeps the single-file behavior byte-identical to before
this task. `recorded_return_source` gained a matching `bundle_paths_by_path: dict[str,
frozenset[str]] | None = None` parameter, looked up per file and passed through unchanged.
`cli.run_review` now builds that map from `group_bundles(selection.reviewable)`'s output and
passes it to the default `recorded_return_source` call — the per-file dispatch loop shape is
unchanged; only the membership each file's parse call sees is widened. Known heuristic scope
limit: the `test`/`tests` segment strip only matches a literal directory component, so a
non-conventional parallel source/test tree (e.g. `sec_overlay/bundle.py` vs
`tests/test_bundle.py`, this very codebase's own layout) does not pair under this rule — both
still ship as correct, safe single-member units via the fallback, so no path is ever mis-grouped
or dropped, only left unpaired.

Phase 4 plan 02 (task 1, SCALE-02) gave `cli.py`'s `review` subcommand three bounded flags:
`--concurrency` (`DEFAULT_CONCURRENCY = 8`, ceiling `MAX_WORKERS = 128`), `--timeout`
(`DEFAULT_TIMEOUT_SECONDS = 600`, ceiling `MAX_TIMEOUT_SECONDS = 3600`), and `--max-git-procs`
(`DEFAULT_MAX_GIT_PROCS = 16`, ceiling `MAX_WORKERS`). Two separate ceiling constants, not one
shared value, because a worker-count ceiling sized for `--concurrency`/`--max-git-procs` would
reject `--timeout`'s own, much larger, order of magnitude (seconds, not workers). A new
`_bounded_int(value, *, flag, ceiling)` helper rejects (never clamps) a value outside `[1,
ceiling]`, raising `ValueError` with a message naming the flag and its range; `run_review` calls
it on all three kwonly params as its first executable statement, before any git subprocess call,
and `main()` maps the `ValueError` to exit 2 exactly like an unknown profile or bad ref.
`--concurrency` has no enforcement point in `cli.py` itself — the Python core never dispatches a
review agent — so it is validated here and its bound is otherwise enforced by `SKILL.md`'s
dispatch loop.

Task 2 (SCALE-02) wrapped `run_review`'s two serial per-file git loops in a bounded
`ThreadPoolExecutor` via a new `_bounded_map(items, workers, fn)` helper: sizes the pool to
`min(workers, len(items))` (never `max(1, min(...))`, never wider than the item count), consumes
through `.map()` — never `as_completed()` — so results land in submission order regardless of
completion order, and builds no pool at all for an empty `items`. The diff-line-count
comprehension now calls `_bounded_map(records, max_git_procs, ...)` then zips the result back
onto `record.path`. The manifest loop's three git calls (`file_diff_text`, `parse_hunks`,
`file_text_at_ref`) moved into a new `_fetch_file_review_inputs(path, base, head, runner)`
worker function that catches its own exception and returns it instead of raising.

Task 3 (SCALE-02) replaced the manifest loop's `_bounded_map` dispatch with a per-`ReviewUnit`
dispatch so `--timeout` fails a whole bundle together, not just its slow member. `group_bundles
(selection.reviewable)` is now retained as `units` (previously computed and discarded inline) and
reused for both `bundle_paths_by_path` and the fetch dispatch. A new `_fetch_review_unit_files
(paths, base, head, runner)` calls `_fetch_file_review_inputs` once per member path, so a normal
per-file error still fails only that file. `run_review` opens one `ThreadPoolExecutor` sized to
`min(max_git_procs, len(units))`, submits one future per unit via `ex.submit(...)` (never `.map
()` here — each future needs its own timeout), and reads results back with `future.result
(timeout=timeout)` in submission order (zipped with `units`, never `as_completed()`). A
`TimeoutError` from `.result()` fails every member path of that unit with the module-level
`TIMEOUT_NOTE = "review unit exceeded --timeout"` constant instead of re-raising. The consuming
(main) thread still iterates `selection.reviewable` in original order, looking each path up in
the accumulated `fetch_by_path` dict, performing every `manifest.add`/`start`/`finish`/`fail`
transition exactly as before — parallel fetch, serial manifest mutation, and a `seal()` of
`"partial"` (rc 3) when any unit times out, unchanged for every other path.

Parity plan Task 10 (REQ-P1) adds sibling-diff context and two grouping rules. New module
`review_budget.py` holds `estimate_tokens(text) = len(text) // 4` — the single size primitive
`bundle.py` and `review_agent.py` share (and REQ-P4's budget projection builds on). `bundle.py`
grows two pairing rules — C/C++ header-impl (`.h/.c`, `.hpp/.cpp`, same directory) and
interface/impl stem pairs (`svc.ts`/`svc.impl.ts`) — and a token-cap split: `group_bundles` now
takes keyword-only `diffs` and `max_unit_tokens` (`MAX_UNIT_TOKENS = 50_000`), and when `diffs`
is supplied a grouped unit whose members' estimated diffs exceed the cap is split into
first-fit runs (an oversized single member becomes its own run, never dropped); `diffs=None`
leaves every existing caller byte-identical. `review_agent.render_review_prompt` gains keyword-only
`sibling_diffs` and `cap_tokens` (`DEFAULT_SIBLING_CAP_TOKENS = 2_000`): siblings render into the
new `{{SIBLING_DIFFS}}` token largest-first as fenced diffs, each over the cap replaced by an
`omitted (token cap)` marker, and each sibling path is annotated `(diff included below)` in
`{{CHANGE_FILES}}`. `cli.run_review`'s prepare path passes each file its unit-mates' diffs as
`sibling_diffs`. Deferred (recorded in `docs/parity/EXTRACTION.md`): single-file units do not yet
receive non-mate sibling diffs (gated on REQ-P4's budget, Task 12), and `import_adjacency
(graph_json)` grouping is not built (SPEC-optional; review mode must not require `kb/graph.json`).

Parity plan Task 12 (REQ-P4) adds a hard token budget over the same size primitive.
`review_budget.py` keeps `estimate_tokens` as the raw `len(text) // 4` primitive and adds
`estimate_review_cost(diff_text)`, which projects OCR's plan-loop cost for one file:
`diff_tokens + (PLAN_PROMPT + PLAN_OUT) + ROUNDS * (diff_tokens + PLAN_PROMPT) + ROUNDS * ROUND_OUT`
(constants `PLAN_PROMPT=2000`, `PLAN_OUT=400`, `ROUNDS=7`, `ROUND_OUT=700`; an empty diff costs
21300). `BudgetGate(budget)` is a latching admission gate: a budget of 0 admits every file
(unlimited); otherwise `admit(estimate)` commits the spend when `spent + estimate <= budget`, and
the first projected breach latches the gate closed so it refuses every later file. `cli.run_review`
gains a keyword-only `token_budget` parameter (CLI `--token-budget`, default 0). After fetch, a file
whose `estimate_review_cost` exceeds `FILE_BUDGET_FRACTION` (0.8) of the budget is excluded as
`too-large-tokens` before review; each remaining file passes through the gate, and a refused file is
sealed `partial` with the `BUDGET_SKIP_NOTE = "skipped(budget)"` note at exit 0 (a budget stop is a
planned outcome, not the fetch-failure `partial` at exit 3). `ReviewPlanEntry` carries a
`token_estimate` field surfaced in `--prepare`, and `CoverageManifest` records a `budget_exceeded`
flag round-tripped through `to_dict`/`load`. This closes the Task-10 deferral: single-file units are
still not given non-mate sibling diffs, now bounded by this budget rather than pending it.

Phase 4 plan 03 (Task 2, SCALE-03) adds a resume-identity gate. `review_coverage.py`'s
`MANIFEST_VERSION` is now 2: `CoverageManifest` gains keyword-only `model`/`profile` fields,
round-tripped through `to_dict`/`load` (a version-1 manifest, or a version-2 one written before
either was ever supplied, loads both as `None`). A new `check_resume_identity(prior, *, model,
profile)` raises `ResumeIdentityError` — naming both the prior and current value — when the
current run's `model` or `profile` differs from `prior`'s recorded value; a `None` prior value
permits any current one, so identity pinning starts from the run that first supplies it, never
enforced retroactively. `cli.py`'s `run_review` gained a keyword-only `model` parameter and now
loads any existing `coverage_manifest.json` and runs this check immediately after resolving the
workspace — before resolving `base`/`head` refs or constructing this run's own
`CoverageManifest` — so a resumed run that switched identity is rejected (exit 2) with the
on-disk workspace left byte-identical and no new file written.

Phase 4 plan 03 (Task 3, SCALE-03/T-04-12) pins a resumed run's reads to the SHAs the prior
run sealed. `cli.py`'s `run_review` now branches past the identity check: when a prior
manifest exists, `base_sha`/`head_sha` come from `prior_manifest.base_sha`/`head_sha` — never
from a fresh `resolve_ref_sha(base, ...)`/`resolve_ref_sha(head, ...)` on the CLI's own
`--base`/`--head` — so a branch that moved since the prior run cannot change what a resumed
run reads. Each persisted SHA is still round-tripped through `resolve_ref_sha`, reusing the
same `try`/`except ValueError` → exit 2 path a bad ref already took, so a rewritten or
collected SHA fails the run loudly instead of silently reading a different tree as an empty
diff. No change was needed in `diffscope.py`: every ref-consuming function there
(`changed_file_records`, `file_diff_line_count`, `binary_paths`, `file_diff_text`,
`file_text_at_ref`) already takes a pre-resolved SHA string, so the fix is entirely in *which*
SHA `cli.py` resolves and passes down, not in how any downstream call uses it. A pre-existing
`test_review_live.py` test that ran `run_review` twice against one target with two different
`profile` values (to compare finding output across profiles) now hits the Task 2 identity gate
on its second call — that test was split into two independent targets, since its intent was
never to model a resume.

Phase 4 plan 04 (Task 1, OUT-01 gap closure) fixes `run_review` calling
`write_review_comments` before `manifest.seal()` ran, which left the embedded
`coverage_manifest.seal` in `review_comments.json` permanently `null` regardless of the
on-disk manifest's real seal. The zero-reviewable early return still writes an unsealed
dict and returns 0 unchanged (there is nothing to seal). Every other path now assigns
`manifest.seal()` to a local before calling `write_review_comments` exactly once with the
post-seal dict, branching the exit code on that local instead of re-deriving it — so the
embedded seal always matches the on-disk manifest, for both a complete and a partial run.

Phase 4 plan 04 (Task 2, SCALE-03 gap closure) gives the `review` subcommand a `--model`
argparse flag (default `None`), forwarded as `model=args.model` at `main()`'s single
`run_review(...)` call site. `run_review`'s `model` keyword parameter, `CoverageManifest`'s
`model` field, and `check_resume_identity`'s model-mismatch check were already fully wired
from Task 2 of plan 04-03 — this closes the CLI surface only, nothing in `run_review`,
`CoverageManifest`, or `check_resume_identity` changed. Before this fix, `--model` had no
argparse surface, so a resumed run could never actually change model identity through the
CLI, leaving the resume-rejection gate dead code in production despite being fully tested
at the `run_review` Python-function level.

Phase 4 plan 04 (Task 3, SCALE-02 gap closure) bounds `run_review`'s wall-clock time on a
hung unit fetch to `--timeout`. Two prior gaps combined to leave the process open past the
declared timeout: the unit-fetch block's `with ThreadPoolExecutor(...) as ex:` blocked on
exit until every submitted worker finished, even one `future.result(timeout=timeout)`
already reported as timed out; and the production runner default was a bare
`subprocess.run`, so a hung git child inside that abandoned worker was never killed, only
orphaned. Both are now fixed together: the executor is built directly (not as a context
manager) and shut down via `ex.shutdown(wait=False)` in a `finally`, so `run_review` returns
without waiting for an abandoned worker; and the production runner default is
`partial(subprocess.run, timeout=timeout)`, so every git call the review path makes — every
unit fetch, `_bounded_map`'s line-count prefetch and binary-path detection, `resolve_ref_sha`,
`RepoMemory.for_target` — inherits a kill deadline equal to the declared `--timeout` through
the shared runner `r`, with no change needed to `_bounded_map` itself. `shutdown(wait=False)`
alone would still leave the process open at interpreter exit (`concurrent.futures.thread`
registers an atexit hook that joins every worker thread); killing the child closes that gap
too, since a killed `subprocess.run` call returns (raising `TimeoutExpired`, caught by
`_fetch_file_review_inputs`'s existing exception-return path) instead of blocking forever.
`_fetch_review_unit_files` also gained its own `timeout` parameter: it computes a monotonic
deadline at its own entry (not at submit time, so a queued unit's wait in the pool never
consumes its own budget) and, once past that deadline, records a unit's remaining members as
timed out instead of fetching them — an abandoned worker stops doing pointless work rather
than working through every member. An injected `runner` (tests) is untouched; only the
bare-`subprocess.run` default changed.

Phase 5 plan 01 (D-05-01-01, discovered running the tracer end to end against a live target
repo) fixes `run_review`'s production runner silently scoping every git call to the CLI
process's own working directory instead of `--root`. `diffscope.py`'s `resolve_ref_sha`,
`changed_file_records`, `file_diff_line_count`, and `binary_paths` all build raw `git`
commands with no `-C <path>` of their own — unlike `repo_memory.repo_slug`'s own git call,
which does pass `-C str(target)` — so they were entirely dependent on the caller's `runner`
having the right cwd. The production default, `partial(subprocess.run, timeout=timeout)`, had
none: invoking `review` from any directory other than `--root` (the realistic invocation
pattern) made every diff/rev-parse call run against the wrong repository, producing an empty
changed-file set and a zero-file sealed coverage manifest with no error — `check=False` on
these calls means a `git diff` against a nonexistent ref pair fails only on stderr, and
`changed_file_records` only reads `stdout`. The fix adds `cwd=root` to the same
`partial(...)` assignment used by SCALE-02's `timeout` fix, so every call through the shared
runner `r` is now scoped correctly with no other call-site change. No existing test caught
this: both `test_diffscope.py` and `test_review_live.py` fully mock the runner, so a new
`test_review_live.py` regression test uses a real temporary git repo and the real
(uninjected) `subprocess.run` path to prove the fix.

Phase 6 plan 01 fixes WR-01: `run_review` now rejects a `--root` that is missing, empty, or
not a directory before any workspace or git subprocess call, exiting 2 with `error: --root
must be an existing directory (got ...)` — the same shape as the `_bounded_int` exit-2
convention. Pre-fix, the three cases each crashed differently depending on where
`Workspace.ensure()`'s `mkdir(parents=True)` landed: a missing root was silently
auto-vivified and the run failed later with an unrelated "unresolvable ref" message; an
empty-string root reached a real `subprocess.run(cwd="")` and raised `FileNotFoundError`; a
file-as-root raised `NotADirectoryError` from `Workspace.ensure()`'s own `mkdir`. The guard is
a single `if not root or not Path(root).is_dir():` — `Path("").is_dir()` normalizes to `"."`
and reports `True` (the CWD exists), so the empty-string case needs the explicit `not root`
check rather than relying on `is_dir()` alone.

Phase 6 plan 01 adds D-03: a `--workspace` override on `review`, mirroring `audit`'s existing
flag. `run_review` gained a keyword-only `workspace: str | None = None` parameter; when truthy
it resolves via `workspace.load_paths(workspace=workspace)` in place of the unconditional
`RepoMemory.for_target(root, runner=r)` / `memory.ensure(target=root)` / `memory.workspace`
sequence, matching `audit`'s own `if args.workspace: ws = load_paths(...)` shape exactly
(`cli.py`'s `audit` branch). The SCALE-03 resume-identity check runs unchanged either way — it
reads the resolved `ws`'s coverage manifest, not how `ws` was resolved, so an explicit
`workspace=` override cannot bypass it. `test_rule_glob.py`'s `fake_run_review` spy gained
`workspace=None` (same class of gap `model=None` closed there previously) once `main()`'s
`review` dispatch started passing `workspace=args.workspace` unconditionally.

Phase 6 plan 03 fixes D-04: `render_finding`'s deps branch named the wrong package on the
`**Fix.**` line for a scoped npm-style identifier (`@scope/name@version`). It split `f.evidence`
on the first `@` (`pkg.split('@')[0]`) to strip the trailing `@version`, but a scoped identifier
already starts with `@`, so the first split lands on the scope delimiter and returns an empty
string — the Fix line rendered `` Bump `` `` with nothing between the backticks. The fix splits
on the last `@` instead (`pkg.rsplit('@', 1)[0] or pkg`), and falls back to the untouched string
when that split empties out (a versionless scoped package like `@scope/name` has only one `@`,
which is the scope delimiter, not a version separator).

`astgrep.py` gained `build_rule()` and `run_astgrep_rule()`, plus a `run --not <pattern>` flag
and a `rule --file <path>` subcommand — a relational-query wrapper for the absence idiom (a
construction present, its safe option absent). Go needs hand-written `kind`/`has` anchoring;
`build_rule()` does not generate it, because a bare selector-call pattern such as
`rego.New($ARGS)` matches nothing in Go. See the module map entry in [`../README.md`](../README.md)
for the full contract.

`run_astgrep_rule()`'s docstring now names only the non-JSON/empty-output case its `except`
catches. A missing `ast-grep`/`sg` binary still raises `FileNotFoundError` from `runner(...)` —
correct, since the harness treats a backend that never ran as a coverage hole, not a clean
empty result.

`coverage_ledger.py`'s `build_coverage_ledger` now keys a covered class's surfaces by sink
site, not by class. It emits one surface per distinct `(file, line)` finding site. Each
surface's `id` is shaped `f"{cls}@{file}:{line}"` and carries `cls` and `site` fields. A class
with no finding still emits one class-level surface, with `id` equal to the class name and no
`site`. This closes the gap where a second `ssrf` sink in a different file inherited "covered"
from an unrelated confirmed finding in the same class. The completeness invariant now runs per
site instead of per class, so it rejects `complete` more often.

Fix round 1 closed three gaps this site-keying opened. `rethreshold.py`'s `_ledger_disposition`
now matches a surface by its `cls` field first, then falls back to bare `id`. A covered class's
cross-repo compensating-control lookup now resolves against a site-keyed surface again. The
per-site `needs_follow_up` branch's `reason`/`next_step` now name the specific sink site (e.g.
"no terminal finding at sink site b.py:20 this pass" / "adjudicate b.py:20"). The old wording
reused the class-level prose, reading as if the whole class were uncovered even when a sibling
site was already `reported`. The class-level branch's wording — a class with zero findings —
stays unchanged.

`calibrate.py` (REQ-P9): a judge `severity-inflated`/`downgrade` verdict also
writes the downgraded severity band back to `f.severity` (`_severity_for_score`,
the inverse of `_SEVERITY_FLOOR`), with a `calibrate:severity-downgraded` history
event recording `from`/`to`. Severity is never raised by this path.

`diffscope.py`/`cli.py` (REQ-P5): `sec-overlay review` gained two scope flags beside
`--base`. `--commit <sha>` reviews one commit alone (`sha^..sha`); `--workspace-dirty`
reviews uncommitted changes (staged, unstaged, untracked) against `HEAD`. Exactly one
of `--base`/`--commit`/`--workspace-dirty` is required (else exit 2); a resumed run
reads its scope from the sealed manifest and ignores the flags. `dirty_file_records(*,
runner)` parses `git status --porcelain` (untracked lines become status `"?"`);
`file_diff_line_count`/`binary_paths`/`file_diff_text` accept `head=None` to diff the
base against the working tree. Dirty mode fetches serially and synthesizes an all-add
hunk for untracked files read from disk. `validate_ref`'s allowlist now permits `^`
(safe: every git call is list-form, never a shell) so `sha^` resolves.

`review_agent.py`/`cli.py` (REQ-P3): a two-phase per-file plan step ports OCR's plan pass.
`review_agent.py` adds `PLAN_LINE_THRESHOLD = 100` (a unit's diff at/over this many changed lines
gets a plan pass), `render_plan_prompt(path, rule_text, diff, *, repo_root, overlay_root)` (renders
`agents/review-plan.md`), `plan_agent_label(path)` (a `plan-file-` sha256-prefixed dispatch label
distinct from `agent_label`), and `plan_guidance_from_return(text)` (parses the plan agent's strict
JSON `{"issues":[{"severity","guidance"}]}`, orders issues most-severe-first, and raises `ValueError`
on invalid JSON, an unknown severity, a non-list `issues`, or a missing/empty `guidance`).
`render_review_prompt` gains a keyword-only `plan_guidance=""` that fills the review prompt's new
`{{PLAN_GUIDANCE}}` token. `cli.run_review` gains `plan: bool`; `--plan --prepare` writes plan
prompts for over-threshold units to `runs/plan_prompts/<plan_agent_label>.md` plus a
`runs/plan_manifest.json` and returns early (0), for `SKILL.md` to dispatch. A subsequent normal
`--prepare` reads each over-threshold unit's recorded plan return under `plan_agent_label`, injects
its `plan_guidance` into the review prompt, and fails open — a missing or invalid plan return yields
empty guidance and a `runs/plan_skips.json` entry (D-15: a plan failure never becomes a coverage
failure). Plan guidance is advisory: never a tool receipt, never a finding, and deliberately not
subject to the base/head staleness envelope that review returns carry.

`evidence.py` gained `VERIFICATION_VALUES` (REQ-02): the closed set for `Finding.verification`
— `verified-static`, `static-only`, `not-fixed`, `verify-error` (REQ-42 removed the fifth value,
`fact-checked`, with the deleted `factcheck` phase that alone wrote it). `models.py`'s
`Finding.from_dict` now rejects a `verification` or `runtime_disposition` outside its closed set
via a module-level `_CLOSED_ENUMS` table, unless the value is `null`. `../references/finding.schema.json`
mirrors both enums, checked verbatim by `../tests/test_contract_lint.py`.

`models.py`'s module docstring lists all four `verification` values, matching
`VERIFICATION_VALUES`.

`models.py` gained `RUNTIME_TEST_KEYS`, `OPEN_QUESTION_KEYS`, and `AFFECTED_SITE_KEYS` (REQ-18):
named key tuples for the `runtime_test`, `open_questions`, and `affected_sites` nested `Finding`
fields. `../references/prompt-constants.md`'s new `FINDING_SHAPES` block publishes the same keys,
and `../agents/investigate.md` imports it. `../tests/test_contract_lint.py` checks all three
surfaces agree.

`calibrate.py` gained `PRECONDITION_CAPS` (a `(threshold, cap)` tuple) and
`PRECONDITION_CAP_FLOOR` (REQ-32): `_precondition_cap` now loops over the table instead of four
hardcoded branches. `../references/prompt-constants.md`'s `SEVERITY_PRECONDITION` block states
the same cap-by-weight table. `driver.py` gained `DISPATCH_TOKENS`; `render_dispatch` builds its
`substitute:` line from that tuple, so `{{ATTACK_CLASS}}` now sits on the same line as the other
three tokens instead of its own trailing line. `../tests/test_contract_lint.py` checks both
constants agree with the document. `render_dispatch` now renders `{{ATTACK_CLASS}}` as a compact
JSON array of class keys (REQ-17). The value is no longer a comma-joined string. The dispatch
fan-out list and `investigate.md`'s single-key `{{ATTACK_CLASS}}` never collide on format.

`driver.py`'s `DISPATCH_TOKENS` gained three tokens (REQ-08): `OVERLAY_ROOT`, `HELPERS_DIR`, and
`FP_FEEDBACK`. `_overlay_root` returns the skill root, the directory holding `agents/` and
`helpers/`. `_write_fp_feedback` writes the prior-rejection block to `<workspace>/kb/fp-feedback.md`
and returns that path, because the block's `<untrusted>` envelope cannot ride the space-joined
`substitute:` line. `{{FP_FEEDBACK}}` now names a file path; `critic.md` and `investigate.md` read
it instead of inlining it. `../tests/test_prompt_tokens.py` scans every `PHASE_TABLE` prompt and
fails if a token has no entry in `DISPATCH_TOKENS`.

`prefilter.py` gained `_relativize_paths` (REQ-15), called from `run_prefilter` right before
`normalize`: an absolute `Finding.file` under the scanned `target` becomes repo-root-relative, an
already-relative path is left alone, and a path outside `target` stays verbatim instead of being
rewritten into something that does not resolve. `PATH_BASE` in `../references/prompt-constants.md`
requires every cited path to resolve from the repo root; the four backends (`sast.py`,
`secrets.py`, `sca.py`, `codeql.py`) each set `Finding.file` from raw tool output with no such
guarantee, so the fix normalizes once at the `run_prefilter` boundary instead of in all four.

`run_prefilter` now writes its `prefilter` receipt (REQ-16) before calling `record_stage`, using
`run.receipt` (a local import to avoid an import cycle) and `workspace.finding_counts`. Previously
`record_stage` ran with no receipt on disk, so a fence abort in the driver's `on_complete` — which
runs after `record_stage` for every other phase — could leave `state.json` saying `prefilter` is
done with nothing to show for it.

`clsmap.py` gained `canonical_classes()` (REQ-09), an `lru_cache`d function unioning every
publisher of an attack-class key: the universal and F2-companion tables in
`../references/attack-classes.md`, `CWE_CLS` and `_RULE_ID_CLS`, the two literal fall-backs
(`security-other`, `unknown`), `review_findings.GENERAL_DEFECT_CLASSES` (a local import, so
`clsmap` stays a leaf at import time), every `../agents/classes/*.md` stem except `README.md`,
and `context.py`'s own `manual-review` pseudo-class. 51 keys observed. `findings_gate.py` now
rejects any finding whose `cls` is not in that set; a missing `agents/classes/*.md` file stays a
`class_ext.py` gap (`needs_follow_up`), never a rejection — REQ-09 is validity, not coverage.

`calibrate.py` gained `_evidence_adjust` (REQ-20), called from `_derived_score` before the
precondition cap: a stronger tool-receipt `receipt_tier`, a `verified-static` `verification`, and
an assessed-reachable `reachability` each add to the score, reward-only, so a finding with none of
these set scores exactly as it did before.

`patch_status.check_patch_applied` (REQ-01) now runs the forward `git apply --check` before the
reverse one: a patch counts as `APPLIED` only when it does NOT apply forward AND does apply
reversed, so an additive patch that has not landed can never read as live.

`coverage.py` is gone (REQ-04). `prefilter.py` no longer computes a per-language dataflow
percentage or writes `kb/coverage.json`, and `report.py` no longer reads that file or renders
a "Coverage & limitations" section from it. `kb/coverage-ledger.json` is now the single coverage
source; `report.py` renders it through `coverage_ledger.render_markdown` unchanged.
`review_coverage.py`'s and `coverage_ledger.py`'s module docstrings no longer name the deleted
module; `test_frozen_contract.py` pins only `models.py` and `evidence.py`.

`route_summary` is a derived field, not a recon output (REQ-11). `profile.py` carries it as an
optional object on `ScanProfile`, and `validate_profile` rejects any non-object value, so the
legacy list of route strings no longer validates. `driver._act_recall_gate` computes it from the
route census after recon: `total` census sites, `covered` sites the profile mentions, and
`uncovered` ids it never mentions, then writes the profile back. The gate holds
`covered == total - len(uncovered)`. `route_control.check_recon_routes` still reads the legacy
list form for the non-census table, and treats any other shape as "nothing summarised" so every
table route stays a logged gap. `agents/recon.md` no longer claims the field.

`dependency_sinks.indicator_classes(root)` routes a class on a source indicator, not only on a
manifest (REQ-25). A Bazel or vendored build declares no `go.mod`, so `match_manifests` returns
nothing and the target's whole dependency-sink surface stays unrouted. The new matcher walks the
same skip-list `match_manifests` uses, reads every file whose suffix is in `_SOURCE_SUFFIXES`,
and returns the sorted classes of each catalog entry with at least one indicator token present.
One hit is enough: an entry's `indicators` list holds alternative call shapes, not a conjunction.
`partition.reconcile_plan` unions the two matchers under its existing `target_root` keyword, so a
class already planned is still never duplicated and a planned class is still never removed. The
matcher is deliberately substring-based and therefore over-inclusive — an unrelated file holding
`Template(` routes `ssti`. That is the recall-biased side of the trade: a spurious investigate
agent costs one wave, an unrouted class costs the whole class.

The investigate saturation loop is now enforced by the driver, not by prose (REQ-24).
`discovery_ledger` shipped as a complete library — `new_ledger`, `record_wave`, `is_terminal`,
`save_ledger`, `load_ledger` — with no production caller, so the loop-until-dry bound existed
only as an instruction in the operating manual. `driver._record_discovery_wave` folds one wave
per `findings-gate` run: it loads the ledger (or starts a fresh one), records every current
finding's fingerprint, and saves it back. It runs before the gate's own validation, so a wave
whose findings the gate then rejects still counts as a wave — otherwise a repeatedly-rejected
wave would loop forever. `driver._investigate_is_saturated` reads the ledger back in the dispatch
loop; once `terminal_reason` is set, the driver records the `investigate` stage and continues
instead of printing another dispatch block, so `next_actionable_phase` cannot return the phase
again. A missing or unreadable ledger reads as not-saturated, so a wave that has not run yet is
never skipped.

The granularity is one wave per `findings-gate` run, not one per investigate agent. The gate is
the first deterministic phase after `investigate`, so it is the only mechanical hook the loop
has; a per-agent wave would need the agents to report back through a channel that does not exist.
The cost is a coarser ledger: a fan-out of six classes that adds one new fingerprint counts as
one productive wave, the same as a fan-out of one. `new_ledger()`'s defaults (`k=2`,
`max_waves=5`) are used as-is — `profile.py:42` documents `scan_options.wave_k` and
`scan_options.max_waves` as the knobs, but nothing reads them, and wiring them is a separate
requirement.

## The triage next action names the section that holds the finding (REQ-03)

`report.py`'s triage table gave every needs-runtime row the same next action, `run redteam-plan
test`. `redteam.discriminate` files a needs-runtime finding into one of three plan sections —
`## Manual test directives`, `## Unrunnable preconditions (payload not traceable)`, and
`## Runtime-validation gaps` — so the one shared action sent most readers to a section their
finding is not in. `_ndt_next_actions(ndt)` calls `discriminate` on the needs-runtime list and
returns a finding-id to action map: `run redteam-plan directive` for the `needs_runtime` bucket,
`see redteam-plan preconditions` for `unrunnable`, and `see redteam-plan gaps` for `below_bar`.
`to_markdown` reads the map when it builds the triage rows and falls back to the gaps phrase for
an id the map omits.

The map has three entries, not four. `discriminate` also returns a `static_settled` bucket, but
`redteam.wants_runtime` returns True for every `NEEDS_DEPLOYMENT_TESTING` finding, so a list of
needs-runtime findings can never reach it. A fourth action would be a phrase no report can print.
Confirmed rows are untouched — `bump` and `apply fix (§ below)` already name real report sections.

## Run economics prints only what the run measured (REQ-05)

`to_markdown` printed `**Tokens by phase** (measured):` and `**Tokens by model** (measured):`
whenever the `economics` payload was truthy, so a run that collected neither still published two
headers over empty bodies. `_render_economics(economics)` originally built three measurement
groups plus an `**Estimated cost:**` line, keeping only groups that held rows and dropping the
`## Run economics` heading when none survived. Token and USD accounting is gone (REQ-46):
`_render_economics` now reads only `by_phase_seconds` and still returns `[]` when it is empty,
so the same drop-when-nothing-measured guarantee holds with one measurement group instead of
three.

The rest of REQ-05 stays open by decision. Five report sections render when empty on purpose
under D-13, D-14, and D-15, and `tests/test_report.py` pins that behaviour, so R-41, R-42, and
R-43's "No X" half is not built here. The word-boundary truncation clause needs no change:
`_short_title` already cuts on a space.

## 2026-08-31 — REQ-31: the artifact-consistency gate

`artifact_consistency.py` is a new terminal gate. `run_artifact_consistency(ws)` reconciles a
finished run's own artifacts against each other and returns one string per contradiction:

1. every `findings/<id>.md` link in the report resolves to a file on disk;
2. every triage next-action names a `redteam-plan.md` section that contains its finding;
3. the report's `Completeness:` claim matches `kb/coverage-ledger.json`;
4. `state.budget.self_score` exists and does not undercount the report's needs-runtime rows;
5. no `(measured):` header stands above an empty body;
6. a truncated triage title matches `report._short_title` of its source message.

The gate writes `kb/gates/artifact-consistency.json` with `passed` and `errors` on every run, so
the audit trail records a pass as well as a failure. It never judges or deletes a finding. A
missing artifact is not a contradiction: a workspace with no `report.md` degrades to a silent
pass, and each check returns `[]` when its own input file is absent. Setting
`scan_options.consistency_gate` to `false` in `kb/scan-profile.json` disables it — the first
production reader of any `scan_options` key.

It runs as the `artifact-consistency` phase, between `artifact-review` and `postflight`
(`phases.py`), and `driver._act_artifact_consistency` raises `PhaseHalt` when the list is not
empty. It is also callable on its own:

```bash
uv run python -m sec_overlay.artifact_consistency --workspace <WS>
```

The CLI prints each contradiction and exits 1 when the artifacts disagree.

### The Part D finding elements (REQ-33)

`report.py` renders eight optional elements on a finding page: `attacker`, `privilege`,
`exact_request`, and `exfil_channels` after the Compliance line, then `library_version`,
`refutation`, `negative_results`, and `baseline` after the Severity Rationale. One helper,
`_optional_sections(extra, keys)`, renders both groups. A list value becomes a bullet list.
`exact_request` renders inside an ```` ```http ```` fence. Every other value renders inline. An
absent, empty, or null key renders nothing, so a finding written before this change loses no
output.

The eight values ride the finding overflow, not a `Finding` field. `models.py` is byte-pinned by
the D-15 frozen-contract test, so a new dataclass field is not available. `workspace.read_findings`
already stashes every unknown key on the instance under `_OVERFLOW_ATTR`, and
`workspace.write_findings` merges the same mapping back on the way out (REQ-27). `render_finding`
reads that mapping. The trade-off: the eight fields are not typed, so a wrong type is caught by the
schema in `references/finding.schema.json` rather than by the dataclass.

### Multi-channel expected signals (REQ-34)

`render_util.signal_lines` now accepts three shapes, not two. A list of channel objects renders
one block per channel; a `{secure, insecure}` dict and a bare string render as before. A channel
object is `{"name", "needs_egress", "secure", "insecure"}`. `_channel_lines` renders the name and
the egress marker on a header bullet, then indents the secure and insecure lines under it.

The egress marker is the point of the change. A tester inside a fenced network cannot observe an
out-of-band channel, so a plan that offers only a collector callback is untestable for that
tester. `agents/redteam.md` now orders the array with every no-egress channel first, and requires
the in-band channel first whenever the sink reply is caller-observable.

Both existing callers — `redteam._signal` and `report.render_ndt` — already delegate to
`signal_lines`, so neither changed. Trade-off: a channel object is validated by
`references/finding.schema.json` only. A malformed entry that is not a dict is skipped in silence
rather than reported.

### The STE linter no longer splits a wrapped list item (REQ-12)

`ste_lint._prose_blocks` folded every list item into its own block and then let an indented continuation line fall through to the paragraph buffer. A hard-wrapped bullet therefore became two blocks, and a sentence spread across the wrap had its words counted twice — once per half. Neither half could exceed the 25-word cap on its own, so the linter passed prose it should reject.

The splitter now keeps a separate `item` buffer. A list marker starts it, an indented continuation line appends to it, and a shared `_flush()` closes it on a blank line, a heading, a table row, a code fence, a new list item, or the end of the text. An unindented line after a list item flushes the item and starts a paragraph, so a paragraph that follows a list stays its own block.

`_flush()` also runs on a heading, a table row, and a fence line, which the old loop did not do. Those lines used to leave the paragraph buffer open, so prose before and after a heading merged into one block and could exceed the six-sentence paragraph cap without a report. The full suite stays green, so no existing document changes its verdict.

`references/prompt-constants.md` also carried a sentence its own linter rejects: the mandated front-matter statement used a semicolon, which the `STE_PROSE` block forbids. It now reads as three sentences. Trade-off: the rest of `prompt-constants.md` still carries pre-existing violations that no gate checks — the file is a rule book, not a generated run artifact, and REQ-12 does not ask for a full-file cleanup.

### A Go CodeQL database builds without a build (REQ-14)

`codeql.run_codeql` now appends `--build-mode=none` to the `codeql database create` argv when the language is `go`. CodeQL's default Go extractor runs an autobuild, which compiles the target inside its own source tree. That write breaks the read-only-source invariant the harness holds over a reviewed repository. No other language gets the flag, because their extractors do not build.

Trade-off: `--build-mode=none` extracts without compiling, so CodeQL resolves fewer cross-package references on a Go target. Some dataflow that an autobuilt database would find is lost. A build that writes into the reviewed tree is the worse cost.

`prefilter.run_prefilter` records that cost when it applies. The CodeQL work unit now returns its result tagged `codeql:<lang>` instead of the bare `codeql`, so the result fold can tell a Go failure from any other. The fold branches on `backend.startswith("codeql")`, and a failing Go unit adds `skipped_reasons["codeql-go"] = "build-unfenceable"`. The `failed` entry still carries the bare name `codeql`, so no external consumer sees the tag. `codeql-go` is a reason key, not a backend: it never joins `backends_run`, and the never-silent contract loop still checks the four real backend names only.

### The opt-in proof-by-execution lane (REQ-30)

`prove.py` is the one module that runs target-derived code. Every other phase reads the target and
never runs it. The lane is off unless `scan_options.prove_findings` is exactly `true` in
`kb/scan-profile.json`, so a normal audit executes nothing. `prove_enabled` returns False for a
missing file, a malformed file, and an absent key.

A proof promotes a finding only when three conditions hold together. The agent drove a real
entrypoint (`scope: entrypoint`), the class has a wrapper-decidable oracle, and the oracle observed
the effect. `_reject_reason` checks them in one order and returns the first failure:
`prove: toolchain-absent`, `prove: slice-unbuildable`, `prove: harness-only-class`,
`prove: class-not-oracle-able`, then `prove: oracle-silent`. `AUTO_CONFIRMABLE` holds `ssrf`,
`cmdi`, `path-traversal`, `deserialization`, and `expr-eval-rce`. `HARNESS_ONLY` holds `sqli` and
`authz`, whose oracles need a provisioned backend, so a proof for them attaches a record and never
promotes. A proof that ran attaches a `reproduction` object to the finding even when it does not
promote; a `toolchain-absent` rejection attaches nothing, because nothing ran.

`loopback_collector` is the in-band oracle. It binds a stdlib `ThreadingHTTPServer` on
`127.0.0.1:0` and records each request path, so an egress proof needs no network egress and no new
dependency.

Six modules carry the wiring. `Workspace.repro` names the out-of-tree build and run root, created
by `ensure()`, so a proof never builds inside the target. `phases.py` declares a `prove` agent
phase between `redteam` and `artifact-gate`, driven by `agents/prove.md` and declaring
`kb/prove.json` as its output. `driver.run_audit` skips that phase and records the stage when the
lane is off — a declared output plus the auto-advance rule would otherwise cost one wasted model
dispatch on every default run. `findings_gate` accepts a `reproduction` receipt in place of a
Tier-1 tool receipt. `preflight_report` adds a `prove_toolchains` map for `opa`, `go`, `node`, and
`python3`; a missing toolchain degrades the lane and never blocks preflight.

`evidence.py` stays byte-identical. It is pinned by the D-15 frozen-contract test, so the
reproduction receipt vocabulary lives in `prove.py`, and `findings_gate` consults both modules.
Trade-offs: a `reproduction`-only confirmed finding leaves `receipt_tier` null, because the tier
map lives in the pinned file; `_promote` writes `runtime_disposition` as `static-settled`, because
the pinned `RUNTIME_DISPOSITIONS` set carries no proven value; and `run_prove` skips a proof whose
named finding file is absent without recording a degradation.

### `validate-fix` is wired as a phase, and `score_fix` gets a caller (REQ-43)

`scoring.score_fix` and `agents/validate-fix.md` shipped with no caller: nothing in `PHASE_TABLE`
ran the prompt, and no module named the scorer. `verify.py`'s `verify:conflict` branch, which
checks a finding's history for a `validate-fix:` event, was dead code for the same reason — that
event never got written.

`phases.py` adds a `validate-fix` agent row between `patch` and `verify`, naming
`agents/validate-fix.md`. Its output is `kb/gates/validate-fix.json`; `verify` declares that same
path as an input, so the deterministic re-check never runs ahead of the scored gate. `verify.py`
gains `apply_fix_gates(ws)`: it reads the gate file, calls `score_fix` on each finding's four
gate statuses, appends a `validate-fix:<verdict>` history event, and sets `verification` to
`not-fixed` on a `partial`/`not_fixed` verdict or `verify-error` on `unverifiable` — it never
touches `status`, leaving promotion to the deterministic `verify` phase that runs next.
`driver.py`'s `_act_verify` calls `apply_fix_gates` before `verify_findings`, as its own step, not
a call inside `verify_findings` itself. `verify.py` was missing the `Finding` import
`apply_fix_gates` needs; it is added alongside the existing `FindingStatus` one.

### `verify_findings` writes back only the findings it touched (REQ-44)

`verify_findings` read the whole finding set with `read_findings` at the top of the function, then
wrote the whole in-memory list back with `write_findings` at the bottom, gated only on a `changed:
bool` flag that recorded whether *any* finding in the set had changed — not which ones. A finding
another writer mutated between that read and that write (for example `apply_fix_gates`, running in
the same phase just before it) was overwritten with `verify`'s stale copy of that finding.

The `changed` flag is replaced with a `touched: list[Finding]` accumulator. The two sites in
`verify_findings` that used to set `changed = True` — the `verify:conflict` branch and the
`verify:cause:<cause>` event after a verdict — now append the finding they just mutated to
`touched` instead. The final write becomes `if touched: write_findings(ws, touched)`,
so a finding `verify_findings` never looked at (no `CONFIRMED` status, or no `patch_diff`) is never
part of the write-back. `write_findings` (`workspace.py`) writes one file per finding, so a subset
write needs no additional locking or barrier — it is already the unit of atomicity.
