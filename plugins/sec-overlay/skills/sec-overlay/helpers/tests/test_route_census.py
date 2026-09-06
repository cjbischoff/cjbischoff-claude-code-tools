"""The census must derive routes from code, never from recon's own output."""

from __future__ import annotations

from pathlib import Path

import pytest

from sec_overlay.route_census import FRAMEWORKS_PATH, census, load_frameworks

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "route_repo"


def test_every_framework_entry_carries_a_pattern_and_globs():
    frameworks = load_frameworks()
    assert frameworks
    for fw in frameworks:
        assert fw.name and fw.language and fw.pattern
        assert fw.globs, f"{fw.name}: no globs, so the census would scan every file"


def test_framework_names_are_unique():
    names = [fw.name for fw in load_frameworks()]
    assert len(names) == len(set(names))


def test_frameworks_path_points_at_the_reference_file():
    assert FRAMEWORKS_PATH.name == "route-frameworks.json"
    assert FRAMEWORKS_PATH.exists()


@pytest.mark.skipif(
    __import__("shutil").which("rg") is None, reason="ripgrep not installed"
)
def test_census_finds_every_registered_route_in_the_fixture():
    sites = census(_FIXTURE)
    found = {(Path(s.file).name, s.path) for s in sites}
    assert ("app.py", "/health") in found
    assert ("app.py", "/policy/evaluate") in found
    assert ("server.go", "/admin/reload") in found


@pytest.mark.skipif(
    __import__("shutil").which("rg") is None, reason="ripgrep not installed"
)
def test_census_site_ids_are_stable_and_unique():
    sites = census(_FIXTURE)
    ids = [s.id for s in sites]
    assert len(ids) == len(set(ids))
    assert ids == [s.id for s in census(_FIXTURE)]


def test_census_returns_empty_when_the_tool_fails():
    """A failing ripgrep must not raise into the phase driver."""

    def fake(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 2

        return R()

    assert census(_FIXTURE, runner=fake) == []


def test_write_and_load_census_round_trip(tmp_path):
    from sec_overlay.route_census import RouteSite, load_census, write_census
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    sites = [RouteSite("route:a.py:3:/x", "a.py", 3, "GET", "/x", "flask")]
    out = write_census(ws, sites)
    assert out.name == "route-census.json"
    assert load_census(ws) == sites


def test_load_census_is_empty_when_absent(tmp_path):
    from sec_overlay.route_census import load_census
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    assert load_census(ws) == []


def test_census_parses_openapi_json(tmp_path):
    """Census must extract routes from openapi.json when present (D-6)."""
    from sec_overlay.route_census import RouteSite

    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/v1/vulnerability-sources": {
                "post": {"operationId": "createVulnerabilitySource"},
                "get": {"operationId": "listVulnerabilitySources"},
            },
            "/health": {"get": {"operationId": "healthCheck"}},
        },
    }
    (tmp_path / "openapi.json").write_text(__import__("json").dumps(spec))
    sites = census(tmp_path, runner=lambda cmd, **kw: type("R", (), {"stdout": "", "returncode": 0})())
    found = {(s.method, s.path) for s in sites}
    assert ("POST", "/v1/vulnerability-sources") in found
    assert ("GET", "/v1/vulnerability-sources") in found
    assert ("GET", "/health") in found
    for s in sites:
        assert s.framework == "openapi"


def test_census_falls_back_to_framework_regex_when_no_openapi(tmp_path):
    """When no openapi spec exists, the census should use framework regex (no crash)."""
    # A directory with no routes and no openapi spec should return empty via framework fallback
    sites = census(tmp_path, runner=lambda cmd, **kw: type("R", (), {"stdout": "", "returncode": 0})())
    assert isinstance(sites, list)
