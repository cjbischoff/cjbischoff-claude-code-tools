# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## 1.40.0 - 2026-08-17

### Added

- `diffscope.py`: full ref-validation and `changed_file_records` behavior. The allowlist pattern
  now permits `~` so `HEAD~1`-style ancestor refs validate; `changed_file_records` parses the
  full `--name-status` vocabulary and carries `old_path` for renames and copies; two new
  functions, `file_diff_line_count` and `binary_paths`, give `file_select.partition` its
  size-cap and binary inputs (landing in the next release). The `review` CLI branch now catches
  a `ValueError` from ref resolution and exits `2` with one actionable stderr line naming the
  ref, without laundering any other `ValueError` into the same exit code.

## 1.39.0 - 2026-08-17

### Added

- New `sec-overlay review --base <ref> --head <ref> --root <path>` CLI verb: a diff-scoped,
  position-verified review pass. Resolves both refs to SHAs before any other git call, selects
  changed files (`file_select.partition`), parses their hunks (`diffhunks.parse_hunks`),
  confirms or declines each finding's claimed position against the diff without fuzzy matching
  (`positioning.resolve_position`), gates findings on that decision
  (`phase_gate.review_position_gate`), and tracks per-file coverage to a terminal seal
  (`review_coverage.CoverageManifest`, persisted to `artifacts/coverage_manifest.json`). Exits 0
  only when the manifest seals `complete`. Wires exactly one changed file through every layer
  (the tracer path) — batching, exit codes 2/3, the full extension allowlist, and the diff-line
  size cap arrive in a later plan. No new runtime dependency; `coverage.py`, `models.py`, and
  `evidence.py` are unchanged.

## 1.38.0 - 2026-08-17

### Added

- `Workspace` gained an `artifacts` property (`root/artifacts`) for review-mode run state — the
  coverage manifest and review ledger the upcoming `review` CLI mode writes. Never routed through
  `reports_dir`. `ensure()` creates it.

## 1.37.11 - 2026-08-17

### Fixed

- `tests/fixtures/graph_target/app/{db,api}.py` reference `cursor`/`app` names that only exist
  at runtime through the fixture's structural-scan contract (`sec_overlay.graph` parses these
  files without importing them). `ty` flagged both as unresolved references. Added a stub
  binding for each (`cursor: Any = None`, `app: Any = None`) placed to preserve every line
  number `test_graph.py` pins (`app/db.py:1:run_query`, `app/api.py:4:handler`,
  `app/api.py:10:get_widget`). No behavior change — these files are never executed.

## 1.37.10 - 2026-08-17

### Fixed

- `sec_overlay/stage_validate.py`'s `_VALIDATORS` dict held three differently-typed validator
  signatures (`dict`-only, `dict | None`, and `object`), which `ty` flagged as a union-callable
  mismatch at the `fn(obj)` call site. Added `_adapt_dict`/`_adapt_optional_dict` factories that
  isinstance-check the stage payload before delegating, unifying every entry to
  `Callable[[object], list[str]]`. This also closes a real gap: a non-dict subagent output to
  most stages previously crashed with `AttributeError` instead of returning a validation error
  (only `_validate_runtime_test` guarded against this before). No behavior change for
  well-formed dict input.

## 1.37.9 - 2026-08-17

### Fixed

- `test_patch_status.py`'s fake-runner helper monkey-patched a `calls` list onto a plain
  function object, which `ty` cannot type (function objects have no declared attribute
  namespace). Replaced with a small `_Runner` class holding `calls` as a real instance
  attribute and a `__call__` method standing in for the function; fixes the remaining
  `unresolved-attribute` VAL-02 row. No behavior change.

## 1.37.8 - 2026-08-17

### Fixed

- `test_rule_matcher.py`, `test_bucket_b.py`, and `test_calibrate.py` add an explicit
  `is not None` assertion before dereferencing a call result typed `X | None`
  (`AsvsCatalog.get`, `emit_semgrep_rule`, `Finding.risk_score`) — each call is known to return
  a non-`None` value at that point in the test, but `ty` cannot infer that without the guard.
  Fixes 3 VAL-02 ledger rows (`unresolved-attribute` / `not-subscriptable` / `unsupported-operator`);
  no behavior change.

## 1.37.7 - 2026-08-17

### Fixed

- `test_bench.py`'s `CorpusEntry` builder and `test_profile.py`'s `ScanProfile` roundtrip test
  now build the base object with explicit fields and layer overrides with `dataclasses.replace`,
  instead of a `dict()` + `.update(kw)` + `Cls(**d)` / `Cls(**base, notes=...)` splat — the same
  `ty` per-field argument-checking bypass fixed for `Finding` builders in 1.37.6. Clears the
  remaining VAL-02 `invalid-argument-type` rows for both files; no behavior change.

## 1.37.6 - 2026-08-17

### Fixed

- `test_citations.py`, `test_factcheck_baseline_envelope.py`, and `test_report.py`'s `Finding`
  test-builders now use `dataclasses.replace(base, **kw)` over per-test overrides instead of
  `dict()` + `.update(kw)` + `Finding(**d)` — `**d`'s concrete inferred dict type bypassed `ty`'s
  per-field argument checking, which `replace`'s `**changes: Any` typing restores; fixes the
  bulk of the VAL-02 `invalid-argument-type` ledger rows; no behavior change.

## 1.37.5 - 2026-08-17

### Fixed

