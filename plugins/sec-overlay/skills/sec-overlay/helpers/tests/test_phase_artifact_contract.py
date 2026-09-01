"""Group 1 (RC-9) acceptance tests: no phase reads what no earlier phase writes.

Each test names the requirement it pins. The defects these cover all share one
shape — a reader whose input has no producer, so the stage ledger records work
that never happened.
"""

from __future__ import annotations


def test_factcheck_phase_is_deleted() -> None:
    # REQ-42: the phase's only input (kb/verdicts.json) had no producing phase,
    # so every run recorded `factcheck: done` after doing nothing.
    from sec_overlay.driver import DETERMINISTIC_ACTIONS
    from sec_overlay.phases import PHASE_TABLE

    assert "factcheck" not in [p.name for p in PHASE_TABLE]
    assert "factcheck" not in DETERMINISTIC_ACTIONS


def test_no_verification_value_lacks_a_writer() -> None:
    # REQ-42: `fact-checked` was written only by the deleted factcheck stage.
    from sec_overlay.evidence import VERIFICATION_VALUES

    assert "fact-checked" not in VERIFICATION_VALUES


def test_the_factcheck_module_and_prompt_are_gone() -> None:
    # REQ-42: a deleted phase must leave no CLI-callable module and no prompt.
    import importlib.util
    from pathlib import Path

    assert importlib.util.find_spec("sec_overlay.factcheck") is None
    skill_root = Path(__file__).resolve().parents[2]
    assert not (skill_root / "agents" / "factcheck.md").exists()
