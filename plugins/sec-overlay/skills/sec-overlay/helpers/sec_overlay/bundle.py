"""Group reviewable changed files into review units (SCALE-01).

Pure and total: no filesystem, subprocess, or `Workspace` access, and no path is
ever dropped or duplicated across the returned units. Grouping rules pair files
that belong to the same review context — impl/test pairs (`foo.py` /
`test_foo.py`, `foo.go` / `foo_test.go`, `foo.ts` / `foo.test.ts` or
`foo.spec.ts`), C/C++ header-impl pairs (`foo.h` / `foo.c`, `foo.hpp` /
`foo.cpp`), interface/impl stem pairs (`svc.ts` / `svc.impl.ts`), and
locale/config siblings in the same directory (`en.json` / `fr.json`,
`config.dev.yaml` / `config.prod.yaml`) — and every file a rule does not claim
falls back to its own single-member unit. When per-path diffs are supplied, a
unit whose combined diffs exceed `MAX_UNIT_TOKENS` is split so one review
prompt never carries an unbounded diff. This is a sec-overlay addition beyond
OCR, which reviews every changed file independently with no grouping stage.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass

from sec_overlay.diffscope import ChangedFile
from sec_overlay.review_budget import estimate_tokens

# Python `test_x.py` / `x_test.py`, Go `x_test.go`, JS/TS `x.test.ts` / `x.spec.ts`.
_PY_TEST_PREFIX = re.compile(r"^test_(.+\.py)$")
_PY_TEST_SUFFIX = re.compile(r"^(.+)_test\.py$")
_GO_TEST_SUFFIX = re.compile(r"^(.+)_test\.go$")
_JS_TEST_SUFFIX = re.compile(r"^(.+)\.(?:test|spec)\.(ts|tsx|js|jsx)$")
# Interface/impl stem pair, `svc.ts` / `svc.impl.ts`.
_IMPL_STEM_SUFFIX = re.compile(r"^(.+)\.impl\.(ts|tsx|js|jsx)$")

# Locale filenames: bare or region-qualified language codes (`en`, `en-US`, `pt-BR`).
_LOCALE_STEM = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
# Config family members: `config.<env>.<ext>`.
_CONFIG_FAMILY = re.compile(r"^config\.[^.]+\.(\w+)$")

# C/C++ header and implementation extensions — a header pairs with its impl of
# the same stem in the same directory (`foo.h` / `foo.c`, `foo.hpp` / `foo.cpp`).
_C_PAIR_EXTS = frozenset({"h", "hpp", "hh", "hxx", "c", "cc", "cpp", "cxx"})

# Token cap for one review unit's combined diffs. A unit whose members' diffs
# exceed this (when `diffs` are supplied) is split so no single review prompt
# carries more than roughly this many tokens of change.
# ponytail: fixed cap, expose a knob if per-model context sizing ever matters.
MAX_UNIT_TOKENS = 50_000


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
    m = _IMPL_STEM_SUFFIX.match(name)
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
    if dot and ext in _C_PAIR_EXTS:
        return f"{directory}::cpair::{stem}"
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


def _split_by_tokens(paths: list[str], diffs: dict[str, str], cap: int) -> list[list[str]]:
    """Split one group's ordered paths into runs whose diff estimates fit `cap`.

    Greedy first-fit in input order: a member is added to the current run
    unless it would push the run's estimated tokens over `cap`, in which case
    a new run starts. A single member whose own diff exceeds `cap` becomes its
    own run — a unit is never dropped for being too large, only isolated.
    """
    runs: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for path in paths:
        tokens = estimate_tokens(diffs.get(path, ""))
        if current and current_tokens + tokens > cap:
            runs.append(current)
            current = []
            current_tokens = 0
        current.append(path)
        current_tokens += tokens
    if current:
        runs.append(current)
    return runs


def group_bundles(
    reviewable: list[ChangedFile],
    *,
    diffs: dict[str, str] | None = None,
    max_unit_tokens: int = MAX_UNIT_TOKENS,
) -> list[ReviewUnit]:
    """Group reviewable files into review units.

    Impl/test pairs, C/C++ header-impl pairs, interface/impl stem pairs, and
    locale/config siblings in the same directory travel together in one
    `ReviewUnit`; every other file becomes its own single-member unit. Input
    order is preserved, both across the returned units and within each unit's
    `files`.

    When `diffs` is supplied, a grouped unit whose members' estimated diff
    tokens exceed `max_unit_tokens` is split into consecutive runs that each
    fit the cap, so no single review prompt carries an unbounded diff. Without
    `diffs`, no size split happens.

    Args:
        reviewable: Files surviving `file_select.partition`, in selection order.
        diffs: Optional per-path diff text, keyed by `ChangedFile.path`, used
            only for the token-cap split. Absent paths estimate as empty.
        max_unit_tokens: Token cap for one unit's combined diffs.

    Returns:
        One `ReviewUnit` per grouping key (further split by token cap when
        `diffs` is given), in first-appearance order.
    """
    groups: dict[str, list[str]] = {}
    for record in reviewable:
        groups.setdefault(_group_key(record.path), []).append(record.path)

    units: list[ReviewUnit] = []
    for paths in groups.values():
        runs = _split_by_tokens(paths, diffs, max_unit_tokens) if diffs is not None else [paths]
        units.extend(ReviewUnit(unit_id=_unit_id(run), files=tuple(run)) for run in runs)
    return units