- `test_postflight.py` replaces a single-element list-slice with `next(...)`, and
  `test_structural_index.py` replaces a `"\n".join([...])` with adjacent string literals —
  fixes the two remaining VAL-02 ruff findings (`RUF015`, `FLY002`); no behavior change.

## 1.37.4 - 2026-08-17

### Fixed

- `test_prefilter.py` and `test_wiring.py`'s `Exclusions([], [], [])` fixture calls now pass
  `Exclusions(set(), [], set())`, matching the dataclass's `set[str]`-typed `rule_ids`/`classes`
  fields — fixes 16 `invalid-argument-type` diagnostics (VAL-02 ty ledger row); no runtime
  behavior change.

## 1.37.3 - 2026-08-17

### Fixed

- `workspace.py`'s `Workspace` gains a hand-written `__init__` (replacing the dataclass
  `__post_init__`) so the `str | Path` constructor argument type-checks under `ty` — fixes
  three `invalid-argument-type` diagnostics in `test_workspace.py` without widening the
  stored `Path`-typed fields (VAL-02 ty ledger row).

## 1.37.2 - 2026-08-16

### Fixed

- Persist the fence baseline so resume invocations catch agent-phase tree writes.
- Add `run.advance` to fence, receipt, and record each agent phase.
- Pin the pass SHA on resume instead of re-reading HEAD.
- Correct `audit.md` resume steps and correlation output paths.

## 1.37.1 - 2026-08-16

### Fixed

- Sort import block in test_run.py to clear ruff I001.

## 1.37.0 - 2026-08-16

### Added

- Add /sec-overlay:audit command.

## 1.36.1 - 2026-08-16

### Fixed

- Fix red-team gate path collision (O-65): the adversary writes redteam-adversary.json. Added test to verify old path absent.

## 1.36.0 - 2026-08-16

### Added

- Add single-repo drive loop with per-phase fence and receipt.

## 1.35.0 - 2026-08-16

### Added

- Add manifest synthesis for correlation.

## 1.34.0 - 2026-08-16

### Added

- Add scan-profile role inference.

## 1.33.0 - 2026-08-16

### Added

- Add run.env token writer.

## 1.32.0 - 2026-08-16

### Added

- Add per-phase receipt writer.

## 1.31.1 - 2026-08-16

### Fixed

- Remove unused `pathlib.Path` import from `helpers/tests/test_run.py` (ruff F401).

## 1.31.0 - 2026-08-16

### Added

- Add run.py driver working-tree fence.

## 1.30.3 - 2026-08-16

### Changed

- Name the CVSS v4.0 score invocation in `agents/threat-model.md` step 5 —
  `sec_overlay.cvss.cvss40_base('<vector>')` run from `helpers/` — so the
  agent has a way to obtain the score it is told never to hand-compute.
  Note the same invocation in `agents/README.md`'s threat-model row.
- Name STRIDE in the skill `CLAUDE.md` §2 phase table and `README.md`'s
  worked-example table, restoring a term dropped from an earlier pass.

## 1.30.2 - 2026-08-16

### Changed

- Restore the phase-adversary annotation on the Threat model row of the
  skill `CLAUDE.md` §2 phase table (dropped in the 1.30.1 compression pass);
  note in the skill `README.md` that each of `arch-gate` / `tm-gate` is
  preceded by the opus phase-adversary review, not only the deterministic
  check.

## 1.30.1 - 2026-08-16

### Changed

- Document the `architecture/` and `threat-model/` artifact trees and the
  `arch-gate` / `tm-gate` deterministic phases across the skill `CLAUDE.md`,
  `SKILL.md`, both READMEs, and the plugin `CLAUDE.md`'s CLI-callable module
  list (`diagram_gate`, `ste_lint`). No behavior change.

## 1.30.0 - 2026-08-16

### Changed

- Re-point every remaining consumer prompt (`investigate.md`, `critic.md`,
  `validate.md`, `context-ingest.md`, `phase-adversary.md`, `postflight.md`)
  from the retired `kb/architecture.md` / `kb/entities/` / `kb/THREAT_MODEL.md`
  paths to `architecture/arc42.md` and `threat-model/threat-model.md`.
  `phase-adversary.md` gains an ownership-boundary checklist bullet: an
  architecture claim naming threats/mitigations, or a threat-model claim
  restating structure/stack, is a defect.
- Remove the now-dead `kb.py::entities_dir` helper (no remaining callers).

## 1.29.0 - 2026-08-16

### Added

- Wire `arch-gate` and `tm-gate` deterministic phase rows into `PHASE_TABLE`,
  right after `architecture` and `threat_model`. Each gate runs the diagram
  gate, the ASD-STE100 prose linter, and (for `tm-gate`) the arc42/threat-model
  duplication check, writing `kb/gates/arch-gate.json` / `kb/gates/tm-gate.json`
  and halting the run on any error. `tm-gate` requires `threat-model/dfd.mmd` to
  exist; `arch-gate` does not require the threat-model tree at all.

## 1.28.0 - 2026-08-16

### Changed

- `agents/threat-model.md` rebuilt on the DFD/STRIDE contract: it now derives
  `threat-model/dfd.mmd` from `architecture/container-diagram.mmd` (SHA-headered),
  `threat-model/attack-sequences/sequence-<scenario>.mmd`, and
  `threat-model/threat-model.md` — a methodology record, a CVSS v4.0 findings table, and
  a prioritized hunt list — replacing the old single-file `kb/THREAT_MODEL.md` output.

