"""Prompt rendering with a loud failure on any unfilled ``{{token}}``.

Token substitution for agent dispatch was done by hand, which is how the
patch prompt once lost its class token. ``render_prompt`` substitutes every
``{{KEY}}`` and refuses to return a template that still carries an unfilled
token — a missing substitution fails loudly instead of shipping a literal
``{{ATTACK_CLASS}}`` to a model.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def render_prompt(template: str, subs: dict[str, str]) -> str:
    """Substitute ``{{KEY}}`` tokens in ``template`` from ``subs``.

    Args:
        template: Prompt text with ``{{TOKEN}}`` placeholders.
        subs: Mapping of token name (without braces) to its value. Extra keys
            are ignored.

    Returns:
        The template with every provided token substituted.

    Raises:
        ValueError: One or more ``{{TOKEN}}`` placeholders had no substitution.

    Example:
        >>> render_prompt("scan {{T}}", {"T": "/repo"})
        'scan /repo'
    """
    rendered = _TOKEN.sub(lambda m: subs.get(m.group(1), m.group(0)), template)
    leftover = sorted(set(_TOKEN.findall(rendered)))
    if leftover:
        raise ValueError(f"unfilled prompt token(s): {', '.join(leftover)}")
    return rendered
