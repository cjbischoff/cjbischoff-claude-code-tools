"""Parse unified-diff hunks, mirroring OCR's internal/diff/hunk.go line classification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
NO_NEWLINE_MARKER = "\\ No newline at end of file"


@dataclass(frozen=True)
class Hunk:
    """One unified-diff hunk, with lines classified by side.

    Frozen with tuple collections so ``parse_hunks`` is a pure function: repeated
    calls on identical input return equal, unmodifiable results that can be
    shared across the positioning and gate stages with no defensive copy.

    ``added`` and ``deleted`` carry ``(line_number, content)`` pairs on their
    respective side; ``context`` carries content only — it appears on both
    sides at an offset, and no consumer needs its line number yet.
    """

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: tuple[tuple[int, str], ...] = field(default_factory=tuple)
    deleted: tuple[tuple[int, str], ...] = field(default_factory=tuple)
    context: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class _MutableHunk:
    """Builder for one hunk while its body lines are still streaming in."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    added: list[tuple[int, str]] = field(default_factory=list)
    deleted: list[tuple[int, str]] = field(default_factory=list)
    context: list[str] = field(default_factory=list)

    def freeze(self) -> Hunk:
        return Hunk(
            self.old_start,
            self.old_count,
            self.new_start,
            self.new_count,
            tuple(self.added),
            tuple(self.deleted),
            tuple(self.context),
        )


def parse_hunks(diff_text: str) -> list[Hunk]:
    """Parse every hunk in a unified diff for a single file.

    Everything before the first ``@@`` header (the ``diff --git``/``---``/``+++``
    preamble) is ignored, which structurally excludes those file-header lines
    even though they share a leading ``+``/``-`` with real body lines. A leading
    ``+`` classifies as added, a leading ``-`` as deleted, anything else as
    context with its marker stripped. An absent hunk count (``@@ -N +M @@``, no
    comma) defaults to 1; an explicit ``0`` count stays 0. The "no newline at
    end of file" marker line is skipped. Splitting with ``str.splitlines()``
    normalizes CRLF line endings so no ``\\r`` survives into a stored line, and
    leaves no spurious trailing empty line for a diff ending in a newline.

    Args:
        diff_text: Unified diff text for one file.

    Returns:
        Parsed hunks in file order.
    """
    hunks: list[Hunk] = []
    current: _MutableHunk | None = None
    old_line = new_line = 0
    for raw_line in diff_text.splitlines():
        match = _HUNK_RE.match(raw_line)
        if match:
            if current is not None:
                hunks.append(current.freeze())
            old_start = int(match.group(1))
            old_count = int(match.group(2) or 1)
            new_start = int(match.group(3))
            new_count = int(match.group(4) or 1)
            current = _MutableHunk(old_start, old_count, new_start, new_count)
            old_line, new_line = old_start, new_start
            continue
        if current is None:
            continue
        if raw_line.startswith(NO_NEWLINE_MARKER):
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
        hunks.append(current.freeze())
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


def hunk_for_line(hunks: list[Hunk], line: int) -> Hunk | None:
    """Return the hunk whose new-side range contains ``line``, or ``None``.

    Args:
        hunks: Parsed hunks.
        line: A new-side line number.

    Returns:
        The containing :class:`Hunk`, or ``None`` if no hunk contains ``line``.
    """
    for hunk in hunks:
        if hunk.new_start <= line < hunk.new_start + hunk.new_count:
            return hunk
    return None