## 1.27.0 - 2026-08-16

### Changed

- `agents/architecture.md` rebuilt on the C4/arc42 contract: it now writes
  `architecture/context-diagram.mmd`, `architecture/container-diagram.mmd`,
  `architecture/component-diagram-<name>.mmd` and
  `architecture/runtime-view/sequence-<scenario>.mmd` (only where warranted), and
  `architecture/arc42.md` — replacing the old single-file `kb/architecture.md` +
  `kb/entities/<component>.md` output.

## 1.26.0 - 2026-08-16

### Added

- `kb.py` gains path helpers for the new `architecture/` and `threat-model/` workspace trees
  (`arch_dir`/`arc42_path`/`container_diagram_path`, `threat_dir`/`threat_model_path`/`dfd_path`),
  replacing the old single-file `kb/architecture.md` and `kb/THREAT_MODEL.md` paths.
  `Workspace.ensure()` now creates `architecture/runtime-view/` and
  `threat-model/attack-sequences/` alongside the existing KB directories.

## 1.25.0 - 2026-08-16

### Added

- `references/architecture-standards.md` fixes the C4 + arc42 contract for the architecture
  phase: which diagrams to produce, the arc42 section table, and the ownership boundary
  against the threat-model phase.
- `references/threat-model-standards.md` fixes the DFD + STRIDE contract for the
  threat-model phase: signal-based methodology augmentation (PASTA/LINDDUN), how `dfd.mmd`
  derives from `container-diagram.mmd`, and the findings-table column contract.
- `references/mermaid-caps.md` is the single source of truth for per-diagram-kind element
  caps, mirrored in `sec_overlay.diagram_gate.CAPS`/`SEQ_CAPS` and kept in sync by
  `tests/test_references_caps.py`.
- `prompt-constants.md` gained an `STE_PROSE` block: human-facing prose (arc42.md,
  threat-model.md, findings-table free text) now follows ASD-STE100's checkable core.

## 1.24.1 - 2026-08-16

### Fixed

- `mermaid_index.py`'s flowchart edge scan matched only the first `-->` on a line, dropping every
  hop after the first in a chained edge (`a --> b --> c`) and false-flagging the middle node as an
  orphan; the scan now restarts each search at the matched destination.
- `mermaid_index.py`'s sequence-diagram regexes rejected hyphenated participant/message ids
  (`auth-api`), silently recording a truncated id and undercounting messages; the id class now
  allows `-` and the source-id match is non-greedy so it stops before the arrow.
- `diagram_gate.py`'s `run_diagram_gate` treated a missing `dfd.mmd` as always-optional; it now
  takes a keyword-only `require_threat_model` flag (CLI: `--require-threat-model`) that turns a
  missing threat-model diagram into a gate error.
