"""Tests for the reflection filter: prompt rendering, verdict validation, and the
mechanical protected-subject veto (D-16)."""

import json
from pathlib import Path

import pytest

from sec_overlay.reflection import (
    APPROVE_ALL_TOOL,
    PROTECTED_SUBJECT_CLASSES,
    REFUSED_REASON,
    REPORT_INCORRECT_TOOL,
    RETRACTED_REASON,
    SKIPPED_REASON,
    ReflectionComment,
    ReflectionResponseError,
    ReflectionRetraction,
    ReflectionSkip,
    apply_verdict,
    render_reflection_prompt,
    validate_verdict,
)
from sec_overlay.report import (
    REFLECTION_SKIPPED_HEADING,
    render_reflection_skipped_section,
    to_markdown,
    write_review_ledger,
)
from sec_overlay.workspace import Workspace


class _Finding:
    def __init__(self, id: str, line: int, rule_id: str, cls: str):
        self.id = id
        self.line = line
        self.rule_id = rule_id
        self.cls = cls


_DIFF = "@@ -1,2 +1,3 @@\n import os\n+os.system(cmd)\n print('hi')\n"
_PATH = "app.py"
_COMMENTS = [ReflectionComment("F-1", "os.system with unsanitized input", "os.system(cmd)")]


# --- render_reflection_prompt -------------------------------------------------


def test_render_reflection_prompt_substitutes_path_and_diff():
    rendered = render_reflection_prompt(_PATH, _DIFF, _COMMENTS)
    assert _PATH in rendered
    assert _DIFF in rendered
    assert "{{PATH}}" not in rendered
    assert "{{DIFF}}" not in rendered
    assert "{{COMMENTS}}" not in rendered


def test_render_reflection_prompt_includes_all_five_protected_subjects():
    rendered = render_reflection_prompt(_PATH, _DIFF, _COMMENTS)
    for phrase in (
        "memory safety",
        "concurrency",
        "linkage",
        "compatibility",
        "unused parameter",
    ):
        assert phrase in rendered


def test_render_reflection_prompt_includes_ordered_method_steps():
    rendered = render_reflection_prompt(_PATH, _DIFF, _COMMENTS)
    veto_pos = rendered.index("Protected-subject veto")
    ground_a_pos = rendered.index("Ground A")
    ground_b_pos = rendered.index("Ground B")
    doubt_pos = rendered.index("When in doubt")
    assert veto_pos < ground_a_pos < ground_b_pos < doubt_pos


# --- validate_verdict ----------------------------------------------------------


def test_validate_verdict_approve_all_retracts_nothing():
    response = json.dumps({"tool": APPROVE_ALL_TOOL})
    assert validate_verdict(response, ["F-1"]) == {}


def test_validate_verdict_report_incorrect_retracts_submitted_id():
    response = json.dumps(
        {
            "tool": REPORT_INCORRECT_TOOL,
            "analysis": ["already sanitized upstream"],
            "comment_ids": ["F-1"],
        }
    )
    verdict = validate_verdict(response, ["F-1"])
    assert verdict == {"F-1": "already sanitized upstream"}


def test_validate_verdict_ignores_extra_fields():
    response = json.dumps(
        {
            "tool": REPORT_INCORRECT_TOOL,
            "analysis": ["already sanitized upstream"],
            "comment_ids": ["F-1"],
            "severity": "critical",
            "message": "rewrite this",
            "add_finding": {"id": "F-99"},
        }
    )
    verdict = validate_verdict(response, ["F-1"])
    assert verdict == {"F-1": "already sanitized upstream"}


def test_validate_verdict_raises_on_unsubmitted_id():
    response = json.dumps(
        {
            "tool": REPORT_INCORRECT_TOOL,
            "analysis": ["not real"],
            "comment_ids": ["F-2"],
        }
    )
    with pytest.raises(ReflectionResponseError):
        validate_verdict(response, ["F-1"])


def test_validate_verdict_raises_on_invalid_json():
    with pytest.raises(ReflectionResponseError):
        validate_verdict("not json at all", ["F-1"])


def test_validate_verdict_raises_when_neither_tool_named():
    response = json.dumps({"tool": "delete_everything"})
    with pytest.raises(ReflectionResponseError):
        validate_verdict(response, ["F-1"])


