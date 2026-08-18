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
:func:`read_rule_file_safe` is the sole entry point for reading a rule file
off disk — every layer's entries route through it — diverging from OCR's
``readRuleFileSafe`` in three ways mandated by this project's requirements
(stronger resolved-path boundary check, hard reject instead of a warn-and-
fallthrough, and a capped read instead of stat-then-read); documented in
full on that function.

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

# RULE-03: the rule-file safety gate's hard limits (see `read_rule_file_safe`).
MAX_RULE_FILE_BYTES = 524288
ALLOWED_RULE_EXTENSIONS = frozenset({".md", ".txt", ".markdown"})

# Ordered: first matching glob wins. Language entries mirror OCR's
# system_rules.json pattern strings and doc filenames exactly (D-02),
# restricted to the languages this project actually ships a doc for. The
# trailing `**/*` catch-all makes default.md a reachable, testable map value
# like every other doc (RULE-05) instead of a fallback outside the map.
BUILTIN_PATH_RULE_MAP: dict[str, str] = {
    "**/*.java": "java.md",
    "**/*.go": "go.md",
    "**/*.{ts,js,tsx,jsx}": "ts_js_tsx_jsx.md",
    "**/*.{kt}": "kotlin.md",
    "**/*.rs": "rust.md",
    "**/*.py": "python.md",
    "**/*.{php,phtml}": "php.md",
    "**/*.swift": "swift.md",
    "**/*": "default.md",
}

# RULE-05: the five defect families every built-in rule doc must cover, in
# the fixed order established by python.md. Accepted heading synonyms live
# alongside the family keys (test_rule_docs.py drives every assertion from
# this data, not a hardcoded per-language doc list) because the same family
# is named differently across languages — a Rust doc says "panic"/"unwrap"
# where a Java doc says "null pointer".
REQUIRED_RULE_SECTIONS: tuple[str, ...] = (
    "null_or_nil_dereference",
    "thread_safety",
    "injection",
    "resource_leaks",
    "swallowed_errors",
)

RULE_SECTION_SYNONYMS: dict[str, tuple[str, ...]] = {
    "null_or_nil_dereference": ("null", "nil", "optional", "unwrap", "panic"),
    "thread_safety": ("thread safety", "concurrency", "race", "synchroniz"),
    "injection": ("injection",),
    "resource_leaks": ("resource leak", "resource management", "resource"),
    "swallowed_errors": ("swallowed error", "error handling", "exception handling", "error"),
}


class RuleSafetyError(Exception):
    """Raised by `read_rule_file_safe` on a symlink escape, bad extension, or oversize file.

    A hard reject (D-08): unlike OCR's soft warn-and-fallthrough, `sec-overlay` never
    silently reviews with the wrong (or no) rule doc after a safety violation. The
    message names the offending path and the specific reason so the error is
    actionable from stderr alone (T-03-07 accepts this as low-severity disclosure —
    the path is one the operator supplied or their own repo already contains).
    """


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
    is read from disk at load time through `read_rule_file_safe` (RULE-03),
    so by the time `match_project_rule_entry` runs, `entry.rule` already
    holds file *content* that has already passed the safety gate.

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
            rule=read_rule_file_safe(_entry_rule_path(raw.get("rule", ""), repo_root), repo_root),
            merge_system_rule=bool(raw.get("merge_system_rule", False)),
        )
        for raw in data.get("rules", [])
    ]
    return ProjectRule(
        entries=entries,
        include=list(data.get("include", [])),
        exclude=list(data.get("exclude", [])),
    )


def _entry_rule_path(rule: str, repo_root: Path) -> Path:
    """Join a rule.json entry's `rule` field against `repo_root` when relative.

    Mirrors OCR's `resolveRuleEntries`; the joined path is then validated and
    read by `read_rule_file_safe`, which does no relative-path resolution of
    its own.
    """
    candidate = Path(rule)
    return candidate if candidate.is_absolute() else repo_root / rule


