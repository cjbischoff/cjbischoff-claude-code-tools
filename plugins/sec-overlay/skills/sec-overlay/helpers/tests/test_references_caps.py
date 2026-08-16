import re
from pathlib import Path

from sec_overlay.diagram_gate import CAPS, SEQ_CAPS

_CAPS_MD = Path(__file__).resolve().parents[1].parent / "references" / "mermaid-caps.md"


def test_caps_table_matches_gate_constants():
    text = _CAPS_MD.read_text()
    rows = dict(re.findall(r"^\|\s*([a-z-]+)\s*\|\s*(\d+)", text, re.MULTILINE))
    assert int(rows["context"]) == CAPS["context"]
    assert int(rows["container"]) == CAPS["container"]
    assert int(rows["component"]) == CAPS["component"]
    assert int(rows["dfd"]) == CAPS["dfd"]
    assert int(rows["sequence-participants"]) == SEQ_CAPS[0]
    assert int(rows["sequence-messages"]) == SEQ_CAPS[1]
