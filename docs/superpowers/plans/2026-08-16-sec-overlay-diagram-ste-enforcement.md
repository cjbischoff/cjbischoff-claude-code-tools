# sec-overlay Diagram + STE Enforcement Implementation Plan (Plan 2 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic enforcement layer — a Mermaid structure indexer, a diagram gate (caps, labels, provenance, freshness), an STE prose linter, and the arc42↔threat-model duplication check.

**Architecture:** Three new stdlib modules under `helpers/sec_overlay/`: `mermaid_index.py` (line-oriented structure extraction), `diagram_gate.py` (hard checks over the architecture/ and threat-model/ trees, CLI-callable), `ste_lint.py` (checkable-subset STE rules). `artifact_gate.py` gains the duplication check. Phase wiring happens in Plan 3; every module here is testable standalone.

**Tech Stack:** Python 3.13 stdlib only. pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md` (§6). Depends on Plan 1 (`2026-08-16-sec-overlay-cvss4-migration.md`) being merged, though only Task 4 touches a shared file.

## Global Constraints

- Branch `feat/architecture-threat-model-standards`; Conventional Commits `<type>(sec-overlay): <summary under 50 chars>`; run from `plugins/sec-overlay/skills/sec-overlay/helpers/` with `uv run`; stdlib-only; TDD.
- Doc-guard: staging `sec_overlay/*.py` stages `sec_overlay/README.md`; `tests/*.py` stages `tests/README.md`; every commit stages `plugins/sec-overlay/CHANGELOG.md` and bumps `plugins/sec-overlay/.claude-plugin/plugin.json` (feat → minor, test/fix → patch). Explicit paths only; never `--no-verify`; no `Co-Authored-By`.
- Environmental test failures to ignore: `test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`, `test_citations.py::test_all_mapped_ids_exist_in_seed` (may pass).
- Caps (hard, from the source standard): context ≤10 nodes; container ≤15; component ≤10; sequence ≤6 participants and ≤15 messages; DFD ≤12 elements; edge/message labels ≤4 words.
- Derivation header format (exact): `%% derived-from: <source-filename> sha256:<64-hex>`.
- The workspace trees these gates scan: `<ws.root>/architecture/` and `<ws.root>/threat-model/` (created by Plan 3; the gate functions take explicit `Path` args so they need no Workspace changes).

---

### Task 1: `mermaid_index.py` — structure extraction

**Files:**
- Create: `sec_overlay/mermaid_index.py`
- Create: `tests/test_mermaid_index.py`

**Interfaces:**
- Consumes: nothing in-repo.
- Produces: `DiagramIndex` dataclass with fields `kind: str` (`"flowchart" | "sequence" | "c4"`), `nodes: dict[str, str]` (id → label), `edges: list[tuple[str, str, str]]` (src, dst, label), `subgraphs: dict[str, set[str]]` (name → member ids), `participants: list[str]`, `messages: int`, `store_ids: set[str]` (data-store/required-shape ids), `has_style: bool`. Function `index_mermaid(text: str) -> DiagramIndex`, raising `ValueError` on unrecognizable input. Tasks 2–3 and Plan 3 consume these names.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_mermaid_index.py — new
import pytest

from sec_overlay.mermaid_index import index_mermaid

FLOWCHART = """\
flowchart LR
    %% derived-from: container-diagram.mmd sha256:abc
    subgraph internet[Internet zone]
        user[User]
    end
    subgraph dmz[DMZ]
        gw[Gateway]
        db[(Sessions)]
    end
    user -->|sends request| gw
    gw -->|reads session| db
"""

SEQUENCE = """\
sequenceDiagram
    participant U as User
    participant G as Gateway
    U->>G: request token
    G-->>U: token
"""

C4 = """\
C4Container
    Person(user, "User")
    Container(gw, "Gateway")
    ContainerDb(db, "Sessions")
    Rel(user, gw, "sends request")
    Rel(gw, db, "reads session")
"""


def test_flowchart_index():
    idx = index_mermaid(FLOWCHART)
    assert idx.kind == "flowchart"
    assert set(idx.nodes) == {"user", "gw", "db"}
    assert ("user", "gw", "sends request") in idx.edges
    assert idx.subgraphs["dmz"] == {"gw", "db"}
    assert idx.store_ids == {"db"}
    assert idx.has_style is False


def test_sequence_index():
    idx = index_mermaid(SEQUENCE)
    assert idx.kind == "sequence"
    assert idx.participants == ["U", "G"]
    assert idx.messages == 2


def test_c4_index():
    idx = index_mermaid(C4)
    assert idx.kind == "c4"
    assert set(idx.nodes) == {"user", "gw", "db"}
    assert ("gw", "db", "reads session") in idx.edges
    assert idx.store_ids == {"db"}


def test_style_detected():
    idx = index_mermaid(FLOWCHART + "    style gw fill:#f00\n")
    assert idx.has_style is True


def test_unrecognizable_raises():
    with pytest.raises(ValueError):
        index_mermaid("this is not mermaid\n")
```

- [ ] **Step 2: Run, confirm red**

Run: `uv run pytest tests/test_mermaid_index.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
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
_FLOW_NODE = re.compile(r"(?<![\w])([A-Za-z][\w-]*)(\[\(|\(\[|\[\[|\{\{|\[|\(|\{)([^\]\)\}]*)")
_FLOW_EDGE = re.compile(
    r"([A-Za-z][\w-]*)\s*[-.=]+>{1,2}\s*(?:\|([^|]*)\|\s*)?([A-Za-z][\w-]*)"
)
_FLOW_EDGE_MID = re.compile(
    r"([A-Za-z][\w-]*)\s*--\s*([^->][^-]*?)\s*-->\s*([A-Za-z][\w-]*)"
)
_SUBGRAPH = re.compile(r"^\s*subgraph\s+([A-Za-z][\w-]*)")
_PARTICIPANT = re.compile(r"^\s*(?:participant|actor)\s+([A-Za-z][\w-]*)")
_SEQ_MSG = re.compile(r"^\s*([A-Za-z][\w-]*)\s*-{1,2}[)>x]{1,2}\+?-?\s*([A-Za-z][\w-]*)\s*:\s*(.*)")
_C4_ELEM = re.compile(
    r"^\s*(Person|System|Container|Component)(?:Db|Queue)?(?:_Ext)?\s*\(\s*([\w-]+)\s*,\s*\"([^\"]*)\""
)
_C4_STORE = re.compile(r"^\s*(?:Container|System)(?:Db|Queue)\s*\(\s*([\w-]+)")
_C4_REL = re.compile(r"^\s*(?:Bi)?Rel(?:_\w+)?\s*\(\s*([\w-]+)\s*,\s*([\w-]+)\s*,\s*\"([^\"]*)\"")
_STYLE = re.compile(r"^\s*(style|classDef|linkStyle)\b")


@dataclass
class DiagramIndex:
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
        m = _SUBGRAPH.match(ln)
        if m:
            idx.subgraphs[m.group(1)] = set()
            stack.append(m.group(1))
            # a subgraph line may also carry a label node form: subgraph id[Label]
        elif ln.strip() == "end" and stack:
            stack.pop()
        for nm in _FLOW_NODE.finditer(ln):
            nid, bracket, label = nm.group(1), nm.group(2), nm.group(3).strip()
            if _SUBGRAPH.match(ln) and nid == ln.split()[1].split("[")[0]:
                continue  # the subgraph's own id is a zone, not a node
            idx.nodes.setdefault(nid, label)
            if bracket in ("[(", "([" ):
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
            if m.group(1) == "Person" or "_Ext" in ln.split("(")[0]:
                idx.store_ids.add(m.group(2))  # required-shape: never an orphan defect
        s = _C4_STORE.match(ln)
        if s:
            idx.store_ids.add(s.group(1))
        r = _C4_REL.match(ln)
        if r:
            idx.edges.append((r.group(1), r.group(2), r.group(3)))
    return idx
```

Adjust regexes as the tests demand — the tests are the contract; the regex bodies above are the starting point, not sacred.

- [ ] **Step 4: Run, confirm green, lint**

Run: `uv run pytest tests/test_mermaid_index.py -q && uv run ruff check sec_overlay/ && uv run ty check`

- [ ] **Step 5: Commit**

```bash
git add helpers/sec_overlay/mermaid_index.py helpers/tests/test_mermaid_index.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add mermaid structure indexer"
```

---

### Task 2: `diagram_gate.py` — hard checks

**Files:**
- Create: `sec_overlay/diagram_gate.py`
- Create: `tests/test_diagram_gate.py`

**Interfaces:**
- Consumes: `index_mermaid`, `DiagramIndex` (Task 1).
- Produces: `CAPS: dict[str, int]`, `SEQ_CAPS: tuple[int, int]`, `check_diagram(path: Path, kind: str, *, source: Path | None = None) -> list[str]`, `run_diagram_gate(arch_dir: Path, tm_dir: Path) -> list[str]`, and CLI `python -m sec_overlay.diagram_gate --architecture DIR --threat-model DIR`. Plan 3's driver action and the caps-consistency test rely on `CAPS`/`SEQ_CAPS`/`run_diagram_gate` exactly as named.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_diagram_gate.py — new
import hashlib

import pytest

from sec_overlay.diagram_gate import CAPS, check_diagram, run_diagram_gate

CONTAINER = """\
flowchart LR
    web[Web] -->|calls| api[API]
    api -->|reads| db[(Users)]
"""


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def _derived_dfd(container_path, extra=""):
    sha = hashlib.sha256(container_path.read_bytes()).hexdigest()
    return (
        f"flowchart LR\n    %% derived-from: {container_path.name} sha256:{sha}\n"
        "    subgraph zone[Internal]\n        web[Web]\n        api[API]\n"
        "        db[(Users)]\n    end\n"
        "    web -->|calls| api\n    api -->|reads| db\n" + extra
    )


def test_clean_tree_passes(tmp_path):
    arch = tmp_path / "architecture"
    tm = tmp_path / "threat-model"
    c = _write(arch / "container-diagram.mmd", CONTAINER)
    _write(arch / "context-diagram.mmd", "flowchart LR\n    u[User] -->|uses| sys[System]\n")
    _write(tm / "dfd.mmd", _derived_dfd(c))
    assert run_diagram_gate(arch, tm) == []


def test_cap_breach_fails(tmp_path):
    nodes = "\n".join(f"    n{i}[N{i}] -->|to| n{i+1}[N{i+1}]" for i in range(CAPS["context"] + 1))
    p = _write(tmp_path / "context-diagram.mmd", "flowchart LR\n" + nodes)
    errs = check_diagram(p, "context")
    assert any("cap" in e for e in errs)


def test_long_edge_label_fails(tmp_path):
    p = _write(
        tmp_path / "context-diagram.mmd",
        "flowchart LR\n    a[A] -->|sends a very long label here| b[B]\n",
    )
    assert any("label" in e for e in check_diagram(p, "context"))


def test_dfd_without_subgraph_fails(tmp_path):
    c = _write(tmp_path / "container-diagram.mmd", CONTAINER)
    sha = __import__("hashlib").sha256(c.read_bytes()).hexdigest()
    p = _write(
        tmp_path / "dfd.mmd",
        f"flowchart LR\n    %% derived-from: {c.name} sha256:{sha}\n    web[Web] -->|calls| api[API]\n",
    )
    assert any("subgraph" in e or "boundary" in e for e in check_diagram(p, "dfd", source=c))


def test_dfd_new_element_fails(tmp_path):
    c = _write(tmp_path / "container-diagram.mmd", CONTAINER)
    p = _write(tmp_path / "dfd.mmd", _derived_dfd(c, "    ghost[Ghost] -->|haunts| api\n"))
    assert any("ghost" in e for e in check_diagram(p, "dfd", source=c))


def test_stale_sha_fails(tmp_path):
    c = _write(tmp_path / "container-diagram.mmd", CONTAINER)
    dfd = _derived_dfd(c)
    c.write_text(CONTAINER + "    api -->|notifies| q[(Queue)]\n")
    p = _write(tmp_path / "dfd.mmd", dfd)
    assert any("derived-from" in e or "stale" in e for e in check_diagram(p, "dfd", source=c))


def test_missing_derivation_header_fails(tmp_path):
    c = _write(tmp_path / "container-diagram.mmd", CONTAINER)
    p = _write(tmp_path / "dfd.mmd", "flowchart LR\n    subgraph z[Z]\n    web[Web]\n    end\n")
    assert any("derived-from" in e for e in check_diagram(p, "dfd", source=c))


def test_style_without_legend_fails(tmp_path):
    p = _write(
        tmp_path / "context-diagram.mmd",
        "flowchart LR\n    a[A] -->|uses| b[B]\n    style a fill:#f00\n",
    )
    assert any("legend" in e for e in check_diagram(p, "context"))


def test_orphan_detail_fails(tmp_path):
    p = _write(
        tmp_path / "container-diagram.mmd",
        CONTAINER + "    api -->|pings| lonely[Lonely]\n",
    )
    assert any("orphan" in e and "lonely" in e for e in check_diagram(p, "container"))


def test_sequence_participant_cap(tmp_path):
    parts = "".join(f"    participant P{i}\n" for i in range(7))
    p = _write(tmp_path / "sequence-x.mmd", "sequenceDiagram\n" + parts + "    P0->>P1: hi\n")
    assert any("participant" in e for e in check_diagram(p, "sequence"))


def test_attack_sequence_new_participant_fails(tmp_path):
    parent = _write(
        tmp_path / "runtime-view" / "sequence-login.mmd",
        "sequenceDiagram\n    participant U\n    participant G\n    U->>G: login\n",
    )
    sha = hashlib.sha256(parent.read_bytes()).hexdigest()
    atk = _write(
        tmp_path / "attack-sequences" / "sequence-replay.mmd",
        f"sequenceDiagram\n    %% derived-from: {parent.name} sha256:{sha}\n"
        "    participant U\n    participant G\n    participant M\n    M->>G: replay\n",
    )
    assert any("participant" in e and "M" in e for e in check_diagram(atk, "sequence", source=parent))
```

- [ ] **Step 2: Run, confirm red**

Run: `uv run pytest tests/test_diagram_gate.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
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


def _provenance(text: str, source: Path) -> list[str]:
    m = _DERIVED.search(text)
    if not m:
        return [f"missing derived-from header naming {source.name}"]
    errs = []
    if m.group(1) != source.name:
        errs.append(f"derived-from names {m.group(1)}, expected {source.name}")
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


def _orphan_errors(idx: DiagramIndex, name: str) -> list[str]:
    degree: dict[str, int] = {}
    for src, dst, _ in idx.edges:
        degree[src] = degree.get(src, 0) + 1
        degree[dst] = degree.get(dst, 0) + 1
    return [
        f"{name}: orphan-detail node {nid!r} (single edge, not a store/actor) — fold into prose"
        for nid in idx.nodes
        if degree.get(nid, 0) <= 1 and nid not in idx.store_ids
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
            errs.append(f"{name}: node cap {cap} exceeded ({len(idx.nodes)}) — group/split/promote")
        errs.extend(_orphan_errors(idx, name))
    errs.extend(_label_errors(idx, name))
    if idx.has_style and "legend" not in text.lower():
        errs.append(f"{name}: styled diagram has no legend")
    if kind == "dfd":
        if not idx.subgraphs:
            errs.append(f"{name}: DFD has no subgraph trust boundary (structural, not a label)")
        element_count = len(idx.nodes)
        if element_count > CAPS["dfd"]:
            errs.append(f"{name}: DFD element cap {CAPS['dfd']} exceeded ({element_count})")
    if source is not None:
        errs.extend(f"{name}: {e}" for e in _provenance(text, source))
        if source.exists():
            src_idx = index_mermaid(source.read_text())
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


def run_diagram_gate(arch_dir: Path, tm_dir: Path) -> list[str]:
    """Gate every diagram in the architecture and threat-model trees.

    Args:
        arch_dir: ``<workspace>/architecture``.
        tm_dir: ``<workspace>/threat-model``.

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
    args = parser.parse_args(argv)
    errors = run_diagram_gate(Path(args.architecture), Path(args.threat_model))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note `_attack_parent`'s MISSING-PARENT fallback: a nonexistent path makes `_provenance` report a missing/stale header and `source.exists()` guard skips the element diff — the error still surfaces. Verify this in the missing-header test.

- [ ] **Step 4: Run, confirm green, lint**

Run: `uv run pytest tests/test_diagram_gate.py tests/test_mermaid_index.py -q && uv run ruff check sec_overlay/ && uv run ty check`

- [ ] **Step 5: Commit**

```bash
git add helpers/sec_overlay/diagram_gate.py helpers/tests/test_diagram_gate.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add deterministic diagram gate"
```

---

### Task 3: `ste_lint.py` — checkable STE structural rules

**Files:**
- Create: `sec_overlay/ste_lint.py`
- Create: `tests/test_ste_lint.py`

**Interfaces:**
- Consumes: nothing in-repo.
- Produces: `lint_prose(text: str) -> tuple[list[str], list[str]]` (errors, warnings) and CLI `python -m sec_overlay.ste_lint <file...>`. Plan 3's driver action calls `lint_prose` on `arc42.md` and `threat-model.md`.

Rules — errors: sentence >25 words; semicolon in prose; paragraph >6 sentences; missing `ASD-STE100` limitation statement (checked only via CLI flag `--require-frontmatter`). Warnings: ≥4 consecutive capitalized tokens mid-sentence (noun-cluster suspicion); a single sentence containing " then " twice or more (sequence buried in prose). Exemptions: fenced code blocks, mermaid blocks, table separator rows, headings, inline code spans, URLs.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ste_lint.py — new
from sec_overlay.ste_lint import lint_prose


def test_clean_prose_passes():
    errs, warns = lint_prose("The gateway rejects the request. The log records the failure.\n")
    assert errs == [] and warns == []


def test_long_sentence_rejected():
    text = " ".join(["word"] * 26) + ".\n"
    errs, _ = lint_prose(text)
    assert any("25 words" in e for e in errs)


def test_semicolon_rejected():
    errs, _ = lint_prose("Open the file; check the header.\n")
    assert any("semicolon" in e for e in errs)


def test_semicolon_in_code_span_ok():
    errs, _ = lint_prose("Run `a; b` to reproduce the failure.\n")
    assert errs == []


def test_code_fence_exempt():
    errs, _ = lint_prose("```python\nx = 1; y = 2\n```\n")
    assert errs == []


def test_long_paragraph_rejected():
    para = " ".join(f"Sentence number {i} is short." for i in range(7))
    errs, _ = lint_prose(para + "\n")
    assert any("6 sentences" in e for e in errs)


def test_heading_and_table_exempt():
    text = "# A Very Long Heading With Many Capitalized Words Here\n\n| a | b |\n|---|---|\n| x; y | z |\n"
    errs, _ = lint_prose(text)
    # table CELLS are linted; the semicolon inside a cell is a real error
    assert any("semicolon" in e for e in errs)


def test_noun_cluster_warns():
    _, warns = lint_prose("The Gateway Token Validation Service Handler fails.\n")
    assert any("noun cluster" in w for w in warns)


def test_buried_sequence_warns():
    _, warns = lint_prose("Open the file then read the header then check the version.\n")
    assert any("sequence" in w for w in warns)
```

- [ ] **Step 2: Run, confirm red**

Run: `uv run pytest tests/test_ste_lint.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement**

```python
"""Deterministic linter for the checkable subset of ASD-STE100 (spec §6).

Checks structural rules only: sentence length, semicolons, paragraph size,
plus two warning-level heuristics (noun clusters, buried sequences). Lexical
rules are directional and unenforced — the produced documents carry a
front-matter statement to that effect. Code fences, mermaid blocks, headings,
table structure, inline code, and URLs are exempt; table free-text cells are
linted.
"""

from __future__ import annotations

import re
from pathlib import Path

_SENTENCE_MAX = 25
_PARA_MAX_SENTENCES = 6
_CODE_SPAN = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://\S+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CAP_RUN = re.compile(r"\b(?:[A-Z][a-z]+\s+){3,}[A-Z][a-z]+\b")


def _prose_blocks(text: str) -> list[str]:
    """Split markdown into linted prose blocks, dropping exempt regions."""
    blocks: list[str] = []
    in_fence = False
    current: list[str] = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        if stripped.startswith("#") or stripped.startswith("%%"):
            continue
        if stripped.startswith("|"):
            if set(stripped) <= set("|-: "):
                continue  # separator row
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            blocks.extend(c for c in cells if c and len(c.split()) > 1)
            continue
        if stripped.startswith(("-", "*", "+")) or re.match(r"^\d+[.)]\s", stripped):
            blocks.append(stripped.lstrip("-*+ ").lstrip("0123456789.) "))
            continue
        current.append(stripped)
    if current:
        blocks.append(" ".join(current))
    return blocks


def _clean(block: str) -> str:
    return _URL.sub("URL", _CODE_SPAN.sub("CODE", block))


def lint_prose(text: str) -> tuple[list[str], list[str]]:
    """Lint markdown prose against the checkable STE structural rules.

    Args:
        text: Full markdown document content.

    Returns:
        ``(errors, warnings)`` — human-readable rule violations.
    """
    errors: list[str] = []
    warnings: list[str] = []
    for block in _prose_blocks(text):
        cleaned = _clean(block)
        sentences = [s for s in _SENT_SPLIT.split(cleaned) if s.strip()]
        if len(sentences) > _PARA_MAX_SENTENCES:
            errors.append(f"paragraph over {_PARA_MAX_SENTENCES} sentences: {cleaned[:60]!r}…")
        for s in sentences:
            words = s.split()
            if len(words) > _SENTENCE_MAX:
                errors.append(f"sentence over {_SENTENCE_MAX} words: {s[:60]!r}…")
            if ";" in s:
                errors.append(f"semicolon in prose: {s[:60]!r}…")
            if s.lower().count(" then ") >= 2:
                warnings.append(f"sequence buried in prose (use a list): {s[:60]!r}…")
            m = _CAP_RUN.search(s[1:])  # skip sentence-initial capital
            if m:
                warnings.append(f"possible noun cluster over 3 words: {m.group(0)!r}")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    """CLI: lint files; exit 1 on any error (warnings never fail)."""
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-ste-lint")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--require-frontmatter", action="store_true")
    args = parser.parse_args(argv)
    failed = False
    for f in args.files:
        text = Path(f).read_text()
        errors, warns = lint_prose(text)
        if args.require_frontmatter and "ASD-STE100" not in text:
            errors.append("missing ASD-STE100 lexical-limitation statement in front matter")
        for e in errors:
            print(f"{f}: error: {e}")
            failed = True
        for w in warns:
            print(f"{f}: warning: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run, confirm green, lint**

Run: `uv run pytest tests/test_ste_lint.py -q && uv run ruff check sec_overlay/ && uv run ty check`

- [ ] **Step 5: Commit**

```bash
git add helpers/sec_overlay/ste_lint.py helpers/tests/test_ste_lint.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add STE structural prose linter"
```

---

### Task 4: arc42↔threat-model duplication check in `artifact_gate`

**Files:**
- Modify: `sec_overlay/artifact_gate.py` (add one function + one call in `run_artifact_gate`)
- Test: `tests/test_artifact_gate.py` (append)

**Interfaces:**
- Consumes: existing `run_artifact_gate(ws)` shape (returns error strings, writes `kb/gates/artifact-gate.json`).
- Produces: `check_duplication(arc42_text: str, tm_text: str) -> list[str]`, called inside `run_artifact_gate` only when both `<ws.root>/architecture/arc42.md` and `<ws.root>/threat-model/threat-model.md` exist (old workspaces and existing tests skip it silently).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_artifact_gate.py — append
from sec_overlay.artifact_gate import check_duplication


def test_duplicated_heading_fails():
    arc = "## Building Block View\n\nContent.\n"
    tm = "## Building Block View\n\nRestated content.\n"
    errs = check_duplication(arc, tm)
    assert any("building block view" in e.lower() for e in errs)


def test_banned_structure_heading_in_threat_model_fails():
    errs = check_duplication("## Something\n", "## Deployment View\n")
    assert any("deployment view" in e.lower() for e in errs)


def test_distinct_headings_pass():
    arc = "## Building Block View\n## Runtime View\n"
    tm = "## Trust Boundaries\n## Findings\n## Glossary\n"
    assert check_duplication(arc, tm) == []


def test_gate_skips_when_trees_absent(tmp_path):
    # existing _good_ws fixture: no architecture/ or threat-model/ trees
    ws = _good_ws(tmp_path)
    assert run_artifact_gate(ws) == []
```

- [ ] **Step 2: Run, confirm red**

Run: `uv run pytest tests/test_artifact_gate.py -v` — Expected: FAIL (`check_duplication` not defined).

- [ ] **Step 3: Implement**

Add to `artifact_gate.py`:

```python
_ALLOWED_SHARED_HEADINGS = {"glossary", "introduction", "references"}
_STRUCTURE_HEADINGS = {
    "building block view", "solution strategy", "deployment view",
    "context and scope", "runtime view", "tech stack",
}


def _headings(md: str) -> set[str]:
    return {
        re.sub(r"^[\d.\s]+", "", ln.lstrip("#").strip()).lower()
        for ln in md.splitlines()
        if ln.startswith("#")
    }


def check_duplication(arc42_text: str, tm_text: str) -> list[str]:
    """Flag threat-model sections that duplicate arc42 building-block content.

    Args:
        arc42_text: Content of ``architecture/arc42.md``.
        tm_text: Content of ``threat-model/threat-model.md``.

    Returns:
        Error strings; empty when the ownership boundary holds.
    """
    tm = _headings(tm_text)
    errors = [
        f"artifact-gate: threat-model restates architecture section {h!r}"
        for h in sorted((_headings(arc42_text) & tm) - _ALLOWED_SHARED_HEADINGS)
    ]
    errors.extend(
        f"artifact-gate: structure heading {h!r} belongs to the architecture doc"
        for h in sorted(_STRUCTURE_HEADINGS & tm)
    )
    return errors
```

In `run_artifact_gate`, before the gate-json write, add:

```python
    arc42 = ws.root / "architecture" / "arc42.md"
    tm_doc = ws.root / "threat-model" / "threat-model.md"
    if arc42.exists() and tm_doc.exists():
        errors.extend(check_duplication(arc42.read_text(), tm_doc.read_text()))
```

(`import re` is already present in the module.)

- [ ] **Step 4: Run, confirm green, lint**

Run: `uv run pytest tests/test_artifact_gate.py -q && uv run ruff check sec_overlay/ && uv run ty check`

- [ ] **Step 5: Full suite, then commit**

Run: `uv run pytest -q` (environmental failures only).

```bash
git add helpers/sec_overlay/artifact_gate.py helpers/tests/test_artifact_gate.py \
  helpers/sec_overlay/README.md helpers/tests/README.md \
  plugins/sec-overlay/CHANGELOG.md plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): gate arc42/threat-model duplication"
```

---

## Self-Review

**1. Spec coverage (§6):** mermaid index → Task 1; caps/labels/orphan/subgraph/provenance/freshness/legend checks → Task 2; STE linter with exemptions and error/warn split → Task 3; duplication scan (source validation rule #6) → Task 4. The re-scoping algorithm is prompt text, not gate code — it lands in Plan 3's prompt rewrites. **Deviation recorded:** the design §6 table listed "3+ step sequences must be lists" as Reject; reliable deterministic detection does not exist, so it ships warning-level (the `then×2` heuristic) — the spec is amended in the same commit as this plan.

**2. Placeholder scan:** all code steps carry full code; Task 1 Step 3 explicitly licenses regex adjustment against the tests, which are the contract. No TBDs.

**3. Type consistency:** `DiagramIndex` field names match between Tasks 1 and 2 (`nodes`, `edges`, `subgraphs`, `participants`, `messages`, `store_ids`, `has_style`). `check_diagram(path, kind, *, source)` and `run_diagram_gate(arch_dir, tm_dir)` match their test usage. `lint_prose` returns `(errors, warnings)` everywhere. `check_duplication(arc42_text, tm_text)` matches its tests and its `run_artifact_gate` call.
