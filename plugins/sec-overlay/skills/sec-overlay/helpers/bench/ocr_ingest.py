"""Parse ``ocr review --format json`` output into benchmark-only findings.

These :class:`Finding` objects exist only to score the open-code-review tool through
the same judge as sec-overlay. They are tagged ``llm-claimed:ocr`` and never satisfy
the tool-receipt gate, so they can never become harness findings.
"""

from __future__ import annotations

import json

from sec_overlay.models import Finding, FindingStatus, Severity

_SEVERITY = {s.value: s for s in Severity}


def _severity(raw: str | None) -> Severity:
    """Map an OCR severity string to :class:`Severity`, defaulting to MEDIUM."""
    return _SEVERITY.get(str(raw or "").strip().lower(), Severity.MEDIUM)


def ocr_findings(json_text: str) -> list[Finding]:
    """Map ``ocr review --format json`` comments to benchmark-only findings.

    Args:
        json_text: The JSON string OCR emits — top level ``{"comments": [...], ...}``,
            each comment ``{path, content, start_line, end_line, severity?, category?}``.

    Returns:
        One CONFIRMED :class:`Finding` per comment (CONFIRMED so the judge scores it),
        each with ``evidence_sources=["llm-claimed:ocr"]``. Benchmark-only — never a
        harness finding, never receipt-backed.

    Example:
        >>> ocr_findings('{"comments": [{"path": "a.py", "content": "x",
        ...   "start_line": 1, "end_line": 1}]}')[0].evidence_sources
        ['llm-claimed:ocr']
    """
    data = json.loads(json_text)
    findings: list[Finding] = []
    for i, c in enumerate(data.get("comments", [])):
        findings.append(Finding(
            id=f"OCR-{i:04d}",
            rule_id="ocr",
            cls=str(c.get("category") or "review-comment"),
            status=FindingStatus.CONFIRMED,
            severity=_severity(c.get("severity")),
            file=str(c.get("path", "")),
            line=int(c.get("start_line", 0) or 0),
            message=str(c.get("content", "")),
            evidence_sources=["llm-claimed:ocr"],
        ))
    return findings
