"""Line-oriented Mermaid structure extraction for the diagram gate.

Not a grammar: extracts exactly what the gate checks — node ids/labels, edges
and edge labels, subgraph membership, sequence participants and message counts,
C4 element macros. Unrecognizable input raises; the gate treats that as a
failure, never a guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FLOW_HEAD = re.compile(r"^\s*(flowchart|graph)\b")
_SEQ_HEAD = re.compile(r"^\s*sequenceDiagram\b")
_C4_HEAD = re.compile(r"^\s*C4(Context|Container|Component|Dynamic|Deployment)\b")
# id followed by a bracketed label: gw[Gateway], db[(Sessions)], q{{Queue}} …
_FLOW_NODE = re.compile(
    r"(?<![\w])([A-Za-z][\w-]*)(\[\(|\(\[|\[\[|\{\{|\[|\(|\{)([^\]\)\}]*)"
)
_FLOW_EDGE = re.compile(
    r"([A-Za-z][\w-]*)\s*[-.=]+>{1,2}\s*(?:\|([^|]*)\|\s*)?([A-Za-z][\w-]*)"
)
# mid-arrow label form: `a -- some label --> b` (as opposed to `a -->|label| b`).
# Tried before _FLOW_EDGE, or the label text itself gets misread as a source node.
_FLOW_EDGE_MID = re.compile(
    r"([A-Za-z][\w-]*)\s*--\s*([^->][^-]*?)\s*-->\s*([A-Za-z][\w-]*)"
)
_SUBGRAPH = re.compile(r"^\s*subgraph\s+([A-Za-z][\w-]*)")
_PARTICIPANT = re.compile(r"^\s*(?:participant|actor)\s+(\w+)")
# Sequence ids never carry hyphens in this notation, so the id class excludes
# "-" to avoid swallowing the arrow's leading dash.
_SEQ_MSG = re.compile(r"^\s*(\w+)\s*-{1,2}[)>x]{1,2}\+?-?\s*(\w+)\s*:\s*(.*)")
_C4_ELEM = re.compile(
    r"^\s*(Person|System|Container|Component)(?:Db|Queue)?(?:_Ext)?\s*"
    r"\(\s*([\w-]+)\s*,\s*\"([^\"]*)\""
)
_C4_STORE = re.compile(r"^\s*(?:Container|System)(?:Db|Queue)\s*\(\s*([\w-]+)")
_C4_REL = re.compile(r"^\s*(?:Bi)?Rel(?:_\w+)?\s*\(\s*([\w-]+)\s*,\s*([\w-]+)\s*,\s*\"([^\"]*)\"")
_STYLE = re.compile(r"^\s*(style|classDef|linkStyle)\b")

# Bracket openers that mark a data-store / required shape (cylinder, stadium).
_STORE_BRACKETS = ("[(", "(["
)


@dataclass
class DiagramIndex:
    """Extracted structure from one Mermaid diagram.

    Attributes:
        kind: Diagram type — ``"flowchart"``, ``"sequence"``, or ``"c4"``.
        nodes: Map of node id to label text.
        edges: List of ``(src, dst, label)`` tuples.
        subgraphs: Map of subgraph name to the set of member node ids.
        participants: Sequence-diagram participant ids, in declaration order.
        messages: Count of sequence-diagram messages.
        store_ids: Node ids that are data-stores or required-shape elements.
        has_style: Whether the diagram source contains a style/classDef/linkStyle line.
    """

    kind: str
    nodes: dict[str, str] = field(default_factory=dict)
    edges: list[tuple[str, str, str]] = field(default_factory=list)
    subgraphs: dict[str, set[str]] = field(default_factory=dict)
    participants: list[str] = field(default_factory=list)
    messages: int = 0
    store_ids: set[str] = field(default_factory=set)
    has_style: bool = False


def index_mermaid(text: str) -> DiagramIndex:
    """Extract gate-relevant structure from Mermaid source.

    Args:
        text: Full ``.mmd`` file content.

    Returns:
        A :class:`DiagramIndex` for the first diagram in the text.

    Raises:
        ValueError: If no known diagram header is found.
    """
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    if not lines:
        raise ValueError("empty mermaid source")
    head = lines[0]
    if _FLOW_HEAD.match(head):
        return _index_flowchart(lines[1:])
    if _SEQ_HEAD.match(head):
        return _index_sequence(lines[1:])
    if _C4_HEAD.match(head):
        return _index_c4(lines[1:])
    raise ValueError(f"unrecognized mermaid diagram header: {head.strip()!r}")


def _index_flowchart(lines: list[str]) -> DiagramIndex:
    idx = DiagramIndex(kind="flowchart")
    stack: list[str] = []
    for ln in lines:
        if _STYLE.match(ln):
            idx.has_style = True
            continue
        sub_m = _SUBGRAPH.match(ln)
        if sub_m:
            zone_id = sub_m.group(1)
            idx.subgraphs[zone_id] = set()
            stack.append(zone_id)
            continue
        if ln.strip() == "end" and stack:
            stack.pop()
            continue
        for nm in _FLOW_NODE.finditer(ln):
            nid, bracket, label = nm.group(1), nm.group(2), nm.group(3).strip()
            idx.nodes.setdefault(nid, label)
            if bracket in _STORE_BRACKETS:
                idx.store_ids.add(nid)
            if stack:
                idx.subgraphs[stack[-1]].add(nid)
        em = _FLOW_EDGE_MID.search(ln) or _FLOW_EDGE.search(ln)
        if em:
            if em.re is _FLOW_EDGE_MID:
                src, label, dst = em.group(1), em.group(2).strip(), em.group(3)
            else:
                src, label, dst = em.group(1), (em.group(2) or "").strip(), em.group(3)
            idx.edges.append((src, dst, label))
            for nid in (src, dst):
                idx.nodes.setdefault(nid, nid)
                if stack:
                    idx.subgraphs[stack[-1]].add(nid)
    return idx


def _index_sequence(lines: list[str]) -> DiagramIndex:
    idx = DiagramIndex(kind="sequence")
    for ln in lines:
        m = _PARTICIPANT.match(ln)
        if m:
            idx.participants.append(m.group(1))
            continue
        m = _SEQ_MSG.match(ln)
        if m:
            idx.messages += 1
            idx.edges.append((m.group(1), m.group(2), m.group(3).strip()))
            for pid in (m.group(1), m.group(2)):
                if pid not in idx.participants:
                    idx.participants.append(pid)
    return idx


def _index_c4(lines: list[str]) -> DiagramIndex:
    idx = DiagramIndex(kind="c4")
    for ln in lines:
        if _STYLE.match(ln):
            idx.has_style = True
        m = _C4_ELEM.match(ln)
        if m:
            idx.nodes[m.group(2)] = m.group(3)
        s = _C4_STORE.match(ln)
        if s:
            idx.store_ids.add(s.group(1))
        r = _C4_REL.match(ln)
        if r:
            idx.edges.append((r.group(1), r.group(2), r.group(3)))
    return idx
