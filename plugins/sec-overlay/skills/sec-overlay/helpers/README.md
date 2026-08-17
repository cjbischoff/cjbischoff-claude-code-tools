# `helpers/` — the deterministic Python core

This folder is the **machine** of the harness. If [`../agents/`](../agents/) is the
judgement (LLM prompts) and [`../references/`](../references/) is the rule book, `helpers/`
is everything that runs: it invokes the SAST tools, parses their output, moves findings
through the pipeline, enforces the gates that no LLM is trusted to enforce, and writes the
final SARIF + Markdown reports.

Two facts define this code and are true of every module here:

1. **It never runs or edits the reviewed source.** Static analysis only. Patches are applied
   to a throwaway *copy* to verify them; the target's own files are never executed or written.
2. **The core is stdlib-only.** `pyproject.toml` has **no runtime dependencies** — only dev
   deps (pytest, ruff, ty). External SAST binaries (semgrep, codeql, osv-scanner, ast-grep)
   are optional backends the code *shells out to*, not Python imports. Do not add a runtime
   dependency without a strong reason and user sign-off.

```
helpers/
├── pyproject.toml            stdlib-only; dev deps pytest/ruff/ty; line-length 100
├── sec_overlay/              ~70 modules — the pipeline (this README's main subject)
│   └── correlate/            cross-repo correlation subpackage (11 modules)
├── bench/                    dev-only detection benchmark — see bench/README.md
├── tests/                    95 pytest files (828 tests)
├── fixtures/                 golden JSON + a deliberately vulnerable_repo/ for tests
└── rules/                    vendored semgrep rules (git submodule) + smoke.yaml
```

---

## How to run it (development)

All commands run **from this `helpers/` directory**:

```bash
uv run pytest -q                                 # full suite (2 env-only failures — see skill CLAUDE.md §1)
uv run pytest tests/test_calibrate.py -q         # one file
uv run pytest tests/test_x.py::test_name         # one test
uv run ruff check sec_overlay/ bench/ tests/     # lint
uv run ruff format sec_overlay/ bench/ tests/    # format
uv run ty check                                  # static types
uv run python -m sec_overlay.preflight           # check which SAST backends/packs are installed
```

The quick end-to-end smoke scan (no agents, deterministic only):

```bash
uv run python -m sec_overlay.cli scan \
  --target <path-to-code> --workspace <out-dir> \
  --config rules/smoke.yaml --sha "$(git -C <path-to-code> rev-parse HEAD)"
```

---

## The pipeline these modules implement

The modules are not a flat bag of utilities — they run in a definite order during an audit.
This is the deterministic spine; the LLM agents plug in between the deterministic steps.

```mermaid
flowchart TD
    PF["preflight.py<br/>tools present?"] --> SS["scanscope.py<br/>pin repo_root + scan_scope"]
    SS --> GR["graph.py build<br/>Tier-1 substrate (LLM-free)"]
    GR --> CTX["context.py<br/>ingest repo docs"]
    CTX --> PROFILE["profile.py<br/>ScanProfile from recon"]
    PROFILE --> PRE["prefilter.py<br/>run semgrep+codeql+sca+secrets concurrently"]
    PRE --> NORM["normalize.py<br/>dedup, assign F-#### ids"]
    NORM --> PART["partition.py<br/>group candidates by attack class"]
    PART --> INV(("investigate agents<br/>(../agents/)"))
    INV --> DED["dedupe.py<br/>refactor-resistant fingerprint"]
    DED --> CLUS["cluster.py<br/>systemic clustering (≥3 same-class/sink)"]
    CLUS --> GATE1["findings_gate.py<br/>schema + tool-receipt gate"]
    GATE1 --> LADDER(("critic / judge / validate agents"))
    LADDER --> CAL["calibrate.py<br/>risk_score 1–10"]
    CAL --> CIT["citations.py<br/>attach ASVS/CodeGuard"]
    CIT --> PATCHV(("patch / validate-fix agents"))
    PATCHV --> VER["verify.py<br/>apply patch to COPY, re-scan"]
    VER --> GATE2["findings_gate.py"]
    GATE2 --> RT(("redteam agents")) --> RTR["redteam.py<br/>render redteam-plan.md"]
    RTR --> REP["report.py<br/>report.sarif + report.md"]
    REP --> POST["postflight.py<br/>prior_context.json (durable)"]
```

