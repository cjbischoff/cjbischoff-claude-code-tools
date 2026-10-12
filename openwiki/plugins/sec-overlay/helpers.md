---
type: architecture-overview
title: sec-overlay Deterministic Python Core (helpers/)
description: The stdlib-only Python modules that run SAST tools, enforce the tool-receipt gate, generate and gate diagrams, score CVSS v4.0 risk, and assemble the SARIF and Markdown reports for the sec-overlay harness.
tags: [sec-overlay, helpers, python, tool-receipt-gate, cli]
---

# helpers — the deterministic Python core

If [`agents/`](agents.md) is the judgement and [`references/`](references.md) is the rule book,
[`helpers/`](/plugins/sec-overlay/skills/sec-overlay/helpers/) is everything that *runs*: it
invokes the SAST tools, parses their output, moves findings through the pipeline, enforces the
gates no LLM is trusted to enforce, and writes the final SARIF + Markdown reports.

Two facts are true of every module here:

1. **It never runs or edits the reviewed source.** Static analysis only. Patches are applied to
   a throwaway *copy* to verify them; the target's own files are never executed or written
   (the opt-in `prove` phase is the one exception — see [overview](overview.md#the-four-invariants)).
2. **The core is stdlib-only.** `pyproject.toml` declares **no runtime dependencies** — only dev
   deps (`pytest`, `ruff`, `ty`). External SAST binaries (semgrep, codeql, osv-scanner,
   ast-grep) are optional backends the code shells out to, not Python imports. Adding a runtime
   dependency needs a strong reason and user sign-off (see
   [developing the skill](developing-the-skill.md)).

```
helpers/
├── pyproject.toml       stdlib-only; dev deps pytest/ruff/ty; line-length 100; Python floor >=3.12
├── sec_overlay/         ~95 modules — the audit pipeline + the diff-review track (this page's main subject)
│   └── correlate/       cross-repo correlation subpackage — see cross-repo-correlation.md
├── bench/               dev-only detection benchmark
├── tests/               98 pytest files, 954 tests
├── fixtures/            golden JSON + a deliberately vulnerable test repo (excluded from this wiki)
└── rules/               vendored semgrep rules (gitignored shallow clone) + the first-party absence/ pack + smoke.yaml
```

## The pipeline these modules implement

```mermaid
flowchart TD
    PF["preflight.py<br/>tools present?"] --> SS["scanscope.py<br/>pin repo_root + scan_scope"]
    SS --> GR["graph.py build<br/>Tier-1 substrate, LLM-free"]
    GR --> RCEN["route_census.py<br/>code-derived route inventory"]
    RCEN --> CTX["context.py<br/>ingest repo docs + IaC configs"]
    CTX --> PROFILE["profile.py<br/>ScanProfile from recon"]
    PROFILE --> PRE["prefilter.py<br/>run semgrep+codeql+sca+secrets concurrently"]
    PRE --> NORM["normalize.py<br/>dedup, assign F-#### ids"]
    NORM --> PART["partition.py<br/>group candidates by attack class"]
    PART --> INV(("investigate agents"))
    INV --> DED["dedupe.py<br/>refactor-resistant fingerprint"]
    DED --> CLUS["cluster.py<br/>systemic clustering"]
    CLUS --> GATE1["findings_gate.py<br/>schema + tool-receipt gate"]
    GATE1 --> LADDER(("critic / judge / validate agents"))
    LADDER --> TRACE(("trace agent<br/>reachability"))
    TRACE --> CAL["calibrate.py<br/>risk_score 1-10, CVSS v4.0"]
    CAL --> CIT["citations.py<br/>attach ASVS/CodeGuard"]
    CIT --> PATCHV(("patch / validate-fix agents"))
    PATCHV --> VER["verify.py<br/>apply patch to COPY, re-scan"]
    VER --> GATE2["findings_gate.py"]
    GATE2 --> RT(("redteam agents")) --> RTR["redteam.py<br/>render redteam-plan.md"]
    RTR --> REP["report.py<br/>report.sarif + report.md"]
    REP --> SCORE["selfscore.py<br/>post-gate counts back to state"]
    SCORE --> PROVE(("prove agent, opt-in<br/>repro out of tree"))
    PROVE --> AGATE["artifact_gate.py<br/>deterministic report self-check"]
    AGATE --> AREV(("artifact-review agent (opus)<br/>claim vs evidence over the report"))
    AREV --> ACON["artifact_consistency.py<br/>terminal cross-reference gate"]
    ACON --> POST["postflight.py<br/>prior_context.json (durable, final phase)"]
```
*The deterministic spine of the pipeline in [pipeline.md](pipeline.md); the LLM agents plug in
between the rectangles. Every step here records completion with
`campaign.record_stage(ws, "<phase>")`. The [diff-scoped review mode](review-mode.md) runs an
entirely different module set, listed on that page instead of here.*

## The tool-receipt gate

This is the mechanism behind the harness's core safety contract: **a finding reaches
`confirmed`/`fixed` only with at least one mechanical tool receipt.**

`helpers/sec_overlay/evidence.py` defines the whitelist:

```python
_MECHANICAL = {"semgrep", "codeql", "ast-grep", "tree-sitter", "ripgrep",
               "structural-index", "secrets", "sca", "dependency-catalog"}
```

`is_tool_receipt(source)` returns `False` for anything `llm`-prefixed and `True` only when the
source's colon-delimited prefix (e.g. `codeql` in `codeql:dataflow`) is in `_MECHANICAL`.
`as_llm_claim(source)` namespaces an LLM-asserted source as `llm-claimed:<source>` so it can
never masquerade as a receipt, and `confidence_for(sources)` grades a finding HIGH if any
source is a real receipt, MEDIUM if any is `llm-corroborated`, else LOW. `VERIFICATION_VALUES`
is the closed set for `Finding.verification` — `verified-static`, `static-only`, `not-fixed`,
`verify-error` — four values, not five: the deleted `factcheck` phase was the sole writer of a
fifth (`fact-checked`) value, removed with it.

`helpers/sec_overlay/findings_gate.py`'s `validate_findings(ws)` enforces this at the schema
level for every `findings/*.json` file: it parses each into a `Finding`, validates against
`references/finding.schema.json`, and — the safety-contract check — for any finding with
`status in ("confirmed", "fixed")`, requires `any(is_tool_receipt(s) for s in
f.evidence_sources)`; if none qualify, it emits an error naming the finding id and its actual
(non-qualifying) sources. It also forbids a `raw`/`confirmed` finding from carrying a
`duplicate_of` (that combination must be `status=duplicate` instead), and requires that a
finding whose `reachability.blocker` is `external-boundary` carry a complete `open_questions`
entry. The CLI (`python -m sec_overlay.findings_gate --workspace <WS>`) exits 1 if any error
exists — this runs after `investigate` (phase 10) and again after patch verification.

For SAST-unsupported languages, a `ripgrep:` receipt proving the sink literally exists is a
valid mechanical ground — the gate does not require semgrep/codeql specifically, only *some*
mechanical source. `dependency-catalog:<entry-id>` is a Tier-2 receipt only: it locates a sink
inside a declared dependency (see `dependency_sinks.py` below) but never confirms a finding
alone — it needs a paired Tier-1 receipt.

## The Finding / CampaignState schema contract

`helpers/sec_overlay/models.py` defines the `Finding` dataclass and `FindingStatus` /
`Severity` enums — the frozen contract every later phase reads and writes. Key lifecycle
statuses: `candidate → raw → confirmed/rejected → fixed`, plus the terminal
`needs-deployment-testing` (real-but-unprovable-from-source; never confirmed and never folded
into rejected) and `informational` (low-value vendored-rule hits, never re-run, never entering
the confirmed report). Notable fields: `evidence_sources` (namespaced, feeds the gate above),
`reachability` (the trace-phase verdict, `{reachable, blocker, chain}`), `runtime_disposition`
/ `runtime_test` (red-team phase output), `cluster_id` / `affected_sites` (set by
`cluster.py`), `cvss_vector` (CVSS v4.0, required for `confirmed` alongside a non-empty
`preconditions` list), and `open_questions` (human-answerable unknowns a live test can't
settle, populated by `trace`/`redteam` — unrelated to `coverage_ledger.py`'s differently-shaped,
same-named list).

**`models.py` and `evidence.py` together define the serialization/schema contract.** Changing a
`Finding`/`CampaignState` field or the `_MECHANICAL` set requires updating
`references/finding.schema.json` too, and keeping `tests/test_contracts.py` (prompt↔schema
drift: a `Finding` JSON example inside an agent prompt must parse against real `models.py`) and
`tests/test_finding_schema.py` green — see [developing the skill](developing-the-skill.md).

## Module map, grouped by job

~95 modules under `sec_overlay/` (plus the `correlate/` subpackage and the review-mode-only
modules listed on [review mode](review-mode.md)). Selected groups (see the module's own
docstring for detail not summarized here):

| Group | Modules | Job |
|---|---|---|
| Data model & serialization | `models.py`, `evidence.py`, `schema.py` | the Finding contract, the tool-receipt gate, a stdlib-only JSON-Schema validator |
| SAST backends & prefilter | `sast.py`, `codeql.py`, `sca.py`, `secrets.py`, `prefilter.py`, `exclusions.py` | run semgrep/CodeQL/osv-scanner/secrets concurrently; merge deterministically; never-silent backend accounting |
| Attack-class routing | `clsmap.py`, `detection_coverage.py`, `rule_matcher.py`, `asvs.py`/`codeguard.py`, `citations.py`, `custom_checks.py`, `dependency_sinks.py` | CWE→class mapping, ASVS/CodeGuard citation attachment, in-repo custom-check discovery, dependency-internal-sink catalog matching |
| Graph & structural substrate | `graph.py`, `structural_index.py`, `entrypoints.py`, `astgrep.py`, `reachability.py`, `route_census.py`, `route_control.py` | the two-tier code graph answering reachability/attacker-control; ripgrep symbol index; code-derived route inventory feeding the recall gate |
| FP reduction & finding identity | `normalize.py`, `dedupe.py`, `fingerprint.py`, `cluster.py`, `findings_gate.py`, `partition.py`, `fp_feedback.py`, `phase_gate.py`, `stage_validate.py` | dedup, fingerprinting, systemic clustering, the tool-receipt gate, phase-adversary pre-checks (incl. recall claims) |
| Scoring & prioritization | `calibrate.py`, `cvss.py`, `cvss4_data.py`, `scoring.py`, `fix_disposition.py`, `crypto_policy.py`, `selfscore.py` | deterministic `risk_score`, CVSS v4.0 MacroVector base score (never LLM arithmetic), the per-run self-score |
| Reporting | `report.py`, `sarif.py`, `render_util.py` | assemble `report.sarif` + `report.md`; shared rendering helpers for `expected_signal` (object/string/null) |
| Diagram generation & gate | `mermaid_index.py`, `diagram_gate.py`, `ste_lint.py` | line-oriented mermaid structure extraction; hard node/participant/message caps + derivation-provenance check; ASD-STE100 structural prose linter |
| Campaign, state & memory | `campaign.py`, `state.py`, `phases.py`, `driver.py`, `repo_memory.py`, `workspace.py`, `scanscope.py`, `kb.py`, `context.py`, `profile.py`, `diffscope.py`, `githist.py`, `postflight.py`, `run.py` | multi-pass supervision, the ordered `PHASE_TABLE` and the audit sequencer that walks it, the on-disk workspace layout, per-repo memory sidecar, context ingestion, the `drive`/`advance` wrapper the `/sec-overlay:audit` slash command calls |
| Coverage & completeness | `coverage_ledger.py`, `coverage_guide.py`, `discovery_ledger.py` | the completeness ledger, multi-pass auto-stop, saturation state |
| Hunting aids & tuning | `variant.py`, `bugchain.py`, `novelty.py`, `rule_gaps.py`, `tuning.py` | sibling-search seeds, finding chains, upstream-fix checks, adaptive-tuning scoreboard |
| Verification, safety & plumbing | `verify.py`, `patch_status.py`, `preflight.py`, `redactor.py`, `envelope.py`, `redteam.py`, `prove.py`, `parse.py`, `gates.py`, `cost.py` | apply a patch to a temp copy and re-scan, secret redaction, the untrusted-text envelope, fail-open JSON parsing, apply the opt-in prove-lane proofs |
| Terminal artifact gates | `artifact_gate.py`, `artifact_consistency.py` | the deterministic self-check before `artifact-review`, and the terminal cross-reference gate after it |
| Doc generation | `phase_docs.py` | regenerates the `PHASE_TABLE`-derived tables in `SKILL.md`/`README.md`/`agents/README.md`/`helpers/README.md` from `phases.py`, so the four can't drift |

`partition.py` is also the mechanism behind the "thoroughly review a codebase" principle's
coverage guarantee: its `unrouted_candidate_classes(ws, agents_to_spawn)` compares the classes
recon actually planned investigate agents for against every class present in the raw candidate
set. Vendored SAST rules often carry no `cls`/CWE and land in a `security-other`/`unknown`
bucket that recon never explicitly planned for — and that bucket can hold high-value hits
(command execution, weak crypto) just as easily as noise. If `unrouted_candidate_classes`
returns anything non-empty, the orchestrator logs the counts and spawns a general-triage
`investigate` agent (`{{ATTACK_CLASS}}=security-other`) over exactly those candidates, so a
class recon missed is never silently dropped from the audit — it is either routed to its own
agent or explicitly triaged by the safety-net agent, never orphaned. `reconcile_plan` also
merges in every attack class a `dependency_sinks.py` catalog entry implies the target declares,
so a dependency whose own code holds a sink (e.g. an OPA policy calling `http.send`) still gets
an investigate agent even though no first-party pattern exists for recon to find.

`dependency_sinks.py` loads and validates `references/dependency-sinks.json` — dependencies
whose own code holds a sink. `match_manifests()` walks a target's manifest files for a
declared dependency; `indicator_classes()` covers a target with no manifest at all (a Bazel or
vendored build) by reading source files for indicator tokens instead.

The `scope.py`/`is_external_package` deterministic-boundary check described in earlier
documentation was removed (REQ-47, dead-lever removal) because it had no live caller. The
`external-boundary` disposition it used to gate is now set directly by `agents/trace.md` when a
sink resolves into an un-ingested dependency, and enforced downstream by `calibrate.py`'s
`_EXTERNAL_CAP`/`_is_external_boundary` (caps `risk_score` at 3, sets
`completeness_tier = "external-unverifiable"`) and by `findings_gate.py`'s `open_questions`
requirement — an agent-asserted judgment with a deterministic cap, not a manifest lookup.

`correlate/` (`helpers/sec_overlay/correlate/`, 11 modules: `ingest.py`, `edges.py`,
`rethreshold.py`, `manifest.py`, `artifacts.py`, `mermaid.py`, `xrepo_sarif.py`, `workspace.py`,
`cli.py`) is a separate cross-repo correlation subpackage with its own promote/demote invariant
— see [cross-repo correlation](cross-repo-correlation.md) rather than the single-repo groups
above.

## CLI-callable modules

Most deterministic steps expose `python -m sec_overlay.<module>` (a `__main__`) — the steps the
orchestrator calls between agent phases: `cli` (scan/review/sessions/memory), `preflight`,
`graph`, `structural_index`, `astgrep`, `route_census`, `dedupe`, `cluster`, `findings_gate`,
`calibrate`, `citations`, `bugchain`, `rule_gaps`, `verify`, `redteam`, `report`, `selfscore`,
`artifact_gate`, `redactor`, `postflight`, `dependency_sinks`, `pr_poster`. See
[running an audit](running-an-audit.md) for how the orchestrator sequences these across a full
pass, [review mode](review-mode.md) for the `cli review`/`cli sessions` subcommands, and
`correlate`'s own dedicated CLI in [cross-repo correlation](cross-repo-correlation.md).

## Related pages

- [Pipeline](pipeline.md) — the phase-by-phase order these modules implement.
- [Agents](agents.md) — the LLM prompts that plug in between the deterministic steps above.
- [References](references.md) — the schema/policy files these modules read.
- [Running an audit](running-an-audit.md) — exact commands, preflight checks, environment prerequisites.
- [Review mode](review-mode.md) — the diff-scoped review track's own module set.
- [Developing the skill](developing-the-skill.md) — tests, linting, the bench harness, and the stdlib-only rule.
- [Cross-repo correlation](cross-repo-correlation.md) — the `correlate/` subpackage in detail.
