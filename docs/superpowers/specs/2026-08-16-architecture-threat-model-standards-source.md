# Standards Spec: Architecture Documentation + Threat Model Artifacts

## Purpose

Define the notation, structure, and cross-referencing rules each generated artifact must follow so architecture documentation and threat models stop duplicating each other. This spec is standards-and-direction only. It assumes artifact generation (codebase scanning, extraction) already exists and works; it does not address ingestion.

This spec is an input for a downstream brainstorming/build-spec skill. Its job is to fix *what standard governs each file and what that file is and is not allowed to contain*.

## Root cause of duplication

Both artifact types are currently being generated as general-purpose descriptions of the same system, using the same implicit notation (boxes and arrows), with no enforced scope boundary. The fix is not deduplication after generation. The fix is assigning each file a standard with a distinct notation and an explicit ownership boundary, then generating the second artifact's diagram as a *transformation* of the first, not an independent redraw.

## Format decisions (resolved)

- **Diagram format: Mermaid, all diagram types, both artifacts.** C4 context/container/component, sequence diagrams, and DFDs all render as Mermaid. This standardizes tooling, keeps every diagram plain-text and git-diffable, and is what enables the "derive diagram B from diagram A" transformation steps below — a script can parse and transform Mermaid source directly. No draw.io/Structurizr/PlantUML branch.
- **Severity scoring: CVSS v4.0** for the threat model findings table, in place of a custom scoring model. Version pinned; do not mix v3.1 and v4.0 scores across findings.
- **No OWASP Threat Dragon.** Mermaid is the sole diagram authoring/rendering format for the DFD, matching the architecture artifacts. No separate tool or JSON-in-git storage layer.
- **Mermaid caps are hard-enforced.** Exceeding a node/edge cap is a generation failure, not a warning. See enforcement rule below.

---

## Artifact 1: Architecture Documentation

