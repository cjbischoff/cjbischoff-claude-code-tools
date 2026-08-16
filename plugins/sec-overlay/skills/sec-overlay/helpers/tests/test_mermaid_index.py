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
