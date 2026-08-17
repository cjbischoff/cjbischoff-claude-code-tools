"""Render findings as SARIF + Markdown; assemble the final report from a workspace."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, is_dataclass
from pathlib import Path

from sec_overlay import cost
from sec_overlay.campaign import record_stage
from sec_overlay.coverage_ledger import render_markdown as render_coverage_ledger
from sec_overlay.evidence import is_tool_receipt
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.patch_status import PatchStatus, check_patch_applied, not_applied_caution
from sec_overlay.positioning import PositionResult
from sec_overlay.render_util import signal_lines
from sec_overlay.sarif import to_sarif
from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace, _atomic_write, load_paths, read_findings

_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_REPORTABLE = {FindingStatus.CONFIRMED, FindingStatus.FIXED}


def _risk_sort_key(f: Finding) -> tuple[int, int, str]:
    """Deterministic finding order: risk descending, then severity, then id.

    Used to order both the confirmed and needs-runtime lists and the triage
    table so direct callers (e.g. :func:`select_reportable`) and the report body
    agree. Findings with no ``risk_score`` fall back to severity order.

    Args:
        f: The finding to key.

    Returns:
        A ``(-risk, severity_rank, id)`` sort tuple.
    """
    return (-(f.risk_score or 0), _ORDER.get(f.severity.value, 9), f.id)


# Full template for these tiers; condensed (Summary/Mechanism/Severity/Fix) below.
_FULL_TIERS = {"critical", "high"}


def render_finding(f: Finding, patch_status: PatchStatus | None = None) -> str:
    """Render one finding as the verified-finding template (references/finding-template.md).

    Populated entirely from the Finding JSON fields so the prose never drifts from
    the data. Critical/High get the full 8 sections; Medium/Low get a condensed
    form (Summary, Mechanism, Severity, Fix). Dependency findings get a purpose-built
    dep-view (Summary with package@version, advisory, Reachability, Fix). The harness
    is static-only, so the Confirmation and Attack-Scenario sections are marked as
    static traces.

    Args:
        f: The finding to render.
        patch_status: Result of :func:`patch_status.check_patch_applied` for this
            finding's ``patch_diff`` against the real target, if a target was supplied
            to :func:`write_report`. A ``fixed`` finding not confirmed applied gets a
            caution note — ``verify.py`` only checks a patch against a throwaway copy,
            never the real target.

    Returns:
        A Markdown section string for the finding.
    """
    # Dep-view: early return for dependency findings.
    if f.cls == "deps":
        reach = f.reachability or {}
        rstate = "reachable" if reach.get("reachable") else "not reachable"
        blocker = reach.get("blocker") or "—"
        adv = (
            f.rule_id
            if f.rule_id.startswith("osv:")
            else (next((s for s in f.evidence_sources if "osv:" in s), f.rule_id))
        )
        pkg = (f.evidence or "").strip() or "(package unknown)"
        out = [
            f"### {f.id} — deps — {f.severity.value.title()}",
            "",
            f"**Package.** `{pkg}` — advisory `{adv}`.  ",
            f"Location: `{f.file}:{f.line}`.",
            "",
            (
                f"**Reachability.** {rstate} in this repo (blocker: {blocker}). "
                f"{f.message.split('|', 1)[0].strip()}"
            ),
            "",
            (f"**Fix.** Bump `{pkg.split('@')[0]}` to a release that resolves `{adv}`."),
            "",
        ]
        if f.status is FindingStatus.FIXED and patch_status is not None:
            caution = not_applied_caution(patch_status)
            if caution:
                out.insert(1, caution)  # right after the header line
        return "\n".join(out)

    receipts = [s for s in f.evidence_sources if is_tool_receipt(s)]
    claimed = [s for s in f.evidence_sources if not is_tool_receipt(s)]
    flow = "\n".join(f"   - `{hop}`" for hop in (f.dataflow or [])) or "   - (no dataflow recorded)"
    risk = f.risk_score if f.risk_score is not None else "-"
    verification = f.verification or "static analysis only — not dynamically confirmed"
    patch = (
        f"```diff\n{f.patch_diff.strip()}\n```"
        if f.patch_diff
        else "_(no patch generated; remediate per §2 root cause)_"
    )
    full = f.severity.value in _FULL_TIERS

    out = [f"### {f.id} — {f.cls} — {f.severity.value.title()}", ""]
    if f.status is FindingStatus.FIXED and patch_status is not None:
        caution = not_applied_caution(patch_status)
        if caution:
            out += [caution, ""]
    # §1 Summary
    out += [f"**1. Summary.** {f.message}  \nLocation: `{f.file}:{f.line}`.", ""]
    if f.asvs_ids or f.codeguard_ids:
        comp = []
        if f.asvs_ids:
            comp.append("ASVS " + ", ".join(f.asvs_ids))
        if f.codeguard_ids:
            comp.append("CodeGuard " + ", ".join(f.codeguard_ids))
        out += [f"**Compliance.** {'; '.join(comp)}.", ""]
    # §2 Mechanism
    out += ["**2. Mechanism (source).** Data flow:", flow]
    if f.evidence:
        out += ["", f"Sink evidence: `{f.evidence.strip()[:300]}`"]
    out += [""]
    # §3 Confirmation (full tier only)
    if full:
        out += [
            "**3. Confirmation (static).** Mechanical tool receipts: "
            + (
                ", ".join(f"`{r}`" for r in receipts)
                or "**NONE — not confirmable on llm-claimed evidence alone**"
            )
            + ".  "
        ]
        if claimed:
            out += ["Non-receipt / llm-claimed: " + ", ".join(f"`{c}`" for c in claimed) + ".  "]
        out += [f"Verification: `{verification}`.", ""]
        # §4 Impact
        impact_text = (f.impact or "").strip() or "(impact not recorded)"
        out += [f"**4. Impact.** {impact_text}", ""]
    # §5 Severity (full) / §3 Severity (condensed)
    sev_no, fix_no = ("5", "7") if full else ("3", "4")
    out += [
        (
            f"**{sev_no}. Severity Rationale.** "
            f"`{f.cvss_vector or '(no vector)'}` — computed risk **{risk}**. "
            "Score computed deterministically from the vector; tier held lower when a "
            "precondition is unproven."
        ),
        "",
    ]
    if not full:
        out += [
            (
                "**Confirmation:** "
                + (
                    ", ".join(f"`{r}`" for r in receipts)
                    or "**NONE — not confirmable on llm-claimed evidence alone**"
                )
                + "."
            ),
            "",
        ]
    # §7 Fix (full) / §4 Fix (condensed)
    out += [f"**{fix_no}. Fix.**", patch, ""]
    return "\n".join(out)


def render_ndt(f: Finding) -> str:
    """Render a needs-deployment-testing finding as a foregrounded, needs-runtime-labeled view.

    Populated from the fields an NDT finding actually carries — ``message`` (what/why),
    ``dataflow`` (source-side chain), ``preconditions``, and ``runtime_test`` (objective +
    secure/insecure signal). Always labeled needs-runtime and never described as confirmed; the
    runnable payloads/telemetry live in ``redteam-plan.md``.

    Args:
        f: A needs-deployment-testing finding.

    Returns:
        A Markdown section string for the finding.
    """
    rt = f.runtime_test or {}
    sig_lines = signal_lines(rt.get("expected_signal"))
    flow = (
        "\n".join(f"  - `{hop}`" for hop in (f.dataflow or [])) or "  - (no source chain recorded)"
    )
    pre = "\n".join(f"  - {p}" for p in (f.preconditions or [])) or "  - (none recorded)"
    out = [
        f"### {f.id} — {f.cls} — {f.severity.value.title()} · needs runtime proof",
        "",
        f"**What.** {f.message}  \nLocation: `{f.file}:{f.line}`.",
        "",
        "**Source-side chain.**",
        flow,
        "",
        "**Preconditions (out-of-repo barrier).**",
        pre,
        "",
    ]
    if rt.get("objective"):
        out += [f"**Runtime test.** {rt['objective']}"]
        out += sig_lines
    if f.affected_sites:
        out += [
            "",
            f"**Affected sites ({len(f.affected_sites)}).** One systemic pattern:",
            "",
            "| id | location |",
            "|----|----------|",
        ]
        out += [f"| {s['id']} | `{s['file']}:{s['line']}` |" for s in f.affected_sites]
        out += [""]
    out += ["_Runnable payloads + telemetry: see `redteam-plan.md`._", ""]
    return "\n".join(out)


def _short_title(text: str, limit: int = 72) -> str:
    """Trim a triage title to ``limit`` chars on a word boundary.

    Args:
        text: The raw title text.
        limit: Maximum characters before the ellipsis.

    Returns:
        ``text`` unchanged when within ``limit``; otherwise the longest
        whole-word prefix that fits, plus a trailing ``"…"``. Never cuts a word.
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip()
    return (cut or text[:limit].rstrip()) + "…"


