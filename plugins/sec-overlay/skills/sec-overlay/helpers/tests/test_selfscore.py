from sec_overlay import selfscore
from sec_overlay.models import Finding, FindingStatus, Severity
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
    }
    assert load_state(ws).budget["self_score"] == score