Every deterministic step records completion with `campaign.record_stage(ws, "<phase>")` so an
interrupted run can resume, and multi-pass campaigns know what's already done.

---

## `sec_overlay/` — module map, grouped by job

~70 modules. Grouped so you can find the one you need. Each line is *module → what it does.*

### Data model & serialization — the finding contract
| Module | Purpose |
|--------|---------|
| `models.py` | The `Finding` and `CampaignState` dataclasses, the `Severity` / `FindingStatus` enums, and `to_dict`/`from_dict`. **This is the schema every phase reads and writes.** Recent: `open_questions` field added (list of dicts with `question`, `why_it_matters`, `who_to_ask_or_check` keys; defaults to []) — unrelated to `coverage_ledger.py`'s same-named, differently-shaped `open_questions` list. |
| `evidence.py` | The tool-receipt gate. `_MECHANICAL` = {semgrep, codeql, ast-grep, tree-sitter, ripgrep, structural-index, secrets, sca}; `is_tool_receipt()` returns False for anything `llm`-prefixed; `confidence_for()` grades HIGH/MEDIUM/LOW from the strongest evidence link. |
| `schema.py` | A tiny stdlib-only JSON-Schema validator (type/enum/required/items/properties) — so schema validation needs no dependency. |

> **These two (`models.py`, `evidence.py`) define the finding serialization/schema contract.**
> Change a `Finding`/`CampaignState` field or the `_MECHANICAL` set and you must update
> `../references/finding.schema.json` and keep `tests/test_contracts.py` and
> `tests/test_finding_schema.py` green.

### SAST backends & prefilter
| Module | Purpose |
|--------|---------|
| `sast.py` | Run semgrep; map its JSON to `Finding`s. |
| `codeql.py` | Build/analyze a CodeQL DB; parse SARIF; **trust-gate** dangerous extractor/build-hook configs (`codeql_config_trusted`). A missing query pack silently drops that language's dataflow coverage (run `preflight` to verify all packs are installed). |
| `sca.py` | Software-composition analysis via `osv-scanner` on lockfiles. |
| `secrets.py` | Offline distinctive-token secret patterns (github/slack/aws/…); one finding per hit. Also backs the redactor. |
| `prefilter.py` | Orchestrates the above **concurrently**, merges deterministically (sorted, `C-<PREFIX>-####` ids numbered per attack class via `_assign_candidate_ids`), applies exclusions, and is **never-silent**: every planned backend ends up in `backends_run` / `skipped` / `failed` with a reason. |
| `exclusions.py` | Evidence-backed noise-floor rules (rule_ids/globs/classes), each with a `reason`; drops are logged, never silent. |

### Attack-class routing & compliance knowledge
| Module | Purpose |
|--------|---------|
| `clsmap.py` | Single source of truth mapping CWE / semgrep metadata → attack-class key (prevents typos & orphaned findings). |
| `detection_coverage.py` | Generates `references/DETECTION_COVERAGE.md` from the live `clsmap` so the coverage doc can't drift. |
| `rule_matcher.py` | Deterministic ASVS 5.0 + CodeGuard pre-filter — attaches advisory IDs, not tool receipts. |
| `asvs.py` / `codeguard.py` | Load the ASVS JSON / CodeGuard checklists from [`../references/`](../references/). |
| `citations.py` | Auto-attach ASVS + CodeGuard citations to findings (deterministic). CLI-callable. |
| `custom_checks.py` | Discover in-repo `.sec-overlay/checks/` custom-check bundles a target ships. |

