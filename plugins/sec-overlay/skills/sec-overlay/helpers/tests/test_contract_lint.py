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

from sec_overlay.calibrate import (
    JUDGE_VERDICTS,
    PRECONDITION_CAP_FLOOR,
    PRECONDITION_CAPS,
    _precondition_cap,
)
from sec_overlay.driver import DISPATCH_TOKENS, render_dispatch
from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    TIER1_RECEIPTS,
    TIER2_RECEIPTS,
    VERIFICATION_VALUES,
    receipt_tier,
)
from sec_overlay.fix_disposition import TIERS
from sec_overlay.models import AFFECTED_SITE_KEYS, OPEN_QUESTION_KEYS, RUNTIME_TEST_KEYS, Finding
from sec_overlay.reachability import BLOCKERS

SKILL = Path(__file__).resolve().parents[2]
CONSTS = SKILL / "references" / "prompt-constants.md"
SCHEMA = SKILL / "references" / "finding.schema.json"
AGENTS = SKILL / "agents"


def test_every_closed_vocabulary_matches_its_schema_enum():
    """Each code constant with a schema counterpart must equal that enum (REQ-50)."""
    props = json.loads(SCHEMA.read_text())["properties"]
    receipt_tiers = frozenset(receipt_tier(f"{p}:x") for p in TIER1_RECEIPTS | TIER2_RECEIPTS)
    for field, allowed in (
        ("verification", VERIFICATION_VALUES),
        ("runtime_disposition", RUNTIME_DISPOSITIONS),
        ("completeness_tier", frozenset(TIERS)),
        ("judge_verdict", JUDGE_VERDICTS),
        ("receipt_tier", receipt_tiers),
    ):
        assert "enum" in props[field], f"{field} has no schema enum"
        assert set(props[field]["enum"]) == allowed | {None}, f"{field} drifted"
    blocker = props["reachability"]["properties"]["blocker"]
    assert set(blocker["enum"]) == frozenset(BLOCKERS) | {None}, "reachability.blocker drifted"


def test_nested_item_schemas_declare_their_published_keys():
    """``open_questions``, ``affected_sites``, and ``history`` items are typed (REQ-50)."""
    props = json.loads(SCHEMA.read_text())["properties"]
    for field, keys in (
        ("open_questions", OPEN_QUESTION_KEYS),
        ("affected_sites", AFFECTED_SITE_KEYS),
    ):
        item = props[field]["items"]
        assert set(item["properties"]) == set(keys), f"{field} item schema drifted"
        assert "required" not in item, f"{field} items must require nothing (ruling R-7)"
    history = props["history"]["items"]
    assert history["required"] == ["event"], "history items must require event"
    assert set(history["properties"]) == {"event"}, "history item schema drifted"


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


def test_operator_notes_name_every_phase_and_nothing_else():
    """The note keys and the PHASE_TABLE phase names are one set (ruling P5-10)."""
    from sec_overlay.phase_docs import NOTE_DOCUMENTS, note_keys
    from sec_overlay.phases import PHASE_TABLE

    phases = {p.name for p in PHASE_TABLE}
    for doc in NOTE_DOCUMENTS:
        keys = set(note_keys(doc.read_text()))
        assert keys == phases, (
            f"{doc.name} note keys drifted from PHASE_TABLE — "
            f"missing: {sorted(phases - keys)}; extra: {sorted(keys - phases)}"
        )


def test_operator_notes_follow_the_table_order():
    """A reorder in PHASE_TABLE must fail until the notes follow it."""
    from sec_overlay.phase_docs import NOTE_DOCUMENTS, note_keys
    from sec_overlay.phases import PHASE_TABLE

    order = [p.name for p in PHASE_TABLE]
    for doc in NOTE_DOCUMENTS:
        keys = note_keys(doc.read_text())
        assert keys == sorted(keys, key=order.index), f"{doc.name} is out of table order"


def test_pipeline_documents_name_only_substitutable_tokens():
    """Every {{TOKEN}} in a pipeline document has a substituter."""
    from sec_overlay.phase_docs import DOCUMENTS, NOTE_DOCUMENTS, ORCHESTRATOR_TOKENS

    known = set(DISPATCH_TOKENS) | set(ORCHESTRATOR_TOKENS)
    for doc in dict.fromkeys((*DOCUMENTS, *NOTE_DOCUMENTS)):
        found = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", doc.read_text()))
        assert found <= known, f"{doc.name} names tokens nothing substitutes: {found - known}"
