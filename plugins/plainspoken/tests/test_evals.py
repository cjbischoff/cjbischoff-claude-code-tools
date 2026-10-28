"""Structure checks for evals/cases.json."""

import json
from pathlib import Path

CASES_PATH = Path(__file__).resolve().parent.parent / "evals" / "cases.json"
MODES = {"interview", "rewrite", "review", "brief", "lint", "deep"}
REQUIRED = ("id", "mode", "prompt", "input", "requirements")


def load_cases() -> list[dict]:
    """Return the case list from cases.json.

    Returns:
        The parsed `cases` array.
    """
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def test_cases_parse_and_are_not_empty():
    assert load_cases()


def test_every_case_has_required_fields():
    for case in load_cases():
        for key in REQUIRED:
            assert case.get(key), f"{case.get('id', '?')}: missing {key}"


def test_followup_is_optional_string():
    for case in load_cases():
        if "followup" in case:
            assert isinstance(case["followup"], str) and case["followup"], case["id"]


def test_ids_are_unique():
    ids = [case["id"] for case in load_cases()]
    assert len(ids) == len(set(ids))


def test_every_mode_is_known():
    for case in load_cases():
        assert case["mode"] in MODES, f"{case['id']}: unknown mode {case['mode']}"
