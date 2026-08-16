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

MID_LABEL_FLOWCHART = """\
flowchart LR
    a -- some label --> b
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
    assert idx.store_ids == {"user", "db"}


def test_flowchart_mid_label_edge():
    idx = index_mermaid(MID_LABEL_FLOWCHART)
    assert ("a", "b", "some label") in idx.edges
    assert {"a", "b"} <= set(idx.nodes)
    assert "label" not in idx.nodes


def test_style_detected():
    idx = index_mermaid(FLOWCHART + "    style gw fill:#f00\n")
    assert idx.has_style is True


def test_flowchart_edge_with_inline_source_label():
    idx = index_mermaid("flowchart LR\n    web[Web] -->|calls| api[API]\n")
    assert ("web", "api", "calls") in idx.edges
    assert idx.nodes == {"web": "Web", "api": "API"}


def test_flowchart_edge_with_double_brace_source_label():
    idx = index_mermaid("flowchart LR\n    q{{Queue}} -->|feeds| w[Worker]\n")
    assert ("q", "w", "feeds") in idx.edges


def test_unrecognizable_raises():
    with pytest.raises(ValueError):
        index_mermaid("this is not mermaid\n")


def test_chained_flowchart_edges():
    # A chained edge line (`a --> b --> c`) must record both hops, not just the
    # first: a single non-restarting search drops the second hop entirely.
    idx = index_mermaid("flowchart LR\n    a[A] --> b[B] --> c[(C)]\n")
    assert ("a", "b", "") in idx.edges
    assert ("b", "c", "") in idx.edges


def test_hyphenated_sequence_participant_and_message():
    idx = index_mermaid(
        "sequenceDiagram\n"
        "    participant auth-api\n"
        "    participant db\n"
        "    auth-api->>db: read row\n"
        "    db-->>auth-api: rows\n"
    )
    assert "auth-api" in idx.participants
    assert idx.messages == 2
    assert ("auth-api", "db", "read row") in idx.edges
    assert ("db", "auth-api", "rows") in idx.edges


def test_unhyphenated_sequence_messages_still_parse():
    idx = index_mermaid(
        "sequenceDiagram\n    participant a\n    participant b\n"
        "    a->>b: hi\n    a--)b: ack\n    a-xb: drop\n"
    )
    assert idx.messages == 3
