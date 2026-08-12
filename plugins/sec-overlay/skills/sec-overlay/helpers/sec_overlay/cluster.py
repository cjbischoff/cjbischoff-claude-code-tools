"""Deterministic systemic clustering: group ≥3 same-class, same-sink RAW findings.

The lumedeodorant run reported 12 findings that were one authorization pattern
across 12 routes. Dedupe only merges exact ``(file, line, cls)`` collisions, so
distinct-file siblings never merged. This pass groups them into one systemic
cluster without dropping any member: each route stays individually addressable,
but the report and machine consumers see one headline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.graph import load_graph, symbol_at
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.workspace import Workspace, read_findings, write_findings

_SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_MIN_CLUSTER = 3


def _sink_symbol(graph, f: Finding) -> str | None:
    """Resolve the sink symbol for a finding.

    Prefers the enclosing symbol from the graph substrate (refactor-resistant);
    falls back to the last dataflow hop when no graph is available.

    Args:
        graph: Loaded graph or ``None``.
        f: The finding.

    Returns:
        The sink symbol name, or ``None`` when it cannot be resolved.
    """
    if graph is not None:
        sym = symbol_at(graph, f.file, f.line)
        if sym:
            return sym
    return f.dataflow[-1] if f.dataflow else None


def cluster_findings(ws: Workspace) -> int:
    """Group RAW findings that share ``(cls, sink_symbol)`` into systemic clusters.

    A group of ≥3 elects a primary (highest severity, tiebreak smallest id),
    stamps every member with ``cluster_id = "cluster:<primary-id>"``, and records
    all member sites on the primary's ``affected_sites``. Only ``RAW`` findings are
    considered; ``CONFIRMED`` and every other status are left untouched.

    Args:
        ws: Workspace whose findings are clustered in place.

    Returns:
        The number of findings stamped with a ``cluster_id``.
    """
    findings = read_findings(ws)
    graph = load_graph(ws) if (ws.kb / "graph.json").exists() else None

    groups: dict[tuple[str, str], list[Finding]] = {}
    for f in findings:
        if f.status is not FindingStatus.RAW:
            continue
        sink = _sink_symbol(graph, f)
        if sink is None:
            continue
        groups.setdefault((f.cls, sink), []).append(f)

    stamped = 0
    for members in groups.values():
        if len(members) < _MIN_CLUSTER:
            continue
        primary = min(members, key=lambda f: (-_SEVERITY_ORDER[f.severity.value], f.id))
        cid = f"cluster:{primary.id}"
        sites = [{"id": m.id, "file": m.file, "line": m.line} for m in members]
        for m in members:
            m.cluster_id = cid
            m.history.append({"event": f"cluster:{cid}"})
            stamped += 1
        primary.affected_sites = sites

    if stamped:
        write_findings(ws, findings)
    record_stage(ws, "cluster")
    return stamped


def main(argv: list[str] | None = None) -> int:
    """CLI: cluster a workspace's RAW findings.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-cluster")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    n = cluster_findings(Workspace(Path(args.workspace)))
    print(f"clustered {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
