"""Tests for the review-file agent seam: prompt rendering and response parsing.

`agents/review-file.md` is Task 2's file, not this task's. These tests
monkeypatch `_review_file_template_path` to a `tmp_path` fixture template
carrying the four uppercase content tokens, so `render_review_prompt`'s
logic is exercised without depending on a file this task does not own.
"""

import json

import pytest

from sec_overlay import review_agent
from sec_overlay.evidence import confirms_alone
from sec_overlay.models import FindingStatus
from sec_overlay.review_agent import (
    CODE_COMMENT_TOOL,
    REVIEW_AGENT_CLAIM,
    TASK_DONE_TOOL,
    ReviewResponseError,
    parse_review_response,
    render_review_prompt,
)

_TEMPLATE = (
    "# Review file\n"
    "path: {{CURRENT_FILE_PATH}}\n"
    "rule: {{SYSTEM_RULE}}\n"
    "diff: {{DIFF}}\n"
    "changed: {{CHANGE_FILES}}\n"
)

_PY_RULE = "## Python\n- no null-dereference: check for None before use"
_GO_RULE = "## Go\n- no nil-dereference: check err before use"
_DIFF = "@@ -1,2 +1,3 @@\n import os\n+os.system(cmd)\n print('hi')\n"


@pytest.fixture(autouse=True)
def _fake_template(tmp_path, monkeypatch):
    template_path = tmp_path / "review-file.md"
    template_path.write_text(_TEMPLATE)
    monkeypatch.setattr(review_agent, "_review_file_template_path", lambda: template_path)


# --- render_review_prompt -----------------------------------------------------


def test_render_review_prompt_substitutes_all_four_tokens():
    rendered = render_review_prompt("app.py", _PY_RULE, _DIFF, ["other.py"])
    assert "app.py" in rendered
    assert _PY_RULE in rendered
    assert _DIFF in rendered
    assert "other.py" in rendered
    assert "{{" not in rendered


def test_render_review_prompt_differs_per_file_language_in_same_run():
    py_rendered = render_review_prompt("app.py", _PY_RULE, _DIFF, [])
    go_rendered = render_review_prompt("main.go", _GO_RULE, _DIFF, [])
    assert "null-dereference" in py_rendered
    assert "null-dereference" not in go_rendered
    assert "nil-dereference" in go_rendered
    assert "nil-dereference" not in py_rendered


def test_render_review_prompt_raises_on_missing_substitution(tmp_path, monkeypatch):
    broken = tmp_path / "broken.md"
    broken.write_text(_TEMPLATE + "unfilled: {{UNKNOWN_TOKEN}}\n")
    monkeypatch.setattr(review_agent, "_review_file_template_path", lambda: broken)
    with pytest.raises(ValueError, match="unfilled prompt token"):
        render_review_prompt("app.py", _PY_RULE, _DIFF, [])


# --- parse_review_response -----------------------------------------------------


def _code_comment(**overrides):
    entry = {
        "tool": CODE_COMMENT_TOOL,
        "path": "app.py",
        "line": 2,
        "message": "os.system called with unsanitized input",
        "defect_class": "injection",
    }
    entry.update(overrides)
    return entry


def test_parse_review_response_converts_one_code_comment_to_one_finding():
    text = json.dumps([_code_comment()])
    findings, discarded = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert discarded == 0
    assert len(findings) == 1
    f = findings[0]
    assert f.file == "app.py"
    assert f.line == 2
    assert f.message == "os.system called with unsanitized input"
    assert f.cls == "injection"


def test_parse_review_response_discards_comment_for_a_different_path():
    text = json.dumps([_code_comment(path="other.py")])
    findings, discarded = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert findings == []
    assert discarded == 1


def test_parse_review_response_task_done_only_yields_empty_list_no_raise():
    text = json.dumps([{"tool": TASK_DONE_TOOL, "state": "DONE"}])
    findings, discarded = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert findings == []
    assert discarded == 0


def test_parse_review_response_drops_model_supplied_evidence_source():
    text = json.dumps([_code_comment(evidence_sources=["semgrep:py.null-deref"])])
    findings, _ = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert findings[0].evidence_sources == [REVIEW_AGENT_CLAIM]


def test_parse_review_response_findings_never_confirm_alone():
    text = json.dumps([_code_comment()])
    findings, _ = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert not confirms_alone(findings[0].evidence_sources)


def test_parse_review_response_raises_on_malformed_json():
    with pytest.raises(ReviewResponseError):
        parse_review_response("not json", path="app.py", rule_id_prefix="review")


def test_parse_review_response_raises_on_missing_line_or_message():
    text = json.dumps([_code_comment(line=None)])
    with pytest.raises(ReviewResponseError):
        parse_review_response(text, path="app.py", rule_id_prefix="review")

    text = json.dumps([_code_comment(message="")])
    with pytest.raises(ReviewResponseError):
        parse_review_response(text, path="app.py", rule_id_prefix="review")


def test_parse_review_response_assigns_status_in_code_not_from_model():
    text = json.dumps([_code_comment(status="confirmed")])
    findings, _ = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert findings[0].status == FindingStatus.RAW


def test_parse_review_response_is_idempotent_across_two_parses():
    text = json.dumps([_code_comment()])
    first, _ = parse_review_response(text, path="app.py", rule_id_prefix="review")
    second, _ = parse_review_response(text, path="app.py", rule_id_prefix="review")
    assert first == second
    assert first[0].id == second[0].id


# --- parse_review_response with bundle_paths (SCALE-01 widened focus rule) ------


def test_parse_review_response_keeps_comment_for_any_bundle_member():
    text = json.dumps([_code_comment(path="sibling.py")])
    findings, discarded = parse_review_response(
        text, path="app.py", rule_id_prefix="review", bundle_paths=frozenset({"app.py", "sibling.py"})
    )
    assert discarded == 0
    assert len(findings) == 1
    assert findings[0].file == "sibling.py"


def test_parse_review_response_discards_comment_outside_bundle_membership():
    text = json.dumps([_code_comment(path="stranger.py")])
    findings, discarded = parse_review_response(
        text, path="app.py", rule_id_prefix="review", bundle_paths=frozenset({"app.py", "sibling.py"})
    )
    assert findings == []
    assert discarded == 1


def test_parse_review_response_none_bundle_paths_keeps_single_path_behavior():
    text = json.dumps([_code_comment(path="app.py")])
    findings, discarded = parse_review_response(
        text, path="app.py", rule_id_prefix="review", bundle_paths=None
    )
    assert discarded == 0
    assert findings[0].file == "app.py"