def _triage_row(f: Finding, status_label: str, action: str) -> str:
    """Render one triage table row: id, risk, one-clause what, location, status, next action.

    Args:
        f: The finding.
        status_label: ``confirmed`` or ``needs-runtime``.
        action: The next action phrase.

    Returns:
        A single Markdown table row string (pipe-delimited).
    """
    what = _short_title((f.message or "").split("|", 1)[0].split(". ")[0].strip())
    risk = f.risk_score if f.risk_score is not None else "-"
    return f"| {f.id} | {risk} | {what} | {f.file}:{f.line} | {status_label} | {action} |"


def to_markdown(
    findings: list[Finding],
    token_spend: dict[str, int] | None = None,
    needs_deployment: list[Finding] | None = None,
    coverage: dict | None = None,
    coverage_ledger: dict | None = None,
    has_redteam_plan: bool = False,
    patch_statuses: dict[str, PatchStatus] | None = None,
    economics: dict | None = None,
    dropped: list | None = None,
    position_reviews: list[PositionResult] | None = None,
) -> str:
    """Render findings and optional token accounting as Markdown.

    Structure: Bottom line → Triage table → Detail link list (per-finding bodies
    live in ``findings/<ID>.md``, written by :func:`write_finding_details`) →
    Coverage / redteam link / coverage-ledger / token-spend tail.
    NDT findings are NEVER folded into confirmed counts; the ``Needs runtime proof``
    line is never 0 when ``needs_deployment`` is non-empty.

    Args:
        findings: Confirmed/fixed findings to render.
        token_spend: Optional per-phase token totals.
        needs_deployment: Findings real-but-unprovable from source alone. Reported
            separately, never counted as confirmed.
        coverage: Optional ``compute_coverage`` output (``kb/coverage.json``); when given,
            appends a "Coverage & limitations" section so a clean scan carries its
            denominator (O-007/O-033). Omitted entirely when ``None``.
        coverage_ledger: Optional coverage-completeness ledger (``kb/coverage-ledger.json``);
            when given, appends a "Coverage completeness" section. Omitted when ``None``.
        has_redteam_plan: True when ``redteam-plan.md`` exists in the reports dir; adds a
            "Manual runtime testing" section pointing the engineer at it (O-022).
        patch_statuses: Optional ``finding.id`` → :class:`PatchStatus`, from
            :func:`check_patch_applied` against the real target, for ``fixed`` findings.
        economics: Optional ``{"by_phase": dict, "by_model": dict, "by_phase_seconds": dict,
            "usd_estimate": float}`` from :func:`sec_overlay.cost`; renders a "Run economics"
            section and takes priority over ``token_spend`` when both are given.
        dropped: Review-mode findings the position gate placed outside the diff
            (``phase_gate.DroppedFinding``); rendered under ``DROPPED_FINDINGS_HEADING``
            unconditionally, so an empty run states none-dropped rather than omitting the
            section.
        position_reviews: Review-mode declines (``needs-position-review``); rendered under
            ``POSITION_REVIEW_HEADING`` the same way.

    Returns:
        A Markdown report string.
    """
    ndt_all = sorted(needs_deployment or [], key=_risk_sort_key)
    external = [f for f in ndt_all if f.completeness_tier == "external-unverifiable"]
    ndt = [f for f in ndt_all if f.completeness_tier != "external-unverifiable"]
    conf = sorted(findings, key=_risk_sort_key)

    # Bottom line — confirmed counts exclude NDT entirely (epistemic honesty)
    conf_counts = Counter(f.severity.value for f in findings)
    crit = conf_counts.get("critical", 0)
    high = conf_counts.get("high", 0)
    med = conf_counts.get("medium", 0)
    low = conf_counts.get("low", 0)
    total_conf = sum(conf_counts.values())
    if total_conf == 0:
        summary_sentence = "No source-provable findings."
    elif crit or high:
        summary_sentence = f"{'Critical' if crit else 'High'}-severity source-provable findings require immediate remediation."
    else:
        summary_sentence = "Source-provable findings at medium/low severity."
    counts_phrase = (
        ", ".join(
            f"{n} {label}"
            for label, n in (("critical", crit), ("high", high), ("medium", med), ("low", low))
            if n
        )
        or "none"
    )
    lines = [
        "# sec-overlay Report",
        "",
        f"**Bottom line.** {summary_sentence}  ",
        f"Confirmed: {counts_phrase}",
        f"Needs runtime proof: {len(ndt)}",
        "",
    ]

    # Triage table — all findings merged, risk-ordered desc
    all_triage = [(f, "needs-runtime", "run redteam-plan test") for f in ndt] + [
        (f, "confirmed", "bump" if f.cls == "deps" else "apply fix (§ below)") for f in conf
    ]
    all_triage.sort(key=lambda t: _risk_sort_key(t[0]))
    lines += [
        "## Triage",
        "",
        "| ID | Risk | What | Location | Status | Next action |",
        "|----|------|------|----------|--------|-------------|",
    ]
    for f, status_label, action in all_triage:
        lines.append(_triage_row(f, status_label, action))
    lines.append("")

    # Detail — risk-ordered links to per-finding files (bodies live in findings/<ID>.md)
    detail = sorted(list(conf) + list(ndt), key=_risk_sort_key)
    if detail:
        lines += ["## Detail", ""]
        for f in detail:
            risk = f.risk_score if f.risk_score is not None else "-"
            label = "needs-runtime" if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING else "confirmed"
            lines.append(
                f"- [{f.id}](findings/{f.id}.md) — risk {risk} — {label} — "
                f"{_short_title((f.message or '').split('|', 1)[0].split('. ')[0].strip())}"
            )
        lines.append("")
        lines += [
            (
                "_Informational findings (not shipped in this report) remain in "
                "`findings.json`._"
            ),
            "",
        ]

    # Review-mode drop/decline sections — always rendered, even when empty (D-14, POS-03)
    lines += ["", render_dropped_findings_section(dropped or [])]
    lines += ["", render_position_review_section(position_reviews or [])]

    # External-unverifiable leads — sink crosses into an un-ingested dependency
    if external:
        lines += [
            "",
            "## Leads — pending external-dependency verification",
            "",
            (
                "These findings' sinks cross into a package whose source was not "
                "ingested. They are capped leads, not confirmed findings."
            ),
        ]
        for f in external:
            lines += ["", render_ndt(f)]

    if coverage:
        lines += [
            "",
            "## Coverage & limitations",
            "",
            (
                "_SAST coverage by language. `none` = no mechanical dataflow OR pattern "
                "analysis (LLM shape-hunting only)._"
            ),
            "",
            "| Language | Files | Tier |",
            "|----------|-------|------|",
        ]
        for lang in coverage.get("languages", []):
            lines.append(f"| {lang['language']} | {lang['files']} | {lang['tier']} |")
        uncovered = ", ".join(coverage.get("uncovered", [])) or "none"
        lines += [
            "",
            (
                f"Dataflow coverage: {coverage.get('dataflow_pct', 0)}% of counted "
                f"source. Uncovered (LLM-only): {uncovered}."
            ),
        ]
    if has_redteam_plan:
        lines += [
            "",
            "## Manual runtime testing",
            "",
            ("See `redteam-plan.md` for the runtime test directives (needs-runtime findings)."),
        ]
    if coverage_ledger:
        lines += ["", render_coverage_ledger(coverage_ledger)]
    if economics:
        lines += ["", "## Run economics", ""]
        lines += ["**Tokens by phase** (measured):"]
        lines += [f"- **{phase}**: {n}" for phase, n in economics.get("by_phase", {}).items()]
        lines += ["", "**Tokens by model** (measured):"]
        lines += [f"- **{model}**: {n}" for model, n in economics.get("by_model", {}).items()]
        by_secs = economics.get("by_phase_seconds") or {}
        if by_secs:
            lines += ["", "**Wall-clock by phase, seconds** (measured):"]
            lines += [f"- **{phase}**: {secs:.2f}" for phase, secs in by_secs.items()]
        usd = economics.get("usd_estimate")
        if usd is not None:
            lines += ["", f"**Estimated cost:** ${usd:.4f} (estimate, not a billed figure)."]
    elif token_spend:
        lines += ["", "## Token spend by phase", ""]
        lines += [f"- **{phase}**: {n}" for phase, n in token_spend.items()]
    return "\n".join(lines) + "\n"


