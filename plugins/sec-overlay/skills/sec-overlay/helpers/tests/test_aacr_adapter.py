"""Tests for the external-dataset adapters (AACR corpus rows, OCR cross-tool findings).

Both adapters live inside the bench oracle. AACR rows must never move the
real-confirmed headline; OCR findings are benchmark-only and never harness findings.
"""
import json

from bench.aacr_adapter import aacr_entries
from bench.corpus import Corpus
from bench.judge import JudgeResult
from bench.ocr_ingest import ocr_findings
from bench.tally import tally
from sec_overlay.models import FindingStatus, Severity

AACR_ROWS = [
    {
        "project_main_language": "Python",
        "pr_url": "https://github.com/o/r/pull/7",
        "pr_source_commit": "a" * 40,
        "pr_target_commit": "b" * 40,
        "pr_change_line_count": 12,
        "pr_category": "Bug Fix",
        "is_ai_comment": False,
        "source_model": "",
        "note": "off-by-one in loop bound",
        "path": "app.py",
        "side": "right",
        "from_line": 10,
        "to_line": 10,
        "category": "Code Defect",
        "context": "Diff Level",
        "label": 1,
    },
    {
        "project_main_language": "Go",
        "pr_url": "https://github.com/o/r/pull/8",
        "pr_source_commit": "c" * 40,
        "pr_target_commit": "d" * 40,
        "pr_change_line_count": 3,
        "pr_category": "Code Refactoring / Architectural Improvement",
        "is_ai_comment": True,
        "source_model": "Claude-Code/Claude-4.5-Sonnet",
        "note": "rename for clarity",
        "path": "main.go",
        "side": "right",
        "from_line": 42,
        "to_line": 44,
        "category": "Maintainability and Readability",
        "context": "File Level",
        "label": 0,
    },
]


def test_aacr_entries_tagged_aacr_and_valid():
    entries = aacr_entries(AACR_ROWS)
    assert len(entries) == 2
    assert all(e.source == "aacr" for e in entries)
    first = entries[0]
    assert first.file == "app.py"
    assert first.line == 10
    assert first.repo_url == "https://github.com/o/r/pull/7"
    assert first.commit == "a" * 40
    # label 1 -> positive, label 0 -> negative
    assert first.kind == "positive"
    assert entries[1].kind == "negative"
    # unique ids, and the corpus validates (source must be registered)
    assert len({e.finding_id for e in entries}) == 2
    assert Corpus(entries=entries).validate() == []


def test_aacr_security_category_tagged_as_security_slice():
    """REQ-T3e: a security-category row is tagged source='aacr-security'."""
    rows = [
        {**AACR_ROWS[0], "category": "Security Vulnerability"},
        {**AACR_ROWS[1], "category": "Security"},
        AACR_ROWS[0],  # "Code Defect" stays plain aacr
    ]
    entries = aacr_entries(rows)
    assert entries[0].source == "aacr-security"
    assert entries[1].source == "aacr-security"
    assert entries[2].source == "aacr"
    assert entries[0].cls == "security-vulnerability"
    assert Corpus(entries=entries).validate() == []


def test_aacr_security_slice_appears_in_tally_but_not_headline():
    """REQ-T3e: tally emits an 'aacr-security' by_source slice, excluded from headline."""
    def jr(fid, source, detected, kind="positive", cls="xss"):
        return JudgeResult(finding_id=fid, kind=kind, source=source, cls=cls,
                           detected=detected, method="deterministic", matched_id=None,
                           reasoning="")

    real = [jr("R1", "real-confirmed", True)]
    sec = [jr("S1", "aacr-security", True), jr("S2", "aacr-security", False, kind="negative")]
    corpus = Corpus(entries=[])
    sc = tally(real + sec, corpus)
    assert "aacr-security" in sc.by_source
    assert sc.by_source["aacr-security"]["tp"] == 1
    assert sc._real == tally(real, corpus)._real  # security slice never moves headline


def test_aacr_never_moves_real_headline():
    def jr(fid, source, detected, kind="positive", cls="xss"):
        return JudgeResult(finding_id=fid, kind=kind, source=source, cls=cls,
                           detected=detected, method="deterministic", matched_id=None,
                           reasoning="")

    real = [jr("R1", "real-confirmed", True), jr("R2", "real-confirmed", False)]
    aacr = [jr("A1", "aacr", True), jr("A2", "aacr", False, kind="negative")]
    corpus = Corpus(entries=[])

    real_only = tally(real, corpus)._real
    with_aacr = tally(real + aacr, corpus)._real
    assert with_aacr == real_only
    assert real_only.get("tp") == 1 and real_only.get("fn") == 1


def test_scorecard_markdown_carries_same_judge_caveat():
    corpus = Corpus(entries=[])
    md = tally([], corpus).to_markdown()
    lowered = md.lower()
    assert "judge" in lowered
    # cross-tool comparisons run OCR and sec-overlay through the same judge; the
    # scorecard must disclose that shared-judge bias so the number is read honestly.
    assert "same judge" in lowered


def test_ocr_findings_parse_to_confirmed_llm_claimed():
    payload = json.dumps({
        "comments": [
            {"path": "main.py", "content": "possible SQL injection",
             "start_line": 10, "end_line": 10, "severity": "HIGH", "category": "sqli"},
            {"path": "util.py", "content": "nit: rename", "start_line": 3, "end_line": 3},
        ],
        "warnings": [],
    })
    findings = ocr_findings(payload)
    assert len(findings) == 2
    f0 = findings[0]
    assert f0.file == "main.py" and f0.line == 10
    assert f0.message == "possible SQL injection"
    assert f0.severity == Severity.HIGH
    assert f0.status == FindingStatus.CONFIRMED
    assert "llm-claimed:ocr" in f0.evidence_sources
    # a comment with no severity still parses, defaulting sensibly
    assert findings[1].severity == Severity.MEDIUM
    assert len({f.id for f in findings}) == 2
