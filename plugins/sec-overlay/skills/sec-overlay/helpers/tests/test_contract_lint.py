"""REQ-32 contract lint: code, schema, and prompt-constants must state one contract.

Each test reads a code constant and asserts the document or the schema agrees.
A failure here is drift, not a flaky test. Fix the document, not the assertion.

Property (c) of REQ-32 — every ``{{TOKEN}}`` in a prompt is in the dispatch
substitution map, and ``render_dispatch`` builds its ``substitute:`` line from
that same map — closed by REQ-08, which also added the three unmapped tokens.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sec_overlay.calibrate import PRECONDITION_CAP_FLOOR, PRECONDITION_CAPS, _precondition_cap
from sec_overlay.driver import DISPATCH_TOKENS, render_dispatch
from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    TIER1_RECEIPTS,
    TIER2_RECEIPTS,
    VERIFICATION_VALUES,
)
from sec_overlay.models import AFFECTED_SITE_KEYS, OPEN_QUESTION_KEYS, RUNTIME_TEST_KEYS, Finding

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


def _doc_key_set(field: str) -> set[str]:
    """Return the key names the ``Finding`` docstring publishes for one nested field."""
    doc = Finding.__doc__ or ""
    header = re.search(rf"^ {{4}}{field}: ", doc, re.MULTILINE)
    assert header, f"{field} has no Attributes entry in the Finding docstring"
    rest = doc[header.end() :]
    nxt = re.search(r"^ {4}\w+: ", rest, re.MULTILINE)
    para = rest[: nxt.start()] if nxt else rest
    group = re.search(r"\{[^{}]*\}|\([^()]*\)", para)
    assert group, f"{field}'s docstring paragraph names no key group"
    return set(re.findall(r'(?:``|")([a-z_]+)(?:``|")', group.group(0)))


def _prose_bullet_keys(block: str, field: str) -> set[str]:
    """Return the key set one ``FINDING_SHAPES`` bullet publishes for a field."""
    marker = f"- **`{field}`**"
    assert marker in block, f"{field} shape not published"
    bullet = block.split(marker, 1)[1].split("\n- ", 1)[0]
    flat = " ".join(bullet.split())
    keys = re.search(r"Keys[^:]*:\s*(.*?)\.", flat)
    assert keys, f"{field}'s bullet names no key list"
    return set(re.findall(r"`([a-z_]+)`", keys.group(1)))


def test_published_finding_shapes_match_the_model():
    """The docstring, the key tuples, and the prose must state one key set each."""
    block = _block("FINDING_SHAPES")
    published = set()
    for field, keys in (
        ("runtime_test", RUNTIME_TEST_KEYS),
        ("open_questions", OPEN_QUESTION_KEYS),
        ("affected_sites", AFFECTED_SITE_KEYS),
    ):
        assert _doc_key_set(field) == set(keys), f"{field}: the docstring drifted from the tuple"
        assert _prose_bullet_keys(block, field) == set(keys), (
            f"{field}: FINDING_SHAPES drifted from the tuple"
        )
        published |= set(keys) | {field}
    assert set(re.findall(r"`([a-z_]+)`", block)) == published, (
        "FINDING_SHAPES names a key or field the model does not declare"
    )


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


def test_validate_prompt_lists_every_tier2_receipt():
    """REQ-07: the prompt's Tier-2 list is a copy of the code's, so it must match it."""
    text = (AGENTS / "validate.md").read_text()
    listed = set(re.findall(r"`([a-z-]+):`", text))
    assert TIER2_RECEIPTS <= listed, f"validate.md omits the Tier-2 receipts {TIER2_RECEIPTS - listed}"
    # llm-claimed is a real backtick-colon token in validate.md but is not a mechanical
    # receipt (evidence.py:50) — it corroborates, never confirms, so it never appears in
    # TIER1_RECEIPTS or TIER2_RECEIPTS. Subtract it by name rather than loosen the check.
    extra = listed - TIER1_RECEIPTS - TIER2_RECEIPTS - {"llm-claimed"}
    assert not extra, f"validate.md names receipts the code does not grade: {extra}"


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


def test_precondition_cap_thresholds_are_published():
    """The document must state the cap table the harness actually applies."""
    block = _block("SEVERITY_PRECONDITION")
    assert "weight" in block.lower(), "the block still describes a count, not a weight"
    bands = tuple(
        (float(t), int(cap))
        for t, cap in re.findall(r"below (\d+(?:\.\d+)?) caps at\s+(\d+)", block)
    )
    assert bands == PRECONDITION_CAPS, f"the published cap bands {bands} drifted from the code"
    floor = re.search(r"(\d+(?:\.\d+)?) or more caps at\s+(\d+)", block)
    assert floor, "the block never states the cap floor"
    assert float(floor.group(1)) == PRECONDITION_CAPS[-1][0], "the floor threshold drifted"
    assert int(floor.group(2)) == PRECONDITION_CAP_FLOOR, "the floor cap drifted"


def test_precondition_cap_reads_the_published_table():
    """_precondition_cap must derive from PRECONDITION_CAPS, not a second copy."""
    assert _precondition_cap([]) == PRECONDITION_CAPS[0][1]
    # one strong precondition weighs 1.0, so it lands in the second band
    assert _precondition_cap(["non-default config"]) == PRECONDITION_CAPS[1][1]


def test_dispatch_tokens_are_a_single_source(tmp_path):
    """render_dispatch must build its substitute line from DISPATCH_TOKENS."""
    from sec_overlay.driver import AuditContext
    from sec_overlay.phases import PHASE_TABLE
    from sec_overlay.workspace import Workspace

    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    ctx = AuditContext(target=str(tmp_path / "repo"), ws=ws, config="", sha="deadbeef")
    phase = next(p for p in PHASE_TABLE if p.prompt == "investigate.md")
    block = render_dispatch(phase, ctx, classes=["ssrf"])
    line = next(ln for ln in block.splitlines() if ln.strip().startswith("substitute:"))
    rendered = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}=", line))
    assert rendered == set(DISPATCH_TOKENS), (
        f"the substitute line and DISPATCH_TOKENS disagree: {rendered ^ set(DISPATCH_TOKENS)}"
    )
    assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*", t) for t in DISPATCH_TOKENS)
