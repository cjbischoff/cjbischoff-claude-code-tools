"""Dependency-sink catalog: dependencies whose OWN code holds the sink.

The prefilter and the investigate agents look for a sink in first-party source.
When the sink lives inside a declared dependency (an OPA policy calling
``http.send``, a CEL program calling a host function), no first-party pattern
matches and recon can omit the whole attack class. This catalog names those
dependencies so a manifest match routes the class regardless.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "references" / "dependency-sinks.json"

_REQUIRED = (
    "id",
    "package",
    "ecosystem",
    "manifests",
    "cls",
    "sink",
    "why",
    "safe_option",
    "indicators",
)


@dataclass(frozen=True)
class SinkEntry:
    """One dependency that contains a sink inside its own code.

    Attributes:
        id: Stable catalog id, used as the ``dependency-catalog:<id>`` receipt suffix.
        package: Manifest-visible package name matched as a substring.
        ecosystem: Package ecosystem (``go``, ``python``, ``node``, ...).
        manifests: Manifest filenames that can declare this package.
        cls: Attack class this dependency routes.
        sink: The sink inside the dependency, named for the proof tuple.
        why: One sentence explaining why the dependency is the sink.
        safe_option: The option that removes or narrows the sink.
        indicators: Source tokens that show the dependency is actually used.
    """

    id: str
    package: str
    ecosystem: str
    manifests: tuple[str, ...]
    cls: str
    sink: str
    why: str
    safe_option: str
    indicators: tuple[str, ...]


def validate_catalog(raw: dict) -> list[str]:
    """Return human-readable defects in a parsed catalog document.

    Args:
        raw: Parsed catalog JSON.

    Returns:
        One message per defect; empty when the document is valid.
    """
    errors: list[str] = []
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        return ["entries: must be a non-empty list"]
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"entries[{i}]: must be an object")
            continue
        for key in _REQUIRED:
            if not e.get(key):
                errors.append(f"entries[{i}]: missing or empty {key}")
        eid = e.get("id")
        if isinstance(eid, str) and eid in seen:
            errors.append(f"entries[{i}]: duplicate id {eid}")
        if isinstance(eid, str):
            seen.add(eid)
    return errors


def load_catalog(path: Path = CATALOG_PATH) -> list[SinkEntry]:
    """Load and validate the catalog.

    Args:
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        One ``SinkEntry`` per catalog entry.

    Raises:
        ValueError: The document is invalid; every defect is listed.
    """
    raw = json.loads(path.read_text())
    errors = validate_catalog(raw)
    if errors:
        raise ValueError(f"invalid dependency-sink catalog {path}: " + "; ".join(errors))
    return [
        SinkEntry(
            id=e["id"],
            package=e["package"],
            ecosystem=e["ecosystem"],
            manifests=tuple(e["manifests"]),
            cls=e["cls"],
            sink=e["sink"],
            why=e["why"],
            safe_option=e["safe_option"],
            indicators=tuple(e["indicators"]),
        )
        for e in raw["entries"]
    ]


def catalog_ids(path: Path = CATALOG_PATH) -> frozenset[str]:
    """Return every catalog id, for receipt-id validation in the findings gate."""
    return frozenset(e.id for e in load_catalog(path))


_SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".sec-overlay",
    "dist",
    "build",
    "target",
}


def _manifest_files(root: Path, names: set[str]) -> list[Path]:
    """Collect manifest files under ``root``, skipping vendored and cache trees."""
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in _SKIP_DIRS:
                    stack.append(child)
            elif child.name in names:
                found.append(child)
    return found


def match_manifests(root: str | Path, *, path: Path = CATALOG_PATH) -> list[SinkEntry]:
    """Return every catalog entry whose package is declared under ``root``.

    Args:
        root: Target repository root.
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        Matched entries in catalog order. A match is a substring hit on the
        package name inside a manifest file the entry names.
    """
    entries = load_catalog(path)
    names = {name for e in entries for name in e.manifests}
    texts: dict[str, list[str]] = {}
    for manifest in _manifest_files(Path(root), names):
        try:
            texts.setdefault(manifest.name, []).append(manifest.read_text(errors="replace"))
        except OSError:
            continue
    matched: list[SinkEntry] = []
    for e in entries:
        for name in e.manifests:
            if any(e.package in text for text in texts.get(name, ())):
                matched.append(e)
                break
    return matched


def manifest_paths(root: str | Path, *, path: Path = CATALOG_PATH) -> dict[str, str]:
    """Map each matched entry id to the manifest that declares its package.

    A recall claim needs a ref the reader can open from the target repository.
    The catalog file itself is not one: it lives in the overlay, not in the
    target. The declaring manifest is the only target-side evidence.

    Args:
        root: Target repository root.
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        One item per matched entry. Each value is a path relative to ``root``.
    """
    entries = load_catalog(path)
    names = {name for e in entries for name in e.manifests}
    root_path = Path(root)
    texts: list[tuple[Path, str]] = []
    for manifest in _manifest_files(root_path, names):
        try:
            texts.append((manifest, manifest.read_text(errors="replace")))
        except OSError:
            continue
    found: dict[str, str] = {}
    for e in entries:
        for manifest, text in texts:
            if manifest.name in e.manifests and e.package in text:
                found[e.id] = manifest.relative_to(root_path).as_posix()
                break
    return found


def matched_classes(root: str | Path, *, path: Path = CATALOG_PATH) -> list[str]:
    """Return the sorted, deduplicated attack classes of every matched entry."""
    return sorted({e.cls for e in match_manifests(root, path=path)})


_SOURCE_SUFFIXES = {".go", ".py", ".js", ".ts", ".rb", ".java", ".rs", ".php", ".cs", ".rego"}


def _source_files(root: Path) -> list[Path]:
    """Collect source files under ``root``, skipping vendored and cache trees."""
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in _SKIP_DIRS:
                    stack.append(child)
            elif child.suffix in _SOURCE_SUFFIXES:
                found.append(child)
    return found


def indicator_classes(root: str | Path, *, path: Path = CATALOG_PATH) -> list[str]:
    """Return the attack classes of every catalog entry an indicator API reaches.

    A manifest match is not the only evidence a target uses a dependency sink. A
    Bazel or vendored build declares no manifest, so routing on manifests alone
    leaves the whole attack surface unrouted (R-34).

    Args:
        root: Target repository root.
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        The sorted, deduplicated classes of every entry with at least one
        indicator hit. One hit is enough: an entry lists alternative call shapes,
        not a conjunction.

    Example:
        >>> indicator_classes("/repo/with/rego/New/call")  # doctest: +SKIP
        ['ssrf']
    """
    entries = load_catalog(path)
    found: set[str] = set()
    for source in _source_files(Path(root)):
        try:
            text = source.read_text(errors="replace")
        except OSError:
            continue
        found.update(e.cls for e in entries if any(ind in text for ind in e.indicators))
    return sorted(found)


def main(argv: list[str] | None = None) -> int:
    """CLI: list the catalog, or the entries a target repo matches."""
    parser = argparse.ArgumentParser(prog="sec-overlay-dependency-sinks")
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Print every catalog entry.")
    m = sub.add_parser("match", help="Print the entries a target repo declares.")
    m.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    catalog = Path(args.catalog)
    if args.cmd == "list":
        for e in load_catalog(catalog):
            print(f"{e.id}\t{e.cls}\t{e.package}")
        return 0
    for e in match_manifests(args.root, path=catalog):
        print(f"{e.id}\t{e.cls}\t{e.sink}\t{e.safe_option}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
