# Threat model standard (DFD + STRIDE, signal-augmented)

## Methodology selection (run once, record the outcome)
1. STRIDE always — a full pass over every DFD element at every boundary crossing.
   Unconditional, never part of the augmentation decision.
2. Augment by signal:
   - auth/credential issuance, payment/financial flow, high business-impact path → add PASTA
   - PII fields, consent flows, user data stores, GDPR/CCPA handling → add LINDDUN
   - both signal sets → both; neither → STRIDE alone.
3. Record applied methodologies + the one-line signal justification at the top of
   threat-model.md. Per-system decision; never a hardcoded combination.

## Derived diagrams
- **dfd.mmd** derives from `architecture/container-diagram.mmd`: same element ids,
  implementation detail stripped, `subgraph` per trust boundary (network zone, auth,
  process, third-party), data-classification labels on flows where determinable
  (credentials, PII, tokens). Carries the derived-from SHA header. This diagram is a
  container/component-class diagram for `mermaid-caps.md` purposes: the orphan rule
  applies, with the same store/actor escape hatch for required terminal elements.
- **attack-sequences/sequence-<attack>.mmd** derive from runtime-view sequences: same
  participants, attack steps inserted or timing assumptions violated. For classes STRIDE
  tables under-represent: races, TOCTOU, token replay, multi-boundary chains. Each ties
  to one findings-table row.

## Findings table columns
threat | affected DFD element | STRIDE/LINDDUN category | CVSS v4.0 score + vector |
existing mitigation (if evidenced) | residual risk | recommended mitigation
The agent proposes the vector; the harness computes the score. ATT&CK technique ids are
cited in the finding text for adversary-realistic findings.

## Ownership boundary (hard)
Owns: trust boundaries, per-crossing threats, attack surface, findings, mitigations,
attack sequences, the prioritized hunt list.
Never restates: system purpose/structure narrative, deployment rationale, tech-stack
justification — reference arc42 by section (`see arc42 §4`) instead.
