"""Shared markdown fragments for finding renderers (report + redteam).

Kept in one place so the tolerance rules for agent-authored fields (which may
arrive in an unexpected shape) live in a single source of truth rather than
being re-derived per renderer.
"""

from __future__ import annotations


def signal_lines(d: object) -> list[str]:
    """Render an ``expected_signal`` value as labeled secure/insecure bullet lines.

    A red-team agent may write ``expected_signal`` as the ``{secure, insecure}``
    object the prompt asks for, or as a bare string. A bare string is treated as
    the insecure signal — the same meaning in every document that renders it.

    Args:
        d: The finding's ``expected_signal`` (dict, str, or None).

    Returns:
        Zero, one, or two ``  - **<label>:** <value>`` lines. Empty for an
        empty/None value.

    Example:
        >>> signal_lines("201 + record")
        ['  - **insecure:** 201 + record']
    """
    if isinstance(d, str):
        d = {"insecure": d} if d.strip() else {}
    if not isinstance(d, dict) or not d:
        return []
    lines: list[str] = []
    if "secure" in d:
        lines.append(f"  - **secure:** {d.get('secure', '_unspecified_')}")
    lines.append(f"  - **insecure:** {d.get('insecure', '_unspecified_')}")
    return lines