def write_finding_details(
    ws: Workspace, findings: list[Finding], patch_statuses: dict | None = None
) -> list[str]:
    """Write one Markdown detail file per finding to ``ws.findings_dir/<ID>.md``.

    Args:
        ws: Workspace whose ``findings_dir`` receives the ``<ID>.md`` files.
        findings: Confirmed/fixed/NDT findings to render in full.
        patch_statuses: Optional ``id -> PatchStatus`` for fixed findings.

    Returns:
        The finding ids written, in input order.
    """
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for f in findings:
        if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING:
            body = render_ndt(f)
        else:
            body = render_finding(f, patch_status=(patch_statuses or {}).get(f.id))
        (ws.findings_dir / f"{f.id}.md").write_text(body + "\n")
        written.append(f.id)
    return written


def collapse_clusters(findings: list[Finding]) -> list[Finding]:
    """Reduce each systemic cluster to a single representative finding.

    Un-clustered findings pass through unchanged. For each ``cluster_id`` group the
    representative is the member carrying ``affected_sites`` (the elected primary);
    if that member is absent from this bucket, the highest-risk member is chosen and
    its ``affected_sites`` is synthesized from the group so the sites table is intact.

    Args:
        findings: Findings in one report bucket.

    Returns:
        One representative per cluster plus every un-clustered finding.
    """
    singletons = [f for f in findings if not f.cluster_id]
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        if f.cluster_id:
            groups.setdefault(f.cluster_id, []).append(f)
    reps: list[Finding] = list(singletons)
    for members in groups.values():
        primary = next((m for m in members if m.affected_sites), None)
        if primary is None:
            primary = min(members, key=_risk_sort_key)
            primary.affected_sites = [{"id": m.id, "file": m.file, "line": m.line} for m in members]
        reps.append(primary)
    return reps


