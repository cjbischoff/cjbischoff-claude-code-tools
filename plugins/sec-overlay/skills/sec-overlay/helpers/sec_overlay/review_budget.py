"""Token-size estimation for review-mode budgeting (REQ-P1, extended by REQ-P4).

`estimate_tokens` is the raw size primitive — OCR's `len(text) // 4`
characters-per-token heuristic. Bundle grouping (`bundle.py`) and sibling-context
capping (`review_agent.py`) share it for their size caps. REQ-P4's budget
projection (`estimate_review_cost`, `BudgetGate`) builds on this primitive
rather than redefining it, so one estimator governs every review-mode size
decision.
"""

from __future__ import annotations

# OCR's per-file plan-loop cost shape (system_prompt.py budget accounting):
# one plan-prompt + plan-output, then ROUNDS review passes each re-sending the
# diff plus the plan prompt and emitting a bounded round output.
PLAN_PROMPT = 2000
PLAN_OUT = 400
ROUNDS = 7
ROUND_OUT = 700

# A single file whose projected review cost exceeds this fraction of the whole
# token budget is excluded before review — one oversized file must not consume
# the budget every other file shares.
FILE_BUDGET_FRACTION = 0.8

# Manifest/finding note stamped on a file skipped because the budget latched.
BUDGET_SKIP_NOTE = "skipped(budget)"


def estimate_tokens(text: str) -> int:
    """Estimate the token count of a text block.

    Uses OCR's `len // 4` characters-per-token heuristic — an approximation,
    not a real tokenizer. Sufficient for size caps where exactness is not
    required and a cheap, deterministic estimate matters more.

    Args:
        text: Any text (a diff, a prompt fragment).

    Returns:
        Estimated token count, `len(text) // 4`, never negative.

    Example:
        >>> estimate_tokens("abcdefgh")
        2
    """
    return len(text) // 4


def estimate_review_cost(diff_text: str) -> int:
    """Project the total token cost of reviewing one file's diff.

    Follows OCR's plan-loop shape: the diff and a plan prompt are sent once for
    planning, then re-sent for each of `ROUNDS` review passes, with a bounded
    output on each. Reduces to `8 * diff_tokens + 21300`; an empty diff costs
    the fixed 21300 floor.

    Args:
        diff_text: The unified diff for one file.

    Returns:
        Estimated total review token cost, always positive.

    Example:
        >>> estimate_review_cost("")
        21300
    """
    diff = estimate_tokens(diff_text)
    return diff + (PLAN_PROMPT + PLAN_OUT) + ROUNDS * (diff + PLAN_PROMPT) + ROUNDS * ROUND_OUT


class BudgetGate:
    """Look-ahead admission gate for a hard review token budget.

    A budget of 0 means unlimited — every estimate is admitted. Otherwise
    `admit` commits spend when the running total plus the estimate stays within
    budget; the first projected breach latches the gate closed, so every later
    call is refused regardless of size. Latching keeps coverage honest: once the
    budget cannot fit the next file, the run seals `partial` rather than
    cherry-picking small files past the breach.
    """

    def __init__(self, budget: int) -> None:
        """Create a gate for a token budget.

        Args:
            budget: Total token budget; 0 means unlimited.
        """
        self._budget = budget
        self._spent = 0
        self._latched = False

    def admit(self, estimate: int) -> bool:
        """Admit an estimated cost, committing spend when it fits.

        Args:
            estimate: Projected token cost of the next file.

        Returns:
            True if admitted (spend committed), False if refused. Unlimited
            budgets always admit; a latched gate always refuses.
        """
        if self._budget == 0:
            return True
        if self._latched:
            return False
        if self._spent + estimate <= self._budget:
            self._spent += estimate
            return True
        self._latched = True
        return False
