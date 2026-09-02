"""Render the phase order from ``PHASE_TABLE`` into the documents that state it.

Every document that states the order carries a marked block::

    <!-- BEGIN GENERATED: phase-table columns=index,phase,kind -->
    | # | Phase | Kind |
    ...
    <!-- END GENERATED: phase-table -->

The marker's own ``columns`` and optional ``kind`` attributes select what that
block holds, so one renderer serves every document and no per-document column
registry can drift from the document it describes.

The skill root ``CLAUDE.md`` is one of ``DOCUMENTS`` but stays markerless: it is
the maintainer's quick map, capped at 200 lines by repo governance, and points
at ``SKILL.md`` for the full table and the per-phase operator notes
(``NOTE_DOCUMENTS``) instead of carrying either itself. ``regenerate`` is a
no-op on a markerless document, so ``--write`` never touches it.

``python -m sec_overlay.phase_docs --check`` fails when a block is stale;
``--write`` rewrites every stale block. The contract lint calls the same code, so
a phase rename or reorder fails a test until the documents regenerate.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

from sec_overlay.phases import PHASE_TABLE, PathOf, PhaseSpec
from sec_overlay.workspace import Workspace

# Every token a skill document names that some producer other than
# `driver.render_dispatch` substitutes:
# - `review_agent.py` supplies BACKGROUND, CHANGE_FILES, CURRENT_FILE_PATH, DIFF,
#   PLAN_GUIDANCE, SIBLING_DIFFS, SYSTEM_RULE, REPO_ROOT
# - `reflection.py` supplies COMMENTS, PATH, DIFF
# - `prompts.py` supplies KEY
# - the orchestrator supplies PHASE, ROUND, SCAN_SCOPE
# Keeping these listed separately from `DISPATCH_TOKENS` lets Task 5's contract
# lint tell "known, supplied elsewhere" apart from "genuinely unfilled".
ORCHESTRATOR_TOKENS: tuple[str, ...] = (
    "BACKGROUND",
    "CHANGE_FILES",
    "COMMENTS",
    "CURRENT_FILE_PATH",
    "DIFF",
    "KEY",
    "PATH",
    "PHASE",
    "PLAN_GUIDANCE",
    "REPO_ROOT",
    "ROUND",
    "SCAN_SCOPE",
    "SIBLING_DIFFS",
    "SYSTEM_RULE",
)

SKILL_ROOT = Path(__file__).resolve().parents[2]

DOCUMENTS: tuple[Path, ...] = (
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "README.md",
    SKILL_ROOT / "agents" / "README.md",
    SKILL_ROOT / "helpers" / "README.md",
    SKILL_ROOT / "CLAUDE.md",
)

# The document that also holds per-phase operator notes. CLAUDE.md is in
# DOCUMENTS but not here — see the module docstring.
NOTE_DOCUMENTS: tuple[Path, ...] = (SKILL_ROOT / "SKILL.md",)

# ``\r?$`` so a document saved with Windows line endings still matches: the bare
# ``$`` anchor sits after the ``\r``, so a CRLF marker line never matched and
# ``regenerate`` returned the stale text with no error.
_BEGIN = re.compile(r"^<!-- BEGIN GENERATED: phase-table(?P<attrs>[^>]*)-->\r?$", re.MULTILINE)
_END = "<!-- END GENERATED: phase-table -->"

_NOTES_BEGIN = "<!-- BEGIN PHASE NOTES -->"
_NOTES_END = "<!-- END PHASE NOTES -->"
_NOTE_KEY = re.compile(r"^ *[-*] +\*\*(?P<key>[a-z0-9][a-z0-9_.-]*)\*\* +—", re.MULTILINE)

_HEADINGS = {
    "index": "#",
    "phase": "Phase",
    "kind": "Kind",
    "prompt": "Prompt",
    "reads": "Reads",
    "writes": "Writes",
}

# A path-only workspace: every PathOf in the table derives from ``ws.root``, so a
# literal root renders each declared artifact as a workspace-relative path with no
# filesystem access and no absolute path leaking into a document.
_WS = Workspace(root="workspace")


def _artifacts(getters: Sequence[PathOf]) -> str:
    """Render one phase's declared artifact paths, workspace-relative."""
    if not getters:
        return "—"
    return "<br>".join(f"`{g(_WS).relative_to(_WS.root).as_posix()}`" for g in getters)


