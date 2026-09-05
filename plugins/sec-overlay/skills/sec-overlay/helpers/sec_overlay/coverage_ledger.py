"""Machine-checked coverage-completeness ledger (kb/coverage-ledger.json).

The single coverage source (REQ-04). Its central invariant is enforced in code: a scan
may not claim ``completeness == "complete"`` while any surface is ``needs_follow_up``,
any item is deferred, or any question is still open. Keeps "gaps logged, never silently
dropped" a machine fact, not a promise.
"""

from __future__ import annotations

import json

from sec_overlay.models import FindingStatus
from sec_overlay.workspace import Workspace, read_findings

_DISPOSITIONS = {"reported", "no_issue_found", "rejected", "not_applicable", "needs_follow_up"}
_COMPLETENESS = {"complete", "partial", "unknown"}


_REPORTED = {FindingStatus.CONFIRMED, FindingStatus.FIXED, FindingStatus.NEEDS_DEPLOYMENT_TESTING}
_SETTLED_NO_ISSUE = {FindingStatus.REJECTED, FindingStatus.INFORMATIONAL}


def build_coverage_ledger(ws: Workspace) -> dict:
    """Derive + persist the coverage-completeness ledger from attack_surface × findings.

    One surface per distinct ``(file, line)`` sink site within each non-``deps``
    ``attack_surface`` class, so a second sink in the same class never inherits a
    coverage claim its sibling earned: ``reported`` (≥1 confirmed/fixed/needs-
    deployment-testing finding at that site), ``no_issue_found`` (only rejected/
    informational findings at that site), or ``needs_follow_up`` (a non-terminal
    finding at that site). A class with no finding at all still emits one
    class-level surface (``id`` equal to the class name, no ``site``) so it does
    not vanish from the ledger. ``completeness`` is ``complete`` only when no
    surface needs follow-up, else ``partial``; ``unknown`` when there is no
    scan-profile. Writes ``kb/coverage-ledger.json`` and returns the ledger.

    Args:
        ws: Workspace to read the profile + findings from and write the ledger into.

    Returns:
        The coverage-ledger dict (also persisted).
    """
    prof_path = ws.kb / "scan-profile.json"
    if not prof_path.exists():
        ledger: dict = {
            "completeness": "unknown", "surfaces": [], "deferred": [], "open_questions": [],
        }
        ws.kb.mkdir(parents=True, exist_ok=True)
        (ws.kb / "coverage-ledger.json").write_text(json.dumps(ledger, indent=2))
        return ledger
    profile = json.loads(prof_path.read_text())
    classes = [c for c in profile.get("attack_surface", []) if c != "deps"]
    by_site: dict[tuple[str, str, int], list[FindingStatus]] = {}
    for f in read_findings(ws):
        by_site.setdefault((f.cls, f.file, f.line), []).append(f.status)
    # Per-class terminal-status check for D16: a class that shipped findings at
    # different sites than the attack_surface evidence should still show "reported".
    cls_has_terminal: dict[str, bool] = {}
    for f in read_findings(ws):
        if f.status in _REPORTED:
            cls_has_terminal[f.cls] = True
    surfaces = []
    for cls in classes:
        sites = {k: v for k, v in by_site.items() if k[0] == cls}
        if not sites:
            if cls_has_terminal.get(cls):
                surface = {"id": f"{cls}", "cls": cls, "disposition": "reported",
                           "reason": f"terminal finding(s) exist for class {cls}",
                           "next_step": "—"}
            else:
                surface = {"id": cls, "cls": cls, "disposition": "needs_follow_up"}
                surface["reason"] = "no terminal finding for this attack surface this pass"
                surface["next_step"] = f"hunt {cls} or record why it is not applicable"
            surfaces.append(surface)
            continue
        for (_, file, line), statuses in sites.items():
            site = f"{file}:{line}"
            if any(s in _REPORTED for s in statuses):
                disp = "reported"
            elif statuses and all(s in _SETTLED_NO_ISSUE for s in statuses):
                disp = "no_issue_found"
            else:
                # non-terminal statuses (RAW/CANDIDATE/STALE/DUPLICATE) remain
                disp = "needs_follow_up"
            surface = {"id": f"{cls}@{site}", "cls": cls, "site": site, "disposition": disp}
            if disp == "needs_follow_up":
                surface["reason"] = f"no terminal finding at sink site {site} this pass"
                surface["next_step"] = f"adjudicate {site}"
            surfaces.append(surface)
    completeness = (
        "complete"
        if not any(s["disposition"] == "needs_follow_up" for s in surfaces)
        else "partial"
    )
    # Coverage caveats (D18): surface the sast_plan's disabled-backend reasons
    # and any prefilter coverage notes so the report reader can calibrate.
    sast_caveats = {}
    codeql_reason = profile.get("sast_plan", {}).get("codeql", {}).get("reason", "")
    if codeql_reason:
        sast_caveats["reason"] = (
            f"CodeQL did not run: {codeql_reason}. "
            "No interprocedural taint receipts exist for any finding. "
            "Tier-1 evidence is limited to semgrep rules only."
        )
    notes_path = ws.kb / "investigate-coverage-notes.md"
    coverage_caveats = []
    if notes_path.exists():
        text = notes_path.read_text().strip()
        if text:
            coverage_caveats.append(
                f"Coverage notes: see kb/investigate-coverage-notes.md"
            )

    ledger = {
        "completeness": completeness, "surfaces": surfaces,
        "deferred": [], "open_questions": [],
        "sast_caveats": sast_caveats,
        "notes": {"coverage_caveats": coverage_caveats},
    }
    (ws.kb / "coverage-ledger.json").write_text(json.dumps(ledger, indent=2))
    return ledger


