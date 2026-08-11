"""CLI: correlate N per-repo scans of one product into a cross-repo edge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sec_overlay.correlate.artifacts import build_artifacts, write_artifacts
from sec_overlay.correlate.edges import (
    control_enforces_edges,
    same_class_recurrence_edges,
    shared_dependency_edges,
    write_edges,
)
from sec_overlay.correlate.ingest import ingest, member_coverage
from sec_overlay.correlate.manifest import load_manifest
from sec_overlay.correlate.rethreshold import rethreshold, write_verdicts
from sec_overlay.correlate.workspace import CorrelationWorkspace
from sec_overlay.correlate.xrepo_sarif import to_correlation_sarif


def main(argv: list[str] | None = None) -> int:
    """Run the deterministic correlation core (B-Plan 1).

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-correlate")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    cw = CorrelationWorkspace(Path(args.out))
    cw.ensure()
    cw.manifest_path.write_text(Path(args.manifest).read_text())  # copy manifest into the workspace
    ings = ingest(manifest)
    edges = shared_dependency_edges(ings) + same_class_recurrence_edges(ings) + control_enforces_edges(ings)
    write_edges(cw.edges_path, edges)
    coverage = member_coverage(manifest)
    verdicts = rethreshold(ings, edges, coverage)
    write_verdicts(cw.verdicts_path, verdicts)
    docs = build_artifacts(manifest, ings, edges, verdicts)
    write_artifacts(cw, docs)
    (cw.artifacts_dir / "report.sarif").write_text(
        json.dumps(to_correlation_sarif(ings, verdicts), indent=2)
    )
    print(
        json.dumps(
            {
                "edges": len(edges),
                "members": len(manifest.members),
                "verdicts": len(verdicts),
                "artifacts": len(docs),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
