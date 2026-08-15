"""Derive one route-to-control table from recon output and check each phase against it.

A missing route, control, or entrypoint is a logged gap (never dropped), carrying
``reason`` and ``next_step`` so a follow-on gate (Plan D) can enforce it.
"""

from __future__ import annotations

import json

from sec_overlay.coverage_ledger import build_coverage_ledger
from sec_overlay.workspace import Workspace


def build_route_control_table(ws: Workspace) -> dict:
    """Build the route-to-control table from ``kb/scan-profile.json``.

    Args:
        ws: The audit workspace holding ``kb/scan-profile.json``.

    Returns:
        ``{"routes": [...], "controls": [...], "entrypoints": [...]}``. Empty
        lists when the profile is absent or a field is missing.
    """
    path = ws.kb / "scan-profile.json"
    if not path.exists():
        return {"routes": [], "controls": [], "entrypoints": []}
    prof = json.loads(path.read_text())
    entrypoints = [str(e) for e in prof.get("entrypoints", [])]
    surface = prof.get("attack_surface", []) or []
    # "controls" is not a scan-profile field; attack_surface is the closest proxy.
    controls = sorted({str(c) for c in prof.get("controls", surface)})
    routes = [{"route": str(e), "entrypoint": str(e), "evidence": ""} for e in entrypoints]
    return {"routes": routes, "controls": controls, "entrypoints": entrypoints}


def _gap(item: str, kind: str) -> dict:
    return {
        "id": item,
        "disposition": "needs_follow_up",
        "reason": f"{kind} {item!r} in the route-to-control table is not reported downstream",
        "next_step": f"report {item!r} in the {kind} section or record why it is out of scope",
    }


def check_recon_routes(table: dict, profile: dict) -> list[dict]:
    """Gap for any table route the recon profile does not summarise.

    ``route_summary`` is an optional recon-emitted field; when absent every table
    route is conservatively flagged as a logged gap (never-drop invariant).
    """
    summarised = {str(r) for r in profile.get("route_summary", [])}
    return [
        _gap(r["route"], "route") for r in table.get("routes", []) if r["route"] not in summarised
    ]


def check_architecture_controls(table: dict, architecture_md: str) -> list[dict]:
    """Gap for any table control the architecture markdown does not mention."""
    text = architecture_md.lower()
    return [_gap(c, "control") for c in table.get("controls", []) if c.lower() not in text]


def check_threat_entrypoints(table: dict, threat_model_md: str) -> list[dict]:
    """Gap for any table entrypoint the threat model drops."""
    text = threat_model_md.lower()
    return [_gap(e, "entrypoint") for e in table.get("entrypoints", []) if e.lower() not in text]


def record_route_gaps(ws: Workspace, gaps: list[dict]) -> None:
    """Append route/control/entrypoint gaps into ``kb/coverage-ledger.json``.

    Reads the existing ledger (seeding one via ``build_coverage_ledger`` if absent),
    appends each gap as a ``needs_follow_up`` surface, and demotes ``completeness``
    to ``partial`` so the ledger's own invariant (``complete`` forbids
    ``needs_follow_up`` surfaces) still holds after the append. ``unknown`` is left
    as-is — there is no scan-profile to be complete about yet.

    Args:
        ws: Workspace holding ``kb/coverage-ledger.json``.
        gaps: Gap dicts from the ``check_*`` functions, each already
            ``{id, disposition, reason, next_step}``.
    """
    path = ws.kb / "coverage-ledger.json"
    ledger = json.loads(path.read_text()) if path.exists() else build_coverage_ledger(ws)
    ledger["surfaces"].extend(gaps)
    if ledger["completeness"] != "unknown" and any(
        s["disposition"] == "needs_follow_up" for s in ledger["surfaces"]
    ):
        ledger["completeness"] = "partial"
    path.write_text(json.dumps(ledger, indent=2))
