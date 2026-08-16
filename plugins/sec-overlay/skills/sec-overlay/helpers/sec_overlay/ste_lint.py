"""Deterministic linter for the checkable subset of ASD-STE100 (spec §6).

Checks structural rules only: sentence length, semicolons, paragraph size,
plus two warning-level heuristics (noun clusters, buried sequences). Lexical
rules are directional and unenforced — the produced documents carry a
front-matter statement to that effect. Code fences, mermaid blocks, headings,
table structure, inline code, and URLs are exempt; table free-text cells are
linted.
"""

from __future__ import annotations

import re
from pathlib import Path

_SENTENCE_MAX = 25
_PARA_MAX_SENTENCES = 6
_CODE_SPAN = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://\S+")
# Only split at sentence-ending punctuation followed by whitespace and a capital
# letter — an abbreviation ("e.g.", "etc.") followed by a lowercase continuation
# never triggers a split; the abbreviation check below catches a capitalized
# word right after one anyway.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_ABBREV = re.compile(r"(?i:\b(?:e\.g|i\.e|etc|vs|cf|approx|viz|al)\.)$")
_CAP_RUN = re.compile(r"\b(?:[A-Z][a-z]+\s+){3,}[A-Z][a-z]+\b")
_UNBALANCED_FENCE = "unbalanced code fence — prose after it was not linted"


def _split_sentences(cleaned: str) -> list[str]:
    """Split prose into sentences, folding an abbreviation back onto its clause."""
    parts = [p for p in _SENT_SPLIT.split(cleaned) if p.strip()]
    sentences: list[str] = []
    for part in parts:
        if sentences and _ABBREV.search(sentences[-1].strip()):
            sentences[-1] = f"{sentences[-1]} {part}"
        else:
            sentences.append(part)
    return sentences


def _prose_blocks(text: str) -> tuple[list[str], list[str]]:
    """Split markdown into linted prose blocks, dropping exempt regions.

    Returns:
        ``(blocks, errors)`` — an unterminated code fence yields no blocks for
        the remainder of the file and reports an error instead of linting
        nothing silently.
    """
    blocks: list[str] = []
    errors: list[str] = []
    in_fence = False
    current: list[str] = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        if stripped.startswith(("#", "%%")):
            continue
        if stripped.startswith("|"):
            if set(stripped) <= set("|-: "):
                continue  # separator row
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            blocks.extend(c for c in cells if c and len(c.split()) > 1)
            continue
        if stripped.startswith(("-", "*", "+")) or re.match(r"^\d+[.)]\s", stripped):
            blocks.append(stripped.lstrip("-*+ ").lstrip("0123456789.) "))
            continue
        current.append(stripped)
    if current:
        blocks.append(" ".join(current))
    if in_fence:
        errors.append(_UNBALANCED_FENCE)
    return blocks, errors


def _clean(block: str) -> str:
    return _URL.sub("URL", _CODE_SPAN.sub("CODE", block))


def lint_prose(text: str) -> tuple[list[str], list[str]]:
    """Lint markdown prose against the checkable STE structural rules.

    Args:
        text: Full markdown document content.

    Returns:
        ``(errors, warnings)`` — human-readable rule violations.
    """
    blocks, errors = _prose_blocks(text)
    warnings: list[str] = []
    for block in blocks:
        cleaned = _clean(block)
        sentences = _split_sentences(cleaned)
        if len(sentences) > _PARA_MAX_SENTENCES:
            errors.append(f"paragraph over {_PARA_MAX_SENTENCES} sentences: {cleaned[:60]!r}…")
        for s in sentences:
            words = s.split()
            if len(words) > _SENTENCE_MAX:
                errors.append(f"sentence over {_SENTENCE_MAX} words: {s[:60]!r}…")
            if ";" in s:
                errors.append(f"semicolon in prose: {s[:60]!r}…")
            if s.lower().count(" then ") >= 2:
                warnings.append(f"sequence buried in prose (use a list): {s[:60]!r}…")
            m = _CAP_RUN.search(s[1:])  # skip sentence-initial capital
            if m:
                warnings.append(f"possible noun cluster over 3 words: {m.group(0)!r}")
    return errors, warnings


def main(argv: list[str] | None = None) -> int:
    """CLI: lint files; exit 1 on any error (warnings never fail)."""
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-ste-lint")
    parser.add_argument("files", nargs="+")
    parser.add_argument("--require-frontmatter", action="store_true")
    args = parser.parse_args(argv)
    failed = False
    for f in args.files:
        text = Path(f).read_text()
        errors, warns = lint_prose(text)
        if args.require_frontmatter and "ASD-STE100" not in text:
            errors.append("missing ASD-STE100 lexical-limitation statement in front matter")
        for e in errors:
            print(f"{f}: error: {e}")
            failed = True
        for w in warns:
            print(f"{f}: warning: {w}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
