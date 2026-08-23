"""Post sec-overlay review findings to a GitHub pull request (REQ-S1).

This is a stdlib-only GitHub API client. It reads a ``review_result.json``, routes
findings by severity, and posts one pull-request review. Critical and high findings
become inline comments. Every other finding is listed in the review summary body.
The review event is always ``COMMENT`` so the action never blocks a merge on its own.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

_INLINE_SEVERITIES = {"critical", "high"}
_API_ROOT = "https://api.github.com"

Transport = Callable[[str, bytes, dict[str, str]], Any]


def route_findings(findings: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split findings into inline (critical/high) and summary (everything else).

    Args:
        findings: Finding records from ``review_result.json`` (``severity`` key).

    Returns:
        A ``(inline, summary)`` pair, each preserving input order.
    """
    inline = [f for f in findings if str(f.get("severity", "")).lower() in _INLINE_SEVERITIES]
    summary = [f for f in findings if str(f.get("severity", "")).lower() not in _INLINE_SEVERITIES]
    return inline, summary


def _line(f: dict) -> str:
    """One-line human label for a finding."""
    return f"**{f.get('severity', '?')}** `{f.get('rule_id', '?')}` ({f.get('id', '?')})"


def build_review_payload(findings: list[dict]) -> dict[str, Any]:
    """Build the GitHub pull-request review payload from findings.

    Args:
        findings: Finding records from ``review_result.json``.

    Returns:
        A payload dict with ``event`` (``COMMENT``), ``body`` (summary markdown),
        and ``comments`` (inline comments for critical/high findings).
    """
    inline, summary = route_findings(findings)
    comments = [
        {"path": f["path"], "line": f["line"], "body": f"sec-overlay: {_line(f)}"}
        for f in inline
    ]
    header = f"## sec-overlay review\n\n{len(inline)} inline, {len(summary)} summary."
    if summary:
        rows = "\n".join(f"- {f.get('path', '?')}:{f.get('line', '?')} — {_line(f)}" for f in summary)
        body = f"{header}\n\n### Lower-severity findings\n{rows}"
    else:
        body = header
    return {"event": "COMMENT", "body": body, "comments": comments}


def _urllib_transport(url: str, data: bytes, headers: dict[str, str]) -> Any:
    """Default transport: POST ``data`` to ``url`` and return the parsed JSON body."""
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post_review(
    *,
    owner: str,
    repo: str,
    pull_number: int,
    token: str,
    payload: dict[str, Any],
    transport: Transport = _urllib_transport,
) -> Any:
    """POST a review payload to the pull-request reviews endpoint.

    Args:
        owner: Repository owner.
        repo: Repository name.
        pull_number: Pull-request number.
        token: GitHub token for bearer auth.
        payload: The review payload from ``build_review_payload``.
        transport: Injectable ``(url, data, headers) -> response`` for testing.

    Returns:
        Whatever ``transport`` returns (the created review, for the default).
    """
    url = f"{_API_ROOT}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    return transport(url, json.dumps(payload).encode("utf-8"), headers)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: post a review from a ``review_result.json`` using GitHub Action env.

    Reads ``GITHUB_TOKEN`` and ``GITHUB_REPOSITORY`` (``owner/repo``) from the
    environment. Takes the result path and pull number from ``argv``.

    Args:
        argv: ``[result_json_path, pull_number]``; defaults to ``sys.argv[1:]``.

    Returns:
        Process exit code (``0`` on success, ``2`` on a configuration error).
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: pr_poster <review_result.json> <pull_number>", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN", "")
    slug = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in slug:
        print("pr_poster: GITHUB_TOKEN and GITHUB_REPOSITORY are required", file=sys.stderr)
        return 2
    owner, repo = slug.split("/", 1)
    findings = json.loads(Path(args[0]).read_text()).get("findings", [])
    payload = build_review_payload(findings)
    post_review(owner=owner, repo=repo, pull_number=int(args[1]), token=token, payload=payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