# --- apply_verdict: protected-subject veto (one test per subject, D-16) --------


@pytest.mark.parametrize("protected_cls", sorted(PROTECTED_SUBJECT_CLASSES))
def test_apply_verdict_refuses_and_records_each_protected_subject(protected_cls):
    findings = [_Finding("F-1", 2, "R1", protected_cls)]
    kept, retractions = apply_verdict(findings, {"F-1": "looks unnecessary"}, path="app.py")
    assert kept == findings
    assert len(retractions) == 1
    assert retractions[0].reason == REFUSED_REASON
    assert retractions[0].analysis == "looks unnecessary"


def test_apply_verdict_applied_retraction_uses_a_different_reason_than_refused():
    findings = [_Finding("F-1", 2, "R1", "xss")]
    _kept, retractions = apply_verdict(findings, {"F-1": "sanitized upstream"}, path="app.py")
    assert retractions[0].reason == RETRACTED_REASON
    assert RETRACTED_REASON != REFUSED_REASON


def test_apply_verdict_does_not_mutate_the_input_list():
    findings = [_Finding("F-1", 2, "R1", "xss"), _Finding("F-2", 3, "R2", "xss")]
    original = list(findings)
    kept, _retractions = apply_verdict(findings, {"F-1": "sanitized upstream"}, path="app.py")
    assert findings == original
    assert kept is not findings


# --- never-silent ledger for retractions and skips (D-14/D-15, Phase 3 Plan 05 Task 2) --------


def test_render_reflection_skipped_section_states_none_skipped_when_empty():
    md = render_reflection_skipped_section([])
    assert md.startswith(REFLECTION_SKIPPED_HEADING)
    assert "No file was skipped" in md


def test_render_reflection_skipped_section_lists_each_skip():
    skip = ReflectionSkip(path="app.py", reason=SKIPPED_REASON, error="response timed out")
    md = render_reflection_skipped_section([skip])
    rows = [line for line in md.splitlines() if line.startswith("| app.py")]
    assert len(rows) == 1
    assert SKIPPED_REASON in rows[0]
    assert "response timed out" in rows[0]


def test_to_markdown_renders_reflection_skipped_heading_with_zero_findings():
    rendered = to_markdown([], reflection_skips=[])
    assert REFLECTION_SKIPPED_HEADING in rendered


def test_write_review_ledger_includes_reflection_skipped_key(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure()
    skip = ReflectionSkip(path="app.py", reason=SKIPPED_REASON, error="boom")
    path = write_review_ledger(
        ws, position_reviews=[], dropped=[], reflection_retractions=[], reflection_skips=[skip]
    )
    data = json.loads(path.read_text())
    assert data["reflection_skipped"] == [
        {"path": "app.py", "reason": SKIPPED_REASON, "error": "boom"}
    ]


def test_write_review_ledger_refused_and_applied_retractions_share_one_list(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure()
    applied = ReflectionRetraction("a.py", 1, "R1", RETRACTED_REASON, "sanitized upstream")
    refused = ReflectionRetraction("b.py", 2, "R2", REFUSED_REASON, "looks unnecessary")
    path = write_review_ledger(
        ws,
        position_reviews=[],
        dropped=[],
        reflection_retractions=[applied, refused],
        reflection_skips=[],
    )
    data = json.loads(path.read_text())
    reasons = {entry["reason"] for entry in data["reflection_retractions"]}
    assert reasons == {RETRACTED_REASON, REFUSED_REASON}


def test_write_review_ledger_writes_no_second_artifact_file_for_reflection(tmp_path: Path):
    ws = Workspace(tmp_path)
    ws.ensure()
    write_review_ledger(
        ws,
        position_reviews=[],
        dropped=[],
        reflection_retractions=[ReflectionRetraction("a.py", 1, "R1", RETRACTED_REASON, "x")],
        reflection_skips=[ReflectionSkip("b.py", SKIPPED_REASON, "boom")],
    )
    json_files = list((tmp_path / "artifacts").glob("*.json"))
    reflection_named = [p for p in json_files if "reflection" in p.name]
    assert reflection_named == []
