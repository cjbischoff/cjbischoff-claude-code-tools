"""Sanitize developer-supplied background context before it enters a review prompt (REQ-P8).

Background text is untrusted input. Five guards run in order: reject over a 1 MB
cap (``ValueError``), strip control characters (newline and tab kept), neutralize
envelope-delimiter smuggling, hard-abort on any detected secret, then run
``redactor.safe_for_prompt`` for defense in depth.

The explicit ``verify_no_secrets`` call runs BEFORE ``safe_for_prompt`` on
purpose: ``safe_for_prompt`` redacts first and only aborts on a secret that
survives masking, so a maskable token would pass silently. REQ-P8 requires that
any detected secret aborts, so we verify the un-redacted text first.
"""

from __future__ import annotations

from pathlib import Path

from sec_overlay import redactor
from sec_overlay.envelope import neutralize_markers

BACKGROUND_MAX_BYTES = 1_000_000

_KEEP = {"\n", "\t"}


def _strip_control(text: str) -> str:
    """Drop C0/C1 control characters, keeping newline and tab."""
    return "".join(c for c in text if c in _KEEP or (ord(c) >= 32 and ord(c) != 127))


def load_background(text: str | None = None, *, path: str | Path | None = None) -> str:
    """Sanitize background context for inclusion in a review prompt.

    Args:
        text: Background text supplied inline. Mutually exclusive with ``path``.
        path: File to read background text from. Mutually exclusive with ``text``.

    Returns:
        Sanitized text: control-stripped, delimiter-neutralized, secret-verified,
        and passed through ``redactor.safe_for_prompt``.

    Raises:
        ValueError: if neither or both sources are given, or the text exceeds
            ``BACKGROUND_MAX_BYTES``.
        redactor.SecretsPresent: if a high-confidence secret is detected.

    Example:
        >>> load_background("service reads config from S3")
        'service reads config from S3'
    """
    if (text is None) == (path is None):
        raise ValueError("load_background requires exactly one of text or path")
    if path is not None:
        raw = Path(path).read_text(encoding="utf-8", errors="replace")
    else:
        assert text is not None
        raw = text
    if len(raw.encode("utf-8")) > BACKGROUND_MAX_BYTES:
        raise ValueError(f"background exceeds {BACKGROUND_MAX_BYTES}-byte cap")
    cleaned = neutralize_markers(_strip_control(raw))
    redactor.verify_no_secrets(cleaned)
    return redactor.safe_for_prompt(cleaned)
