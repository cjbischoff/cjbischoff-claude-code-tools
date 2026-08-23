"""Token-budget estimator and look-ahead gate (REQ-P4, Task 12)."""

from sec_overlay.review_budget import (
    FILE_BUDGET_FRACTION,
    PLAN_OUT,
    PLAN_PROMPT,
    ROUND_OUT,
    ROUNDS,
    BudgetGate,
    estimate_review_cost,
    estimate_tokens,
)


def _expected(diff_text: str) -> int:
    diff = len(diff_text) // 4
    return (
        diff
        + (PLAN_PROMPT + PLAN_OUT)
        + ROUNDS * (diff + PLAN_PROMPT)
        + ROUNDS * ROUND_OUT
    )


def test_shape_constants_match_ocr():
    assert (PLAN_PROMPT, PLAN_OUT, ROUNDS, ROUND_OUT) == (2000, 400, 7, 700)
    assert FILE_BUDGET_FRACTION == 0.8


def test_raw_primitive_unchanged():
    # estimate_tokens stays the len//4 size primitive used by bundle/review_agent
    assert estimate_tokens("abcdefgh") == 2
    assert estimate_tokens("") == 0


def test_cost_formula_empty_diff():
    assert estimate_review_cost("") == _expected("")
    # 0 + 2400 + 7*2000 + 7*700 == 21300
    assert estimate_review_cost("") == 21300


def test_cost_scales_with_diff_length():
    diff = "x" * 400  # 100 diff tokens
    assert estimate_review_cost(diff) == _expected(diff)
    assert estimate_review_cost(diff) > estimate_review_cost("")


def test_gate_unlimited_when_budget_zero():
    gate = BudgetGate(0)
    assert gate.admit(10**9) is True
    assert gate.admit(10**9) is True


def test_gate_admits_until_projected_breach_then_refuses_all():
    gate = BudgetGate(1000)
    assert gate.admit(400) is True
    assert gate.admit(400) is True
    # 800 + 400 > 1000 -> refuse
    assert gate.admit(400) is False
    # latched: a small estimate that would still fit is refused after first breach
    assert gate.admit(100) is False


def test_gate_admits_estimate_hitting_budget_exactly():
    gate = BudgetGate(1000)
    assert gate.admit(1000) is True
    assert gate.admit(1) is False
