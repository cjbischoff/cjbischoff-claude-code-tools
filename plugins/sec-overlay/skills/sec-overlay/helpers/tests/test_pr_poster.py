"""Tests for the stdlib GitHub PR review poster (REQ-S1)."""
from __future__ import annotations

import json

from sec_overlay import pr_poster

_FINDINGS = [
    {"id": "F-1", "path": "app/a.py", "line": 10, "severity": "critical", "rule_id": "sqli"},
    {"id": "F-2", "path": "app/b.py", "line": 20, "severity": "high", "rule_id": "xss"},
    {"id": "F-3", "path": "app/c.py", "line": 30, "severity": "medium", "rule_id": "open-redirect"},
    {"id": "F-4", "path": "app/d.py", "line": 40, "severity": "low", "rule_id": "verbose-error"},
    {"id": "F-5", "path": "app/e.py", "line": 50, "severity": "info", "rule_id": "note"},
]


def test_route_findings_splits_inline_and_summary():
    inline, summary = pr_poster.route_findings(_FINDINGS)
    assert {f["id"] for f in inline} == {"F-1", "F-2"}
    assert {f["id"] for f in summary} == {"F-3", "F-4", "F-5"}


def test_build_review_payload_event_is_comment():
    payload = pr_poster.build_review_payload(_FINDINGS)
    assert payload["event"] == "COMMENT"


def test_build_review_payload_inline_comments_carry_path_and_line():
    payload = pr_poster.build_review_payload(_FINDINGS)
    comments = payload["comments"]
    assert [(c["path"], c["line"]) for c in comments] == [("app/a.py", 10), ("app/b.py", 20)]
    assert "critical" in comments[0]["body"]
    assert "sqli" in comments[0]["body"]


def test_build_review_payload_summary_body_lists_lower_severities():
    payload = pr_poster.build_review_payload(_FINDINGS)
    body = payload["body"]
    assert "open-redirect" in body
    assert "verbose-error" in body


def test_build_review_payload_empty_findings_has_no_comments():
    payload = pr_poster.build_review_payload([])
    assert payload["comments"] == []
    assert payload["event"] == "COMMENT"


def test_post_review_posts_to_reviews_endpoint_with_auth():
    seen = {}

    def fake_transport(url, data, headers):
        seen["url"] = url
        seen["data"] = json.loads(data)
        seen["headers"] = headers
        return {"id": 123}

    payload = pr_poster.build_review_payload(_FINDINGS)
    result = pr_poster.post_review(
        owner="acme", repo="widget", pull_number=7, token="t0ken",
        payload=payload, transport=fake_transport,
    )
    assert result == {"id": 123}
    assert seen["url"] == "https://api.github.com/repos/acme/widget/pulls/7/reviews"
    assert seen["headers"]["Authorization"] == "Bearer t0ken"
    assert seen["data"]["event"] == "COMMENT"