- `diagram_gate.py` gained a node-label word-count check (spec's "node labels: name only" rule):
  a bracket label over 4 words is now an error, matching the existing edge-label check.

## 1.24.0 - 2026-08-16

### Added

- `sec_overlay/artifact_gate.py` gains `check_duplication(arc42_text, tm_text)`: flags a
  threat-model heading that restates an `architecture/arc42.md` heading, and flags a
  structure heading (e.g. "Building Block View", "Deployment View") appearing in the
  threat-model doc at all. `run_artifact_gate` calls it only when both
  `architecture/arc42.md` and `threat-model/threat-model.md` exist; older workspaces and
  the existing tests are unaffected.

## 1.23.1 - 2026-08-16

### Fixed

- `sec_overlay/ste_lint.py`'s `_prose_blocks` no longer silently drops every line after an
  unterminated code fence — an unclosed ` ``` ` now yields an `"unbalanced code fence"` error
  instead of a false-clean result.
- `sec_overlay/ste_lint.py`'s sentence splitter no longer fractures a paragraph or sentence at
  an abbreviation (`e.g.`, `i.e.`, `etc.`, `vs.`, `cf.`, `approx.`, `viz.`, `al.`) — it now
  splits only at sentence-ending punctuation followed by a capitalized word and folds an
  abbreviation-preceded split back onto its clause, so an abbreviation-heavy paragraph no
  longer produces a false "over 6 sentences" error and a genuinely over-length sentence
  containing an abbreviation is still flagged.

## 1.23.0 - 2026-08-16

### Added

- `sec_overlay/ste_lint.py`: a deterministic linter for the checkable structural subset of
  ASD-STE100 — sentence >25 words, semicolon in prose, and paragraph >6 sentences are errors;
  a 4+ word capitalized run mid-sentence and a sentence repeating " then " are warnings. Fenced
  code, mermaid blocks, headings, table separator rows, inline code spans, and URLs are exempt;
  table free-text cells are linted. `lint_prose(text)` is the entry point; the CLI
  (`python -m sec_overlay.ste_lint <files...> [--require-frontmatter]`) exits 1 on any error.

## 1.22.1 - 2026-08-16

### Fixed

- `sec_overlay/diagram_gate.py`'s `_provenance` no longer crashes with `FileNotFoundError` when
  the derived-from source file doesn't exist — a missing `container-diagram.mmd`, or an attack
  sequence whose header names an unknown parent — it now returns a `"derived-from source ... not
  found"` error string.
- `sec_overlay/diagram_gate.py`'s `check_diagram` no longer crashes with an uncaught `ValueError`
  when the source diagram (for element/participant-diff checks) is unparseable — it now returns a
  `"source ... unparseable: ..."` error string.
- `sec_overlay/mermaid_index.py`'s `_INLINE_LABEL_SKIP` only spanned single-char bracket pairs and
  missed multi-char forms like `q{{Queue}}`, dropping the edge entirely and false-flagging the
  source node as an orphan-detail node — widened to one bracket-class alternation covering all
  Mermaid node shapes.

## 1.22.0 - 2026-08-16

### Added

- `sec_overlay/diagram_gate.py`: deterministic hard gate over generated Mermaid diagrams —
  per-type node/participant/message caps (`CAPS`, `SEQ_CAPS`), ≤4-word edge labels, DFD
  trust-boundary-subgraph requirement, derivation provenance (`%% derived-from: <file>
  sha256:<hash>`, rejecting a stale hash or a new element/participant absent from the source),
  legend-required styling, and orphan-detail nodes (a node that only ever receives and isn't a
  store/actor) scoped to `container`/`component`/`dfd` diagrams only. `run_diagram_gate(arch_dir,
  tm_dir)` walks a full architecture/threat-model tree. CLI-callable
  (`python -m sec_overlay.diagram_gate --architecture DIR --threat-model DIR`).

### Fixed

- `sec_overlay/mermaid_index.py`'s edge regexes no longer drop an edge whose source node carries
  an inline bracket label on the same line (`web[Web] --> api[API]`) — previously produced zero
  edges for that shape.
- `sec_overlay/mermaid_index.py`'s C4 parser now also adds `Person(...)` and `*_Ext(...)` element
  ids to `store_ids`, marking them orphan-exempt alongside `ContainerDb`/`SystemDb`/`*Queue`.

## 1.21.1 - 2026-08-16

### Fixed

- `sec_overlay/mermaid_index.py`'s flowchart edge scan no longer misreads a mid-arrow label
  (`a -- some label --> b`) as a phantom source node — `_FLOW_EDGE_MID` now runs first, so the
  real node ids and the label are captured instead of silently dropped.

## 1.21.0 - 2026-08-16

### Added

- `sec_overlay/mermaid_index.py`: `index_mermaid(text)` line-oriented structure extractor for
  Mermaid flowchart, sequence, and C4 diagrams — nodes, edges, subgraph membership, sequence
  participants/message count, data-store ids, and style detection, feeding the upcoming diagram
  gate.

## 1.20.2 - 2026-08-16

### Fixed

- `sec_overlay/cvss.py`'s `_parse` no longer silently drops score-affecting Threat (`E`) or
  Environmental (`CR`/`IR`/`AR`/`M*`) metrics — a vector carrying one with a value other than `X`
  (Not Defined) now raises `ValueError` instead of returning the unchanged base score; NVD-shaped
  `.../E:X/CR:X/IR:X/AR:X` suffixes still parse and score identically to the bare base vector.
- `sec_overlay/calibrate.py`'s `_derived_score` now records a `calibrate:cvss-unparseable` history
  event (with the offending vector) before falling back to the heuristic score on any unparseable
  `cvss_vector`, so a pre-migration CVSS 3.1 vector leaves an audit trail instead of a silent
  fallback.
- `references/finding-template.md`'s §5 metric-justification list updated from the CVSS 3.1 metrics
  (`AV, AC, PR, UI, S, C, I, A`) to all 11 CVSS v4.0 base metrics (`AV, AC, AT, PR, UI, VC, VI, VA,
  SC, SI, SA`).

## 1.20.1 - 2026-08-16

### Fixed

- Migrated the last `CVSS:3.1` fixture vectors in `test_report.py`, `test_models.py`,
  `test_citations.py`, and `test_factcheck_baseline_envelope.py` to `CVSS:4.0` vectors of
  equivalent meaning, so the repo has zero v3.1 vectors outside `sec_overlay/cvss.py`'s
  rejection-path test and its own error message.

## 1.20.0 - 2026-08-16

### Changed

- `agents/validate.md`'s confirmed-finding contract and `agents/investigate.md`'s example
  finding now specify a CVSS v4.0 vector (`CVSS:4.0/AV:_/AC:_/AT:_/PR:_/UI:_/VC:_/VI:_/VA:_/
  SC:_/SI:_/SA:_`) instead of v3.1, matching the v4.0-only parser (`sec_overlay/cvss.py`).
  `references/prompt-constants.md`'s `SEVERITY_GUIDANCE` block, `references/finding-template.md`,
  and `references/README.md` updated to the same legal v4.0 base-metric values so every prompt
  that imports the shared block proposes a vector the engine accepts.

## 1.19.0 - 2026-08-16

### Changed

- Re-point `sec_overlay/calibrate.py` from the removed `cvss31_base` to `cvss40_base`
  (`sec_overlay/cvss.py`'s CVSS v4.0 engine); `risk_score`/`priority` derivation shape is
  unchanged. `Finding.cvss_vector`'s docstring in `models.py` now says "CVSS v4.0". Migrated
  `test_calibrate.py`'s CVSS fixtures to v4.0 vectors, with expectations recomputed from the
  real scoring engine.

## 1.18.1 - 2026-08-16

### Fixed

- Wrap `tests/test_cvss.py`'s `sec_overlay.cvss` import across multiple lines to clear a ruff
  `I001` warning introduced by the CVSS v4.0 scoring-engine rewrite.

## 1.18.0 - 2026-08-16

### Changed

- Rewrite the scoring engine (`sec_overlay/cvss.py`) from CVSS 3.1 to CVSS v4.0: `cvss40_base`
  computes the base score via a MacroVector/interpolation port of FIRST's official calculator
  (`cvss_score.js`, BSD-2-Clause) against `cvss4_data.py`'s tables, base metrics only (no
  Threat/Environmental/Supplemental support). `offensive_priority` keeps its 3.1 branch order
  verbatim. A `CVSS:3.x` vector now raises `ValueError` naming the required 4.0 migration.

## 1.17.0 - 2026-08-16

### Added

- Vendor CVSS v4.0 MacroVector lookup and interpolation tables (`sec_overlay/cvss4_data.py`) from
  FIRST's official calculator (BSD-2-Clause), for a future v4.0 scoring engine.

## 1.16.2 - 2026-08-15

### Fixed

- Rewrite the `_full` test helper in `test_report.py` as a dict literal to clear a ruff `C408`
  warning introduced by the report-split work.

## 1.16.1 - 2026-08-15

### Changed

- Document the `artifact-gate` → `artifact-review` phases (Tasks 14–16) in the operating manual:
  `skills/sec-overlay/CLAUDE.md` §2 phase order and §4 workspace artifacts, `CLAUDE.md`'s
  CLI-callable module list (`artifact_gate`), and `skills/sec-overlay/README.md`'s pipeline map.

## 1.16.0 - 2026-08-15

### Added

- `PHASE_TABLE` (`phases.py`) gains two phases after `selfscore`: `artifact-gate` (deterministic,
  runs `run_artifact_gate`) then `artifact-review` (agent, `agents/artifact-review.md`). The driver
  registers `_act_artifact_gate`, which raises `PhaseHalt` when the gate reports any error, wiring
  Task 14's `artifact_gate.py` and Task 15's prompt into a normal run for the first time.

## 1.15.0 - 2026-08-15

### Added

- New `agents/artifact-review.md` (§4.8): the opus adversary that runs after the deterministic
  `artifact_gate` passes, checking that `report.md`, `report.sarif`, and `redteam-plan.md` tell
  the truth about what the run found — claim-to-evidence against each finding's tool receipt,
  impact honesty, and red-team coverage. Reasoning alone may demote severity, force a re-render
  via `render_stale`, or add an `open_questions` entry, but never delete or reject a tool-receipt-
  backed finding. Writes `kb/gates/artifact-review.json`.

## 1.14.0 - 2026-08-15

### Added

- New `artifact_gate.py` module (§4.8): `run_artifact_gate(ws)` is a deterministic gate over a
  finished run's own output artifacts, checking `report.md` for stale constant sections and
  over-long triage cells, every shipping finding for a detail file and a red-team directive, every
  triage-table ID for a resolving finding, and `CONTEXT.md`'s mermaid diagram for the ≤10-node
  style cap (ISSUE-022). Writes `kb/gates/artifact-gate.json` and runs before the opus
  artifact-review adversary.

## 1.13.1 - 2026-08-15

### Fixed

- `validate.md` now requires a `confirmed` finding to carry a real, derived `cvss_vector` and a
  non-empty `preconditions` list, routing to `needs-deployment-testing` otherwise; `trace.md` now
  records `preconditions` on a statically-confirmed reachability verdict — calibrate scores off
  these fields verbatim, so a missing/guessed vector no longer produces a flat, wrong score
  (ISSUE-008). Prompt-only fix; the calibrate scorer is unchanged.

## 1.13.0 - 2026-08-15

### Added

- `build_self_score` gained `critic_viable`, `critic_rejected`, and `critic_reject_rate` (0.0 with
  no critic events), counted from `critic:viable`/`critic:rejected` history events across all
  findings (ISSUE-043) — measurement only, nothing gates on the rate.

## 1.12.3 - 2026-08-15

### Fixed

- `validate_stage` now raises `ValueError` for a stage with no registered validator instead of
  silently passing — a silent pass masked mis-named stages (ISSUE-034).
- `run_prefilter` gained a `strict: bool = True` parameter: a planned SAST backend left in
  `skipped_reasons` or `failed` now raises `RuntimeError` via the new `_raise_on_incomplete_backends`
  helper instead of returning a silent partial result. Pass `strict=False` only for a deliberately
  partial run. A `"disabled"` skip reason is excluded from the raise — a profile turning a backend
  off on purpose is a planning decision, not a coverage hole.

## 1.12.1 - 2026-08-15

### Fixed

- `context-ingest` now has a real check on `docs_read`: `cited_source_docs` collects
  every `source_doc` an item or its history cites, and the `context` stage-validator
  rejects a citation to a doc absent from `provenance.docs_read` — `docs_read` can no
  longer be a placeholder count.

## 1.12.0 - 2026-08-15

### Added

- Time each deterministic driver phase (`run_deterministic_phase`) and record it into
  `state.budget["timings"]`; the report's economics section renders a "Wall-clock by
  phase" list when timings are present (ISSUE-014).

## 1.11.0 - 2026-08-15

### Added

- Per-phase wall-clock timing accounting: `cost.record_timing` and
  `cost.aggregate_timings_by_phase` sum recorded seconds by phase (ISSUE-014).

## 1.10.0 - 2026-08-15

### Added

- Split `report.md`: full per-finding bodies now write to `findings/<ID>.md`, and the
  Markdown report renders a slim, risk-ordered **Detail** link list instead of inlining
  every finding's full body (`write_finding_details`, ISSUE-009).

## 1.9.5 - 2026-08-15

### Fixed

- A `needs_follow_up` coverage-ledger surface now carries a non-empty `reason` and
  `next_step`; `validate_coverage_ledger` rejects one missing either, and `render_markdown`
  renders both columns.

## 1.9.4 - 2026-08-15

### Fixed

- Prefilter candidate ids are now class-prefixed and numbered per class
  (`C-SQLI-0001`, `C-XSS-0001`, ...) instead of one global `C-0001..` sequence, so ids carry
  the attack class and never collide across rulesets (ISSUE-013).

## 1.9.3 - 2026-08-15

### Fixed

- The triage table's `what` column now trims a long title to a word boundary with a trailing
  `…` instead of cutting mid-word at a fixed 80-character slice (ISSUE-011).

## 1.9.2 - 2026-08-15

### Fixed

- The report's bottom-line `Confirmed:` line now renders counts in words (e.g. `"1 critical, 1
  high, 2 medium, 1 low"`) instead of an ambiguous digit ratio (`"1/1/2/1"`) (ISSUE-010).

## 1.9.1 - 2026-08-15

### Fixed

- `render_finding`'s §4 Impact now renders the finding's real `impact` text instead of a
  boilerplate sentence. Deleted the constant §6 Confirmed Attack Scenario and §8 Testing
  sections — both always emitted the same fixed prose regardless of the finding, misleadingly
  labelled `full` tier (ISSUE-052).

## 1.9.0 - 2026-08-15

### Added

- `Finding.impact: str = ""` — the concrete consequence of exploitation, rendered as the
  report's Impact section. `findings_gate.validate_findings` now rejects a `SHIPPING_STATUSES`
  finding (`confirmed`/`fixed`/`needs-deployment-testing`) whose `impact` is blank; non-shipping
  findings may stay blank. `references/finding.schema.json` gained the matching `impact` property
  (not in `required`).

## 1.8.3 - 2026-08-15

### Fixed

- `route_control.py`'s control and entrypoint coverage-gap matching is word-bounded (alphanumeric-
  neighbor guard), not substring, so a token that is part of a longer word (`auth` inside
  `authorization`) is no longer treated as covered and the gap is no longer suppressed.

