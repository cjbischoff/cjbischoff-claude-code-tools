"""Partition changed files into reviewable and excluded sets — path-shaped, not finding-shaped.

Deliberately distinct from `exclusions.py`, which filters findings (RESEARCH.md Pitfall 5):
this module never imports `Finding`. The size cap ("too-large", D-11) and full enum enforcement
land in 02-02 Task 3.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field

from sec_overlay.diffscope import ChangedFile

EXCLUSION_REASONS: frozenset[str] = frozenset(
    {"deleted", "binary", "generated", "not-allowlisted", "too-large"}
)

# Ported from open-code-review's
# internal/config/allowlist/supported_file_types.json, 2026-08-17 (86 extensions, D-09).
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".astro", ".bash", ".bicep", ".c", ".cc", ".cjs", ".cmake", ".cpp", ".cs", ".css",
        ".cxx", ".dart", ".env", ".erl", ".ets", ".ex", ".exs", ".fish", ".fs", ".ftl",
        ".ftlh", ".ftlx", ".gemspec", ".go", ".gql", ".gradle", ".graphql", ".groovy", ".h",
        ".hcl", ".hpp", ".hrl", ".hs", ".htm", ".html", ".hxx", ".ini", ".java", ".jl", ".js",
        ".json", ".json5", ".jsx", ".kt", ".kts", ".less", ".lhs", ".lua", ".m", ".mjs", ".mm",
        ".nim", ".nimble", ".nims", ".nix", ".php", ".phtml", ".pl", ".pm", ".prisma", ".proto",
        ".ps1", ".py", ".pyi", ".r", ".rake", ".rb", ".rs", ".sass", ".scala", ".scss", ".sh",
        ".sql", ".svelte", ".swift", ".tf", ".tfvars", ".toml", ".ts", ".tsx", ".vb", ".vue",
        ".xml", ".yaml", ".yml", ".zsh",
    }
)

# Ported from open-code-review's
# internal/config/allowlist/default_exclude_patterns.json, 2026-08-17 (D-09/D-10). The source
# uses doublestar `{a,b,c}` brace groups; each group is pre-expanded here because Python's
# fnmatch has no brace syntax. All entries lowercase — matching folds case (Go source does too).
# ponytail: fnmatch approximates doublestar (no true "**" zero-or-more-segments); the
# parametrised glob test (test_file_select.py) is what holds this approximation honest.
DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "**/*_test.go",
    "**/src/test/java/**/*.java",
    "**/src/test/**/*.kt",
    "**/*.test.js",
    "**/*.test.jsx",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.spec.js",
    "**/*.spec.jsx",
    "**/*.spec.ts",
    "**/*.spec.tsx",
    "**/__tests__/**",
    "**/test/**/*_test.py",
    "**/tests/**/*_test.py",
    "**/*_test.py",
    "**/*_spec.rb",
    "**/spec/**/*_spec.rb",
    "**/*test.java",
    "**/*tests.java",
    "**/*_test.rs",
    "**/oh_modules/**",
    "**/*.test.ets",
    "**/test/**/*.jl",
    "**/test/**/*.hs",
    "**/*spec.hs",
    "**/test/**/*.lhs",
    "**/*spec.lhs",
    "**/tests/**/*.nim",
    "**/__snapshots__/**",
    "**/*.snap",
    "**/testdata/**",
    "**/fixtures/**",
    "**/*.generated.*",
    "**/*.gen.go",
    "**/*.pb.go",
    "**/*.pb.cc",
    "**/*.pb.h",
    "**/*test.swift",
    "**/*tests.swift",
    "**/tests/**/*.swift",
)

_OCTAL_ESCAPE_RE = re.compile(r"\\([0-7]{3})")


def _normalize_path(path: str) -> str:
    """Undo git's core.quotepath octal-escape quoting of non-ASCII path bytes.

    Args:
        path: A path as reported by git — plain, or double-quoted with ``\\NNN`` octal
            byte escapes when it contains non-ASCII bytes.

    Returns:
        The path with any surrounding quotes and octal escapes resolved to real characters,
        so a quoted and an unquoted form of the same path compare equal.
    """
    if len(path) < 2 or path[0] != '"' or path[-1] != '"':
        return path
    inner = path[1:-1]
    raw = _OCTAL_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 8)), inner)
    return raw.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")


def _is_generated(path: str) -> bool:
    """Check whether a path matches one of the ported default-exclude globs.

    Args:
        path: A normalized, lowercased repo-relative path.

    Returns:
        True if any pattern in :data:`DEFAULT_EXCLUDE_GLOBS` matches the path.
    """
    return any(fnmatch.fnmatch(path, pattern) for pattern in DEFAULT_EXCLUDE_GLOBS)


@dataclass(frozen=True)
class ExcludedFile:
    """A changed file routed out of review, with the reason it was excluded."""

    path: str
    reason: str


@dataclass(frozen=True)
class Selection:
    """Changed files split into what review covers and what it skips."""

    reviewable: list[ChangedFile] = field(default_factory=list)
    excluded: list[ExcludedFile] = field(default_factory=list)


def partition(records: list[ChangedFile]) -> Selection:
    """Split changed-file records into reviewable and excluded.

    Exclusion checks run in this order, first match wins: deleted status, then
    the ported default-exclude globs ("generated"), then the extension allowlist
    ("not-allowlisted"). Binary detection and the diff-line size cap land in Task 3.

    Args:
        records: Changed-file records from :func:`sec_overlay.diffscope.changed_file_records`.

    Returns:
        A Selection: a record lands in ``reviewable`` when it survives every check
        above; otherwise it lands in ``excluded`` with a reason from
        :data:`EXCLUSION_REASONS`.
    """
    reviewable: list[ChangedFile] = []
    excluded: list[ExcludedFile] = []
    for record in records:
        if record.status == "D":
            excluded.append(ExcludedFile(path=record.path, reason="deleted"))
            continue
        normalized = _normalize_path(record.path).lower()
        if _is_generated(normalized):
            excluded.append(ExcludedFile(path=record.path, reason="generated"))
            continue
        suffix = f".{normalized.rsplit('.', 1)[-1]}" if "." in normalized else ""
        if suffix not in ALLOWED_EXTENSIONS:
            excluded.append(ExcludedFile(path=record.path, reason="not-allowlisted"))
            continue
        reviewable.append(record)
    return Selection(reviewable=reviewable, excluded=excluded)
