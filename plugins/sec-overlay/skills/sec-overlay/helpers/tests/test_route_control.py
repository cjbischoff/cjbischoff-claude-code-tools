"""Tests for the route-to-control table and phase-output gap checks."""

import json

from sec_overlay.route_control import (
    check_architecture_controls,
    check_threat_entrypoints,
    record_route_gaps,
)
from sec_overlay.workspace import Workspace


def test_architecture_gap_when_control_unreported():
    table = {"routes": [], "controls": ["auth", "rate-limit", "csrf"], "entrypoints": []}
    arch = "# Architecture\nThe app enforces auth on all routes.\n"  # mentions only auth
    gaps = check_architecture_controls(table, arch)
    ids = {g["id"] for g in gaps}
    assert "rate-limit" in ids and "csrf" in ids and "auth" not in ids
    for g in gaps:
        assert g["disposition"] == "needs_follow_up"
        assert g["reason"] and g["next_step"]


def test_threat_gap_when_entrypoint_dropped():
    table = {"routes": [], "controls": [], "entrypoints": ["POST /login", "GET /admin"]}
    tm = "Attackers target POST /login.\n"  # /admin dropped
    gaps = check_threat_entrypoints(table, tm)
    assert [g["id"] for g in gaps] == ["GET /admin"]


def test_no_gap_when_all_present():
    table = {"routes": [], "controls": ["auth"], "entrypoints": ["GET /"]}
    assert check_architecture_controls(table, "auth is enforced") == []
    assert check_threat_entrypoints(table, "GET / is the entrypoint") == []


def test_record_route_gaps_round_trips_through_ledger(tmp_path):
    ws = Workspace(root=tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    gaps = [
        {
            "id": "csrf",
            "disposition": "needs_follow_up",
            "reason": "control 'csrf' in the route-to-control table is not reported downstream",
            "next_step": "report 'csrf' in the control section or record why it is out of scope",
        }
    ]

    record_route_gaps(ws, gaps)

    ledger = json.loads((ws.kb / "coverage-ledger.json").read_text())
    recorded = next(s for s in ledger["surfaces"] if s["id"] == "csrf")
    assert recorded["reason"] == gaps[0]["reason"]
    assert recorded["next_step"] == gaps[0]["next_step"]

    from sec_overlay.coverage_ledger import validate_coverage_ledger

    assert validate_coverage_ledger(ledger) == []