## 1.8.2 - 2026-08-15

### Added

- Regression pins in `test_wiring.py` for four already-wired items: `reconcile_plan(` and
  `unrouted_candidate_classes(`/`unrouted_triage_dispatch(` in `driver.py`, `render_fp_feedback`
  keying on `fingerprint`, and `run_deterministic_phase` halting on a missing output artifact
  (ISSUE-017, ISSUE-020, ISSUE-031, ISSUE-033).
- `test_feedback_survives_workspace_rename` in `test_fp_feedback.py`: pins that the fingerprint-
  keyed false-positive feedback body is identical across a workspace rename (ISSUE-033).

## 1.8.1 - 2026-08-15

### Fixed

- `render_plan` now renders `discriminate`'s `"unrunnable"` bucket as its own plan section
  (`## Unrunnable preconditions (payload not traceable)`), and folds its `open_questions` into
  "Questions to ask"; `write_plan`'s returned summary carries an `"unrunnable"` count. Previously
  these above-bar needs-runtime findings vanished from `redteam-plan.md` and the summary entirely
  once `payload_runnable` routed them out of `needs_runtime` (ISSUE-056).

## 1.8.0 - 2026-08-15

### Added

- `sec_overlay.redteam.payload_runnable(f)` gates red-team payloads on reachability: a needs-
  runtime finding above the confidence bar now reaches the manual test plan only if it carries a
  non-empty `dataflow` trace or a `reachability` dict with `reachable is True`; otherwise it
  routes to a new `discriminate()` `"unrunnable"` bucket instead of a live directive (ISSUE-056).
  `agents/redteam.md` now requires the producer to trace each payload source→sink through the
  target's own input validation before shipping it as a live test.

