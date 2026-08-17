"""Parse unified-diff hunks, mirroring OCR's internal/diff/hunk.go line classification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass
class Hunk:
    """One unified-diff hunk, with lines classified by side.

    ``added`` and ``deleted`` carry ``(line_number, content)`` pairs on their
    respective side; ``context`` carries content only — it appears on both
    sides at an offset, and no consumer needs its line number yet.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: list[tuple[int, str]] = field(default_factory=list)
    deleted: list[tuple[int, str]] = field(default_factory=list)
    context: list[str] = field(default_factory=list)


def parse_hunks(diff_text: str) -> list[Hunk]:
    """Parse every hunk in a unified diff for a single file.

    Everything before the first ``@@`` header (the ``diff --git``/``---``/``+++``
    preamble) is ignored. A leading ``+`` classifies as added, a leading ``-`` as
    deleted, anything else as context with its marker stripped. An absent hunk
    count (``@@ -N +M @@``, no comma) defaults to 1. The "no newline at end of
    file" marker line is skipped.

    Args:
        diff_text: Unified diff text for one file.

    Returns:
        Parsed hunks in file order.
    """
    hunks: list[Hunk] = []
    current: Hunk | None = None
    old_line = new_line = 0
    for raw_line in diff_text.split("\n"):
        match = _HUNK_RE.match(raw_line)
        if match:
            if current is not None:
                hunks.append(current)
            old_start = int(match.group(1))
            old_count = int(match.group(2) or 1)
            new_start = int(match.group(3))
            new_count = int(match.group(4) or 1)
            current = Hunk(old_start, old_count, new_start, new_count)
            old_line, new_line = old_start, new_start
            continue
        if current is None:
            continue
        if raw_line.startswith("\\ No newline at end of file"):
            continue
        if raw_line.startswith("+"):
            current.added.append((new_line, raw_line[1:]))
            new_line += 1
        elif raw_line.startswith("-"):
            current.deleted.append((old_line, raw_line[1:]))
            old_line += 1
        else:
            current.context.append(raw_line[1:] if raw_line else raw_line)
            old_line += 1
            new_line += 1
    if current is not None:
        hunks.append(current)
    return hunks


def added_line_numbers(hunks: list[Hunk]) -> set[int]:
    """Return every new-side line number introduced by ``added`` lines.

    Args:
        hunks: Parsed hunks.

    Returns:
        The set of added line numbers across all hunks.
    """
    return {line for hunk in hunks for line, _ in hunk.added}


def line_in_hunk(hunks: list[Hunk], line: int) -> bool:
    """Return True when ``line`` falls in any hunk's new-side range.

    Args:
        hunks: Parsed hunks.
        line: A new-side line number.

    Returns:
        True if ``line`` is within ``[new_start, new_start + new_count)`` of
        any hunk.
    """
    return any(hunk.new_start <= line < hunk.new_start + hunk.new_count for hunk in hunks)