def _cell(phase: PhaseSpec, index: int, column: str) -> str:
    """Render one table cell.

    Args:
        phase: The phase the row describes.
        index: The phase's 1-based position in the full ``PHASE_TABLE``.
        column: One key of ``_HEADINGS``.

    Returns:
        The cell's markdown text.

    Raises:
        ValueError: ``column`` is not a known column name.
    """
    if column == "index":
        return str(index)
    if column == "phase":
        return f"`{phase.name}`"
    if column == "kind":
        return phase.kind
    if column == "prompt":
        return f"`agents/{phase.prompt}`" if phase.prompt else "—"
    if column == "reads":
        return _artifacts(phase.inputs)
    if column == "writes":
        return _artifacts(phase.outputs)
    raise ValueError(f"unknown phase-table column: {column}")


def render_phase_table(columns: tuple[str, ...], kind: str | None = None) -> str:
    """Return the markdown table for ``columns``, optionally one ``kind`` only.

    The index column always counts positions in the full ``PHASE_TABLE``, so a
    filtered view still states each phase's real place in the run.

    Args:
        columns: Column keys, in render order; each must be a ``_HEADINGS`` key.
        kind: ``"agent"`` or ``"deterministic"`` to filter rows; ``None`` for all.

    Returns:
        The table as markdown, with no trailing newline.
    """
    rows = [(i, p) for i, p in enumerate(PHASE_TABLE, start=1) if kind is None or p.kind == kind]
    head = "| " + " | ".join(_HEADINGS[c] for c in columns) + " |"
    rule = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(_cell(p, i, c) for c in columns) + " |" for i, p in rows]
    return "\n".join([head, rule, *body])


def _attrs(raw: str) -> tuple[tuple[str, ...], str | None]:
    """Parse a marker's ``columns=`` and optional ``kind=`` attributes.

    Args:
        raw: The marker text between ``phase-table`` and ``-->``.

    Returns:
        The column keys and the kind filter, or ``None`` for no filter.

    Raises:
        ValueError: The marker declares no columns.
    """
    found = dict(re.findall(r"(\w+)=([\w,\-]+)", raw))
    if "columns" not in found:
        raise ValueError("phase-table marker declares no columns=")
    return tuple(found["columns"].split(",")), found.get("kind")


def regenerate(text: str) -> str:
    """Return ``text`` with every phase-table block replaced by fresh output.

    Blocks are rewritten last-first, so an earlier match's offsets stay valid.
    Every block is validated before any rewrite, so a malformed document raises
    with nothing written.

    Args:
        text: A document's full text.

    Returns:
        The same text with each block regenerated.

    Raises:
        ValueError: A block has no end marker, a second BEGIN marker opens
            before the current block's END, or a marker declares no columns.
    """
    blocks = []
    matches = list(_BEGIN.finditer(text))
    for i, m in enumerate(matches):
        stop = text.find(_END, m.end())
        if stop < 0:
            raise ValueError("phase-table block has no END marker")
        if i + 1 < len(matches) and matches[i + 1].start() < stop:
            # A nested BEGIN would be swallowed by the outer rewrite, silently
            # deleting itself and everything between the two markers.
            line = text.count("\n", 0, matches[i + 1].start()) + 1
            raise ValueError(f"nested phase-table BEGIN marker at line {line}")
        blocks.append((m, stop))
    out = text
    for m, stop in reversed(blocks):
        columns, kind = _attrs(m.group("attrs"))
        out = out[: m.end()] + "\n" + render_phase_table(columns, kind) + "\n" + out[stop:]
    return out


def note_keys(text: str) -> list[str]:
    """Return the phase keys of a document's operator-note list, in order.

    Args:
        text: A document's full text, holding one phase-notes region.

    Returns:
        The bolded key of each ``- **<key>** — …`` item, in document order.

    Raises:
        ValueError: The document has no phase-notes region.
    """
    if _NOTES_BEGIN not in text or _NOTES_END not in text:
        raise ValueError("document has no phase-notes region")
    body = text.split(_NOTES_BEGIN, 1)[1].split(_NOTES_END, 1)[0]
    return [m.group("key") for m in _NOTE_KEY.finditer(body)]


def main(argv: list[str] | None = None) -> int:
    """Check or rewrite every generated phase-table block.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        1 when ``--check`` found a stale block, else 0.
    """
    ap = argparse.ArgumentParser(description="Generate phase-order document blocks.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when a block is stale")
    mode.add_argument("--write", action="store_true", help="rewrite every stale block")
    args = ap.parse_args(argv)
    stale = []
    for doc in DOCUMENTS:
        text = doc.read_text()
        fresh = regenerate(text)
        if fresh == text:
            continue
        stale.append(doc)
        if args.write:
            doc.write_text(fresh)
    for doc in stale:
        print(f"{'rewrote' if args.write else 'stale'}: {doc}")
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
