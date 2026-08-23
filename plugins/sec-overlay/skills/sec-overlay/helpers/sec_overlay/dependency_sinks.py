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


def main(argv: list[str] | None = None) -> int:
    """CLI: print the catalog, one ``id<TAB>cls<TAB>package`` line per entry."""
    parser = argparse.ArgumentParser(prog="sec-overlay-dependency-sinks")
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    args = parser.parse_args(argv)
    for e in load_catalog(Path(args.catalog)):
        print(f"{e.id}\t{e.cls}\t{e.package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
