# Mermaid generation rules (hard constraints)

Exceeding any cap is a generation failure, not a warning. `sec_overlay.diagram_gate`
enforces this table mechanically; `tests/test_references_caps.py` keeps the two in sync.

| kind | cap | counts |
|---|---|---|
| context | 10 | nodes (external systems/actors) |
| container | 15 | nodes per bounded system |
| component | 10 | nodes per container |
| dfd | 12 | processes + data stores + external entities (boundaries excluded) |
| sequence-participants | 6 | participants per sequence diagram |
| sequence-messages | 15 | messages per sequence diagram |

## Generation rules
1. One diagram, one story — structure, behavior, and trust boundaries never share a diagram.
2. Node labels, edge labels, and sequence message labels: 4 words or fewer each. Node labels
   are name only, no verb phrase; edge and message labels are a verb phrase.
3. No orphan detail: a single-edge node that is not an actor or data store folds into prose.
   Escape hatch — a required terminal element (leaf sink, hub spoke, external system) drawn as
   a store/actor shape is exempt from this rule: flowchart `[( )]` or `([ ])`, or C4
   `Person(...)`/`*_Ext(...)`/`ContainerDb(...)`. Folding into prose is also always allowed.
   This orphan rule applies to container, component, and dfd diagrams only — context diagrams
   and sequence diagrams are exempt.
4. Grouping over enumeration: more than 3 similar elements collapse to one counted node
   ("Downstream tools (5)") with the members in a table below the diagram.
5. DFD trust boundaries are `subgraph` blocks — structural, never a decorative label.
6. Re-scoping on cap breach, in order: **group** (rule 4), then **split** (one diagram per
   bounded sub-scope, e.g. "request path" and "async settlement path"), then **promote**
   (remaining excess moves to a summary table in prose). Never emit an over-cap diagram.
7. No decorative styling. Any non-default style requires a legend on or below the diagram.
8. Derived diagrams carry `%% derived-from: <source-filename> sha256:<hex-of-source>` and
   introduce no element or participant absent from their source. The gate verifies this by
   diffing the derived diagram's element/participant ids against the named source file.
