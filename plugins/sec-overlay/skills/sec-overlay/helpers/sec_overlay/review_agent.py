"""Diff-review agent seam: render the per-file review prompt, parse its response.

Mirrors `reflection.py`'s discipline: this module renders a prompt and parses
a response, it never dispatches. No shelled-out process, no network client, no model SDK —
`SKILL.md` owns dispatch (D-13), spawning one `review-file` subagent per file
and persisting its return with `workspace.record_agent_return`.

`parse_review_response` is the elevation-of-privilege backstop (REV-03): every
finding it produces carries `REVIEW_AGENT_CLAIM` as its only evidence source,
regardless of what the model's response claims, so `evidence.confirms_alone`
is false for every agent-authored finding and none can reach `confirmed` or
`fixed` on an LLM's say-so alone. Status is likewise assigned in code
(`FindingStatus.RAW`), never read from the response.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from sec_overlay.evidence import as_llm_claim
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.prompts import render_prompt
from sec_overlay.workspace import Workspace, _atomic_write, read_agent_return

REVIEW_AGENT_CLAIM = as_llm_claim("review-agent")

# The two tool calls a review-file response may name — see
# `agents/review-file.md`'s "## Output" section. No third shape exists.
CODE_COMMENT_TOOL = "code_comment"
TASK_DONE_TOOL = "task_done"
_KNOWN_TOOLS = frozenset({CODE_COMMENT_TOOL, TASK_DONE_TOOL})

# A missing return, a stale base/head pair, and an unparseable response are all
# ledgered identically — a reviewer failure, never a coverage failure (D-15).
SOURCE_SKIPPED_REASON = "review-source-skipped"


class ReviewResponseError(Exception):
    """A review-file response is malformed or names an unknown tool."""


def _review_file_template_path() -> Path:
    """Return the `review-file.md` agent prompt path, resolved from this file.

    Never derived from cwd (mirrors `reflection._review_filter_template_path`'s
    T-03-01 discipline) — resolution must be stable regardless of where the
    caller runs.
    """
    return Path(__file__).resolve().parents[2] / "agents" / "review-file.md"


def _render_change_files_block(changed_files: Sequence[str]) -> str:
    """Render the diff's other changed paths into the `{{CHANGE_FILES}}` block."""
    if not changed_files:
        return "(no other files changed in this diff)"
    return "\n".join(f"- {p}" for p in changed_files)


def render_review_prompt(
    path: str,
    rule_text: str,
    diff: str,
    changed_files: Sequence[str],
    *,
    repo_root: str = "",
    overlay_root: str = "",
) -> str:
    """Render the `agents/review-file.md` prompt for one file's review pass.

    Args:
        path: The file under review, substituted into `{{CURRENT_FILE_PATH}}`.
        rule_text: The rule doc `rule_glob.resolve_rule_doc` picked for this
            path, substituted into `{{SYSTEM_RULE}}` — the seam that makes
            RULE-01 observable: the checklist the reviewer reads is the doc
            resolved for this file, not a fixed one.
        diff: This file's diff hunk text, substituted into `{{DIFF}}`.
        changed_files: The other paths changed in this diff, rendered into
            `{{CHANGE_FILES}}` for context only — a comment about one of
            these must not become a finding against `path`.
        repo_root: Substituted into `{{REPO_ROOT}}` — the base every cited
            line is relative to (`PATH_BASE`). Defaults to empty for callers
            (existing unit tests) whose fixture template never references it.
        overlay_root: Substituted into `{{OVERLAY_ROOT}}` — where the
            harness's own `review_findings.py` lives, for the prompt's
            profile-decision note. Same empty default as `repo_root`.

    Returns:
        The fully rendered prompt text.

    Raises:
        ValueError: A template token had no substitution
            (`sec_overlay.prompts.render_prompt`).
    """
    template = _review_file_template_path().read_text()
    subs = {
        "CURRENT_FILE_PATH": path,
        "SYSTEM_RULE": rule_text,
        "DIFF": diff,
        "CHANGE_FILES": _render_change_files_block(changed_files),
        "REPO_ROOT": repo_root,
        "OVERLAY_ROOT": overlay_root,
    }
    return render_prompt(template, subs)


def _stable_finding_id(rule_id_prefix: str, path: str, line: int, cls: str) -> str:
    """Derive a deterministic finding id from identity fields (idempotent re-parse)."""
    key = f"{rule_id_prefix}|{path}|{line}|{cls}"
    return f"{rule_id_prefix}-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]}"


