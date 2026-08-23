"""Tests for the route-to-control table and phase-output gap checks."""

import json

from sec_overlay.route_control import (
    check_architecture_controls,
    check_threat_entrypoints,
    record_route_gaps,
)
from sec_overlay.workspace import Workspace


def _workspace_with_profile(tmp_path, profile: dict) -> Workspace:
    ws = Workspace(tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    (ws.kb / "scan-profile.json").write_text(json.dumps(profile))
    return ws


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


def test_control_substring_of_longer_word_is_still_a_gap():
    # control "auth" must NOT be considered covered by the word "authorization"
    table = {"routes": [], "controls": ["auth"], "entrypoints": []}
    gaps = check_architecture_controls(table, "The service uses authorization tokens.")
    assert [g["id"] for g in gaps] == ["auth"]


def test_control_as_standalone_token_is_covered():
    table = {"routes": [], "controls": ["auth"], "entrypoints": []}
    gaps = check_architecture_controls(table, "The auth layer validates each request.")
    assert gaps == []


def test_entrypoint_with_path_punctuation_still_matches():
    # a token carrying a slash must still be found as a standalone mention (not a false gap)
    table = {"routes": [], "controls": [], "entrypoints": ["/login"]}
    gaps = check_threat_entrypoints(table, "Attackers target the /login endpoint directly.")
    assert gaps == []


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


def test_route_control_table_prefers_the_census_over_the_scan_profile(tmp_path):
    """Deriving routes from the scan profile made the check compare recon to itself."""
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import build_route_control_table

    ws = _workspace_with_profile(tmp_path, {"entrypoints": ["/health"]})
    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    table = build_route_control_table(ws, census=sites)
    assert table["source"] == "route-census"
    assert any("/policy/evaluate" in str(r) for r in table["routes"])
    assert table["routes"][0]["evidence"] == "app.py:9"


def test_route_control_table_falls_back_to_the_profile_without_a_census(tmp_path):
    from sec_overlay.route_control import build_route_control_table

    ws = _workspace_with_profile(tmp_path, {"entrypoints": ["/health"]})
    assert build_route_control_table(ws)["source"] == "scan-profile"


def test_check_census_routes_reports_a_route_the_profile_never_mentions(tmp_path):
    """This is the whole point of F6: an unmentioned route becomes a gap row."""
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import check_census_routes

    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    gaps = check_census_routes(sites, {"entrypoints": ["/health"]})
    assert len(gaps) == 1
    assert gaps[0]["disposition"] == "needs_follow_up"
    assert "/policy/evaluate" in gaps[0]["id"]


def test_check_census_routes_is_silent_when_the_profile_mentions_the_route(tmp_path):
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import check_census_routes

    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    assert check_census_routes(sites, {"entrypoints": ["POST /policy/evaluate"]}) == []


def test_check_recon_routes_is_silent_for_a_census_sourced_table():
    """check_census_routes owns recon comparison for a census table; this must not double-gap."""
    from sec_overlay.route_control import check_recon_routes

    table = {
        "routes": [{"route": "POST /policy/evaluate", "entrypoint": "/policy/evaluate",
                     "evidence": "app.py:9"}],
        "source": "route-census",
    }
    profile = {"route_summary": ["/policy/evaluate"]}
    assert check_recon_routes(table, profile) == []


def test_check_recon_routes_still_gaps_for_a_scan_profile_table():
    from sec_overlay.route_control import check_recon_routes

    table = {
        "routes": [{"route": "/admin", "entrypoint": "/admin", "evidence": ""}],
        "source": "scan-profile",
    }
    profile = {"route_summary": ["/health"]}
    gaps = check_recon_routes(table, profile)
    assert [g["id"] for g in gaps] == ["/admin"]
