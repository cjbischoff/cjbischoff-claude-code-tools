# sec-overlay: Architecture Documentation + Threat Model Standards — Design Spec

**Date:** 2026-08-16
**Source standard:** [`2026-08-16-architecture-threat-model-standards-source.md`](2026-08-16-architecture-threat-model-standards-source.md) (the user-authored standards spec; this design implements it inside sec-overlay)
**Target:** `plugins/sec-overlay/` — the `architecture` and `threat_model` phases and their enforcement machinery.

---

## 1. Purpose

Rebuild sec-overlay's architecture and threat-model phases so each artifact follows a named standard with an explicit ownership boundary. The architecture phase emits C4 diagrams and an arc42 document. The threat-model phase emits a DFD **derived from** the container diagram, attack sequences **derived from** the runtime sequences, and a STRIDE-based findings table scored with CVSS v4.0. Deterministic gates hard-enforce diagram caps, derivation provenance, and the checkable subset of ASD-STE100 prose rules.

The root cause this cures: both artifacts were general-purpose descriptions of the same system with no scope boundary. The fix is standards plus transformation, not post-hoc deduplication.

## 2. Interview rulings (binding)

| # | Question | Ruling |
|---|---|---|
| R1 | Where does the build land? | Extend sec-overlay. The existing `architecture`/`threat_model` phases are rebuilt. |
| R2 | CVSS 3.1 engine vs the spec's v4.0 pin | Migrate the whole harness to CVSS v4.0. One version everywhere; no mixing. |
| R3 | Artifact layout | Replace outright. `<workspace>/architecture/` and `<workspace>/threat-model/` replace `kb/architecture.md`, `kb/entities/*.md`, and `kb/THREAT_MODEL.md`. No shims; all consumers re-pointed. |
| R4 | Derivation mechanism | Agent transforms, gate proves. An agent performs the DFD/attack-sequence transformation with judgment; a deterministic checker proves element-set derivation, caps, and subgraph structure. |
| R5 | ADRs | **Skipped entirely.** A read-only scanner cannot author decision records; ADRs are outside the plugin's remit. All ADR cross-reference rules in the source standard are void; the threat model references arc42 sections instead (`see arc42 §4`). |
| R6 | STE-100 scope and cost | STE governs human-read artifacts only: `arc42.md` and `threat-model.md` (including findings-table free-text cells). Machine-read files (`.mmd`, `kb/*.json`, gates, state) are exempt. Existing `report.md`/`redteam-plan.md` stay out of scope. Enforcement is generation-time (prompt block) plus a deterministic linter for the checkable structural rules, with re-render rounds capped at one. |

## 3. Artifact layout and ownership

```
<workspace>/architecture/            (replaces kb/architecture.md + kb/entities/*.md)
  context-diagram.mmd                 C4 context, ≤10 nodes
  container-diagram.mmd               C4 container, ≤15 nodes — source of truth for structure
  component-diagram-<name>.mmd        only for containers the scan profile flags high-complexity
  runtime-view/
    sequence-<scenario>.mmd           normal-path only, ≤6 participants / ≤15 messages
  arc42.md                            sections 1–8 and 10–12; §9 (ADRs) omitted per R5
<workspace>/threat-model/            (replaces kb/THREAT_MODEL.md)
  dfd.mmd                             derived from container-diagram.mmd, ≤12 elements
  attack-sequences/
    sequence-<attack-scenario>.mmd    derived from runtime-view sequences
  threat-model.md                     methodology record; STRIDE(+PASTA/LINDDUN) findings
                                      table (CVSS v4.0); opens with a pointer to arc42.md
```

**Ownership boundary (enforced, not advisory).**

- Architecture owns: system purpose, tech stack, deployment topology, component structure, design rationale, quality attributes, normal-path runtime behavior.
- Architecture must not contain: threats, attack surface, mitigations, trust boundaries, findings.
- Threat model owns: trust boundaries, per-crossing threats, attack surface, findings, mitigations, attack sequences.
- Threat model must not restate: system purpose or structure narrative, deployment rationale, tech-stack justification. It references arc42 by section.

**Versioning.** Every derived file records the SHA-256 of its source file in a header comment (`%% derived-from: container-diagram.mmd sha256:<hex>`). The diagram gate recomputes and rejects on mismatch. A changed container diagram therefore forces DFD regeneration.

**Consumer rewiring.** Sixteen files reference the old paths (`agents/investigate.md`, `critic.md`, `validate.md`, `threat-model.md`, `architecture.md`, `context-ingest.md`, `phase-adversary.md`, `postflight.md`, `correlate-combiner.md`, `helpers/sec_overlay/kb.py`, `phase_gate.py`, `phases.py`, `context.py`, `repo_memory.py`, `correlate/artifacts.py`, `SKILL.md`). Each is re-pointed: orientation readers consume `architecture/arc42.md` and `architecture/container-diagram.mmd`; threat readers consume `threat-model/threat-model.md`. Old paths are removed in the same change.