def validate_coverage_ledger(d: dict) -> list[str]:
    """Validate a coverage ledger; empty list == valid.

    Args:
        d: The ledger ``{completeness, surfaces[], deferred[], ...}``.

    Returns:
        Human-readable error strings; empty when valid. Enforces the completeness
        invariant: ``complete`` forbids ``needs_follow_up`` surfaces, a non-empty
        ``deferred``, and a non-empty ``open_questions``.
    """
    if not isinstance(d, dict):
        return ["coverage-ledger must be an object"]
    errs: list[str] = []
    completeness = d.get("completeness")
    if completeness not in _COMPLETENESS:
        errs.append(f"coverage-ledger.completeness must be one of {sorted(_COMPLETENESS)}")
    surfaces = d.get("surfaces")
    if not isinstance(surfaces, list):
        errs.append("coverage-ledger.surfaces must be a list")
        surfaces = []
    for i, s in enumerate(surfaces):
        if not isinstance(s, dict) or s.get("disposition") not in _DISPOSITIONS:
            errs.append(f"coverage-ledger.surfaces[{i}].disposition must be one of "
                        f"{sorted(_DISPOSITIONS)}")
        if isinstance(s, dict) and s.get("disposition") == "needs_follow_up":
            if not (s.get("reason") or "").strip():
                errs.append(f"coverage-ledger.surfaces[{i}] needs_follow_up requires a reason")
            if not (s.get("next_step") or "").strip():
                errs.append(f"coverage-ledger.surfaces[{i}] needs_follow_up requires a next_step")
    deferred = d.get("deferred", [])
    if not isinstance(deferred, list):
        errs.append("coverage-ledger.deferred must be a list")
        deferred = []
    open_questions = d.get("open_questions", [])
    if not isinstance(open_questions, list):
        errs.append("coverage-ledger.open_questions must be a list")
        open_questions = []
    if completeness == "complete":
        if deferred:
            errs.append("completeness=complete forbids a non-empty deferred[]")
        if open_questions:
            errs.append("completeness=complete forbids a non-empty open_questions[]")
        if any(isinstance(s, dict) and s.get("disposition") == "needs_follow_up"
               for s in surfaces):
            errs.append("completeness=complete forbids any surface with "
                        "disposition=needs_follow_up")
    return errs


def render_markdown(d: dict) -> str:
    """Render the coverage ledger as a report section.

    Args:
        d: The coverage ledger.

    Returns:
        A Markdown "Coverage completeness" section listing surfaces and deferred gaps.
    """
    lines = ["## Coverage completeness", "",
             f"Completeness: **{d.get('completeness', 'unknown')}**", "",
             "| Surface | Disposition | Reason | Next step |",
             "|---------|-------------|--------|-----------|"]
    surfaces = d.get("surfaces", [])
    # Filter non-shipping paths from needs_follow_up surfaces (D15).
    _NON_SHIPPING_PATTERNS = (
        ".test.", ".spec.", "__mocks__", "__fixtures__", "e2e/",
        ".stories.", "__tests__", "/test/", "/tests/",
        "internal/ufe-dev-server",
    )
    def _is_non_shipping(surface: dict) -> bool:
        site = surface.get("site", "")
        if surface.get("disposition") != "needs_follow_up":
            return False
        return any(p in site.lower() for p in _NON_SHIPPING_PATTERNS)

    filtered = [s for s in surfaces if not _is_non_shipping(s)]
    non_shipping_count = len(surfaces) - len(filtered)
    surfaces = filtered

    # Cap needs_follow_up surfaces to avoid flooding the report (D15).
    follow_up = [s for s in surfaces if s.get("disposition") == "needs_follow_up"]
    capped = follow_up[:20]
    capped_count = len(follow_up) - len(capped)
    other = [s for s in surfaces if s.get("disposition") != "needs_follow_up"]

    for s in other + capped:
        lines.append(
            f"| {s.get('id', '?')} | {s.get('disposition', '?')} "
            f"| {s.get('reason', '') or '—'} | {s.get('next_step', '') or '—'} |"
        )
    if capped_count:
        lines.append(f"| — | — | _({capped_count} more needs_follow_up surfaces omitted)_ | — |")

    # Caveats section (D18): render coverage caveats from the run's notes.
    notes = d.get("notes", {})
    caveats = notes.get("coverage_caveats", [])
    sast_reason = d.get("sast_caveats", {}).get("reason", "")
    if caveats or sast_reason:
        lines += ["", "### Limitations", ""]
        if sast_reason:
            lines.append(f"- {sast_reason}")
        for c in caveats:
            lines.append(f"- {c}")

    deferred = d.get("deferred", [])
    if deferred:
        lines += ["", "Deferred (not examined this pass):"]
        lines += [f"- {item}" for item in deferred]
    return "\n".join(lines)
