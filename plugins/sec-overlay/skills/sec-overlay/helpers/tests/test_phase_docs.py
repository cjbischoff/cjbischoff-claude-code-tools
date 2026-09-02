"""REQ-61: every document states the phase order the code holds."""

from __future__ import annotations

from dataclasses import replace

import pytest

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


_BEGIN_MARKER = "<!-- BEGIN GENERATED: phase-table columns=index,phase -->"
_END = "<!-- END GENERATED: phase-table -->"


def test_a_nested_begin_marker_raises_instead_of_deleting_the_text():
    """A second BEGIN before the END must fail loudly, naming the line.

    Without the guard the outer block swallows the inner marker and everything
    between them, so a mis-edited document loses text on the next ``--write``.
    """
    lines = ("intro", _BEGIN_MARKER, "| # | Phase |", _BEGIN_MARKER, "| # | Phase |", _END, "out")
    text = "\n".join(lines)
    with pytest.raises(ValueError, match="line 4"):
        regenerate(text)


def test_a_crlf_document_regenerates():
    """The BEGIN pattern must match a marker line that ends ``\\r\\n``.

    A document saved with Windows line endings put a ``\\r`` between the marker
    and the newline, so the ``$`` anchor never matched and ``regenerate``
    silently returned the stale text.
    """
    lines = ("intro", _BEGIN_MARKER, "| stale |", _END, "outro")
    text = "\r\n".join(lines)
    out = regenerate(text)
    assert out != text, "the CRLF marker never matched"
    assert render_phase_table(("index", "phase")) in out
    assert "| stale |" not in out


def test_claude_md_is_in_documents_but_not_note_documents():
    claude_md = phase_docs.SKILL_ROOT / "CLAUDE.md"
    assert claude_md in DOCUMENTS
    assert claude_md not in phase_docs.NOTE_DOCUMENTS