## 4. Phases and agents

The phase table changes at two rows; the surrounding pipeline is unchanged.

**`architecture` (agent, sonnet producer — prompt rewritten).**
Input: `kb/scan-profile.json`. Emits the five architecture artifacts in one phase. Component diagrams only for containers the scan profile flags high-complexity. Runtime sequences only for scenarios with branching, retries, async handoffs, or ordering the container diagram does not imply. The prompt carries the C4 notation rules, the Mermaid caps table, the label rules, and the `STE_PROSE` block. Phase-table outputs: `architecture/container-diagram.mmd` and `architecture/arc42.md` (the two files every consumer needs); the remaining files are content-checked by the diagram gate.

**`threat_model` (agent, sonnet producer — prompt rewritten).**
Input: the architecture tree. Ordered procedure baked into the prompt:

1. **Methodology selection.** STRIDE always — a full pass over every DFD element, unconditional. Augmentation by signal: auth/credential issuance, payment/financial flow, or high business-impact paths → add PASTA; PII fields, consent flows, user data stores, GDPR/CCPA handling → add LINDDUN; both → both; neither → STRIDE alone. Record the applied methodologies and the one-line signal justification at the top of `threat-model.md`. Re-evaluated per system; never a hardcoded combination.
2. **Derive `dfd.mmd`** from `container-diagram.mmd`: same element ids, implementation detail stripped, Mermaid `subgraph` blocks for every trust boundary (network zone, auth, process, third-party), data-classification labels on flows where determinable (credentials, PII, tokens).
3. **Derive attack sequences** from runtime sequences: same participant set, attack steps inserted or timing assumptions violated. Targets the classes STRIDE tables under-represent: races, TOCTOU, token replay, multi-boundary chains. Each attack sequence ties to a specific findings-table row. ATT&CK technique ids are cited in the finding text for adversary-realistic findings; no ATT&CK dataset dependency.
4. **Findings table.** Columns: threat, affected DFD element, STRIDE/LINDDUN category, CVSS v4.0 score + vector, existing mitigation (if evidenced), residual risk, recommended mitigation. The agent proposes the vector; the harness computes the score (same division of labor as the finding pipeline).

**`diagram-gate` (deterministic, new).** Runs after each producing phase. Checks are listed in §6. Any failure raises `PhaseHalt` with the violation list; the producer re-scopes and regenerates once; a second failure halts for a human.

**Adversary gating unchanged.** Both phases keep their opus `phase-adversary` pass. The adversary checklist gains the ownership-boundary rule: architecture text that names threats or mitigations is a defect, and the reverse.

## 5. CVSS v4.0 migration

**Engine.** `helpers/sec_overlay/cvss.py` is rewritten to the CVSS v4.0 specification. v4.0 uses the MacroVector model, not a formula: base metrics (AV, AC, AT, PR, UI, VC, VI, VA, SC, SI, SA) map to a 6-digit MacroVector; each MacroVector has a published score; the final score interpolates within the MacroVector's severity depth. The published lookup table (~270 entries) and interpolation rule embed as module data — stdlib-only holds. The module keeps its current interface shape (`parse_vector`, scoring entry point, rating bands) and the orthogonal OffensivePriority axis is untouched.

**No mixing.** `agents/validate.md` and the finding schema move to `CVSS:4.0/...` vectors in the same change. `calibrate` consumes the 0–10 base score unchanged. A 3.1 vector at the parser is a hard error whose message names the migration. No dual support.

**Multi-pass workspaces.** Carried-forward findings holding 3.1 vectors are re-scored on the next pass: the re-validate step emits fresh 4.0 vectors from the finding's own evidence. No mechanical 3.1→4.0 translation (FIRST publishes none; conversion is lossy).

**Ordering.** This lands first; both rebuilt phases depend on it.

## 6. Enforcement: Mermaid index, diagram gate, STE linter

**`mermaid_index.py` (stdlib, new).** Line-oriented structure extraction, not a grammar: node ids and labels, edges and edge labels, `subgraph` blocks and membership, sequence participants and message counts, C4 element macros. It answers only what the gates ask. Unparseable input is a gate failure, never a guess.

**Diagram gate checks (all hard failures):**

