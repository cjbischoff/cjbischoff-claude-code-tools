"""Derive one route-to-control table from recon output and check each phase against it.

A missing route, control, or entrypoint is a logged gap (never dropped), carrying
``reason`` and ``next_step`` so a follow-on gate (Plan D) can enforce it.
"""

from __future__ import annotations

import json
import re

from sec_overlay.coverage_ledger import build_coverage_ledger
from sec_overlay.route_census import RouteSite, load_census
from sec_overlay.workspace import Workspace


def build_route_control_table(ws: Workspace, *, census: list[RouteSite] | None = None) -> dict:
    """Build the route-to-control table, preferring the code-derived census.

    Reading ``kb/scan-profile.json`` for routes made the recon check compare
    recon against itself. The census (code-derived) is now the primary
    source; the scan profile is a fallback for when no census exists.

    Args:
        ws: The audit workspace holding ``kb/scan-profile.json`` and, when
            present, ``kb/route-census.json``.
        census: Sites to use; defaults to ``load_census(ws)``.

    Returns:
        ``{"routes": [...], "controls": [...], "entrypoints": [...], "source": ...}``.
        ``source`` is ``"route-census"`` when the census supplies the routes,
        else ``"scan-profile"``. Empty lists when both sources are absent.
    """
    sites = load_census(ws) if census is None else census
    path = ws.kb / "scan-profile.json"
    prof = json.loads(path.read_text()) if path.exists() else {}
    entrypoints = [str(e) for e in prof.get("entrypoints", [])]
    surface = prof.get("attack_surface", []) or []
    # "controls" is not a scan-profile field; attack_surface is the closest proxy.
    controls = sorted({str(c) for c in prof.get("controls", surface)})

    if sites:
        routes = [
            {
                "route": f"{s.method} {s.path}",
                "entrypoint": s.path,
                "evidence": f"{s.file}:{s.line}",
            }
            for s in sites
        ]
        return {
            "routes": routes,
            "controls": controls,
            "entrypoints": entrypoints,
            "source": "route-census",
        }

    routes = [{"route": str(e), "entrypoint": str(e), "evidence": ""} for e in entrypoints]
    return {
        "routes": routes,
        "controls": controls,
        "entrypoints": entrypoints,
        "source": "scan-profile",
    }


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
    A census-sourced table returns no gaps here: ``check_census_routes`` owns
    that comparison, since a census route carries a method prefix
    ``route_summary`` can never contain.
    """
    if table.get("source") == "route-census":
        return []
    summarised = {str(r) for r in profile.get("route_summary", [])}
    return [
        _gap(r["route"], "route") for r in table.get("routes", []) if r["route"] not in summarised
    ]


def _mentions(token: str, text: str) -> bool:
    """True when ``token`` appears in ``text`` (both lowercased) not as part of a longer alphanumeric word.

    Guards only alphanumeric neighbours, so a token carrying path punctuation
    (``/login``) still matches while ``auth`` no longer matches inside ``authorization``.
    """
    return re.search(rf"(?<![a-z0-9]){re.escape(token.lower())}(?![a-z0-9])", text) is not None


def check_census_routes(census_sites: list[RouteSite], profile: dict) -> list[dict]:
    """Report every code-derived route the recon profile never mentions.

    Args:
        census_sites: RouteSite records from route_census.
        profile: The recon scan profile.

    Returns:
        One gap row per unmentioned route. An empty list means recon named every
        route the code registers.
    """
    text = json.dumps(profile).lower()
    return [
        _gap(f"{s.method} {s.path} ({s.file}:{s.line})", "route")
        for s in census_sites
        if not _mentions(s.path, text)
    ]


def check_architecture_controls(table: dict, architecture_md: str) -> list[dict]:
    """Gap for any table control the architecture markdown does not mention."""
    text = architecture_md.lower()
    return [_gap(c, "control") for c in table.get("controls", []) if not _mentions(c, text)]


def check_threat_entrypoints(table: dict, threat_model_md: str) -> list[dict]:
    """Gap for any table entrypoint the threat model drops."""
    text = threat_model_md.lower()
    return [_gap(e, "entrypoint") for e in table.get("entrypoints", []) if not _mentions(e, text)]


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
