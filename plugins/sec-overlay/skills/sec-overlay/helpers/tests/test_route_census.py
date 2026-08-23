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