def read_rule_file_safe(path: str | Path, repo_root: Path) -> str:
    """Read one rule file after the RULE-03 safety gate, or raise `RuleSafetyError`.

    The sole entry point for reading a rule file off disk (RULE-03) — every
    layer's entries route through this, so a symlink escape, a disallowed
    extension, or an oversize file rejects the whole run instead of silently
    reviewing with the wrong (or no) rule doc.

    Check order (D-02): resolve symlinks first via `Path.resolve(strict=True)`,
    then the resolved path's suffix against `ALLOWED_RULE_EXTENSIONS`, then
    containment under the resolved `repo_root` via `Path.is_relative_to`, then
    the `MAX_RULE_FILE_BYTES` cap enforced on the read itself, then a UTF-8
    decode that strips only trailing newlines (`rstrip("\\n")`) so inner blank
    lines survive.

    Three deliberate divergences from OCR's `readRuleFileSafe`, each mandated
    by a sec-overlay requirement rather than a port defect (D-02):

    1. OCR boundary-checks the cleaned join before resolving symlinks; RULE-03
       requires the RESOLVED path to be under the repo root, which is
       strictly stronger and closes the symlink-escape path OCR leaves open.
    2. OCR warns to stderr and returns `nil`, letting resolution fall through
       to the next layer; D-08 requires a hard reject, so every violation
       here raises `RuleSafetyError` naming the offending path and the
       specific reason — a typo'd rule path must never silently review with
       the wrong checklist.
    3. OCR stats then reads, leaving a window where a file can grow between
       the two calls; the cap is enforced on the read itself by reading at
       most `MAX_RULE_FILE_BYTES + 1` bytes and rejecting when that much
       comes back, so the cap holds regardless of concurrent writes. Size is
       measured in bytes via the binary length, never in decoded characters.

    Args:
        path: The rule file's path, already joined against its layer's base
            directory (see `_entry_rule_path`) — this function performs no
            relative-path resolution of its own, only symlink resolution.
        repo_root: The boundary the resolved path must fall under. Callers
            pass whatever base their own layer already resolves relative
            `rule` fields against (`load_project_rule`'s `repo_root`
            parameter) — the true project root for the project layer, a
            layer's own config directory for the custom/global layers — so
            every layer is checked against the same root it trusts for its
            own relative paths (T-03-09).

    Returns:
        The file's text, UTF-8 decoded, with trailing newlines stripped.

    Raises:
        RuleSafetyError: On an unresolvable path, a resolved path outside
            `repo_root`, a disallowed extension, or a read exceeding
            `MAX_RULE_FILE_BYTES`.
    """
    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RuleSafetyError(f"cannot resolve rule file {candidate}: {exc}") from exc

    if resolved.suffix.lower() not in ALLOWED_RULE_EXTENSIONS:
        raise RuleSafetyError(
            f"rule file {resolved} has disallowed extension {resolved.suffix!r}; "
            f"allowed: {sorted(ALLOWED_RULE_EXTENSIONS)}"
        )

    resolved_root = Path(repo_root).resolve(strict=False)
    if not resolved.is_relative_to(resolved_root):
        raise RuleSafetyError(f"rule file {resolved} resolves outside repo root {resolved_root}")

    with resolved.open("rb") as fh:
        data = fh.read(MAX_RULE_FILE_BYTES + 1)
    if len(data) > MAX_RULE_FILE_BYTES:
        raise RuleSafetyError(
            f"rule file {resolved} exceeds {MAX_RULE_FILE_BYTES} bytes "
            f"(read at least {len(data)} bytes)"
        )

    return data.decode("utf-8").rstrip("\n")


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


def build_file_filter(layers: list[ProjectRule | None]) -> FileFilter | None:
    """Return the whole-run filter from the first layer with a non-empty include or exclude.

    Whole-layer first-non-empty selection (RULE-02, Task 2). Structurally separate
    from :func:`match_project_rule_entry`'s per-path fallthrough — this walks a
    list of layers looking for one whole-layer answer, never merging two layers'
    patterns together. Neither function calls the other.

    Args:
        layers: Ordered layers to consider (e.g. `[custom, project, global]`).
            `None` entries (an absent layer) are skipped.

    Returns:
        A `FileFilter` copied from the first layer whose `include` or `exclude`
        is non-empty, with every pattern lower-cased (D-04); `None` when no
        layer has either list populated, including an empty `layers` list.
    """
    for layer in layers:
        if layer is None:
            continue
        if not layer.include and not layer.exclude:
            continue
        return FileFilter(
            include=[p.lower() for p in layer.include],
            exclude=[p.lower() for p in layer.exclude],
        )
    return None


def _global_rule_path() -> Path:
    """Return the fixed global rule.json location (``~/.sec-overlay/rule.json``).

    A separate function so tests substitute it directly instead of monkeypatching
    the stdlib `Path.home` class.
    """
    return Path.home() / ".sec-overlay" / "rule.json"


def build_resolution(rule_path: str | None, excludes: list[str], repo_root: Path) -> RuleResolution:
    """Assemble the four-layer resolution `resolve_rule_doc` and the exclude filter walk.

    Mirrors OCR's `NewResolver`: the custom (`--rule`) and global layers resolve a
    relative `rule` field against their OWN config file's directory
    (`loadRuleFile`/`loadGlobalRule`, both call `resolveRuleEntries(pr.Rules,
    filepath.Dir(path))`); only the project layer resolves against `repo_root`
    (`loadProjectRule`). `build_file_filter` then picks one layer's filter, and
    CLI `--exclude` values (lower-cased) always append to it.

    Args:
        rule_path: Path to a custom rule.json passed via `--rule`, or `None`.
        excludes: Raw `--exclude` values from the CLI, in flag order.
        repo_root: Repo root; anchors the project layer and the boundary check.

    Returns:
        The assembled `RuleResolution`.
    """
    custom = (
        load_project_rule(Path(rule_path), Path(rule_path).parent)
        if rule_path is not None
        else None
    )
    project = load_project_rule(repo_root / ".sec-overlay" / "rule.json", repo_root)
    global_path = _global_rule_path()
    global_layer = load_project_rule(global_path, global_path.parent)
    layers = [custom, project, global_layer]

    file_filter = build_file_filter(layers)
    lowered_excludes = [e.lower() for e in excludes]
    if lowered_excludes:
        base_include = file_filter.include if file_filter is not None else []
        base_exclude = file_filter.exclude if file_filter is not None else []
        file_filter = FileFilter(include=base_include, exclude=[*base_exclude, *lowered_excludes])

    return RuleResolution(layers=layers, file_filter=file_filter, repo_root=repo_root)


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
