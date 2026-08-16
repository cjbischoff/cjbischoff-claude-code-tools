"""Deterministic gate over generated Mermaid diagrams (design spec §6).

Hard-enforces the source standard's caps and generation rules: per-type
node/participant/message caps, ≤4-word edge labels, no orphan-detail nodes,
structural trust boundaries in the DFD, derivation provenance (derived
diagrams introduce no new elements), source-SHA freshness, and
legend-required styling. Exceeding a cap is a generation failure, never a
warning.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sec_overlay.mermaid_index import DiagramIndex, index_mermaid

CAPS = {"context": 10, "container": 15, "component": 10, "dfd": 12}
SEQ_CAPS = (6, 15)  # participants, messages
_EDGE_LABEL_MAX_WORDS = 4
_DERIVED = re.compile(r"%% derived-from:\s*(\S+)\s+sha256:([0-9a-f]{64})")
# Context diagrams are by definition required actors/systems — often degree-1
# by design — so the orphan-detail check never applies to them (design spec §6, R4).
_ORPHAN_CHECKED_KINDS = {"container", "component", "dfd"}


def _provenance(text: str, source: Path) -> list[str]:
    m = _DERIVED.search(text)
    if not m:
        return [f"missing derived-from header naming {source.name}"]
    errs = []
    if m.group(1) != source.name:
        errs.append(f"derived-from names {m.group(1)}, expected {source.name}")
    if not source.exists():
        errs.append(f"derived-from source {source.name} not found")
        return errs
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if m.group(2) != actual:
        errs.append(f"derived-from sha stale for {source.name} (source changed)")
    return errs


def _label_errors(idx: DiagramIndex, name: str) -> list[str]:
    return [
        f"{name}: edge label over {_EDGE_LABEL_MAX_WORDS} words: {label!r}"
        for _, _, label in idx.edges
        if label and len(label.split()) > _EDGE_LABEL_MAX_WORDS
    ]


def _node_label_errors(idx: DiagramIndex, name: str) -> list[str]:
    # A node with no bracket label defaults its label to its own id (bare id) —
    # that's not a description, so it's exempt from the word-count check.
    return [
        f"{name}: node label over {_EDGE_LABEL_MAX_WORDS} words: {label!r}"
        for nid, label in idx.nodes.items()
        if label and label != nid and len(label.split()) > _EDGE_LABEL_MAX_WORDS
    ]


def _orphan_errors(idx: DiagramIndex, name: str) -> list[str]:
    # A chain's entry node (out-degree only) is normal topology, not over-detailing.
    # Only a node that exclusively receives — a single incoming edge and no
    # outgoing edge — reads as a bolted-on detail node.
    in_degree: dict[str, int] = {}
    out_degree: dict[str, int] = {}
    for src, dst, _ in idx.edges:
        out_degree[src] = out_degree.get(src, 0) + 1
        in_degree[dst] = in_degree.get(dst, 0) + 1
    return [
        f"{name}: orphan-detail node {nid!r} (single edge, not a store/actor) — fold into prose"
        for nid in idx.nodes
        if out_degree.get(nid, 0) == 0
        and in_degree.get(nid, 0) <= 1
        and nid not in idx.store_ids
    ]


def check_diagram(path: Path, kind: str, *, source: Path | None = None) -> list[str]:
    """Check one diagram file against the caps and generation rules.

    Args:
        path: The ``.mmd`` file.
        kind: One of ``context|container|component|dfd|sequence``.
        source: For derived kinds (``dfd``, attack sequences), the file this
            diagram must be derived from.

    Returns:
        Error strings; empty when the diagram passes.
    """
    name = path.name
    text = path.read_text()
    try:
        idx = index_mermaid(text)
    except ValueError as e:
        return [f"{name}: unparseable mermaid: {e}"]
    errs: list[str] = []
    if kind == "sequence":
        p_cap, m_cap = SEQ_CAPS
        if len(idx.participants) > p_cap:
            errs.append(f"{name}: participant cap {p_cap} exceeded ({len(idx.participants)})")
        if idx.messages > m_cap:
            errs.append(f"{name}: message cap {m_cap} exceeded ({idx.messages})")
    else:
        cap = CAPS[kind]
        if len(idx.nodes) > cap:
            errs.append(
                f"{name}: node cap {cap} exceeded ({len(idx.nodes)}) — group/split/promote"
            )
        if kind in _ORPHAN_CHECKED_KINDS:
            errs.extend(_orphan_errors(idx, name))
        errs.extend(_node_label_errors(idx, name))
    errs.extend(_label_errors(idx, name))
    if idx.has_style and "legend" not in text.lower():
        errs.append(f"{name}: styled diagram has no legend")
    if kind == "dfd" and not idx.subgraphs:
        errs.append(f"{name}: DFD has no subgraph trust boundary (structural, not a label)")
    if source is not None:
        errs.extend(f"{name}: {e}" for e in _provenance(text, source))
        if source.exists():
            try:
                src_idx = index_mermaid(source.read_text())
            except ValueError as e:
                errs.append(f"{name}: source {source.name} unparseable: {e}")
                return errs
            if kind == "sequence":
                extra = set(idx.participants) - set(src_idx.participants)
                errs.extend(
                    f"{name}: participant {p!r} not in parent {source.name}" for p in sorted(extra)
                )
            else:
                extra = set(idx.nodes) - set(src_idx.nodes)
                errs.extend(
                    f"{name}: element {n!r} not in source {source.name}" for n in sorted(extra)
                )
    return errs


def run_diagram_gate(
    arch_dir: Path, tm_dir: Path, *, require_threat_model: bool = False
) -> list[str]:
    """Gate every diagram in the architecture and threat-model trees.

    Args:
        arch_dir: ``<workspace>/architecture``.
        tm_dir: ``<workspace>/threat-model``.
        require_threat_model: When ``True``, a missing ``dfd.mmd`` is a gate
            error instead of a silently-skipped optional diagram.

    Returns:
        Error strings across all diagrams; empty when everything passes.
    """
    errs: list[str] = []
    container = arch_dir / "container-diagram.mmd"
    for p, kind in ((arch_dir / "context-diagram.mmd", "context"), (container, "container")):
        if p.exists():
            errs.extend(check_diagram(p, kind))
        else:
            errs.append(f"missing required diagram {p.name}")
    for p in sorted(arch_dir.glob("component-diagram-*.mmd")):
        errs.extend(check_diagram(p, "component"))
    runtime = sorted((arch_dir / "runtime-view").glob("sequence-*.mmd"))
    for p in runtime:
        errs.extend(check_diagram(p, "sequence"))
    dfd = tm_dir / "dfd.mmd"
    if dfd.exists():
        errs.extend(check_diagram(dfd, "dfd", source=container))
    elif require_threat_model:
        errs.append(f"missing required diagram {dfd.name}")
    for p in sorted((tm_dir / "attack-sequences").glob("sequence-*.mmd")):
        parent = _attack_parent(p, runtime)
        errs.extend(check_diagram(p, "sequence", source=parent))
    return errs


def _attack_parent(attack: Path, runtime: list[Path]) -> Path:
    """Resolve an attack sequence's parent from its derived-from header."""
    m = _DERIVED.search(attack.read_text())
    if m:
        for p in runtime:
            if p.name == m.group(1):
                return p
    # no/unknown header: provenance check against a placeholder fails loudly
    return attack.parent / "MISSING-PARENT.mmd"


def main(argv: list[str] | None = None) -> int:
    """CLI: gate the diagrams of a workspace's architecture/threat-model trees."""
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-diagram-gate")
    parser.add_argument("--architecture", required=True)
    parser.add_argument("--threat-model", required=True)
    parser.add_argument("--require-threat-model", action="store_true")
    args = parser.parse_args(argv)
    errors = run_diagram_gate(
        Path(args.architecture),
        Path(args.threat_model),
        require_threat_model=args.require_threat_model,
    )
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
