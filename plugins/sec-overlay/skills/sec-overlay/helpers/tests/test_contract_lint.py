"""REQ-32 contract lint: code, schema, and prompt-constants must state one contract.

Each test reads a code constant and asserts the document or the schema agrees.
A failure here is drift, not a flaky test. Fix the document, not the assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

from sec_overlay.evidence import RUNTIME_DISPOSITIONS, VERIFICATION_VALUES

SKILL = Path(__file__).resolve().parents[2]
CONSTS = SKILL / "references" / "prompt-constants.md"
SCHEMA = SKILL / "references" / "finding.schema.json"
AGENTS = SKILL / "agents"


def test_every_closed_vocabulary_matches_its_schema_enum():
    """Each code constant with a schema counterpart must equal that enum."""
    props = json.loads(SCHEMA.read_text())["properties"]
    for field, allowed in (
        ("verification", VERIFICATION_VALUES),
        ("runtime_disposition", RUNTIME_DISPOSITIONS),
    ):
        assert "enum" in props[field], f"{field} has no schema enum"
        assert set(props[field]["enum"]) == allowed | {None}, f"{field} drifted"