def select_reportable(findings: list[Finding]) -> list[Finding]:
    """Select findings suitable for the final report.

    Keeps only ``CONFIRMED``/``FIXED`` findings, ordered by :func:`_risk_sort_key`
    (risk descending, then severity, then id) so the reportable order matches the
    report body's triage/confirmed ordering.

    Args:
        findings: All findings in the workspace.

    Returns:
        The reportable subset, highest-risk first.
    """
    reportable = [f for f in findings if f.status in _REPORTABLE]
    return sorted(reportable, key=_risk_sort_key)


def write_report(
    ws: Workspace,
    *,
    target: str | None = None,
    confirmed_only: bool = False,
    dropped: list | None = None,
    position_reviews: list[PositionResult] | None = None,
) -> dict:
    """Assemble the final SARIF + Markdown report from a workspace's findings.

    Overwrites ``report.sarif``, ``report.md``, and ``findings.json`` so they
    reflect the finished analysis rather than prefilter-time candidates.
    ``findings.json`` always carries confirmed/fixed findings plus
    needs-deployment-testing findings (distinguished by status). By default,
    SARIF carries the same set, with needs-deployment-testing findings marked
    with an ``inSource`` suppression so downstream tools see them without
    failing a gate; ``confirmed_only=True`` restores the prior behavior of
    emitting confirmed/fixed findings only, with no suppressions.

    Args:
        ws: Workspace to read findings from and write reports into.
        target: Path to the real target repo. When given, ``fixed`` findings are mechanically
            checked (``git apply --check``) against the real working tree so the report never
            implies a still-vulnerable finding's patch is deployed.
        confirmed_only: When true, SARIF excludes needs-deployment-testing findings
            entirely, matching the pre-suppression default output.
        dropped: Review-mode findings the position gate placed outside the diff; rendered
            into the markdown report and into ``artifacts/review_ledger.json`` from this one
            argument, so the two outputs cannot disagree (D-14, POS-03).
        position_reviews: Review-mode declines (``needs-position-review``); rendered and
            ledgered the same way as ``dropped``.

    Returns:
        ``{"reported": <count>, "sarif": <path>, "report": <path>}``.
    """
    dropped = dropped or []
    position_reviews = position_reviews or []
    all_findings = read_findings(ws)
    reportable = select_reportable(all_findings)
    ndt = [f for f in all_findings if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING]
    reportable = collapse_clusters(reportable)
    ndt = collapse_clusters(ndt)
    coverage_path = ws.kb / "coverage.json"
    coverage = json.loads(coverage_path.read_text()) if coverage_path.exists() else None
    cl_path = ws.kb / "coverage-ledger.json"
    if not cl_path.exists():
        from sec_overlay.coverage_ledger import build_coverage_ledger  # local: avoid cycle

        build_coverage_ledger(ws)
    coverage_ledger = json.loads(cl_path.read_text()) if cl_path.exists() else None
    has_redteam_plan = (ws.reports / "redteam-plan.md").exists()
    state = load_state(ws)
    by_phase = cost.aggregate_by_phase(state)
    by_phase_seconds = cost.aggregate_timings_by_phase(state)
    economics = (
        {
            "by_phase": by_phase,
            "by_model": cost.aggregate_by_model(state),
            "by_phase_seconds": by_phase_seconds,
            "usd_estimate": cost.estimate_cost_usd(state),
        }
        if by_phase or by_phase_seconds
        else None
    )
    patch_statuses = None
    if target:
        patch_statuses = {
            f.id: check_patch_applied(target, f.patch_diff)
            for f in reportable
            if f.status is FindingStatus.FIXED and f.patch_diff
        }
    if confirmed_only:
        sarif_findings, suppressed = reportable, None
    else:
        sarif_findings, suppressed = reportable + ndt, ndt
    ws.sarif_path.write_text(json.dumps(to_sarif(sarif_findings, suppressed=suppressed), indent=2))
    ws.report_path.write_text(
        to_markdown(
            reportable,
            needs_deployment=ndt,
            coverage=coverage,
            coverage_ledger=coverage_ledger,
            has_redteam_plan=has_redteam_plan,
            patch_statuses=patch_statuses,
            economics=economics,
            dropped=dropped,
            position_reviews=position_reviews,
        )
    )
    write_finding_details(ws, reportable + ndt, patch_statuses=patch_statuses)
    findings_out = reportable + ndt
    ws.findings_json_path.write_text(json.dumps([f.to_dict() for f in findings_out], indent=2))
    write_review_ledger(ws, position_reviews=position_reviews, dropped=dropped)
    record_stage(ws, "report")
    return {"reported": len(reportable), "sarif": str(ws.sarif_path), "report": str(ws.report_path)}


