# Architecture documentation standard (C4 + arc42)

## Diagrams — C4, rendered as Mermaid
- **context-diagram.mmd** — the system plus external actors/systems only.
- **container-diagram.mmd** — deployable units and the protocols between them. This is
  the single source of truth for system structure; the threat model's DFD is derived
  from it, never redrawn.
- **component-diagram-<name>.mmd** — only for containers the scan profile flags
  high-complexity. Most containers get none.
- **runtime-view/sequence-<scenario>.mmd** — normal-path sequence diagrams, only for
  scenarios with branching, retries, async handoffs, or ordering the container diagram's
  arrows do not already imply.
All diagrams obey `mermaid-caps.md`, including its escape hatch: a required terminal
element (leaf sink, hub spoke, external system) drawn as a store/actor shape is exempt
from the orphan rule.

## Document — arc42.md
| Section | Content |
|---|---|
| 1. Introduction & Goals | Requirements, stakeholders, top quality goals |
| 2. Constraints | Technical/organizational constraints |
| 3. Context & Scope | embeds/points to context-diagram.mmd |
| 4. Solution Strategy | core design decisions inferred from code, with file:line evidence |
| 5. Building Block View | points to container/component diagrams; one block per
security-relevant component: name, responsibility, key files (path:line), inputs it
trusts/untrusts. This replaces the old kb/entities/ files — later agents read these blocks. |
| 6. Runtime View | points to runtime-view/ sequences, key scenarios only |
| 7. Deployment View | infrastructure/deployment topology |
| 8. Crosscutting Concepts | cross-cutting technical topics |
| 10. Quality Requirements | as evidenced |
| 11. Risks & Technical Debt | non-security technical debt only |
| 12. Glossary | one line per kept domain term |
Section 9 (Architecture Decisions) is omitted: a read-only scanner cannot author ADRs.

## Ownership boundary (hard)
Owns: purpose, tech stack, deployment topology, component structure, rationale, quality
attributes, normal-path runtime behavior.
Never contains: threats, attack surface, mitigations, findings. Trust boundaries appear
ONLY as structure (which zone contains what), never with attacker narrative.
