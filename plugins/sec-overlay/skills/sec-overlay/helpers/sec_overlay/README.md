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

`kb.py` gained the arc42/threat-model tree path helpers (`arch_dir`/`arc42_path`/
`container_diagram_path`, `threat_dir`/`threat_model_path`/`dfd_path`), replacing the old
`kb/architecture.md` and `kb/THREAT_MODEL.md` single-file paths; `kb_status` now reports
`arc42_path`/`threat_model_path` existence. `workspace.py`'s `Workspace.ensure()` now also
creates `architecture/runtime-view/` and `threat-model/attack-sequences/` under the workspace
root.

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
after `selfscore`.

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
run's own artifacts). `artifact-review` is an agent phase with no registered action — it
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