| Check | Rule |
|---|---|
| Caps | Context ≤10 nodes; Container ≤15; Component ≤10 per container; Sequence ≤6 participants and ≤15 messages; DFD ≤12 elements (processes + stores + external entities, boundaries excluded); attack sequences inherit the sequence caps. |
| Labels | Edge labels ≤4 words. Node labels carry a name only. |
| Orphan detail | No single-edge node that is not a required actor or data store. |
| Trust boundaries | DFD boundaries must be `subgraph` blocks — structural, not decorative labels. |
| Derivation provenance | DFD element ids ⊆ container-diagram ids. Attack-sequence participants ⊆ parent sequence participants. |
| Freshness | `derived-from` SHA-256 header matches the current source file. |
| Styling | Any non-default style requires a legend on or immediately below the diagram. |

**Re-scoping algorithm (resolves source open item #1).** On cap breach, the regeneration prompt applies in order: (1) **group** — collapse categories with more than 3 similar elements into one counted node and emit the member table below the diagram; (2) **split** — partition along the strongest boundary (sequence: request path vs async path; container: sub-context per bounded group); (3) **promote** — move remaining excess to a summary table in prose. One retry, then `PhaseHalt`.

**`ste_lint.py` (stdlib, new).** Runs over `arc42.md` and `threat-model.md` prose only. Skips code fences, table structure, and `.mmd` files; includes findings-table free-text cells. Checks the mechanically checkable structural rules:

| Rule | Enforcement |
|---|---|
| Sentence length ≤25 words | Reject (uniform cap; instruction-vs-description intent detection is guesswork) |
| No semicolons in prose | Reject |
| Paragraphs ≤6 sentences | Reject |
| 3+ step sequences must be lists | Reject |
| Noun clusters ≤3 words | Warn only (4+ consecutive noun-like tokens; not reliably checkable) |

Lexical rules stay directional-only per the source standard: no dictionary check. The document front matter carries the one-time lexical-limitation statement. Reject → one regeneration round → a second failure ships with violations listed in the gate file as flags. Modality preservation ("may have failed" never becomes "failed") is a prompt rule and an adversary-checklist item, not a lint rule.

**Artifact-gate addition.** The existing `artifact_gate` gains the duplication scan (source validation rule #6): heading/keyword overlap between `threat-model.md` and arc42 building-block content is an error.

## 7. References, prompts, testing, governance

**New reference files** (each imported by the prompts that need it, tracked in `references/README.md`):

- `references/architecture-standards.md` — C4 notation rules, arc42 section table (§9 marked out-of-remit), runtime-view scope rule.
- `references/threat-model-standards.md` — STRIDE element table, PASTA/LINDDUN signal table, DFD derivation rules, findings-table columns, Threat Modeling Manifesto citation instruction.
- `references/mermaid-caps.md` — the caps table and generation rules 1–7; single source for both prompts and gate constants.
- `references/prompt-constants.md` — gains the `STE_PROSE` block (structural rules, tense exception, modality-wins rule, boundaries), injected into the two producing agents only.

**Prompt hard rules preserved.** Rewritten prompts keep the load-bearing blocks verbatim: trust envelope, ANTI_MANIPULATION, FIELD_OWNERSHIP, tool-receipt contract, model-family diversity.

**Testing (TDD).**

- `test_cvss.py` rewritten: FIRST v4.0 reference-score pins, full-parse property coverage, [0.0, 10.0] bounds, rating-band boundaries. 3.1 tests deleted with the engine.
- `test_mermaid_index.py`, `test_diagram_gate.py` (one test per check, including derivation-provenance and stale-SHA rejections), `test_ste_lint.py` (one per rule plus fence/table exemptions).
- `test_phases.py` / `test_wiring.py` extended for the new rows and re-pointed paths; contract tests catch prompt↔schema drift.

**Governance.** Implementation branch `feat/architecture-threat-model-standards`; Conventional Commits; folder READMEs and plugin `CHANGELOG.md` in the same commit as the code they document; plugin.json minor bumps per `feat` commit; skill `CLAUDE.md` §2/§4 updated under the 200-line cap.

## 8. Out of scope

- ADRs in any form (R5).
- STE over `report.md`, `redteam-plan.md`, or finding detail files.
- MITRE ATT&CK automation beyond prompt-cited technique ids.
- Structurizr, pytm, Threat Dragon, or any non-Mermaid tooling.
- Ingestion/scanning changes — the scan profile and recon pipeline are unchanged.

## 9. Resolution of the source spec's open items

| Source open item | Resolution |
|---|---|
| Re-scoping algorithm on cap breach | Group → split → promote, deterministic order (§6). |
| CVSS vector computation source | Agent proposes the vector per finding; harness computes the score deterministically (§5). |
| STE pass: generation-time vs post-pass | Generation-time prompt block plus deterministic structural linter, one retry (§6, R6). |
