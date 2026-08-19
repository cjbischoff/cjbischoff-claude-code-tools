"""Retract-only reflection filter: an LLM verdict can remove a finding, never add one.

Mirrors `evidence.py`'s "code decides, not the LLM's claim" discipline
(D-16): `apply_verdict` is the sole authority over which findings are
retracted, and `PROTECTED_SUBJECT_CLASSES` is a hardcoded veto no verdict
can override, regardless of what the LLM's mapping says. The veto lives in
the prompt (`agents/review-filter.md`) AND in this module — the model
output is never trusted alone.

`build_payload` deliberately omits severity, category, and suggestion from
the LLM's input so the filter cannot rank or rewrite a finding, only ask to
remove it. `render_reflection_prompt` renders the review-filter agent
prompt wholesale (`sec_overlay.prompts.render_prompt`); `validate_verdict`
parses and validates the LLM's raw JSON response before any finding sees
it — reading only the named tool, the retracted id list, and the analysis
text, discarding every other field.

Every retraction — applied AND refused — and every fail-open skip is a
`ReflectionRetraction` / `ReflectionSkip` record for the never-silent
ledger (D-14/D-15) — the caller is responsible for collecting and
rendering these, never dropping them silently.

This module never spawns or calls a model itself — it performs zero
dispatch of any kind. `SKILL.md` spawns the review-filter subagent per
file; this module only builds its prompt and validates/applies its
response.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sec_overlay.prompts import render_prompt

RETRACTED_REASON = "reflection-retracted"
REFUSED_REASON = "reflection-retraction-refused"
SKIPPED_REASON = "reflection-skipped"

# The two tool calls a review-filter response may name — see
# `agents/review-filter.md`'s "## Output" section. No third shape exists.
APPROVE_ALL_TOOL = "approve_all_comments"
REPORT_INCORRECT_TOOL = "report_incorrect_comments"
_KNOWN_TOOLS = frozenset({APPROVE_ALL_TOOL, REPORT_INCORRECT_TOOL})

# Subject classes an LLM verdict can never retract, regardless of its
# analysis text (D-16). Code-owned veto, not configurable.
PROTECTED_SUBJECT_CLASSES = frozenset(
    {
        "memory-safety",
        "concurrency",
        "linkage",
        "compatibility",
        "unused-parameter",
    }
)


class _ReflectableFinding(Protocol):
    """Structural shape `apply_verdict`/`build_payload` need from a finding.

    `message` is deliberately absent: `build_payload` reads it defensively via
    `getattr(f, "message", "")` since not every caller's finding type carries it.
    """

    id: str
    line: int
    rule_id: str
    cls: str


@dataclass(frozen=True)
class ReflectionComment:
    """One finding's payload sent to the reflection LLM for a retract/keep verdict.

    Deliberately carries no severity, category, or suggestion field — the
    filter can only ask to remove a finding, never rank or rewrite one.
    """

    id: str
    content: str
    existing_code: str


@dataclass(frozen=True)
class ReflectionRetraction:
    """Record of a finding the reflection filter retracted."""

    path: str
    line: int
    rule_id: str
    reason: str
    analysis: str


@dataclass(frozen=True)
class ReflectionSkip:
    """Record of a file whose reflection pass was skipped (fail-open, D-15)."""

    path: str
    reason: str
    error: str


class ReflectionResponseError(Exception):
    """A reflection LLM's raw response is malformed or violates the retract-only contract."""


def _review_filter_template_path() -> Path:
    """Return the `review-filter.md` agent prompt path, resolved from this file.

    Never derived from cwd (mirrors `rule_glob.builtin_rule_docs_dir`'s T-03-01
    discipline) — resolution must be stable regardless of where the caller runs.
    """
    return Path(__file__).resolve().parents[2] / "agents" / "review-filter.md"


def _render_comments_block(comments: Sequence[ReflectionComment]) -> str:
    """Render this file's comments into the prompt's `### Comments` section."""
    if not comments:
        return "(no comments to review)"
    blocks = [
        f"- id: {c.id}\n  analysis: {c.content}\n  existing_code: {c.existing_code}"
        for c in comments
    ]
    return "\n".join(blocks)


def render_reflection_prompt(path: str, diff: str, comments: Sequence[ReflectionComment]) -> str:
    """Render the `agents/review-filter.md` prompt for one file's reflection pass.

    The payload is limited to each comment's id, analysis text, and quoted
    existing code — the filter has nothing to rank or rewrite, only to
    check (D-16).

    Args:
        path: The file's path, substituted into `{{PATH}}`.
        diff: This file's diff hunk text, substituted into `{{DIFF}}`.
        comments: This file's kept findings as reflection payload, rendered
            into `{{COMMENTS}}`.

    Returns:
        The fully rendered prompt text.

    Raises:
        ValueError: A template token had no substitution
            (`sec_overlay.prompts.render_prompt`).
    """
    template = _review_filter_template_path().read_text()
    subs = {"PATH": path, "DIFF": diff, "COMMENTS": _render_comments_block(comments)}
    return render_prompt(template, subs)


