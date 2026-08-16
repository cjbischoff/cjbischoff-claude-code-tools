import hashlib

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
    errs = check_diagram(p, "container")
    assert any("orphan" in e and "lonely" in e for e in errs)


def test_source_only_node_is_not_orphan(tmp_path):
    # A chain's entry node (out-degree only, never a destination) is a normal
    # topology shape, not over-detailing — it must not be flagged (design spec §6, R4).
    p = _write(tmp_path / "container-diagram.mmd", CONTAINER)
    assert check_diagram(p, "container") == []


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
