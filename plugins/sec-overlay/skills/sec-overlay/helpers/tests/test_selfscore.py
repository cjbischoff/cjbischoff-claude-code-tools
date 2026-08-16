import json

from sec_overlay import selfscore
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.selfscore import build_self_score
from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace, write_findings


def _f(id_, status, **kw):
    return Finding(
        id=id_,
        rule_id="r",
        cls="authz",
        status=status,
        severity=Severity.MEDIUM,
        file="a.py",
        line=1,
        message="m",
        **kw,
    )


def test_self_score_counts_by_status_and_persists(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(
        ws,
        [
            _f("F-1", FindingStatus.CONFIRMED),
            _f("F-2", FindingStatus.FIXED),
            _f("F-3", FindingStatus.NEEDS_DEPLOYMENT_TESTING),
            _f("F-4", FindingStatus.REJECTED),
            _f("F-5", FindingStatus.NEEDS_DEPLOYMENT_TESTING, cluster_id="cluster:F-5"),
            _f(
                "F-6",
                FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                cluster_id="cluster:F-5",
                reachability={"reachable": False, "blocker": "external-boundary"},
            ),
        ],
    )
    score = selfscore.write_self_score(ws)
    assert score == {
        "reported": 2,
        "confirmed": 1,
        "needs_runtime": 3,
        "rejected": 1,
        "clusters": 1,
        "external_boundary": 1,
        "shipping": 5,
        "critic_viable": 0,
        "critic_rejected": 0,
        "critic_reject_rate": 0.0,
    }
    assert load_state(ws).budget["self_score"] == score


def _write_finding_json(ws, fid, status):
    (ws.findings_dir / f"{fid}.json").write_text(
        json.dumps(
            {
                "id": fid,
                "rule_id": "r",
                "cls": "c",
                "status": status,
                "severity": "low",
                "file": "a.py",
                "line": 1,
                "message": "m",
                "dataflow": [],
            }
        )
    )


def test_shipping_counts_full_set(tmp_path):
    ws = Workspace(tmp_path)
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    _write_finding_json(ws, "F-1", "confirmed")
    _write_finding_json(ws, "F-2", "fixed")
    _write_finding_json(ws, "F-3", "needs-deployment-testing")
    _write_finding_json(ws, "F-4", "rejected")
    score = build_self_score(ws)
    assert score["shipping"] == 3


def _wf(ws, fid, events):
    (ws.findings_dir / f"{fid}.json").write_text(
        json.dumps(
            {
                "id": fid,
                "rule_id": "r",
                "cls": "sqli",
                "status": "raw",
                "severity": "low",
                "file": "a.py",
                "line": 1,
                "message": "m",
                "history": [{"event": e} for e in events],
            }
        )
    )


def test_self_score_counts_critic_reject_rate(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure()
    _wf(ws, "F-1", ["critic:viable"])
    _wf(ws, "F-2", ["critic:rejected"])
    _wf(ws, "F-3", ["critic:rejected"])
    s = build_self_score(ws)
    assert s["critic_viable"] == 1
    assert s["critic_rejected"] == 2
    assert abs(s["critic_reject_rate"] - (2 / 3)) < 1e-9


def test_self_score_reject_rate_zero_without_critic_events(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure()
    _wf(ws, "F-1", [])
    assert build_self_score(ws)["critic_reject_rate"] == 0.0