### Graph & structural substrate (the "where does this reach?" engine)
| Module | Purpose |
|--------|---------|
| `graph.py` | The two-tier code graph. **Tier-1** (LLM-free): definitions + one-hop call edges + osv/secrets/crypto facts. **Tier-2**: post-prefilter CodeQL/semgrep taint merged in. Answers reachability / attacker-control / `no_path`. Persisted to `kb/graph.json`. CLI-callable. |
| `structural_index.py` | Ripgrep-backed symbol index (definitions, callers, function boundaries). CLI-callable. |
| `entrypoints.py` | Regex classification of routes / user-input / CLI args / env vars to seed Tier-1. |
| `astgrep.py` | ast-grep availability check + structural-search wrapper. CLI-callable. |
| `reachability.py` | Reachability verdict + blocker taxonomy (sanitizer/auth/validation/dead-code/flag) — the static-vs-runtime discriminator. |

### False-positive reduction & finding identity
| Module | Purpose |
|--------|---------|
| `normalize.py` | Dedup `(file, line, cls)`, keep the highest-severity survivor, assign stable `F-####` ids. |
| `dedupe.py` | Active-finding dedup; stamps the **refactor-resistant fingerprint** so a finding survives line-shift refactors across passes. CLI-callable. |
| `fingerprint.py` | The fingerprint itself: `sha256(rule_id\|cls\|enclosing-symbol)`, degrading to file:line if no symbol. |
| `cluster.py` | Groups ≥3 same-class, same-sink `raw` findings into one systemic cluster: elects a primary (highest severity, tiebreak smallest id), stamps `cluster_id` on every member, and records all member sites on the primary's `affected_sites`. Runs after dedupe, before the critic/gate ladder. CLI-callable. |
| `findings_gate.py` | Schema-validates every finding; forbids `raw`+`duplicate_of` collisions; **enforces the tool-receipt bar** for `confirmed`/`fixed`. CLI-callable. |
| `partition.py` | Group candidates by attack class for parallel agent fan-out. |
| `fp_feedback.py` | Recycle prior-pass rejections into the next pass's investigate/critic prompts as negative examples. |
| `factcheck.py` | Post-investigation re-verification of citations/scope/severity against source. |
| `phase_gate.py` | Deterministic pre-check for analysis phases (schema + `file:line` resolution) before the opus adversary runs; writes `kb/gates/<phase>.json`. Detects comment-only citations via `is_comment_line()` and appends a gate note flagging them for extra scrutiny (prose files — `.md`/`.rst`/`.txt` — are skipped, since every Markdown heading would otherwise read as a comment); the comment check and the basename-fallback note are independent, so a sloppy citation can raise both. Also `review_position_gate(findings, hunks_by_path)` — the diff-pipeline gate: keeps a finding only when `positioning.resolve_position` calls it `exact`, else drops it with an `OUTSIDE_DIFF_REASON`-shaped `DroppedFinding`. Audit-mode symbols above are unchanged by this addition. |
| `stage_validate.py` | Per-stage structured-output validation + repair contract. |

