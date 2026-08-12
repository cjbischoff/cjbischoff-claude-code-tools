"""Tests for the systemic clustering pass."""

from sec_overlay.cluster import cluster_findings
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, read_findings, write_findings


def _f(id_, sev, line, status=FindingStatus.RAW, cls="authz", sink="ownsResource"):
    # No graph in tmp_path -> sink symbol resolves from the last dataflow hop.
    return Finding(
        id=id_,
        rule_id="r",
        cls=cls,
        status=status,
        severity=sev,
        file=f"route_{id_}.py",
        line=line,
        message="missing owner check",
        dataflow=["req.params.id", sink],
    )


def test_clusters_three_or_more_same_class_same_sink(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(
        ws,
        [
            _f("F-1", Severity.MEDIUM, 10),
            _f("F-2", Severity.HIGH, 11),
            _f("F-3", Severity.MEDIUM, 12),
        ],
    )
    n = cluster_findings(ws)
    assert n == 3
    by_id = {f.id: f for f in read_findings(ws)}
    # Primary is highest severity, tiebreak smallest id -> F-2.
    assert by_id["F-2"].cluster_id == "cluster:F-2"
    assert by_id["F-1"].cluster_id == "cluster:F-2"
    assert by_id["F-3"].cluster_id == "cluster:F-2"
    assert len(by_id["F-2"].affected_sites) == 3  # primary carries all sites
    assert by_id["F-1"].affected_sites == []  # members do not
    site_ids = {s["id"] for s in by_id["F-2"].affected_sites}
    assert site_ids == {"F-1", "F-2", "F-3"}


def test_two_sites_do_not_cluster(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(ws, [_f("F-1", Severity.HIGH, 10), _f("F-2", Severity.HIGH, 11)])
    assert cluster_findings(ws) == 0
    assert all(f.cluster_id is None for f in read_findings(ws))


def test_different_sink_does_not_cluster(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(
        ws,
        [
            _f("F-1", Severity.HIGH, 10, sink="ownsResource"),
            _f("F-2", Severity.HIGH, 11, sink="ownsResource"),
            _f("F-3", Severity.HIGH, 12, sink="somethingElse"),
        ],
    )
    assert cluster_findings(ws) == 0  # only 2 share ownsResource; needs 3


def test_confirmed_findings_are_never_clustered(tmp_path):
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(
        ws,
        [
            _f("F-1", Severity.HIGH, 10, status=FindingStatus.CONFIRMED),
            _f("F-2", Severity.HIGH, 11),
            _f("F-3", Severity.HIGH, 12),
        ],
    )
    assert cluster_findings(ws) == 0  # only 2 RAW share the sink; F-1 excluded
