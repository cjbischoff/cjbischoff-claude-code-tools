"""Group reviewable changed files into review units (SCALE-01).

Pure and total: no filesystem, subprocess, or `Workspace` access, and no path is
ever dropped or duplicated across the returned units. Two grouping rules pair
files that belong to the same review context — impl/test pairs (`foo.py` /
`test_foo.py`, `foo.go` / `foo_test.go`, `foo.ts` / `foo.test.ts` or
`foo.spec.ts`) and locale/config siblings in the same directory (`en.json` /
`fr.json`, `config.dev.yaml` / `config.prod.yaml`) — and every file a rule does
not claim falls back to its own single-member unit. This is a sec-overlay
addition beyond OCR, which reviews every changed file independently with no
grouping stage.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from sec_overlay.diffscope import ChangedFile

# Python `test_x.py` / `x_test.py`, Go `x_test.go`, JS/TS `x.test.ts` / `x.spec.ts`.
_PY_TEST_PREFIX = re.compile(r"^test_(.+\.py)$")
_PY_TEST_SUFFIX = re.compile(r"^(.+)_test\.py$")
_GO_TEST_SUFFIX = re.compile(r"^(.+)_test\.go$")
_JS_TEST_SUFFIX = re.compile(r"^(.+)\.(?:test|spec)\.(ts|tsx|js|jsx)$")

# Locale filenames: bare or region-qualified language codes (`en`, `en-US`, `pt-BR`).
_LOCALE_STEM = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
# Config family members: `config.<env>.<ext>`.
_CONFIG_FAMILY = re.compile(r"^config\.[^.]+\.(\w+)$")


def _canonical_name(name: str) -> str:
    """Map a test-file name onto its implementation counterpart's filename.

    Returns `name` unchanged when it does not match a known test-naming
    convention, so an implementation file's own canonical name is itself.
    """
    m = _PY_TEST_PREFIX.match(name)
    if m:
        return m.group(1)
    m = _PY_TEST_SUFFIX.match(name)
    if m:
        return f"{m.group(1)}.py"
    m = _GO_TEST_SUFFIX.match(name)
    if m:
        return f"{m.group(1)}.go"
    m = _JS_TEST_SUFFIX.match(name)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return name


def _group_key(path: str) -> str:
    """Derive the grouping key two paths must share to land in one unit.

    Impl/test pairing strips a `test`/`tests` directory component before
    comparing, so a top-level `tests/test_foo.py` pairs with `foo.py`
    (this repo's own convention) exactly like a sibling `test_foo.py` would.
    """
    directory, _, name = path.rpartition("/")
    stem, dot, ext = name.rpartition(".")
    if dot and _LOCALE_STEM.match(stem):
        return f"{directory}::locale::{ext}"
    config_match = _CONFIG_FAMILY.match(name)
    if config_match:
        return f"{directory}::config::{config_match.group(1)}"
    canon_dir = "/".join(p for p in directory.split("/") if p not in ("test", "tests"))
    return f"{canon_dir}/{_canonical_name(name)}"


def _unit_id(paths: Sequence[str]) -> str:
    """Derive a deterministic unit id from member paths (`_stable_finding_id` idiom)."""
    key = "|".join(paths)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ReviewUnit:
    """One or more reviewable files grouped for a single review pass."""

    unit_id: str
    files: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject a unit with no members.

        Raises:
            ValueError: If `files` is empty.
        """
        if not self.files:
            raise ValueError("ReviewUnit requires at least one file")


def group_bundles(reviewable: list[ChangedFile]) -> list[ReviewUnit]:
    """Group reviewable files into review units.

    Impl/test pairs and locale/config siblings in the same directory travel
    together in one `ReviewUnit`; every other file becomes its own
    single-member unit. Input order is preserved, both across the returned
    units and within each unit's `files`.

    Args:
        reviewable: Files surviving `file_select.partition`, in selection order.

    Returns:
        One `ReviewUnit` per grouping key, in first-appearance order.
    """
    groups: dict[str, list[str]] = {}
    for record in reviewable:
        groups.setdefault(_group_key(record.path), []).append(record.path)
    return [ReviewUnit(unit_id=_unit_id(paths), files=tuple(paths)) for paths in groups.values()]
