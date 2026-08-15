"""Per-run self-score: post-gate finding counts written back to state.

The self-score reads finding records after the gate, so its counts match
``findings`` exactly. It is a run-quality signal (reported vs needs-runtime,
cluster count, rejected count, external-boundary count), not a re-score.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sec_overlay.evidence import SHIPPING_STATUSES
from sec_overlay.models import FindingStatus
from sec_overlay.state import load_state, save_state
from sec_overlay.workspace import Workspace, read_findings

_REPORTED = {FindingStatus.CONFIRMED, FindingStatus.FIXED}


def build_self_score(ws: Workspace) -> dict:
    """Compute the per-run self-score from workspace findings.

    Args:
        ws: Finished-scan workspace.

    Returns:
        ``{reported, confirmed, needs_runtime, rejected, clusters,
        external_boundary, shipping}`` — all ints.
    """
    findings = read_findings(ws)
    clusters = {f.cluster_id for f in findings if getattr(f, "cluster_id", None)}
    external = sum(
        1 for f in findings if (f.reachability or {}).get("blocker") == "external-boundary"
    )
    return {
        "reported": sum(1 for f in findings if f.status in _REPORTED),
        "confirmed": sum(1 for f in findings if f.status is FindingStatus.CONFIRMED),
        "needs_runtime": sum(
            1 for f in findings if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING
        ),
        "rejected": sum(1 for f in findings if f.status is FindingStatus.REJECTED),
        "clusters": len(clusters),
        "external_boundary": external,
        "shipping": sum(1 for f in findings if f.status.value in SHIPPING_STATUSES),
    }


def write_self_score(ws: Workspace) -> dict:
    """Build the self-score and persist it at ``state.budget['self_score']``.

    Args:
        ws: Finished-scan workspace.

    Returns:
        The self-score dict that was persisted.
    """
    score = build_self_score(ws)
    state = load_state(ws)
    state.budget["self_score"] = score
    save_state(ws, state)
    return score


def main(argv: list[str] | None = None) -> int:
    """CLI: write the per-run self-score into state.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-selfscore")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    score = write_self_score(Workspace(Path(args.workspace)))
    print(f"self-score: {score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
