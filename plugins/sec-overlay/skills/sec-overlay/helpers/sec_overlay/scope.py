"""Ingested-source scope: decide whether a dependency was scanned or is external.

A dataflow sink that resolves into a package whose source was never ingested cannot
be confirmed from source. This module makes that boundary check deterministic via a
``kb/scan-scope.json`` manifest instead of guessing.
"""

from __future__ import annotations

import json

from sec_overlay.workspace import Workspace


def _ingested_packages(ws: Workspace) -> set[str] | None:
    """Load the ingested-package set from the manifest, or ``None`` if absent.

    Args:
        ws: Workspace holding ``kb/scan-scope.json``.

    Returns:
        The set of ingested package names, or ``None`` when no manifest exists.
    """
    path = ws.kb / "scan-scope.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return set(data.get("ingested_packages", []))


def is_external_package(pkg: str, ws: Workspace) -> bool:
    """Report whether ``pkg`` was outside the ingested source set.

    Args:
        pkg: Dependency/package name a sink resolves into.
        ws: Workspace holding the scan-scope manifest.

    Returns:
        ``True`` only when a manifest exists and ``pkg`` is not in it. Without a
        manifest, returns ``False`` — the check never invents a boundary.
    """
    ingested = _ingested_packages(ws)
    if ingested is None:
        return False
    return pkg not in ingested
