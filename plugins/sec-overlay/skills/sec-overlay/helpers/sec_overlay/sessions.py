"""Read-only rendering over sidecar session state and review ledgers (REQ-S2).

This module never writes. It reads the per-repo sidecar folders that a scan
already produced (``<slug>/state.json`` plus ``<slug>/artifacts/*.json``) and
renders a one-row-per-slug list and a per-session detail view for the
``sessions list`` / ``sessions show`` CLI subcommands.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def _read_json(path: Path) -> dict:
    """Return parsed JSON from ``path``, or an empty dict when absent/unreadable.

    Args:
        path: File to read.

    Returns:
        The parsed object, or ``{}`` when the file is missing or malformed.
    """
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _session_dirs(sessions_root: Path) -> list[Path]:
    """Return sidecar slug directories under ``sessions_root``, sorted by name.

    A directory qualifies when it holds a ``state.json`` file.

    Args:
        sessions_root: Base directory holding ``<slug>/`` session folders.

    Returns:
        The qualifying directories, sorted by directory name.
    """
    if not sessions_root.is_dir():
        return []
    dirs = [d for d in sessions_root.iterdir() if (d / "state.json").is_file()]
    return sorted(dirs, key=lambda d: d.name)


def _finding_counts(session_dir: Path) -> dict:
    """Return total and per-severity finding counts for one session.

    Args:
        session_dir: A ``<slug>/`` session directory.

    Returns:
        A dict with ``total`` and one key per severity seen (e.g. ``critical``);
        ``total`` is 0 when no ``review_result.json`` exists.
    """
    result = _read_json(session_dir / "artifacts" / "review_result.json")
    findings = result.get("findings", [])
    counts: dict = {"total": len(findings)}
    for finding in findings:
        sev = str(finding.get("severity", "")).lower()
        if sev:
            counts[sev] = counts.get(sev, 0) + 1
    return counts


def session_rows(sessions_root: Path) -> list[dict]:
    """Return one summary row per sidecar session, sorted by slug.

    Args:
        sessions_root: Base directory holding ``<slug>/`` session folders.

    Returns:
        A list of row dicts with keys ``id``, ``pass``, ``sha``, ``date``, and
        ``findings`` (a dict of counts with at least ``total``).

    Example:
        >>> rows = session_rows(Path("/repo/.sec-overlay"))
        >>> rows[0]["findings"]["total"]
        2
    """
    rows: list[dict] = []
    for session_dir in _session_dirs(sessions_root):
        state = _read_json(session_dir / "state.json")
        mtime = (session_dir / "state.json").stat().st_mtime
        rows.append(
            {
                "id": session_dir.name,
                "pass": state.get("pass_number"),
                "sha": state.get("active_sha"),
                "date": datetime.fromtimestamp(mtime, tz=UTC).isoformat(),
                "findings": _finding_counts(session_dir),
            }
        )
    return rows


def resolve_session(sessions_root: Path, session_id: str) -> Path:
    """Resolve ``session_id`` to a session directory under ``sessions_root``.

    Args:
        sessions_root: Base directory holding ``<slug>/`` session folders.
        session_id: A slug, or the literal ``"latest"`` for the newest session
            by ``state.json`` modification time.

    Returns:
        The resolved session directory.

    Raises:
        KeyError: When ``session_id`` matches no session.
    """
    dirs = _session_dirs(sessions_root)
    if session_id == "latest":
        if not dirs:
            raise KeyError("latest")
        return max(dirs, key=lambda d: (d / "state.json").stat().st_mtime)
    for session_dir in dirs:
        if session_dir.name == session_id:
            return session_dir
    raise KeyError(session_id)


def session_detail(session_dir: Path, *, severity: str | None) -> dict:
    """Return a detail view for one session, optionally filtered by severity.

    Args:
        session_dir: A ``<slug>/`` session directory.
        severity: When given, keep only findings whose severity matches
            case-insensitively; when ``None``, keep all findings.

    Returns:
        A dict with keys ``id``, ``pass``, ``sha``, ``stages``, ``ledger`` (a
        summary with ``position_reviews`` and ``dropped`` counts), and
        ``findings`` (the filtered finding records).
    """
    state = _read_json(session_dir / "state.json")
    result = _read_json(session_dir / "artifacts" / "review_result.json")
    ledger = _read_json(session_dir / "artifacts" / "review_ledger.json")
    findings = result.get("findings", [])
    if severity is not None:
        want = severity.lower()
        findings = [f for f in findings if str(f.get("severity", "")).lower() == want]
    return {
        "id": session_dir.name,
        "pass": state.get("pass_number"),
        "sha": state.get("active_sha"),
        "stages": state.get("stages", {}),
        "ledger": {
            "position_reviews": len(ledger.get("position_reviews", [])),
            "dropped": len(ledger.get("dropped", [])),
        },
        "findings": findings,
    }


def render_rows(rows: list[dict]) -> str:
    """Render session rows as a plain-text table.

    Args:
        rows: Rows from :func:`session_rows`.

    Returns:
        A newline-joined table; a single ``(no sessions)`` line when empty.
    """
    if not rows:
        return "(no sessions)"
    lines = [f"{'SESSION':<28} {'PASS':>4} {'SHA':<12} {'FINDINGS':>8}"]
    for row in rows:
        sha = (row.get("sha") or "-")[:12]
        lines.append(
            f"{row['id']:<28} {row.get('pass') or '-'!s:>4} "
            f"{sha:<12} {row['findings'].get('total', 0):>8}"
        )
    return "\n".join(lines)


def render_detail(detail: dict) -> str:
    """Render one session detail view as plain text.

    Args:
        detail: A detail dict from :func:`session_detail`.

    Returns:
        A newline-joined text block covering identity, stages, ledger summary,
        and findings.
    """
    stages = ", ".join(f"{k}={v}" for k, v in detail.get("stages", {}).items()) or "(none)"
    lines = [
        f"session: {detail['id']}",
        f"pass: {detail.get('pass')}    sha: {detail.get('sha')}",
        f"stages: {stages}",
        (
            f"ledger: position_reviews={detail['ledger']['position_reviews']} "
            f"dropped={detail['ledger']['dropped']}"
        ),
        f"findings ({len(detail['findings'])}):",
    ]
    for finding in detail["findings"]:
        lines.append(
            f"  {finding.get('id', '?')} {finding.get('severity', '?')} "
            f"{finding.get('rule_id', '?')} {finding.get('path', '?')}:{finding.get('line', '?')}"
        )
    return "\n".join(lines)
