"""Rule-doc resolution: map a changed file's path to its per-language rule doc.

Ports the OCR brace-expansion + `**`-aware glob matcher (Open Code Review's
`system_rules.go`) to stdlib-only Python. `pathlib`'s 3.13-only whole-path
matcher gives `**`-aware globbing natively but needs a newer floor than this
project's; segment-based matching is hand-rolled here instead (D-01, D-02, D-04).

Matching is case-insensitive on both pattern and path (D-04) and resolution
is first-match-wins over an ordered path->doc-filename map, falling back to
``default.md`` when nothing matches (D-03).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

BUILTIN_DEFAULT_RULE = "default.md"

# Ordered: first matching glob wins. New entries append before default's
# catch-all is implied by resolve_rule_doc's fallback (no `**/*` entry here).
BUILTIN_PATH_RULE_MAP: dict[str, str] = {
    "**/*.py": "python.md",
}


def expand_braces(pattern: str) -> list[str]:
    """Expand the first `{a,b,c}` brace group in a glob pattern.

    Non-recursive: only the first group is expanded. A pattern with no
    brace group returns unchanged as a single-element list.

    Args:
        pattern: A glob pattern, e.g. ``"**/*.{ts,js}"``.

    Returns:
        One pattern per comma-separated alternative in the first group.
    """
    start = pattern.find("{")
    if start == -1:
        return [pattern]
    end = pattern.find("}", start)
    if end == -1:
        return [pattern]
    prefix = pattern[:start]
    suffix = pattern[end + 1 :]
    alternatives = pattern[start + 1 : end].split(",")
    return [f"{prefix}{alt}{suffix}" for alt in alternatives]


def _match_segments(pattern_segments: list[str], path_segments: list[str]) -> bool:
    """Match path segments against pattern segments, `**` spanning zero or more."""
    if not pattern_segments:
        return not path_segments
    head, *rest = pattern_segments
    if head == "**":
        if _match_segments(rest, path_segments):
            return True
        return bool(path_segments) and _match_segments(pattern_segments, path_segments[1:])
    if not path_segments:
        return False
    if not fnmatch.fnmatchcase(path_segments[0], head):
        return False
    return _match_segments(rest, path_segments[1:])


def glob_match(pattern: str, path: str) -> bool:
    """Match `path` against a single glob `pattern`, `**` spanning path segments.

    Case-insensitive on both sides. Does not handle brace groups — call
    :func:`expand_braces` first and try each alternative.

    Args:
        pattern: A glob pattern, e.g. ``"**/*.py"``.
        path: A forward-slash-separated relative path.

    Returns:
        Whether the path matches the pattern.
    """
    pattern_segments = pattern.lower().split("/")
    path_segments = path.lower().split("/")
    return _match_segments(pattern_segments, path_segments)


def builtin_rule_docs_dir() -> Path:
    """Return the built-in rule-docs directory, resolved from this file's location.

    Never derived from cwd (T-03-01) — resolution must be stable regardless of
    where the CLI is invoked from.
    """
    return Path(__file__).resolve().parents[2] / "rules" / "rule_docs"


def resolve_rule_doc(path: str) -> str:
    """Resolve a changed file's path to its rule-doc text, first-match-wins.

    Args:
        path: A forward-slash-separated relative path to the changed file.

    Returns:
        The text of the matched rule doc, or ``default.md``'s text if no
        entry in :data:`BUILTIN_PATH_RULE_MAP` matches.
    """
    docs_dir = builtin_rule_docs_dir()
    for pattern, doc_name in BUILTIN_PATH_RULE_MAP.items():
        for expanded in expand_braces(pattern):
            if glob_match(expanded, path):
                return (docs_dir / doc_name).read_text()
    return (docs_dir / BUILTIN_DEFAULT_RULE).read_text()
