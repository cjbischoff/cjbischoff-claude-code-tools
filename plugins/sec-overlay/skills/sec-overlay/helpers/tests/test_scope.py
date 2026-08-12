import json

from sec_overlay import scope
from sec_overlay.workspace import Workspace


def _ws(tmp_path, packages=None):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    if packages is not None:
        ws.kb.mkdir(parents=True, exist_ok=True)
        (ws.kb / "scan-scope.json").write_text(json.dumps({"ingested_packages": packages}))
    return ws


def test_package_absent_from_manifest_is_external(tmp_path):
    ws = _ws(tmp_path, packages=["@lume/web"])
    assert scope.is_external_package("@lume/account-portal-core", ws) is True


def test_package_in_manifest_is_not_external(tmp_path):
    ws = _ws(tmp_path, packages=["@lume/web", "@lume/account-portal-core"])
    assert scope.is_external_package("@lume/account-portal-core", ws) is False


def test_no_manifest_never_invents_a_boundary(tmp_path):
    ws = _ws(tmp_path, packages=None)
    assert scope.is_external_package("@lume/anything", ws) is False
