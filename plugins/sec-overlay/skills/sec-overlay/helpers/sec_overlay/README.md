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

`review_findings.py` (new, REV-01) adds the review-profile gate `apply_profile` — see the
module map entry in [`../README.md`](../README.md) for the full contract; `cli.py`'s
`run_review` and `report.py`'s `write_report`/`write_review_ledger` now thread its
`ReviewFinding` output through, both documented at the same map entries.

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

`cost.py` gained `aggregate_by_model` (per-model token totals, alongside the existing
`aggregate_by_phase`), feeding `report.py`'s "Run economics" section — see the module map entry.
It also gained `record_timing`/`aggregate_timings_by_phase`, summing per-phase wall-clock
seconds recorded in `CampaignState.budget["timings"]` (ISSUE-014). `write_report` folds
`aggregate_timings_by_phase` into the economics dict as `by_phase_seconds`, and `to_markdown`
renders it as a "Wall-clock by phase, seconds" list in "Run economics" when present.

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
see the module map entry. `PHASE_TABLE` now ends with `artifact-gate` (deterministic, input
`_report`/`_sarif`, output `_artifact_gate_json`) then `artifact-review` (agent,
`agents/artifact-review.md`, input `_artifact_gate_json`, output `_artifact_review_json`), both
after `selfscore`. `architecture` now outputs `_arc42`/`_container` (`kb.arc42_path` /
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
`selfscore.write_self_score`, `artifact-gate` → `_act_artifact_gate` (calls
`artifact_gate.run_artifact_gate`, raising `PhaseHalt` naming every error when the gate rejects the
run's own artifacts), `arch-gate` → `_act_arch_gate`, `tm-gate` → `_act_tm_gate`. Both new actions
run `diagram_gate.run_diagram_gate` over `architecture/` (and `threat-model/` where present) plus
`ste_lint.lint_prose` over their doc, write `{"passed", "errors", "warnings"}` to
`kb/gates/<name>.json` via the shared `_write_gate` helper, and raise `PhaseHalt` naming every
error; `_act_tm_gate` additionally runs `artifact_gate.check_duplication` against `arc42.md` and
calls `run_diagram_gate(..., require_threat_model=True)` so a missing `dfd.mmd` is a gate error
instead of the silently-optional default. `artifact-review` is an agent phase with no registered action — it
auto-advances once `kb/gates/artifact-review.json` exists, same as any other output-only agent
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

`route_control.py` (new, ISSUE-027/029/036) derives one route-to-control table from
`kb/scan-profile.json` (`build_route_control_table`) and checks recon, architecture, and threat-
model output against it (`check_recon_routes`, `check_architecture_controls`,
`check_threat_entrypoints`). A missing route, control, or entrypoint is never dropped: each check
returns a `needs_follow_up` gap dict with `reason`/`next_step`, and `record_route_gaps` appends
those gaps into `kb/coverage-ledger.json`'s `surfaces`, demoting `completeness` to `partial` so the
ledger's own "complete forbids needs_follow_up" invariant still holds after the append.
`check_architecture_controls`/`check_threat_entrypoints` match a control or entrypoint via
`_mentions`, a word-bounded (alphanumeric-neighbor guard) check, not substring — so a token that is
part of a longer word (`auth` inside `authorization`) is still flagged as a gap.

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
later plan. `coverage.py`, `models.py`, and `evidence.py` — the frozen milestone contracts —
are untouched; no new runtime dependency. See the module map entries.

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
through `apply_verdict` (an always-empty verdict in this tracer slice — no finding source is wired
into review mode yet) inside a `try`/`except` that records a `ReflectionSkip` and fails open on
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
parses, and `apply_verdict` retracts — `cli.py review`'s tracer slice still calls it with an
always-empty verdict, so live dispatch remains a later plan.

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
