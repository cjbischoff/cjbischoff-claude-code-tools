"""Tests for the diff-anchored review comment payload (OUT-01)."""

import json

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.review_comments import (
    COMMENTS_FILENAME,
    DEFAULT_SIDE,
    comment_from_finding,
    write_review_comments,
)
from sec_overlay.workspace import Workspace

_MANIFEST = {"version": 1, "base_sha": "a" * 40, "head_sha": "b" * 40, "seal": "complete", "files": []}


def _finding(file="app.py", line=18, evidence="cursor.execute(query)", message="possible SQLi"):
    return Finding(
        id="F-0001",
        rule_id="review.sqli",
        cls="sqli",
        status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH,
        file=file,
        line=line,
        message=message,
        evidence=evidence,
    )


def test_comment_from_finding_maps_fields():
    c = comment_from_finding(_finding())
    assert c.path == "app.py"
    assert c.line == 18
    assert c.side == DEFAULT_SIDE
    assert c.existing_code == "cursor.execute(query)"
    assert c.content == "possible SQLi"


def test_write_review_comments_empty_list_still_has_manifest(tmp_path):
    ws = Workspace(tmp_path)
    path = write_review_comments(ws, [], _MANIFEST)
    payload = json.loads(path.read_text())
    assert payload["comments"] == []
    assert payload["coverage_manifest"] == _MANIFEST


def test_write_review_comments_writes_to_artifacts_dir(tmp_path):
    ws = Workspace(tmp_path)
    path = write_review_comments(ws, [], _MANIFEST)
    assert path == ws.artifacts / COMMENTS_FILENAME


def test_comment_payload_has_exactly_five_keys(tmp_path):
    ws = Workspace(tmp_path)
    c = comment_from_finding(_finding())
    path = write_review_comments(ws, [c], _MANIFEST)
    payload = json.loads(path.read_text())
    assert set(payload["comments"][0].keys()) == {"path", "line", "side", "existing_code", "content"}


def test_written_comment_matches_source_finding(tmp_path):
    ws = Workspace(tmp_path)
    c = comment_from_finding(_finding(file="pkg/mod.py", line=42, evidence="x = 1", message="msg"))
    path = write_review_comments(ws, [c], _MANIFEST)
    payload = json.loads(path.read_text())
    entry = payload["comments"][0]
    assert entry == {
        "path": "pkg/mod.py",
        "line": 42,
        "side": DEFAULT_SIDE,
        "existing_code": "x = 1",
        "content": "msg",
    }
