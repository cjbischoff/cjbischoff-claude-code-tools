"""REQ-M2: the headless skill driver behind `CCSkillAdapter`."""

from bench.adapter import CCSkillAdapter
from bench.driver import HeadlessDriver
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_driver_substitutes_tokens(tmp_path):
    calls = []

    def fake_runner(argv, **kw):
        calls.append(argv)
        return _Result(0)

    d = HeadlessDriver(["claude", "-p", "scan {target} into {workspace}"], runner=fake_runner)
    assert d.run("/repo", tmp_path / "ws") is True
    assert calls == [["claude", "-p", f"scan /repo into {tmp_path / 'ws'}"]]
    assert d.failures == []


def test_driver_records_failure_never_raises(tmp_path):
    def bad_runner(argv, **kw):
        raise OSError("no claude binary")

    d = HeadlessDriver(["claude", "-p", "{target}"], runner=bad_runner)
    assert d.run("/repo", tmp_path / "ws") is False
    assert d.failures and d.failures[0]["target"] == "/repo"
    assert "no claude binary" in d.failures[0]["error"]


def test_driver_nonzero_exit_is_failure(tmp_path):
    d = HeadlessDriver(
        ["claude", "-p", "{target}"],
        runner=lambda argv, **kw: _Result(1, stderr="boom"),
    )
    assert d.run("/repo", tmp_path / "ws") is False
    assert "boom" in d.failures[0]["error"]


def test_cc_skill_adapter_scans_and_reads_workspace(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    f = Finding(id="F-1", rule_id="r", cls="xss", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="a.py", line=1, message="m")
    write_findings(ws, [f])

    d = HeadlessDriver(["claude", "-p", "{target}"], runner=lambda argv, **kw: _Result(0))
    adapter = CCSkillAdapter(driver=d)
    out = adapter.scan("/repo", ws)
    assert [x.id for x in out] == ["F-1"]


def test_cc_skill_adapter_failure_yields_empty(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    d = HeadlessDriver(["claude", "-p", "{target}"],
                       runner=lambda argv, **kw: _Result(1, stderr="quota"))
    adapter = CCSkillAdapter(driver=d)
    assert adapter.scan("/repo", ws) == []
    assert d.failures