## 1.7.3 - 2026-08-15

### Added

- `test_every_codeql_finding_carries_receipt` regression test in `sec_overlay.codeql` to pin that
  every parsed CodeQL finding carries a `codeql:<rule_id>` evidence source at parse time. Confirms
  the receipt mechanism is working (ISSUE-004).

## 1.7.2 - 2026-08-15

### Fixed

- `dedupe_findings()` now collapses two active findings sharing `(file, line, cls)` even when
  both have empty `dataflow` and differ only in message wording (ISSUE-042).
- `correlate/edges.py`'s `_RECURRENCE_STATUSES` is now `evidence.SHIPPING_STATUSES` instead of a
  separate literal, so the shipping-status set is defined once (ISSUE-005).

## 1.7.1 - 2026-08-15

### Fixed

- `run_semgrep()` excludes `.sec-overlay`, `.git`, `.venv`, and `node_modules` directories from scans via `--no-git-ignore` flag. Prevents audit sidecar findings on the harness's own output (ISSUE-032).

## 1.7.0 - 2026-08-15

### Added

- `sec_overlay.class_ext`: `class_extension_status()` checks which investigate/patch extension
  files exist; absent classes are logged as gaps so coverage is never silent. Uses an alias map
  (e.g., sqli/cmdi/xss → injection.md) to count coarse files (ISSUE-037, ISSUE-049).

## 1.6.0 - 2026-08-15

### Added