def validate_verdict(response: str, submitted_ids: Sequence[str]) -> dict[str, str]:
    """Parse and validate a reflection LLM's raw tool-call response.

    Reads only the named tool, its `comment_ids`, and its `analysis` text —
    every other field (severity, message, a would-be new finding) is
    ignored, so the filter has nothing to rank or rewrite (D-16).

    Args:
        response: Raw JSON text the LLM returned.
        submitted_ids: The ids this file's payload actually offered
            (`build_payload`'s output) — the only ids a verdict may act on.

    Returns:
        Mapping of retracted finding id -> its analysis text.
        `approve_all_comments` returns an empty mapping.

    Raises:
        ReflectionResponseError: The response is not valid JSON, names
            neither known tool, or `report_incorrect_comments` names an id
            outside `submitted_ids`.
    """
    try:
        parsed = json.loads(response)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReflectionResponseError(f"reflection response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict) or parsed.get("tool") not in _KNOWN_TOOLS:
        raise ReflectionResponseError(
            f"reflection response named neither {APPROVE_ALL_TOOL!r} "
            f"nor {REPORT_INCORRECT_TOOL!r}"
        )

    if parsed["tool"] == APPROVE_ALL_TOOL:
        return {}

    comment_ids = parsed.get("comment_ids") or []
    analysis = parsed.get("analysis") or []
    submitted = set(submitted_ids)
    unknown = [cid for cid in comment_ids if cid not in submitted]
    if unknown:
        raise ReflectionResponseError(f"reflection response named unsubmitted id(s): {unknown}")

    return {cid: (analysis[i] if i < len(analysis) else "") for i, cid in enumerate(comment_ids)}


def build_payload(
    path: str,
    findings: Sequence[_ReflectableFinding],
    file_text_by_path: dict[str, str],
) -> list[ReflectionComment]:
    """Build the reflection LLM's per-file input payload from kept findings.

    Args:
        path: The file's path, used to look up `file_text_by_path`.
        findings: Findings already surviving the position gate.
        file_text_by_path: Full file text by path, for the flagged line's
            surrounding code (empty string if the path is absent).

    Returns:
        One :class:`ReflectionComment` per finding, in input order.
    """
    text = file_text_by_path.get(path, "")
    lines = text.splitlines()
    comments: list[ReflectionComment] = []
    for f in findings:
        existing_code = lines[f.line - 1] if 0 < f.line <= len(lines) else ""
        comments.append(ReflectionComment(f.id, getattr(f, "message", ""), existing_code))
    return comments


def apply_verdict(
    findings: Sequence[_ReflectableFinding],
    verdict: dict[str, str],
    *,
    path: str,
) -> tuple[list[_ReflectableFinding], list[ReflectionRetraction]]:
    """Apply an LLM retract-verdict to kept findings, retract-only (D-16).

    A finding retracts only if its id is a key in `verdict` AND its `cls`
    is not in :data:`PROTECTED_SUBJECT_CLASSES`. When a verdict names an id
    whose `cls` IS protected, the retraction is refused — the finding stays
    in `kept` — but the refusal is still recorded in `retractions` with
    :data:`REFUSED_REASON`, never dropped silently, so a reviewer can see
    the filter tried and was stopped. An id in `verdict` that was never
    submitted (not in `findings`) is silently ignored — the verdict can
    only act on what it was shown.

    Args:
        findings: Findings surviving the position gate for this file.
        verdict: Mapping of finding id -> the LLM's retraction analysis text.
        path: The file's path, recorded on each retraction.

    Returns:
        ``(kept, retractions)`` — findings not retracted (including any
        protected-class finding whose retraction was refused), and a record
        per applied AND refused retraction, sorted by ``(path, line,
        rule_id)`` for the ledger.
    """
    kept: list[_ReflectableFinding] = []
    retractions: list[ReflectionRetraction] = []
    for f in findings:
        if f.id not in verdict:
            kept.append(f)
            continue
        if f.cls in PROTECTED_SUBJECT_CLASSES:
            kept.append(f)
            retractions.append(
                ReflectionRetraction(path, f.line, f.rule_id, REFUSED_REASON, verdict[f.id])
            )
        else:
            retractions.append(
                ReflectionRetraction(path, f.line, f.rule_id, RETRACTED_REASON, verdict[f.id])
            )
    retractions.sort(key=lambda r: (r.path, r.line, r.rule_id))
    return kept, retractions
