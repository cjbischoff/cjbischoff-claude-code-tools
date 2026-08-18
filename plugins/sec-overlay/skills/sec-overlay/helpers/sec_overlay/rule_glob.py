"""Rule-doc resolution: map a changed file's path to its per-language rule doc.

Ports the OCR brace-expansion + `**`-aware glob matcher (Open Code Review's
`system_rules.go`) to stdlib-only Python. `pathlib`'s 3.13-only whole-path
matcher gives `**`-aware globbing natively but needs a newer floor than this
project's; segment-based matching is hand-rolled here instead (D-01, D-02, D-04).

Matching is case-insensitive on both pattern and path (D-04) and built-in
resolution is first-match-wins over an ordered path->doc-filename map, falling
back to ``default.md`` when nothing matches (D-03).

RULE-02 layers this into two structurally separate algorithms that must never
share a code path:

- Per-path fallthrough (:func:`match_project_rule_entry`, walked by
  :func:`resolve_rule_doc`): custom > project > global > built-in, decided
  independently for every changed path.
- Whole-layer first-non-empty file-filter selection (:func:`build_file_filter`,
  Task 2): the entire include/exclude filter comes from ONE layer, chosen
  once for the whole run, never merged across layers.

RULE-04's :func:`merge_with_system_rule` concatenates built-in and user rule
text under fixed headers instead of replacing. RULE-03's
:func:`read_rule_file_safe` (Task 3) is the sole entry point for reading a
rule file off disk, diverging from OCR's ``readRuleFileSafe`` in three ways
mandated by this project's requirements — documented on that function.

All resolver functions take their config as an argument and hold no
module-level mutable state, so parallel resolution in Phase 4 cannot
interleave through a shared cache.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path

BUILTIN_DEFAULT_RULE = "default.md"
SYSTEM_RULE_HEADER = "## System-Specific Rules (Mandatory)"
USER_RULE_HEADER = "## User-Specific Rules (Mandatory)"

# Ordered: first matching glob wins. New entries append before default's
# catch-all is implied by resolve_rule_doc's fallback (no `**/*` entry here).
BUILTIN_PATH_RULE_MAP: dict[str, str] = {
    "**/*.py": "python.md",
}


@dataclass
class ProjectRuleEntry:
    """One glob-pattern-to-rule mapping inside a project/global rule.json layer.

    Mirrors OCR's `ProjectRuleEntry` JSON shape byte-for-byte (D-06) so an
    existing OCR config ports unchanged.

    Attributes:
        path: The glob pattern a changed file's path is matched against.
        rule: The entry's resolved rule text (a file's *content*, not its
            path — :func:`load_project_rule` reads the file at load time).
        merge_system_rule: When true, resolution concatenates the built-in
            rule text with `rule` (RULE-04) instead of replacing it.
    """

    path: str
    rule: str
    merge_system_rule: bool = False


@dataclass
class ProjectRule:
    """One rule.json layer: ordered entries plus an include/exclude filter.

    Attributes:
        entries: Ordered path->rule mappings, first-match-wins for per-path
            resolution (RULE-02, :func:`match_project_rule_entry`).
        include: Glob patterns consumed only by :func:`build_file_filter`'s
            whole-layer selection (Task 2) — never by per-path resolution.
        exclude: Glob patterns, same as `include`.
    """

    entries: list[ProjectRuleEntry] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass
class FileFilter:
    """The whole-run include/exclude filter selected by `build_file_filter`."""

    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass
class RuleResolution:
    """The assembled four-layer resolution `resolve_rule_doc` walks.

    Attributes:
        layers: `[custom, project, global]`, each a `ProjectRule` or `None`;
            built-in is implicit (`BUILTIN_PATH_RULE_MAP`) and always last.
        file_filter: The whole-layer exclude filter from `build_file_filter`,
            or `None` when no layer and no CLI `--exclude` supplied one.
        repo_root: Resolved repo root; relative rule-file paths and the
            safety gate's boundary check both anchor here.
    """

    layers: list[ProjectRule | None]
    file_filter: FileFilter | None
    repo_root: Path


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


def _resolve_builtin_or_default(path: str) -> str:
    """Match `path` against the built-in map, falling back to `default.md`.

    The original tracer resolution, kept as its own function since both
    `resolve_rule_doc`'s base case and `merge_with_system_rule`'s built-in
    side need it independently of any layered `RuleResolution`.
    """
    docs_dir = builtin_rule_docs_dir()
    for pattern, doc_name in BUILTIN_PATH_RULE_MAP.items():
        for expanded in expand_braces(pattern):
            if glob_match(expanded, path):
                return (docs_dir / doc_name).read_text()
    return (docs_dir / BUILTIN_DEFAULT_RULE).read_text()


def load_project_rule(path: Path, repo_root: Path) -> ProjectRule | None:
    """Load one rule.json layer, returning `None` when the file is absent.

    Follows `exclusions.load_exclusions`'s defensive-load idiom: a missing
    file contributes nothing rather than raising. Each entry's `rule` field
    is read from disk at load time (a placeholder read until Task 3 lands
    `read_rule_file_safe` — see that function's docstring), so by the time
    `match_project_rule_entry` runs, `entry.rule` already holds file *content*.

    Args:
        path: Path to the layer's `rule.json` file.
        repo_root: Repo root; a relative `rule` field resolves against this,
            not against `path`'s parent directory (mirrors OCR's
            `loadProjectRule`, which always resolves against `repoDir`).

    Returns:
        The parsed layer, or `None` if `path` does not exist.
    """
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    entries = [
        ProjectRuleEntry(
            path=raw["path"],
            rule=_read_entry_rule_placeholder(raw.get("rule", ""), repo_root),
            merge_system_rule=bool(raw.get("merge_system_rule", False)),
        )
        for raw in data.get("rules", [])
    ]
    return ProjectRule(
        entries=entries,
        include=list(data.get("include", [])),
        exclude=list(data.get("exclude", [])),
    )


def _read_entry_rule_placeholder(rule: str, repo_root: Path) -> str:
    """Read a rule-json entry's `rule` file (Task 1 placeholder for the safety gate).

    Resolves a relative `rule` value against `repo_root`, per OCR's
    `resolveRuleEntries`. Task 3 replaces every call site of this function
    with `read_rule_file_safe`, so every layer's rule file passes the same
    symlink/extension/boundary/size gate — this placeholder has none of that
    and exists only to keep Task 1's `load_project_rule` runnable before
    Task 3 lands.
    """
    file_path = Path(rule)
    if not file_path.is_absolute():
        file_path = repo_root / rule
    return file_path.read_text().rstrip("\n")


def match_project_rule_entry(layer: ProjectRule | None, path: str) -> ProjectRuleEntry | None:
    """Return the first entry in `layer` whose pattern matches `path`.

    The per-path fallthrough building block (RULE-02). Structurally separate
    from `build_file_filter`'s whole-layer selection (Task 2) — this walks
    one layer's entries looking for a per-path answer; that walks a list of
    layers looking for one whole-layer answer. Neither calls the other.

    Args:
        layer: One resolution layer, or `None` (an absent/empty layer).
        path: A forward-slash-separated relative path to the changed file.

    Returns:
        The first matching entry in JSON array order, or `None`.
    """
    if layer is None:
        return None
    for entry in layer.entries:
        for expanded in expand_braces(entry.path):
            if glob_match(expanded, path):
                return entry
    return None


def merge_with_system_rule(builtin_text: str, user_text: str) -> str:
    """Concatenate built-in and user rule text under fixed headers (RULE-04).

    Byte-exact port of OCR's `mergeWithSystemRule` header format (D-02).

    Args:
        builtin_text: The built-in rule doc's text for the matched path.
        user_text: The `merge_system_rule` entry's rule text.

    Returns:
        `user_text` alone when `builtin_text` is empty, `builtin_text` alone
        when `user_text` is empty, the empty string when both are empty,
        otherwise both concatenated under `SYSTEM_RULE_HEADER` and
        `USER_RULE_HEADER` separated by a horizontal rule.
    """
    if not builtin_text:
        return user_text
    if not user_text:
        return builtin_text
    return (
        f"{SYSTEM_RULE_HEADER}\n\n{builtin_text}\n\n---\n\n{USER_RULE_HEADER}\n\n{user_text}"
    )


def resolve_rule_doc(path: str, resolution: RuleResolution | None = None) -> str:
    """Resolve a changed file's path to its rule-doc text, layer by layer.

    Per-path fallthrough (RULE-02): custom, then project, then global, then
    the built-in map, deciding independently for every path — one layer
    answering for this path never stops another layer answering for a
    different path.

    Args:
        path: A forward-slash-separated relative path to the changed file.
        resolution: The four-layer resolution to walk. `None` resolves
            against the built-in map alone (the tracer's original behavior,
            kept for callers not yet passing a `RuleResolution`).

    Returns:
        The matched entry's text — merged with the built-in text via
        `merge_with_system_rule` when the entry sets `merge_system_rule` —
        else the built-in map's match, else `default.md`'s text.
    """
    if resolution is not None:
        for layer in resolution.layers:
            entry = match_project_rule_entry(layer, path)
            if entry is not None:
                if entry.merge_system_rule:
                    return merge_with_system_rule(_resolve_builtin_or_default(path), entry.rule)
                return entry.rule
    return _resolve_builtin_or_default(path)
