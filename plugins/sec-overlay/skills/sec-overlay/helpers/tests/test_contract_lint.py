"""REQ-32 contract lint: code, schema, and prompt-constants must state one contract.

Each test reads a code constant and asserts the document or the schema agrees.
A failure here is drift, not a flaky test. Fix the document, not the assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

from sec_overlay.evidence import RUNTIME_DISPOSITIONS, TIER1_RECEIPTS, VERIFICATION_VALUES
from sec_overlay.models import AFFECTED_SITE_KEYS, OPEN_QUESTION_KEYS, RUNTIME_TEST_KEYS

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


def _block(name: str) -> str:
    """Return the body of a single ``## NAME`` block in prompt-constants.md."""
    text = CONSTS.read_text()
    marker = f"## {name}"
    assert marker in text, f"{name} block missing from prompt-constants.md"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def test_published_finding_shapes_match_the_model():
    block = _block("FINDING_SHAPES")
    for field, keys in (
        ("runtime_test", RUNTIME_TEST_KEYS),
        ("open_questions", OPEN_QUESTION_KEYS),
        ("affected_sites", AFFECTED_SITE_KEYS),
    ):
        assert field in block, f"{field} shape not published"
        for key in keys:
            assert f"`{key}`" in block, f"{field}.{key} missing from FINDING_SHAPES"


def test_investigate_prompt_imports_the_published_shapes():
    text = (AGENTS / "investigate.md").read_text()
    assert "FINDING_SHAPES" in text, "investigate.md does not import FINDING_SHAPES"


def test_validate_prompt_states_the_tier1_confirmation_rule():
    text = (AGENTS / "validate.md").read_text()
    for receipt in sorted(TIER1_RECEIPTS):
        assert receipt in text, f"validate.md never names the Tier-1 receipt {receipt}"
    assert "Tier-1" in text, "validate.md does not name the Tier-1 requirement"
    assert "needs-deployment-testing" in text, (
        "validate.md does not route a Tier-2-only finding to needs-deployment-testing"
    )


def test_validate_prompt_does_not_imply_tier2_confirms():
    """A Tier-2 receipt must never appear as sufficient for ``confirmed``."""
    text = (AGENTS / "validate.md").read_text()
    confirmed = text.split("**Confirmed**", 1)[1].split("- **Rejected**", 1)[0]
    assert "Tier-1" in confirmed, "the Confirmed verdict does not require a Tier-1 receipt"


def _imports_line(prompt: Path) -> str:
    """Return the ``## Imports`` section of an agent prompt, or an empty string."""
    text = prompt.read_text()
    if "## Imports" not in text:
        return ""
    return text.split("## Imports", 1)[1].split("\n## ", 1)[0]


def test_threat_model_prompt_imports_qualifier_proof():
    """REQ-10: the threat-model prompt grades severity, so it needs the qualifier rule."""
    imports = _imports_line(AGENTS / "threat-model.md")
    assert "QUALIFIER_PROOF" in imports, (
        "threat-model.md's ## Imports section does not name QUALIFIER_PROOF"
    )