- `recon.md`, `architecture.md`, and `threat-model.md` each gained one additive instruction so
  their output matches `sec_overlay.route_control`'s checks: recon emits a `route_summary`
  field, architecture names every control by key, and threat-model keeps every entrypoint
  listed before its hunt-list prioritization (ISSUE-027, ISSUE-029, ISSUE-036).

## 1.5.0 - 2026-08-15

### Added

- `sec_overlay.route_control`: derives one route-to-control table from `kb/scan-profile.json`
  and checks recon, architecture, and threat-model output against it. A missing route, control,
  or entrypoint is logged as a `needs_follow_up` gap (`reason` + `next_step`), never dropped;
  `record_route_gaps` appends gaps into `kb/coverage-ledger.json` (ISSUE-027, ISSUE-029,
  ISSUE-036).

## 1.4.0 - 2026-08-15

### Added

- `validate_citations()` in `sec_overlay.findings_gate` to reject any shipping finding whose
  `file:line` citation does not resolve against the target source, reusing
  `phase_gate.resolve_ref`; wired into the driver's findings-gate phase alongside
  `validate_findings` (ISSUE-018, ISSUE-019, ISSUE-023). Control findings from
  `context.control_findings` inherit the check since they flow through the same gate.

## 1.3.0 - 2026-08-15

### Added

- `doc_coverage()` in `sec_overlay.context` to compute read/discovered ratio with low-coverage warnings (ISSUE-016).
- `load()` now accepts optional `repo_root` and `scan_scope` parameters to populate `provenance["docs_discovered"]` — wiring is handled by downstream caller (driver/orchestration).

## 1.2.1 - 2026-08-15

### Added

- `EVIDENCE_VOCABULARY` block in `references/prompt-constants.md`: the closed set of receipt
  tiers, shipping statuses, and `runtime_disposition` values, pasted into every agent prompt like
  the other twelve blocks. A drift test in `test_docs_invariants.py` binds the block's listed
  values to `sec_overlay.evidence`'s `TIER1_RECEIPTS`/`TIER2_RECEIPTS`/`SHIPPING_STATUSES`/
  `RUNTIME_DISPOSITIONS` constants so the two cannot drift apart.

## 1.2.0 - 2026-08-15

### Added

- `sec_overlay.prompts.render_prompt(template, subs)` substitutes `{{KEY}}` tokens and raises
  `ValueError` naming every unfilled `{{TOKEN}}` — closes the class of bug where a hand-substituted
  agent prompt shipped a literal `{{ATTACK_CLASS}}` to a model. `skills/sec-overlay/CLAUDE.md` §2
  now instructs the orchestrator to render every agent dispatch prompt through it.

## 1.1.0 - 2026-08-15

### Added

- Recon gate: `phase_gate.attack_surface_gate` rejects an `attack_surface` key whose evidence
  refs are absent, unresolved, or resolve only to comment lines — a comment is a claim about
  code, not proof it executes (ISSUE-026).

## 1.0.4 - 2026-08-15

### Fixed

- `scan-profile.schema.json` gains `attack_surface_evidence` (required) and `subsystems`
  (optional), matching the two `ScanProfile` fields recon already writes.

## 1.0.3 - 2026-08-15

### Fixed

- `phase_gate._parse_ref` now anchors a citation with a leading-match regex instead of
  `rsplit(":", 1)`, so a trailing human hint after the line or range (`foo.py:42 in the
  handler`) is stripped instead of failing the ref to resolve (ISSUE-024/028).

## 1.0.2 - 2026-08-15

### Fixed

- `redteam._above_bar` is now coverage-first: a critical/high/medium finding above the risk
  floor earns a manual test directive regardless of receipt strength — a missing tool
  receipt no longer withholds the test that would settle it. The dead
  `redteam:prime-manual-test` history branch (no producer wrote that event) is removed.

## 1.0.1 - 2026-08-15

### Fixed

- `selfscore.build_self_score` gained a `shipping` count over the full `evidence.SHIPPING_STATUSES`
  set (`confirmed`/`fixed`/`needs-deployment-testing`), alongside the existing narrower `reported`
  count. `factcheck.md` now targets ONE shipping-status finding rather than narrowly `confirmed`.

## 1.0.0 - 2026-08-15

### Changed

- **Breaking:** the findings gate now requires a Tier-1 tool receipt (codeql/semgrep/sca/
  secrets) for any `confirmed`/`fixed` finding. A Tier-2-only receipt (ripgrep/ast-grep/
  structural-index/tree-sitter) — previously enough to confirm a finding on
  SAST-unsupported languages — now fails the gate and must route to
  `needs-deployment-testing` instead. The gate also stamps `Finding.receipt_tier` and
  rejects any `runtime_disposition` value outside the shared enum. `_act_findings_gate`
  now raises `PhaseHalt` when the gate reports errors, instead of validating silently.

### BREAKING CHANGE

Any pipeline consumer treating `confirmed`/`fixed` as ground truth for a ripgrep-only
finding must re-triage it as `needs-deployment-testing` — a manual test directive, not
an automatic confirmation.

## 0.12.0 - 2026-08-15

### Added

- `Finding` gains a derived `receipt_tier: int | None` field, round-tripped by `to_dict`/
  `from_dict` and declared in `finding.schema.json` (optional, not required). Task 3 stamps
  the value; this task only adds it to the shared vocabulary.

## 0.11.0 - 2026-08-15

### Added