**Standard:** [C4 model](https://c4model.com/) (Simon Brown) for diagrams, [arc42](https://arc42.org/) for the document template, [ADRs](https://github.com/joelparkerhenderson/architecture-decision-record) (Nygard format) for decisions.

**Owns:** system purpose, tech stack, deployment topology, component structure, design rationale, quality attributes, normal-path runtime behavior.

**Explicitly does not own:** threats, attack surface, mitigations, trust boundaries, findings.

### Diagrams — C4
- **Context diagram**: system + external actors/systems. Reference: [c4model.com/diagrams](https://c4model.com/diagrams)
- **Container diagram**: deployable units and protocols between them. This is the diagram the threat model's DFD will be derived from downstream — it is the single source of truth for system structure.
- **Component diagram**: only for containers where internal complexity warrants it. Not mandatory for every container. Reference: [c4model.com/introduction](https://c4model.com/introduction)
- Notation guidance and legend requirements: [c4model.com FAQ](https://c4model.com/faq)
- Rendered in Mermaid: [Mermaid C4 diagrams](https://mermaid.js.org/syntax/c4.html)

### Diagrams — Runtime view (sequence diagrams)
- Sequence diagrams belong in arc42 §6 (Runtime View), not as a standalone artifact type.
- Scope rule: only diagram scenarios with branching, retries, async handoffs, or ordering that isn't already implied by the container diagram's arrows.
- Format reference: [Mermaid sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html) (text-based, diffable, matches the C4-as-code approach)

### Document — arc42
Twelve-section template. Reference: [arc42.org/overview](https://arc42.org/overview/), full section-by-section guidance at [docs.arc42.org](https://docs.arc42.org/home/).

Sections directly relevant to this pipeline:
| Section | Content |
|---|---|
| 1. Introduction & Goals | Requirements, stakeholders, top quality goals |
| 2. Constraints | Technical/organizational constraints |
| 3. Context & Scope | = C4 Context diagram |
| 4. Solution Strategy | Core design decisions, links to ADRs |
| 5. Building Block View | = C4 Container/Component diagrams |
| 6. Runtime View | Sequence diagrams, key scenarios only |
| 7. Deployment View | Infrastructure/deployment topology |
| 8. Crosscutting Concepts | Cross-cutting technical topics |

Sections 9–12 (Architecture Decisions, Quality Requirements detail, Risks/Technical Debt, Glossary) per standard template; Architecture Decisions section should be a pointer to the ADR directory, not restated content.

Format: get the template in [AsciiDoc or Markdown](https://arc42.org/documentation/) — diffs cleanly, lives in git next to code.

### Decisions — ADRs
- One file per significant decision. Nygard format: context / decision / consequences.
- Reference and templates: [adr.github.io](https://adr.github.io/), [Joel Parker Henderson's ADR template collection](https://github.com/joelparkerhenderson/architecture-decision-record)
- Decisions with security implications get flagged in the ADR's context section. They are **not** duplicated into the threat model narrative — the threat model links to the ADR by ID instead.

---

## Artifact 2: Threat Model

**Standard:** Data Flow Diagram with trust boundaries, threats categorized via [STRIDE](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html) as the mandatory baseline, augmented per-system with [PASTA](https://www.securitycompass.com/blog/comparing-stride-linddun-pasta-threat-modeling/) and/or [LINDDUN](https://www.linddun.org/) based on detected codebase/context signals (procedure below), plus [MITRE ATT&CK](https://attack.mitre.org/) for adversary TTP mapping. General methodology overview: [OWASP Threat Modeling Project](https://owasp.org/www-project-threat-modeling/).

**Methodology selection procedure (run once per system, before the STRIDE pass):**
1. Run STRIDE. Always. This is not conditional and is not part of the augmentation decision — every threat model gets a full STRIDE pass over every DFD element regardless of what else gets added.
2. Scan the system's context for augmentation signals:
   - Auth/credential issuance, token handling, payment or financial transaction flow, or any path flagged high business-impact → **augment with PASTA**.
   - PII fields, consent flows, user data stores, or GDPR/CCPA-relevant data handling → **augment with LINDDUN**.
   - Both sets of signals present → augment with both. Neither present → STRIDE stands alone; do not add PASTA or LINDDUN by default.
3. Record which methodologies were applied and why (one line, tied to the detected signal) at the top of the threat model document, so the choice is auditable rather than silent.
4. This is a per-system decision, re-evaluated for every system scanned. Never hardcode a fixed combination (e.g. "always STRIDE+PASTA+LINDDUN") as a pipeline-wide default.

**Owns:** trust boundaries, per-boundary-crossing threats, attack surface, findings, mitigations, abuse-path/attack sequences.

**Explicitly does not own:** system purpose/structure narrative, deployment rationale, tech stack justification — these are referenced, not restated.

### Diagram — DFD with trust boundaries
- **Must be derived from the C4 Container diagram**, not independently generated. Same elements, different notation: strip implementation detail not relevant to data flow, add explicit trust boundary lines at every crossing (network zone, auth boundary, process boundary, third-party boundary), add data classification labels to flows where determinable (credentials, PII, tokens).
- Version the DFD against the container diagram it was derived from. Regenerate when the container diagram changes.
- Rendered in Mermaid (flowchart syntax with `subgraph` blocks for trust boundaries — see Mermaid generation rules below). No OWASP Threat Dragon dependency — Mermaid is the sole rendering/authoring format, kept text-based and in git alongside the architecture diagrams. [OWASP pytm](https://github.com/izar/pytm) remains a reference point for methodology/rule-engine thinking only, not a tooling dependency.

### Threats — STRIDE pass
- Per DFD element (process, data store, data flow, external entity), enumerate applicable STRIDE categories at each trust boundary crossing.
- Reference: [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- If risk-to-business-impact prioritization is required instead of a flat enumeration, use PASTA's 7-stage process instead of or alongside STRIDE.
- If privacy threats are relevant to scope (PII handling, consent, data minimization), add a LINDDUN pass: [linddun.org](https://www.linddun.org/)

### Attack sequences (time-ordered abuse cases)
- For timing-dependent findings STRIDE tables under-represent: race conditions, TOCTOU, token replay, multi-step attack chains crossing several trust boundaries.
- **Derived from the architecture doc's sequence diagrams**, not independently authored: same actors/steps as the normal-path baseline, with attack steps inserted or timing assumptions violated.
- Tie each attack sequence to a specific finding in the STRIDE/PASTA findings table.
- ATT&CK mapping for adversary-realistic findings (credential handling, lateral movement): [attack.mitre.org](https://attack.mitre.org/)

### Findings table
Columns: threat, affected DFD element, STRIDE/LINDDUN category, CVSS v4.0 score + vector string, existing mitigation (if evidenced), residual risk, recommended mitigation. CVSS reference: [first.org/cvss](https://www.first.org/cvss/), [CVSS v4.0 specification](https://www.first.org/cvss/v4-0/).

### Methodology selection signals (detail supporting the procedure above)

| Signal in the system | Add | Why |
|---|---|---|
| Auth/credential issuance, payment/financial flow, high business-impact transaction path | PASTA | STRIDE tells you *what* can go wrong; PASTA ties it to business impact for stakeholders who need risk-to-cost, not just threat category. |
| PII fields, consent flows, user data stores, GDPR/CCPA-relevant data handling | LINDDUN | Covers privacy-specific categories STRIDE doesn't (linkability, identifiability, non-repudiation-as-privacy-problem, detectability, disclosure, unawareness, non-compliance). |
| Neither of the above present | STRIDE only | Adding PASTA or LINDDUN to a system with no relevant signal is overhead without findings value. |

### Guiding principles
[Threat Modeling Manifesto](https://www.threatmodelingmanifesto.org/) — cite in the threat model's intro to justify methodology and scope choices rather than re-litigating them per document.

---

## Mermaid generation rules (anti-clutter constraints)

LLM-generated Mermaid diagrams tend toward visual overload: every node gets included, every relationship gets drawn, labels run long, and nothing gets left out because nothing was scoped out before generation. These are hard constraints, not style suggestions — enforce them at generation time, not as a post-hoc cleanup pass.

### Per-diagram-type node/complexity caps
| Diagram | Max nodes | Max edges per node | Notes |
|---|---|---|---|
| C4 Context | 10 | — | External systems/actors only; if a system has more than ~10 external dependents, group by category (e.g. "Internal auth providers (3)") rather than listing each. |
| C4 Container | 15 | — | One diagram per bounded system. If a system has more containers than this, it's a scope signal to split into sub-context diagrams, not to cram one diagram. |
| C4 Component | 10 | — | Per container. Only generate for containers flagged high-complexity (see prior scope rule); most containers get none. |
| Sequence (runtime view) | 6 participants | 15 messages | If a flow needs more, split into two sequence diagrams (e.g. "request path" and "async settlement path") rather than one diagram with everything. |
| DFD | 12 elements | — | Elements = processes + data stores + external entities combined, not counting trust boundary lines. |
| Attack sequence | 6 participants | 15 messages | Same cap as runtime sequences; derived diagrams inherit the parent's participant set, do not add new ones beyond the inserted attack step(s). |

### Generation rules
1. **One diagram, one story.** Each diagram answers one question ("what talks to what," "what happens in what order," "where does data cross a trust boundary"). If a diagram is trying to show structure and behavior and trust boundaries at once, split it.
2. **Label discipline.** Node labels: name only, no descriptions inline (descriptions go in accompanying prose/table, not the diagram). Edge labels: verb phrase, under 4 words ("issues token," not "the gateway issues a signed JWT token to the calling agent after validating credentials").
3. **No orphan detail.** Don't include a node whose only purpose is to be mentioned once. If an element has exactly one edge and isn't a required actor/data store per the standard's notation, fold it into prose instead.
4. **Grouping over enumeration.** When a category has more than 3 similar elements (e.g. multiple downstream tool integrations behind the gateway), collapse to a single grouped node with a count, and enumerate the members in a table below the diagram, not as separate nodes.
5. **Consistent subgraph use for trust boundaries.** DFDs must use Mermaid `subgraph` blocks for trust boundary zones, not just a label — the visual boundary has to be structural, not decorative. Reference: [Mermaid flowchart subgraphs](https://mermaid.js.org/syntax/flowchart.html#subgraphs).
6. **Hard enforcement: reject on generation, not review.** Exceeding any cap in the table above is a generation failure, not a lint warning. The generation step must not emit a diagram over cap; it re-scopes (split, group, or promote excess detail to a summary table) and regenerates before output. No oversized diagram reaches the output directory under any circumstance, including "just this once" cases with unusually complex systems — a system that doesn't fit the caps gets split into multiple diagrams, the caps don't get waived.
7. **No decorative styling.** No custom colors/icons/fonts unless they encode meaning defined in a legend (e.g., color = trust zone, not color = "looks nice"). Every non-default style choice must be explained in a legend on the diagram or immediately below it.

Mermaid syntax references: [flowchart](https://mermaid.js.org/syntax/flowchart.html), [sequence](https://mermaid.js.org/syntax/sequenceDiagram.html), [C4](https://mermaid.js.org/syntax/c4.html).

## Writing Standard: ASD-STE100 (for human-readable prose)

**Scope:** applies to every prose sentence in generated artifacts — arc42 body text, ADR context/decision/consequences, threat-model.md narrative, and findings-table free-text cells (threat description, mitigation, residual risk). Does **not** apply to diagram node/edge labels — those are governed by the Mermaid label rules above (short, single-meaning by design, already directionally consistent with STE).

**Standard:** [ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English), a controlled natural language built for maintenance documentation that cannot be misread. It splits into two enforcement tiers here:

- **Structural rules — apply with confidence.** Self-contained, checkable without the official dictionary.
- **Lexical rules — direction of travel only.** The official standard defines these against a ~900-word approved dictionary this spec does not reproduce. Apply the *principle* (one word per meaning, verb over noun form, no phrasal verbs) but do not claim dictionary-verified STE compliance in generated output. State this limitation once in the threat-model/architecture doc front matter, not per sentence.

### Structural rules (hard requirements)

| Rule | Do | Don't |
|---|---|---|
| Active voice | "The gateway rejects the request." | "The request is rejected." (unless the actor is genuinely unknown/irrelevant) |
| No phrasal verbs | "Remove the credential." | "Take away the credential." |
| One instruction/claim per sentence | "Open the connection. Validate the token." | "Open the connection and validate the token, then check scope." |
| Sentence length | ≤20 words (instructions/procedures), ≤25 words (descriptive text) | Long compound/subordinate-clause sentences |
| No semicolons | Split into separate sentences | Any semicolon, including as a clause join |
| Noun clusters | ≤3 stacked words ("token validation service") | 4+ word stacks ("gateway token validation service handler") |
| No ellipsis | Keep subject, verb, article explicit | Drop words to shorten ("Requests not validated will fail" — ambiguous which requests) |
| Keep modality | "The request may have failed" stays "may have" | Promote a hedge to fact, or invent certainty the source doesn't state |
| Paragraph limits | One topic, ≤6 sentences | Multi-topic paragraphs |
| Lists for sequences | Numbered/bulleted list for 3+ steps or conditions | Sequence buried in one prose sentence |

### Lexical rules (directional, not verified)

| Rule | Do | Don't |
|---|---|---|
| One word, one meaning | Pick one verb per action, reuse it ("validate" everywhere, never mix "validate"/"check"/"confirm" for the same action) | Rotate synonyms for the same idea across a document |
| Verb, not noun (Rule 3.7) | "Validate the token." | "Perform validation of the token." |
| Domain terms | Keep necessary technical nouns, define once via a one-line glossary entry | Use jargon without ever defining it |

### Tense exception

STE permits infinitive, imperative, simple present/past/future, and past-participle-as-adjective; it excludes present perfect ("we received," not "we have received"). Exception: where the compound form carries information the simple form can't — current relevance, or a hedge like "may have failed" — keep it and flag the departure. This matters specifically for findings-table language ("the endpoint **may have been** exposed since the last deploy") and threat model status claims. **When the tense rule and the modality rule conflict, modality wins.**

### Boundaries

Will:
- Rewrite ambiguous or dense English into short, single-meaning, active-voice sentences.
- Return the rewritten text alone by default, and name the rules it applied when the user asks.
- Preserve every fact, condition, and scope qualifier in the original.
- Preserve the strength of every hedge, and add no claim the source did not make.
- Suggest a one-line glossary entry for domain terms that must stay.

Will not:
- Reproduce ASD's official ~900-word dictionary as if it were memorized verbatim — always treat the official download as the source of truth for exact approved wording.
- Simplify creative, marketing, or persuasive copy where voice and nuance are the point (not applicable to these artifacts, but stated for completeness if this rewrite pass is reused elsewhere).
- Silently drop a safety condition, exception, or scope qualifier to shorten a sentence — flag the trade-off instead.
- Convert "may have failed" into "failed," or "could be caused by X" into "X is the cause" — losing a hedge changes the claim.
- Guarantee an aerospace/defense-grade STE-compliant document; this is a clarity pass inspired by STE, not certified STE authoring.
- Make weak content true or useful. STE fixes form, not substance. A hollow finding rewritten under these rules becomes a clean, short, well-punctuated hollow finding — say so instead of polishing it.
- Shorten past the point of clarity. Stop when the sentence is unambiguous, not when it's shortest.

### Examples, applied to these artifacts

**arc42 — Constraints section**

Before: *"The system is designed to be deployed across multiple availability zones in order to provide resilience against zone-level failures, although this has not yet been fully validated in the current environment."*
Violations: nominalized passive ("is designed to be deployed"), two claims in one sentence (deployment strategy + validation status), 34 words over the 25-word descriptive cap.
After: *"The system deploys across multiple availability zones. This design resists zone-level failures. The team has not yet validated this resilience in the current environment."*
Note: "has not yet validated" keeps present perfect deliberately — it states current status, not a past event, so it falls under the tense exception. Flag it as a deliberate departure rather than an oversight.

**Threat model — findings table, threat description cell**

Before: *"There is a possibility that an attacker could exploit a potential race condition in the token refresh logic, which may or may not be exploitable depending on network timing, and this has not been fully confirmed."*
Violations: three claims in one sentence (vulnerability class, exploit precondition, confirmation status), passive/hedge stacking that obscures which hedge applies to what.
After: *"A race condition may exist in the token refresh logic. Exploitability depends on network timing. The team has not confirmed this finding."*
Note: every hedge in the original ("possibility," "may or may not," "not been fully confirmed") survives, just attached to one claim per sentence instead of stacked in one. No hedge got upgraded to a fact.

**ADR — consequences section**

Before: *"By choosing this approach we are accepting that there could be some increase in latency, though the extent of this has not been benchmarked, and it's also worth noting that rollback would require significant rework."*
Violations: hedge buried mid-sentence, two consequences joined by "and," 34 words.
After: *"This choice may increase latency. The team has not benchmarked the extent of the increase. Rollback would require significant rework."*



1. Threat model opens with a single-paragraph pointer to the architecture doc's Container diagram. No system overview restated.
2. Threat model references ADRs by ID (`see ADR-004`) instead of re-explaining design decisions.
3. Architecture doc contains no findings/threats/mitigations section. Security-relevant constraints go in the relevant ADR's context section only.
4. DFD is generated as a transformation of the Container diagram (Stage: derive, not scan-and-redraw).
5. Attack sequences are generated as transformations of the architecture doc's sequence diagrams (same rule as #4, applied to runtime view).
6. Validation check before final output: flag threat model sections that duplicate arc42 building-block content via heading/keyword overlap.

## File/directory structure

```
/architecture/
  context-diagram.mmd
  container-diagram.mmd          # source of truth for structure; DFD is derived from this
  component-diagram-<name>.mmd   # only where warranted
  runtime-view/
    sequence-<scenario>.mmd      # normal-path only
  arc42.md
  adr/
    ADR-001-<slug>.md

/threat-model/
  dfd.mmd                        # derived from container-diagram.mmd; versioned against it
  attack-sequences/
    sequence-<attack-scenario>.mmd  # derived from runtime-view sequences
  threat-model.md                # opens with pointer to arc42.md; findings table; ADR references by ID
```

## Reference index

| Topic | Link |
|---|---|
| C4 model | https://c4model.com/ |
| C4 diagram types | https://c4model.com/diagrams |
| C4 tooling | https://c4model.com/tooling |
| Mermaid C4 syntax | https://mermaid.js.org/syntax/c4.html |
| Mermaid sequence diagrams | https://mermaid.js.org/syntax/sequenceDiagram.html |
| Structurizr | https://structurizr.com/ |
| arc42 overview | https://arc42.org/overview/ |
| arc42 full docs | https://docs.arc42.org/home/ |
| arc42 downloads/formats | https://arc42.org/download/ |
| ADR reference/templates | https://adr.github.io/ |
| ADR template collection | https://github.com/joelparkerhenderson/architecture-decision-record |
| OWASP Threat Modeling Project | https://owasp.org/www-project-threat-modeling/ |
| OWASP Threat Modeling Cheat Sheet (STRIDE) | https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html |
| STRIDE vs LINDDUN vs PASTA comparison | https://www.securitycompass.com/blog/comparing-stride-linddun-pasta-threat-modeling/ |
| LINDDUN | https://www.linddun.org/ |
| MITRE ATT&CK | https://attack.mitre.org/ |
| OWASP pytm (threat-modeling-as-code, methodology reference only) | https://github.com/izar/pytm |
| Threat Modeling Manifesto | https://www.threatmodelingmanifesto.org/ |
| Mermaid (all diagram types) | https://mermaid.js.org/ |
| Mermaid flowchart/subgraph syntax | https://mermaid.js.org/syntax/flowchart.html |
| CVSS v4.0 specification | https://www.first.org/cvss/v4-0/ |
| ASD-STE100 official site | https://www.asd-ste100.org/ |
| ASD-STE100 — About STE | https://www.asd-ste100.org/about-ste.html |
| Simplified Technical English — Wikipedia | https://en.wikipedia.org/wiki/Simplified_Technical_English |

## Open items for the downstream build spec

All prior open items are resolved: Mermaid only (no Threat Dragon), CVSS v4.0 pinned, Mermaid caps hard-enforced at generation time. Remaining implementation detail left to the downstream build spec:

- Exact re-scoping algorithm when a diagram exceeds cap (which elements get grouped first, how the summary table is auto-generated from grouped nodes).
- Where the CVSS v4.0 vector string gets computed from (manual per finding vs. derived from a rules engine mapping STRIDE/LINDDUN category + exploitability signals to vector components).
- Whether the ASD-STE100 prose pass runs as a generation-time constraint (prose generated STE-compliant from the start) or a post-generation rewrite pass over drafted prose. Given the hard-enforcement precedent set for Mermaid caps, generation-time constraint is the consistent choice, but the downstream build spec should confirm the mechanism.