DROPPED_FINDINGS_HEADING = "## Dropped findings"


def render_dropped_findings_section(dropped: list) -> str:
    """Render every review-mode drop as a dedicated markdown section (D-14, POS-03).

    Args:
        dropped: ``phase_gate.DroppedFinding``s the review-mode gate placed outside every
            diff hunk. Rendered in the order given — the gate owns the sort order, so this
            function never re-sorts; the report and the ledger must not disagree.

    Returns:
        A markdown string starting with ``DROPPED_FINDINGS_HEADING``.
    """
    if not dropped:
        return f"{DROPPED_FINDINGS_HEADING}\n\nNo finding was dropped.\n"
    lines = [
        DROPPED_FINDINGS_HEADING,
        "",
        "| Path | Line | Rule | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for d in dropped:
        lines.append(f"| {d.path} | {d.line} | {d.rule_id} | {d.reason} |")
    lines.append("")
    return "\n".join(lines)


POSITION_REVIEW_HEADING = "## Position review required"


def _escape_snippet_cell(snippet: str | None) -> str:
    """Make a snippet safe for one markdown table cell.

    Args:
        snippet: The claimed snippet, or ``None``.

    Returns:
        The snippet with pipe characters escaped and newlines collapsed to spaces, so the
        cell cannot restructure the table and hide a neighbouring row.
    """
    text = snippet or ""
    return text.replace("\r\n", " ").replace("\n", " ").replace("|", "\\|")


def render_position_review_section(results: list[PositionResult]) -> str:
    """Render every declined finding as a dedicated markdown section (D-13, POS-02).

    Args:
        results: `PositionResult`s that need human review (typically every
            `needs-position-review` decision from a run). Declines are otherwise easy to
            miss, so this section — and its explicit none-required line when empty — makes
            them impossible to omit from the report.

    Returns:
        A markdown string starting with `POSITION_REVIEW_HEADING`.
    """
    if not results:
        return f"{POSITION_REVIEW_HEADING}\n\nNo finding required position review.\n"
    lines = [
        POSITION_REVIEW_HEADING,
        "",
        "| Claimed path | Claimed line | Snippet | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for r in results:
        snippet_cell = _escape_snippet_cell(r.snippet)
        lines.append(f"| {r.claimed_path} | {r.claimed_line} | {snippet_cell} | {r.reason} |")
    lines.append("")
    return "\n".join(lines)


def write_review_ledger(ws: Workspace, *, position_reviews: list[PositionResult], dropped: list) -> Path:
    """Write the machine-readable record of every position decline (D-13, POS-02).

    A separate artifact rather than a `findings.json` state, because `models.py` is the
    frozen milestone contract, its `FindingStatus` enum has no review-position member, and
    adding one would break the Go port's byte mirror — do not "simplify" this back into
    `findings.json`.

    Args:
        ws: Workspace to write `artifacts/review_ledger.json` into.
        position_reviews: `PositionResult`s needing review; each becomes a `position_reviews`
            entry carrying `state` `needs-position-review`.
        dropped: Findings the review-mode gate dropped; plan 02-05 supplies its content.
            Dataclass instances are converted to dicts; plain dicts pass through unchanged.

    Returns:
        The path written.
    """
    ledger = {
        "position_reviews": [
            {
                "state": "needs-position-review",
                "claimed_path": r.claimed_path,
                "claimed_line": r.claimed_line,
                "snippet": r.snippet,
                "reason": r.reason,
            }
            for r in position_reviews
        ],
        "dropped": [asdict(d) if is_dataclass(d) else d for d in dropped],
    }
    path = ws.artifacts / "review_ledger.json"
    _atomic_write(path, json.dumps(ledger, indent=2))
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI: assemble the final report for a workspace.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-report")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--findings-dir", default=None)
    parser.add_argument("--kb-dir", default=None)
    parser.add_argument("--paths-config", default=None)
    parser.add_argument("--target", default=None)
    parser.add_argument("--confirmed-only", action="store_true")
    args = parser.parse_args(argv)
    ws = load_paths(
        workspace=args.workspace,
        paths_config=args.paths_config,
        reports_dir=args.reports_dir,
        findings_dir=args.findings_dir,
        kb_dir=args.kb_dir,
    )
    result = write_report(ws, target=args.target, confirmed_only=args.confirmed_only)
    print(f"reported {result['reported']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