- `evidence.py` exports a shared receipt-tier and status vocabulary: `TIER1_RECEIPTS`/
  `TIER2_RECEIPTS` (partitioning `_MECHANICAL` into confirms-alone vs locates-only sources),
  `SHIPPING_STATUSES`, `RUNTIME_DISPOSITIONS`, and the `receipt_tier()`/`confirms_alone()`
  predicates, giving later modules one source of truth for whether a source can confirm a finding
  alone.

## 0.10.1 - 2026-08-15

### Fixed

- The `audit` CLI no longer calls `begin_pass` on every invocation (C1). It was wiping
  `state.stages` and bumping `pass_number` on each re-invocation, livelocking the six
  `findings_dir`-in/out agent phases (investigate, critic, judge, validate, trace, patch) that
  rely on the orchestrator's manual `record_stage` between calls. Pass lifecycle is now owned
  solely by the campaign supervisor, matching the `scan` path.
- `run_audit`'s investigate/patch branch now raises `PhaseHalt` instead of crashing with
  `FileNotFoundError`/`JSONDecodeError` when `kb/scan-profile.json` is absent or malformed.

## 0.10.0 - 2026-08-15

### Added

- `run_audit` passes the reconciled attack-class set to the `patch` phase's dispatch, matching `investigate` (ISSUE-050). A multi-class run's patch dispatch previously fell through to the classless `render_dispatch(phase, ctx)` call and carried no `{{ATTACK_CLASS}}` line at all.

### Fixed

- Corrected the `begin_pass` signature and increment condition in `SKILL.md` and `CLAUDE.md` (ISSUE-002): `begin_pass(ws: Workspace, sha: str | None) -> CampaignState`, incrementing the pass counter only after a prior pass recorded a stage.

## 0.9.0 - 2026-08-15

### Added

- Wire `redactor.safe_for_prompt` and `factcheck.apply_verdict` into the driver (ISSUE-047, ISSUE-051). `render_dispatch` now passes its composed block through `safe_for_prompt` before returning, so no agent dispatch can carry a high-confidence secret. A new deterministic `factcheck` phase between `trace` and `calibrate` applies verdicts from an optional `kb/verdicts.json`, no-oping silently until Plan B's fact-check agent writes one.

## 0.8.0 - 2026-08-15

### Added

- `verify_findings` now routes a `static-only` re-verify to `needs-deployment-testing` instead of leaving the finding `confirmed` (ISSUE-053) — a finding `verify` cannot dynamically confirm no longer implies a dynamic check passed. `verified-static` still promotes to `fixed`; `not-fixed`/`verify-error` are unchanged.

## 0.7.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.unrouted_triage_dispatch`: a general-triage dispatch block naming any candidate class `agents_to_spawn` doesn't route (e.g. `security-other`), with its candidate count, or `None` when every class is routed.
- Widen `render_dispatch` with an optional `classes=` kwarg, emitting a `{{ATTACK_CLASS}}` line for the investigate phase's reconciled attack-class list.
- `run_audit`'s `investigate`-phase dispatch now reconciles `agents_to_spawn` via `partition.reconcile_plan` (recon-omitted classes) and appends `unrouted_triage_dispatch`'s block after the investigate dispatch when a class remains unrouted.

### Fixed

- `render_dispatch` now raises `ValueError` when called on a deterministic phase (`prompt is None`) instead of printing `agents/None.md`.

## 0.6.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.run_audit`: the resumable table-walker that runs deterministic phases in place, auto-advances agent phases only on a distinct (non-shared) output, and returns the next dispatch or `"AUDIT COMPLETE"`.
- Register `DETERMINISTIC_ACTIONS` for `prefilter`, `findings-gate`, `dedupe`, `calibrate`, `verify`, `demote-noise`, `report`, and `selfscore`.
- Add the `audit` CLI subcommand (`python -m sec_overlay.cli audit --target <T> --config <rules>`).

## 0.5.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.render_dispatch`: a deterministic, side-effect-free printer that names an agent phase's `agents/<prompt>` file and the `{{TARGET}}`/`{{WORKSPACE}}`/`{{SHA}}` substitutions the orchestrator must apply.

## 0.4.0 - 2026-08-15

### Added

- Add `sec_overlay.driver`: `run_deterministic_phase` gates a `PhaseSpec` on inputs/outputs, runs its registered `DETERMINISTIC_ACTIONS` entry, and records the stage — raising `PhaseHalt` when an input or output artifact is missing.

## 0.3.0 - 2026-08-15

### Added

- Add `sec_overlay.phases`: a frozen, ordered `PhaseSpec` table (`PHASE_TABLE`) and pure sequencer helpers (`missing_inputs`, `outputs_present`, `next_actionable_phase`) for the audit driver.

## 0.2.1 - 2026-08-14

### Changed

- Split the plugin documentation by audience: maintainer manual at the plugin root, trimmed skill CLAUDE.md focused on running the harness, and a SKILL.md pointer to it.
- Fix the README quick-start command to `cd` into `skills/sec-overlay/helpers` (the README sits at the plugin root, not inside `helpers`), and note the `${CLAUDE_PLUGIN_ROOT}` path for an installed plugin.

## 0.2.0 - 2026-08-12

### Changed

- Default SARIF output to suppressed-full and populate driver.rules.

### Added

- Add systemic finding clustering, per-run self-score, and run-economics report section.
- Add external-boundary disposition: risk cap, ingested-package scope check, lead bucket.

## 0.1.0 - 2026-08-11

### Added

- Initial release: agentic security-audit harness (SAST prefilter, multi-agent gate ladder, SARIF + Markdown reports).