def parse_review_response(
    text: str, *, path: str, rule_id_prefix: str
) -> tuple[list[Finding], int]:
    """Parse a recorded review-file response into findings for `path`.

    Accepts only `code_comment` and `task_done` entries. A `code_comment`
    naming a path other than `path` is discarded and counted rather than
    converted, so context gathered from another file can never become a
    finding against this one (OCR's Strict Focus Rule, enforced mechanically
    here rather than only asked for in the prompt).

    Args:
        text: The raw recorded response text (a JSON array of tool calls).
        path: The file under review; only `code_comment` entries naming this
            exact path become findings.
        rule_id_prefix: Prefix combined with each comment's defect class to
            form `Finding.rule_id`, and with the path/line/class to derive a
            deterministic `Finding.id`.

    Returns:
        `(findings, discarded)` — findings for `path`, and the count of
        `code_comment` entries discarded for naming a different path.

    Raises:
        ReviewResponseError: `text` is not valid JSON, is not a JSON array,
            names a tool other than `code_comment`/`task_done`, or a
            `code_comment` entry is missing a `line` or a `message`.
    """
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReviewResponseError(f"review response is not valid JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise ReviewResponseError("review response must be a JSON array of tool calls")

    findings: list[Finding] = []
    discarded = 0
    for entry in parsed:
        if not isinstance(entry, dict) or entry.get("tool") not in _KNOWN_TOOLS:
            raise ReviewResponseError(f"review response named an unknown tool: {entry!r}")
        if entry["tool"] == TASK_DONE_TOOL:
            continue

        line = entry.get("line")
        message = entry.get("message")
        if line is None or not message:
            raise ReviewResponseError(f"code_comment entry missing line or message: {entry!r}")

        if entry.get("path") != path:
            discarded += 1
            continue

        cls = entry.get("defect_class") or "unknown"
        findings.append(
            Finding(
                id=_stable_finding_id(rule_id_prefix, path, line, cls),
                rule_id=f"{rule_id_prefix}.{cls}",
                cls=cls,
                status=FindingStatus.RAW,
                severity=Severity.MEDIUM,
                file=path,
                line=line,
                message=message,
                evidence_sources=[REVIEW_AGENT_CLAIM],
            )
        )
    return findings, discarded


def agent_label(path: str) -> str:
    """Derive a stable, filesystem-safe recorded-return label for one file.

    A repo path carries `/` and cannot be a `runs/<label>.txt` filename
    directly (mirrors `_stable_finding_id`'s hash-derivation approach) — the
    label is a deterministic hash of the path instead.
    """
    digest = hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]
    return f"review-file-{digest}"


@dataclass(frozen=True)
class ReviewPlanEntry:
    """One `--prepare` plan entry: where its prompt lives and what to record it under."""

    path: str
    prompt_path: str
    agent_label: str
    base: str
    head: str


def write_review_plan(ws: Workspace, entries: Sequence[ReviewPlanEntry]) -> Path:
    """Write `runs/review_plan.json`, the `--prepare` half's SKILL.md-facing manifest.

    Args:
        ws: Workspace whose `runs/` receives the plan.
        entries: One entry per reviewable file, in selection order.

    Returns:
        The path written.
    """
    path = ws.runs / "review_plan.json"
    _atomic_write(path, json.dumps([asdict(e) for e in entries], indent=2))
    return path


@dataclass(frozen=True)
class ReviewSourceSkip:
    """Record of a file whose review source produced nothing (D-15 fail-open)."""

    path: str
    reason: str
    error: str


def recorded_return_source(ws: Workspace, *, base: str, head: str):
    """Build a per-file source reading recorded `review-file` returns from disk.

    Each return is recorded as a JSON envelope (`{"base", "head", "response"}`)
    under its own `agent_label`. A return recorded for a different base/head
    pair is refused rather than consumed, so a stale return can never
    masquerade as this run's finding (T-03-19).

    Args:
        ws: Workspace `runs/<label>.txt` returns are read from.
        base: This run's resolved base SHA.
        head: This run's resolved head SHA.

    Returns:
        A callable taking one file path and returning its findings. Raises
        `ValueError` for a missing return or a base/head mismatch;
        `ReviewResponseError` from `parse_review_response` propagates
        unchanged. The caller treats all of these identically — one skip,
        zero findings for that file (D-15).
    """

    def _source(path: str) -> list[Finding]:
        text = read_agent_return(ws, agent_label(path))
        if text is None:
            raise ValueError(f"no recorded return for {path}")
        try:
            envelope = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"recorded return for {path} is not valid JSON: {exc}") from exc
        if envelope.get("base") != base or envelope.get("head") != head:
            raise ValueError(f"recorded return for {path} was captured for a different base/head")
        findings, _discarded = parse_review_response(
            envelope.get("response", ""), path=path, rule_id_prefix="review"
        )
        return findings

    return _source
