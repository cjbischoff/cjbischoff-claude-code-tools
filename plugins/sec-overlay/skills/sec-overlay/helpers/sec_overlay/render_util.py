"""Shared markdown fragments for finding renderers (report + redteam).

Kept in one place so the tolerance rules for agent-authored fields (which may
arrive in an unexpected shape) live in a single source of truth rather than
being re-derived per renderer.
"""

from __future__ import annotations


def _channel_lines(channel: dict) -> list[str]:
    """Render one named observation channel as a header line plus two signal lines."""
    name = channel.get("name") or "_unnamed channel_"
    egress = "needs egress" if channel.get("needs_egress") else "no egress"
    return [
        f"  - **{name}** ({egress})",
        f"    - **secure:** {channel.get('secure', '_unspecified_')}",
        f"    - **insecure:** {channel.get('insecure', '_unspecified_')}",
    ]


def signal_lines(d: object) -> list[str]:
    """Render an ``expected_signal`` value as labeled secure/insecure bullet lines.

    A red-team agent may write ``expected_signal`` as a list of named observation
    channels, as the ``{secure, insecure}`` object the prompt asks for, or as a
    bare string. A list renders one block per channel, each marked ``no egress``
    or ``needs egress`` so a tester reads the in-band oracle first. A bare string
    is treated as the insecure signal — the same meaning in every document that
    renders it.

    Args:
        d: The finding's ``expected_signal`` (list, dict, str, or None).

    Returns:
        Three ``  - **<name>** (<egress>)`` blocks per channel for a list, or
        zero to two ``  - **<label>:** <value>`` lines otherwise. Empty for an
        empty/None value.

    Example:
        >>> signal_lines("201 + record")
        ['  - **insecure:** 201 + record']
    """
    if isinstance(d, list):
        return [ln for c in d if isinstance(c, dict) for ln in _channel_lines(c)]
    if isinstance(d, str):
        d = {"insecure": d} if d.strip() else {}
    if not isinstance(d, dict) or not d:
        return []
    lines: list[str] = []
    if "secure" in d:
        lines.append(f"  - **secure:** {d.get('secure', '_unspecified_')}")
    lines.append(f"  - **insecure:** {d.get('insecure', '_unspecified_')}")
    return lines