### Scoring & prioritization
| Module | Purpose |
|--------|---------|
| `calibrate.py` | Deterministic 1–10 `risk_score` for confirmed / needs-deployment-testing findings (severity base map + class boost + baseline cap + precondition gates). CLI-callable. |
| `cvss.py` | CVSS v4.0 base-score from a vector (MacroVector model ported from FIRST's official calculator — **never** LLM arithmetic) + an orthogonal offensive-priority axis. |
| `scoring.py` | Weighted fix-validation score (root_cause, scope_verified, …); regression is non-waivable. |
| `fix_disposition.py` | Conservative fix-completeness tier (FULL / MITIGATION / WORKAROUND); ambiguity → LLM_REVIEW. |
| `crypto_policy.py` | Machine-checked crypto policy from the two `references/approved-*.yaml` files (deny md5/sha1/des/ecb; floor rsa≥3072/pbkdf2≥600000/…). |
| `selfscore.py` | Per-run self-score: counts findings by status (`reported`, `confirmed`, `needs_runtime`, `rejected`), plus `clusters` and `external_boundary` (both read defensively via `getattr`/`.get`, since `cluster_id` and `reachability.blocker` are populated by later phases). Persisted to `CampaignState.budget["self_score"]`. CLI-callable. |

### Reporting
| Module | Purpose |
|--------|---------|
| `report.py` | Assemble the final `report.sarif` + `report.md`. Structure: bottom-line count block (confirmed counts rendered in words, e.g. `1 critical, 1 high, 2 medium, 1 low`, never as digit ratios; zero counts omitted, `none` when all zero; + NDT count, never merged) → risk-ordered `## Triage` table (`_triage_row`: id/risk/what/location/status/action; the `what` clip splits on period-space so semver like `decompress@4.2.1` survives) → `## Needs runtime proof — the real leads` (NDT via `render_ndt`, which renders `expected_signal` through the shared `render_util.signal_lines` — tolerant of a bare-string value, foregrounded above confirmed) → `## Confirmed (source-provable)` (via `render_finding`; deps get dep-view, condensed medium/low numbered 1–4 with no gaps) → coverage/redteam-link/ledger/token-spend tail. NDT is never counted as confirmed. `_risk_sort_key` (risk desc → severity → id) orders triage, confirmed, NDT, and `select_reportable` identically. CLI-callable. |
| `sarif.py` | Emit valid SARIF 2.1.0; map severity → SARIF level. `_rules()` builds a de-duplicated `driver.rules` array (one entry per `rule_id`, first occurrence wins) carrying `cls` as `name` and `asvs_ids`/`codeguard_ids` as `properties` — additive to `driver.rules`, `results` unchanged. |
| `render_util.py` | Shared markdown fragments for the two finding renderers. `signal_lines()` is the single source of truth for rendering an agent-authored `expected_signal` (dict `{secure, insecure}`, bare string, or None) into labeled bullet lines; a bare string is treated as the insecure signal everywhere it is rendered. |

### Diagram generation & gate
| Module | Purpose |
|--------|---------|
| `mermaid_index.py` | Line-oriented Mermaid structure extraction (not a grammar): `index_mermaid(text) -> DiagramIndex` pulls node ids/labels, edges + edge labels, subgraph membership, sequence participants/message count, and C4 element macros out of a flowchart/sequence/C4 diagram. `store_ids` marks orphan-exempt required shapes (data-stores, queues, `Person`/`*_Ext` actors); unrecognizable input raises `ValueError`. |
| `diagram_gate.py` | Deterministic hard gate over generated diagrams: `CAPS`/`SEQ_CAPS` node/participant/message ceilings, ≤4-word edge labels, ≤4-word node labels (bare-id nodes with no bracket label exempt), DFD trust-boundary-subgraph requirement, derivation provenance (`%% derived-from: <file> sha256:<hash>` — a derived diagram introduces no element/participant absent from its source, and the hash must match the current source), legend-required styling, and orphan-detail nodes (a node that only ever receives, never sends, and isn't a store/actor). The orphan check applies only to `container`/`component`/`dfd` — never `context` (context actors are by definition often degree-1) or `sequence`. `run_diagram_gate(arch_dir, tm_dir, *, require_threat_model=False)` walks an architecture/threat-model tree end to end; `require_threat_model=True` turns a missing `dfd.mmd` into a gate error instead of a silent skip. CLI-callable. |
| `ste_lint.py` | Deterministic linter for the checkable structural subset of ASD-STE100: sentence length, semicolons, paragraph size, plus warning-level noun-cluster and buried-sequence heuristics. Lexical rules are directional/unenforced — flagged with a front-matter statement instead. Code fences, mermaid blocks, headings, table structure, inline code, and URLs are exempt; table free-text cells are linted. `lint_prose(text) -> (errors, warnings)`. CLI-callable. |

### Campaign, state & per-repo memory
| Module | Purpose |
|--------|---------|
| `campaign.py` | Multi-pass supervision: `record_stage`, `pass_report`, `carry_forward` (re-check settled findings on changed files). |
| `state.py` | Load/save `CampaignState`; `begin_pass` pins the SHA and increments the pass counter. |
| `phases.py` | The ordered phase table (`PhaseSpec`, `PHASE_TABLE`) + pure sequencer helpers (`missing_inputs`, `outputs_present`, `next_actionable_phase`) the audit driver walks. `architecture` now outputs `arc42.md` + `container-diagram.mmd` (not `kb/architecture.md`) followed by the deterministic `arch-gate` row; `threat_model` outputs `threat-model.md` + `dfd.mmd` followed by `tm-gate`. |
| `driver.py` | The audit sequencer: deterministic-phase runner, loud halt, agent-dispatch printer. `run_deterministic_phase` gates a `PhaseSpec` on inputs/outputs, runs its `DETERMINISTIC_ACTIONS` entry, then `record_stage`s it — raising `PhaseHalt` on either gate. `_act_arch_gate`/`_act_tm_gate` run `diagram_gate.run_diagram_gate` + `ste_lint.lint_prose` (and, for `tm-gate`, `artifact_gate.check_duplication`), writing `kb/gates/arch-gate.json` / `kb/gates/tm-gate.json`; `tm-gate` alone passes `require_threat_model=True` so a missing `dfd.mmd` halts the run. |
| `repo_memory.py` | The per-repo sidecar (`<target>/.sec-overlay/<slug>/`): workspace, `MEMORY.md`, dated `learnings/`, run status for resume. |
| `workspace.py` | The on-disk layout (`kb/`, `findings/`, reports, `artifacts/` review-mode run state); per-finding read/write; `record_agent_return` / `read_agent_return`. |
| `scanscope.py` | Resolve + pin `repo_root` + `scan_scope` once per campaign (monorepo-safe); `kb/scan-scope.json`. |
| `scope.py` | `is_external_package(pkg, ws)` reads `kb/scan-scope.json`'s `ingested_packages` list to decide whether a sink's package was scanned; `True` only when a manifest exists and excludes `pkg`, so the check never invents a boundary when no manifest is present. |
| `kb.py` | Paths to the KB files (profile/architecture/threat-model/entities). |
| `context.py` | Deterministic context ingestion (docs/specs/runbooks + prior scans), trust-tagged. Also discovers IaC/deployment-config files (Pulumi, Terraform, Helm, k8s, docker-compose, serverless) as `deployment_config` items, carrying a `deployed_in` env tag. `Context.diagram` holds the C1 agent's claimed-control status map (a raw mermaid block); `render_markdown` writes it into `CONTEXT.md`, which is regenerated on every `save()` and never hand-edited. |
| `profile.py` | The `ScanProfile` contract; validate/load `kb/scan-profile.json`. |
| `diffscope.py` | `changed_files(base, head)` — scope incremental passes to changed code. Also the diff-pipeline ref/file layer: `validate_ref`/`resolve_ref_sha` (reject a leading-dash or empty ref before it reaches git as an option, allow `HEAD~1`-style ancestor refs, then resolve to a SHA so every later call in a run is pinned — no ref-repoint TOCTOU window), `changed_file_records`/`file_diff_text` (full status+path vocabulary including renames/copies with `old_path`, and per-file unified diff text, between two resolved SHAs), and `file_diff_line_count`/`binary_paths` (per-path diff size and the binary-file set, feeding `file_select.partition`'s size cap and binary check). |
| `githist.py` | Mine git history for likely security-fix commits to seed recon/context. |
| `postflight.py` | Distill a finished scan into durable `kb/prior_context.json` (accretes, drift-keyed by SHA). CLI-callable. |

### Coverage & completeness
| Module | Purpose |
|--------|---------|
| `coverage.py` | Per-language SAST coverage accounting (dataflow vs pattern-only vs none). |
| `coverage_ledger.py` | The machine-checked completeness ledger — refuses `completeness=="complete"` while any surface `needs_follow_up`/`deferred` or open questions remain. |
| `coverage_guide.py` | Auto-stop condition for multi-pass campaigns (coverage-complete AND yield-below-threshold). |
| `discovery_ledger.py` | Loop-until-dry saturation state: stop after K consecutive waves add no new fingerprints. |
| `route_control.py` | One route-to-control table from `kb/scan-profile.json`; checks recon/architecture/threat-model output against it, logging a `needs_follow_up` gap (never dropping) via `record_route_gaps` into `coverage-ledger.json`. |

### Diff-scoped review (`sec-overlay review` — tracer path)
| Module | Purpose |
|--------|---------|
| `diffhunks.py` | `parse_hunks(diff_text)` — walk a unified diff into `Hunk` records (added/deleted/context lines, new-side range); `added_line_numbers(hunks)`; `line_in_hunk(hunks, line)`. |
| `file_select.py` | `partition(records)` — split `diffscope.ChangedFile` records into `reviewable` and `excluded` (deleted / not-allowlisted, from the closed `EXCLUSION_REASONS` vocabulary). Path-shaped, not finding-shaped: never imports `Finding` — deliberately distinct from `exclusions.py`, which filters findings. Tracer scope only: a minimal `ALLOWED_EXTENSIONS`, no glob-based "generated" exclusion, no diff-line size cap — the full OCR allowlist and size cap land in a later plan. |
| `positioning.py` | `resolve_position(claimed_path, claimed_line, hunks_by_path)` — confirm or decline a finding's claimed position against the diff. Never imports the stdlib sequence-matching helper: a fuzzy match presented as an exact location is the defect this module exists to prevent. Declines to `needs-position-review` rather than approximating; the relocation ladder lands later. |
| `review_coverage.py` | `CoverageManifest` — per-file review coverage (`pending` → `in_review` → `done`/`failed`) persisted to `artifacts/coverage_manifest.json` after every transition. `seal()` returns `complete` only when every entry is `done`, `partial` when some are `failed`, and **raises** `CoverageTransitionError` if any entry is still `pending`/`in_review` — a run must never claim coverage it did not perform. Separate from the shipped `coverage.py`; only this class edits the manifest JSON. |

---

## Test coverage & contracts

The `tests/` folder houses 95 files, 828 tests. Key structural guards:
- `test_docs_invariants.py` enforces documentation contracts: prompt-constants block presence, `finding-template.md` sections (triage line, NDT-view, dep-view, reachability, renumber), and agent prompt rules (determinism, tool receipt trust, evidence chains). Regression-tested so template drift is caught early.

### Hunting aids & tuning
| Module | Purpose |
|--------|---------|
| `variant.py` | Turn a confirmed finding into deterministic search seeds for sibling call sites. |
| `bugchain.py` | Link confirmed findings that share a file/dataflow node for the chaining agent. CLI-callable. |
| `novelty.py` | Cheap git-only upstream-fix check (FIXED/UNFIXED/UNKNOWN) — no execution. |
| `rule_gaps.py` | Flag confirmed findings that no detection rule caught (hunting-only) to feed rule authoring. CLI-callable. |
| `tuning.py` | Adaptive-tuning scoreboard (did a re-tuned config strictly improve the confirmed set?). |

### Verification, safety & plumbing
| Module | Purpose |
|--------|---------|
| `verify.py` | Apply a `patch_diff` to a **temp copy**, re-scan, confirm the finding is gone. Never touches the real target. A `deps`-class patch that only bumps to an obviously non-functional placeholder version (e.g. `vX.Y.Z`) is rejected as `not-fixed` before the re-scan even runs (`_placeholder_version_bump`) — an SCA re-scan can't tell "real fix" from "text that no longer matches the old version string." `verify_findings` also never silently overwrites an explicit `validate-fix:not_fixed`-family verdict on a `CONFIRMED` finding: if the deterministic re-scan disagrees (says `verified-static`), it appends a `verify:conflict` history event (once — a re-run does not duplicate it) and leaves status/verification untouched for human review, instead of promoting to `FIXED`. The guard is deliberately broad: **any** `validate-fix:*` event other than `validate-fix:fixed` blocks promotion, `validate-fix:unverifiable` included — a verify-error is never laundered into a clean verdict. CLI-callable. |
| `patch_status.py` | Deterministic check: is a patch actually applied to the real target vs only verified in isolation? |
| `preflight.py` | Verify SAST binaries + vendored rules + CodeQL packs; print exact setup commands for what's missing (never installs). CLI-callable. |
| `redactor.py` | Three-step secret redaction before any prompt send: mask → hard-verify no residual HIGH-confidence secret → **abort** if any remain. CLI-callable. |
| `envelope.py` | Nonce-delimited wrapper for untrusted repo text inlined into prompts (injection-resistant). *(`import secrets` here is the stdlib module, unrelated to `secrets.py`.)* |
| `redteam.py` | Render `redteam-plan.md` from findings marked `needs-runtime`, filtered by risk bar; includes markdown renderers `_bullets()` and `_signal()` for runtime directives (both accept list/dict *or* plain-string `runtime_test` values); `_signal()` delegates to the shared `render_util.signal_lines`, so a bare-string `expected_signal` renders as an `**insecure:**` bullet — the same shape `report.py` uses; `_question_block()` renders `open_questions` from all statuses (plan + below-bar + static-settled) into a "Questions to ask" section. The "static-settled" footer counts `disc["static_settled"]` (not the needs-runtime code-settled subset). CLI-callable. |
| `parse.py` | Fail-open JSON extraction from LLM prose/fences (largest balanced substring); returns None, never a silent empty. |
| `gates.py` | Fail-closed gate orchestrator: a `GATE_ROUTING` table + `REQUIRED_GATES`; a missing gate result hard-fails. |
| `cost.py` | Per-phase and per-model token accounting into `CampaignState.budget` (`aggregate_by_phase`, `aggregate_by_model`); USD is an opt-in estimate (`estimate_cost_usd`), never rendered as measured. Also records per-phase wall-clock duration (`record_timing`, `aggregate_timings_by_phase`). Feeds `report.py`'s "Run economics" section. |
| `scanscope.py` / `normalize.py` | (listed above) |

### `sec_overlay/correlate/` — cross-repo correlation (a product spans many repos)
When one product is several repos (an RBAC source, a service that enforces it, infra), a
per-repo scan can't see a control that lives in a *different* repo. This subpackage joins N
completed per-repo scans, deterministically, with **no source reads and no LLM**:

| Module | Purpose |
|--------|---------|
| `ingest.py` | Read each member repo's sidecar findings, tagged with a `member_key`. |
| `manifest.py` | The product's member list + each member's role. |
| `edges.py` | Deterministic cross-repo edges: shared-dependency (same CVE), same-class-recurrence, control-enforces. |
| `rethreshold.py` | Re-decide an out-of-repo "blocked" barrier using another member's evidence → promote / demote / coverage-gap. |
| `artifacts.py` / `mermaid.py` | Code-authored combined mermaid graphs + tables (the LLM only fills narrative slots). |
| `xrepo_sarif.py` | Multi-run SARIF (one run per member + a correlation run). |
| `workspace.py` / `cli.py` / `__main__.py` | Correlation workspace + `python -m sec_overlay.correlate` entry. |

---

## CLI-callable modules (`python -m sec_overlay.<module>`)

Seventeen modules expose a command line (they have a `__main__`). These are the deterministic
steps the orchestrator calls between agent phases:

| Module | Command does |
|--------|--------------|
| `cli` | `scan` (deterministic prefilter → SARIF/MD), `memory` (status / append a learning), `audit` (deterministic audit driver), and `review --base <ref> --head <ref> --root <path>` (diff-scoped, position-verified review pass — tracer path, one changed file end to end). |
| `preflight` | Report which SAST tools + CodeQL packs are installed; print setup commands. |
| `graph` | Build/query the Tier-1/Tier-2 code graph → `kb/graph.json`. |
| `structural_index` | Build the ripgrep symbol index. |
| `astgrep` | ast-grep availability + structural search. |
| `dedupe` | Mark duplicates + stamp fingerprints. |
| `cluster` | Group ≥3 same-class, same-sink `raw` findings into one systemic cluster. |
| `findings_gate` | Schema + tool-receipt gate over `findings/*.json`. |
| `calibrate` | Assign 1–10 risk scores. |
| `citations` | Attach ASVS/CodeGuard citations. |
| `bugchain` | Link confirmed findings for chaining. |
| `rule_gaps` | Flag hunting-only findings. |
| `verify` | Apply a patch to a copy + re-scan. |
| `redteam` | Render `redteam-plan.md`. |
| `diagram_gate` | Hard-check generated Mermaid diagrams against caps, provenance, and orphan-detail rules. |
| `ste_lint` | Lint markdown prose against the checkable ASD-STE100 structural rules. |
| `report` | Assemble final SARIF + Markdown. |
| `redactor` | Mask/verify secrets in a text blob. |
| `postflight` | Write durable `kb/prior_context.json`. |

---

## The two invariants, in code

```mermaid
flowchart LR
    subgraph TR["Tool-receipt gate (evidence.py + findings_gate.py)"]
        E1["evidence_sources: ['codeql:dataflow']"] -->|is_tool_receipt=True| CONF["may become confirmed"]
        E2["evidence_sources: ['llm-claimed:reasoning']"] -->|is_tool_receipt=False| NOCONF["cannot confirm — corroborates only"]
    end
```

- **A finding reaches `confirmed`/`fixed` only with ≥1 mechanical receipt.** LLM reasoning is
  namespaced `llm-claimed:` and can corroborate but never confirm. Gate lives in
  `findings_gate.py`; the whitelist in `evidence.py:_MECHANICAL`.
- **Never-silent backends.** `prefilter.py` accounts for every planned backend. A backend
  that errored or whose CodeQL pack is missing is a *coverage hole*, surfaced explicitly —
  not "no findings." `test_wiring.py` regression-tests this.

---

## `tests/` and `bench/`

- **`tests/`** — 78 files, 575 tests, deterministic. Two are structural guards worth
  knowing: `test_contracts.py` catches **prompt↔schema drift** (a Finding JSON example in an
  agent prompt must parse against the real `models.py`), and `test_wiring.py` catches
  **silent-backend / clsmap / dead-link regressions**. Two failures on a clean checkout are
  *environmental* (gitignored bench corpus, excluded semgrep submodule) — see skill
  [`CLAUDE.md`](../CLAUDE.md) §1, do not "fix" them by committing the missing data.
- **`bench/`** — the dev-only detection benchmark (precision/recall on a labelled corpus +
  regression lock). **Not part of an audit run.** Its own docs: [`bench/README.md`](bench/README.md).

**When a module here changes, update this README's module map in the same commit** — enforced
by the repo pre-commit hook (plugin [`CLAUDE.md`](../../../CLAUDE.md), "Documentation" section).
