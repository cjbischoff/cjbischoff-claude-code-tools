"""REQ-61: every document states the phase order the code holds."""

from __future__ import annotations

from dataclasses import replace

from sec_overlay import phase_docs
from sec_overlay.phase_docs import DOCUMENTS, regenerate, render_phase_table
from sec_overlay.phases import PHASE_TABLE


def test_every_document_carries_a_generated_block():
    for doc in DOCUMENTS:
        if doc.name == "CLAUDE.md":
            continue  # markerless by design — see test_claude_md_carries_no_generated_block
        assert "<!-- BEGIN GENERATED: phase-table" in doc.read_text(), doc.name


def test_every_generated_block_is_current():
    for doc in DOCUMENTS:
        text = doc.read_text()
        assert regenerate(text) == text, f"{doc.name} phase-table block is stale"


def test_the_table_states_every_phase_in_order():
    out = render_phase_table(("index", "phase"))
    rows = [ln for ln in out.splitlines()[2:] if ln.startswith("|")]
    assert len(rows) == len(PHASE_TABLE)
    for i, (row, phase) in enumerate(zip(rows, PHASE_TABLE, strict=True), start=1):
        assert row.startswith(f"| {i} | `{phase.name}` |")


def test_a_kind_filter_keeps_the_full_table_index():
    out = render_phase_table(("index", "phase"), kind="agent")
    rows = [ln for ln in out.splitlines()[2:] if ln.startswith("|")]
    agents = [(i, p) for i, p in enumerate(PHASE_TABLE, start=1) if p.kind == "agent"]
    assert len(rows) == len(agents)
    assert rows[0].startswith(f"| {agents[0][0]} | `{agents[0][1].name}` |")


def test_renaming_a_phase_makes_a_block_stale(monkeypatch):
    renamed = tuple(
        replace(p, name="renamed-phase") if p.name == "dedupe" else p for p in PHASE_TABLE
    )
    monkeypatch.setattr(phase_docs, "PHASE_TABLE", renamed)
    for doc in DOCUMENTS:
        text = doc.read_text()
        if "`dedupe`" in text:
            assert regenerate(text) != text, doc.name


def test_check_mode_passes_and_reports_nothing(capsys):
    assert phase_docs.main(["--check"]) == 0
    assert capsys.readouterr().out == ""


def test_claude_md_carries_no_generated_block():
    """P5-2: the skill CLAUDE.md points at SKILL.md instead of duplicating the table."""
    claude_md = phase_docs.SKILL_ROOT / "CLAUDE.md"
    text = claude_md.read_text()
    assert "<!-- BEGIN GENERATED: phase-table" not in text
    assert "<!-- BEGIN PHASE NOTES -->" not in text
    assert "SKILL.md" in text


def test_note_documents_is_skill_md_only():
    assert phase_docs.NOTE_DOCUMENTS == (phase_docs.SKILL_ROOT / "SKILL.md",)


def test_claude_md_is_in_documents_but_not_note_documents():
    claude_md = phase_docs.SKILL_ROOT / "CLAUDE.md"
    assert claude_md in DOCUMENTS
    assert claude_md not in phase_docs.NOTE_DOCUMENTS


def test_every_table_phase_has_a_note_in_skill_md():
    (skill_md,) = phase_docs.NOTE_DOCUMENTS
    keys = phase_docs.note_keys(skill_md.read_text())
    assert keys == [p.name for p in PHASE_TABLE]
