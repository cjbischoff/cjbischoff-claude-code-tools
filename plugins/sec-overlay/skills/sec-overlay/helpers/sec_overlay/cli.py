"""CLI entry point orchestrating the deterministic scan pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

from sec_overlay.bundle import group_bundles
from sec_overlay.campaign import record_stage
from sec_overlay.diffhunks import parse_hunks
from sec_overlay.diffscope import (
    binary_paths,
    changed_file_records,
    file_diff_line_count,
    file_diff_text,
    file_text_at_ref,
    resolve_ref_sha,
)
from sec_overlay.file_select import partition
from sec_overlay.models import Finding
from sec_overlay.normalize import normalize
from sec_overlay.phase_gate import review_position_gate
from sec_overlay.reflection import SKIPPED_REASON, ReflectionSkip, apply_verdict
from sec_overlay.repo_memory import RepoMemory, repo_slug
from sec_overlay.report import to_markdown, write_report
from sec_overlay.review_agent import (
    SOURCE_SKIPPED_REASON,
    ReviewPlanEntry,
    ReviewSourceSkip,
    agent_label,
    recorded_return_source,
    render_review_prompt,
    write_review_plan,
)
from sec_overlay.review_comments import comment_from_finding, write_review_comments
from sec_overlay.review_coverage import (
    MANIFEST_FILENAME,
    CoverageManifest,
    ResumeIdentityError,
    check_resume_identity,
)
from sec_overlay.review_findings import GatedFinding, apply_profile, classify
from sec_overlay.rule_glob import RuleSafetyError, build_resolution, glob_match, resolve_rule_doc
from sec_overlay.sarif import to_sarif
from sec_overlay.sast import run_semgrep
from sec_overlay.scanscope import resolve as _resolve_scope
from sec_overlay.scanscope import write_scope
from sec_overlay.workspace import Workspace, _atomic_write, load_paths, write_findings

# SCALE-02: ceilings and defaults for the review subcommand's three bound flags.
# Two separate ceilings (not one shared value) because a worker-count ceiling
# sized for --concurrency/--max-git-procs would reject --timeout's own,
# much larger, order of magnitude (seconds, not workers).
MAX_WORKERS = 128
MAX_TIMEOUT_SECONDS = 3600
DEFAULT_CONCURRENCY = 8
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_MAX_GIT_PROCS = 16
TIMEOUT_NOTE = "review unit exceeded --timeout"


def _bounded_int(value: int, *, flag: str, ceiling: int) -> int:
    """Reject a bound value outside ``[1, ceiling]``; never clamp it.

    Args:
        value: The operator-supplied bound (already an ``int`` via argparse).
        flag: The flag's CLI spelling (e.g. ``"--concurrency"``), named in the
            error so a rejection is actionable.
        ceiling: The largest value this flag accepts.

    Returns:
        ``value`` unchanged, when it is within range.

    Raises:
        ValueError: If ``value`` is below 1 or above ``ceiling``. Silently
            clamping would misreport what the run actually did (ASVS V5).
    """
    if value < 1 or value > ceiling:
        raise ValueError(f"{flag} must be between 1 and {ceiling} (got {value})")
    return value


def _bounded_map(items, workers: int, fn):
    """Apply ``fn`` to every item, order-preserved, via a pool sized to fit ``items``.

    ``.map()`` yields results in submission order regardless of which worker
    finishes first, so callers can consume this list positionally and get
    file-order results, not completion-order results (SCALE-02). Never builds
    a pool for an empty ``items`` — nothing to dispatch.

    Args:
        items: The sequence to map ``fn`` over.
        workers: The operator's ``--max-git-procs`` bound; only ever narrowed
            down to ``len(items)``, never widened past it.
        fn: A one-argument callable applied to each item.

    Returns:
        A list of ``fn(item)`` results, one per item, in ``items`` order.
    """
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as ex:
        return list(ex.map(fn, items))


def _fetch_file_review_inputs(path: str, base: str, head: str, runner):
    """Fetch one file's diff text, parsed hunks, and head-ref text on a worker thread.

    Catches its own exception so one file's failure never cancels a sibling's
    fetch; the caller applies the coverage-manifest transition on the
    consuming thread, in file order, not fetch-completion order (SCALE-02).

    Args:
        path: Repo-relative file path.
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        A ``(diff_text, hunks, file_text)`` tuple on success, or the caught
        exception on failure — never re-raised here.
    """
    try:
        diff_text = file_diff_text(path, base, head, runner=runner)
        hunks = parse_hunks(diff_text)
        file_text = file_text_at_ref(path, head, runner=runner)
        return diff_text, hunks, file_text
    except Exception as exc:  # noqa: BLE001 - reported to the caller, not raised here
        return exc


def _fetch_review_unit_files(paths, base, head, runner):
    """Fetch every member file of one ``ReviewUnit``, one exception per file.

    Each member's own fetch failure is caught individually (delegated to
    :func:`_fetch_file_review_inputs`) so a normal per-file error only fails
    that file, not its unit-mates. Only the caller's ``future.result(timeout=
    ...)`` — timing out this whole call — fails every member together
    (SCALE-02).

    Args:
        paths: The unit's member file paths.
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        A dict mapping each path to its ``(diff_text, hunks, file_text)``
        tuple on success, or the caught exception on failure.
    """
    return {path: _fetch_file_review_inputs(path, base, head, runner) for path in paths}


def write_scan_scope(ws, target, *, sha: str = "", runner=None):
    """Resolve + persist the canonical ScanScope for a scan (called at pass start).

    Args:
        ws: Campaign workspace.
        target: The scan target path.
        sha: Pinned git SHA for the pass.
        runner: Injectable subprocess runner (tests); defaults to subprocess.run.

    Returns:
        The persisted :class:`sec_overlay.scanscope.ScanScope`.
    """
    import subprocess

    _raw = runner or subprocess.run

    def r(cmd, **kwargs):
        # ponytail: adapt list→str so test fakes using `"show-toplevel" in cmd`
        # (substring check) work correctly; subprocess.run accepts both forms.
        return _raw(" ".join(cmd) if (runner and isinstance(cmd, list)) else cmd, **kwargs)

    scope = _resolve_scope(target, sha=sha, runner=r)
    scope.slug = repo_slug(target, runner=r)
    write_scope(ws, scope)
    return scope


def run_scan(target: str, ws: Workspace, config: str, *, sha: str | None = None) -> list[Finding]:
    """Run the deterministic scan pipeline and write outputs.

    Steps: run semgrep -> normalize -> stamp discovery SHA -> persist findings ->
    emit SARIF + Markdown + findings.json -> record the prefilter stage. Pass
    lifecycle (``begin_pass``) is owned by the campaign supervisor, not this
    function, so a prefilter run never advances the pass counter.

    Args:
        target: Path to the codebase to scan.
        ws: Workspace to hold the KB and reports.
        config: Path to the semgrep rules file.
        sha: Git SHA to stamp onto each finding's ``discovery_sha``.

    Returns:
        The normalized findings.
    """
    ws.ensure()

    findings = normalize(run_semgrep(target, config))
    for f in findings:
        f.discovery_sha = sha
    write_findings(ws, findings)

    ws.sarif_path.write_text(json.dumps(to_sarif(findings), indent=2))
    ws.report_path.write_text(to_markdown(findings))
    ws.findings_json_path.write_text(json.dumps([f.to_dict() for f in findings], indent=2))
    record_stage(ws, "prefilter")
    return findings


def run_review(
    base: str,
    head: str,
    root: str,
    *,
    profile: str = "security",
    rule_path: str | None = None,
    excludes: list[str] | None = None,
    runner=None,
    review_source=None,
    prepare: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_git_procs: int = DEFAULT_MAX_GIT_PROCS,
    model: str | None = None,
) -> int:
    """Run one review pass end to end: resolve refs, select files, position, seal.

    Batches over every reviewable changed file and implements exit codes 2 and 3.
    Live findings come from ``review_source`` — called once per file with its path
    — then traverse the position gate and :func:`review_findings.apply_profile`.
    ``apply_profile``'s kept output then feeds :func:`reflection.apply_verdict`,
    called once per reviewable file with only that file's kept findings; the
    findings surviving every file's verdict are what ``review_findings`` reports.
    The gate's dropped/declined output is always written to ``report.md`` and
    ``artifacts/review_ledger.json`` via :func:`report.write_report` — including the
    zero-drop/zero-decline case — so "no finding was dropped" is recorded, not just
    absent (T-02-15).

    With ``prepare=True``, refs are resolved and files selected as usual, then each
    reviewable file's rule doc and diff are rendered into a `review-file` prompt
    under ``runs/review_prompts/`` and listed in ``runs/review_plan.json`` (path,
    prompt path, agent label, base/head refs). No gate runs; this is the
    deterministic half of the step, SKILL.md owns dispatching the agent half.

    Each reviewable file's rule doc is resolved via :func:`rule_glob.resolve_rule_doc`
    and its post-gate findings run through :func:`reflection.apply_verdict`; a
    per-file reflection failure is recorded as a :class:`reflection.ReflectionSkip`
    and the run fails open rather than aborting (D-15).

    Args:
        base: Base ref. Validated and resolved to a SHA before any other git call.
        head: Head ref, same treatment.
        root: Target repo under review; the workspace and its ``artifacts/`` dir live in
            the per-repo sidecar resolved beneath it (``<root>/.sec-overlay/<slug>/``),
            not at ``root`` itself.
        profile: Review profile (``"security"`` or ``"general"``); gates the position
            gate's kept findings through :func:`review_findings.apply_profile` (REV-01).
        rule_path: Path to a custom rule.json (``--rule``); resolved as the highest-priority
            layer via :func:`rule_glob.build_resolution`. ``None`` skips the custom layer.
        excludes: Raw ``--exclude`` glob values, appended (lower-cased) to whichever layer's
            file filter wins, or used alone when no layer defines one.
        runner: Injectable subprocess runner (tests); defaults to ``subprocess.run``.
        review_source: Callable taking one file path and returning that file's
            findings; defaults to :func:`review_agent.recorded_return_source` reading
            recorded returns from ``ws``. Injecting a source keeps the gate chain
            testable without a model call, and keeps this module free of dispatch
            (D-13).
        prepare: When true, write the prompt/plan files described above and return
            before any gate runs.
        concurrency: Review-unit dispatch fan-out bound (``--concurrency``); recorded
            for the dispatching document (SKILL.md) to honor — the Python core never
            dispatches an agent, so this value is validated here but read nowhere else
            in this module (T-04-09).
        timeout: Per-unit deadline in seconds (``--timeout``), used unrounded as the
            worker-future timeout for that unit's git fetch work (SCALE-02).
        max_git_procs: Bound on concurrent git subprocesses (``--max-git-procs``),
            sizing the worker pools around the two per-file git loops (SCALE-02).
        model: This run's model identity (SCALE-03); pinned into the coverage
            manifest on first write. Resuming a workspace whose manifest already
            recorded a different ``model`` or ``profile`` is rejected before any
            write — a resumed run must not silently switch identity mid-review.

    Returns:
        0 when the coverage manifest seals ``complete`` (including a diff with no
        reviewable files) or ``prepare=True`` completed, 2 on an invalid ``base``/
        ``head`` ref (D-06), an out-of-range bound flag, a ``RuleSafetyError``
        from the RULE-03 rule-file safety gate (no fallback to another layer), or
        a ``ResumeIdentityError`` (SCALE-03), 3 when the seal is ``partial``
        (D-15) — one or more files could not be reviewed, including every member
        of a unit that timed out. A skipped review source never turns a complete
        pass into a partial one — a source skip is a reviewer failure, not a
        coverage failure.
    """
    try:
        _bounded_int(concurrency, flag="--concurrency", ceiling=MAX_WORKERS)
        _bounded_int(timeout, flag="--timeout", ceiling=MAX_TIMEOUT_SECONDS)
        _bounded_int(max_git_procs, flag="--max-git-procs", ceiling=MAX_WORKERS)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    import subprocess

    r = runner or subprocess.run

    memory = RepoMemory.for_target(root, runner=r)
    memory.ensure(target=root)
    ws = memory.workspace

    manifest_path = ws.artifacts / MANIFEST_FILENAME
    if manifest_path.exists():
        prior_manifest = CoverageManifest.load(manifest_path)
        try:
            check_resume_identity(prior_manifest, model=model, profile=profile)
        except ResumeIdentityError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    try:
        base_sha = resolve_ref_sha(base, runner=r)
        head_sha = resolve_ref_sha(head, runner=r)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        resolution = build_resolution(rule_path, excludes or [], Path(root))
    except RuleSafetyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    records = changed_file_records(base_sha, head_sha, runner=r)
    line_counts = _bounded_map(
        records,
        max_git_procs,
        lambda record: file_diff_line_count(record.path, base_sha, head_sha, runner=r),
    )
    diff_line_counts = dict(zip((record.path for record in records), line_counts))
    excluded_binary = binary_paths(base_sha, head_sha, runner=r)
    selection = partition(records, diff_line_counts=diff_line_counts, binary_paths=excluded_binary)

    file_filter = resolution.file_filter
    if file_filter is not None:
        kept = [
            record
            for record in selection.reviewable
            if (
                not file_filter.include
                or any(glob_match(p, record.path) for p in file_filter.include)
            )
            and not any(glob_match(p, record.path) for p in file_filter.exclude)
        ]
        selection = replace(selection, reviewable=kept)

    # SCALE-01: group reviewable files into units so an impl/test pair or a
    # locale/config family shares one review pass's membership, and one slow
    # member's --timeout fails its bundle-mates together, not just itself
    # (SCALE-02).
    units = group_bundles(selection.reviewable)
    bundle_paths_by_path: dict[str, frozenset[str]] = {}
    for unit in units:
        members = frozenset(unit.files)
        for member_path in unit.files:
            bundle_paths_by_path[member_path] = members

    if review_source is None:
        review_source = recorded_return_source(
            ws, base=base_sha, head=head_sha, bundle_paths_by_path=bundle_paths_by_path
        )

    manifest = CoverageManifest(base_sha, head_sha, manifest_path, model=model, profile=profile)
    hunks_by_path: dict[str, list] = {}
    diff_text_by_path: dict[str, str] = {}
    file_text_by_path: dict[str, str] = {}
    rule_docs: list[dict] = []
    fetch_by_path = {}
    if units:
        with ThreadPoolExecutor(max_workers=min(max_git_procs, len(units))) as ex:
            futures = [
                ex.submit(_fetch_review_unit_files, unit.files, base_sha, head_sha, r)
                for unit in units
            ]
            for unit, future in zip(units, futures):
                try:
                    fetch_by_path.update(future.result(timeout=timeout))
                except TimeoutError:
                    # The whole unit missed --timeout — every member fails
                    # together, not just whichever file was slow (SCALE-02).
                    fetch_by_path.update(
                        {path: TimeoutError(TIMEOUT_NOTE) for path in unit.files}
                    )
    for record in selection.reviewable:
        fetched = fetch_by_path[record.path]
        manifest.add(record.path)
        manifest.start(record.path)
        if isinstance(fetched, Exception):
            # Any per-file fetch failure becomes a coverage gap, not a crash.
            manifest.fail(record.path, note=str(fetched))
            continue
        diff_text, hunks, file_text = fetched
        diff_text_by_path[record.path] = diff_text
        hunks_by_path[record.path] = hunks
        file_text_by_path[record.path] = file_text
        manifest.finish(record.path)
        try:
            rule_text = resolve_rule_doc(record.path, resolution)
        except RuleSafetyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        rule_docs.append({"path": record.path, "text": rule_text})

    if prepare:
        rule_text_by_path = {d["path"]: d["text"] for d in rule_docs}
        overlay_root = str(Path(__file__).resolve().parents[2])
        prompts_dir = ws.runs / "review_prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        entries: list[ReviewPlanEntry] = []
        for record in selection.reviewable:
            if record.path not in hunks_by_path:
                continue
            label = agent_label(record.path)
            prompt = render_review_prompt(
                record.path,
                rule_text_by_path[record.path],
                diff_text_by_path[record.path],
                [r.path for r in selection.reviewable if r.path != record.path],
                repo_root=root,
                overlay_root=overlay_root,
            )
            prompt_path = prompts_dir / f"{label}.md"
            _atomic_write(prompt_path, prompt)
            entries.append(
                ReviewPlanEntry(
                    path=record.path,
                    prompt_path=str(prompt_path),
                    agent_label=label,
                    base=base_sha,
                    head=head_sha,
                )
            )
        write_review_plan(ws, entries)
        return 0

    live_findings: list[Finding] = []
    review_source_skips: list[ReviewSourceSkip] = []
    for record in selection.reviewable:
        if record.path not in hunks_by_path:
            continue
        try:
            live_findings.extend(review_source(record.path))
        except Exception as exc:  # noqa: BLE001 - a source failure is a reviewer skip, not a crash
            review_source_skips.append(
                ReviewSourceSkip(record.path, SOURCE_SKIPPED_REASON, str(exc))
            )

    # The agent's `code_comment` claims a path/line only, never a snippet (D-13's
    # tool-receipt discipline: never trust an LLM's claim of code content). The harness
    # derives each finding's position-gate snippet itself, from the real file text at its
    # claimed line — the gate then independently confirms that real line against the diff.
    for finding in live_findings:
        lines = file_text_by_path.get(finding.file, "").splitlines()
        if 1 <= finding.line <= len(lines):
            finding.evidence = lines[finding.line - 1]

    _kept, dropped, declines = review_position_gate(live_findings, hunks_by_path, file_text_by_path)

    try:
        review_findings, profile_dropped = apply_profile(
            [GatedFinding(finding=f, gate="B" if classify(f) is not None else None) for f in _kept],
            profile,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    dropped = [*dropped, *profile_dropped]

    reflection_retractions: list = []
    reflection_skips: list[ReflectionSkip] = []
    retracted_ids: set[str] = set()
    for record in selection.reviewable:
        kept_for_file = [rf.finding for rf in review_findings if rf.finding.file == record.path]
        try:
            surviving, retractions = apply_verdict(kept_for_file, {}, path=record.path)
            reflection_retractions.extend(retractions)
            surviving_ids = {f.id for f in surviving}
            retracted_ids.update(f.id for f in kept_for_file if f.id not in surviving_ids)
        except Exception as exc:  # noqa: BLE001 - reflection fails open, never aborts the run
            reflection_skips.append(ReflectionSkip(record.path, SKIPPED_REASON, str(exc)))

    review_findings = [rf for rf in review_findings if rf.finding.id not in retracted_ids]

    write_report(
        ws,
        dropped=dropped,
        position_reviews=declines,
        rule_docs=rule_docs,
        reflection_retractions=reflection_retractions,
        reflection_skips=reflection_skips,
        review_findings=review_findings,
        review_source_skips=review_source_skips,
    )

    comments = [comment_from_finding(rf.finding) for rf in review_findings]
    write_review_comments(ws, comments, manifest.to_dict())

    if not selection.reviewable:
        return 0

    if manifest.seal() == "complete":
        return 0

    for entry in manifest.entries():
        if entry.state != "done":
            print(f"unfinished file: {entry.path} (state={entry.state}, note={entry.note})")
    return 3


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv``).

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay")
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan", help="Run the deterministic scan pipeline.")
    scan.add_argument("--target", required=True)
    scan.add_argument(
        "--workspace",
        default=None,
        help="Override the workspace; default is the in-repo per-repo "
        "memory folder (<target>/.sec-overlay/<slug>/, or "
        "$SEC_OVERLAY_HOME/<slug>/ if set).",
    )
    scan.add_argument("--config", required=True)
    scan.add_argument("--sha", default=None)
    scan.add_argument("--reports-dir", default=None)
    scan.add_argument("--findings-dir", default=None)
    scan.add_argument("--kb-dir", default=None)
    scan.add_argument("--paths-config", default=None)

    mem = sub.add_parser("memory", help="Show/append the per-repo scan memory.")
    mem.add_argument("--target", required=True)
    mem.add_argument("--learn", default=None, help="Append a dated learning.")
    mem.add_argument("--tag", default="", help="Optional tag for the learning.")

    audit = sub.add_parser("audit", help="run the deterministic audit driver")
    audit.add_argument("--target", required=True)
    audit.add_argument("--workspace")
    audit.add_argument("--config", required=True)
    audit.add_argument("--sha")

    review = sub.add_parser("review", help="Run a diff-scoped review pass (tracer path).")
    review.add_argument("--base", required=True)
    review.add_argument("--head", default="HEAD")
    review.add_argument("--root", default=".")
    review.add_argument("--profile", choices=["security", "general"], default="security")
    review.add_argument("--rule", default=None, help="Path to a custom rule.json layer.")
    review.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude (repeatable); appends to the resolved layer's excludes.",
    )
    review.add_argument(
        "--prepare",
        action="store_true",
        help="Write review prompts and review_plan.json; skip the gate chain.",
    )
    review.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Review-unit dispatch fan-out bound, 1-128 (default 8). Enforced by "
        "SKILL.md's dispatch loop, not by this process.",
    )
    review.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-unit deadline in seconds, 1-3600 (default 600).",
    )
    review.add_argument(
        "--max-git-procs",
        type=int,
        default=DEFAULT_MAX_GIT_PROCS,
        help="Bound on concurrent git subprocesses, 1-128 (default 16).",
    )
    args = parser.parse_args(argv)

    if args.cmd == "scan":
        memory = None
        if args.workspace:
            ws = load_paths(
                workspace=args.workspace,
                paths_config=args.paths_config,
                reports_dir=args.reports_dir,
                findings_dir=args.findings_dir,
                kb_dir=args.kb_dir,
            )
        else:
            memory = RepoMemory.for_target(args.target)
            memory.ensure(target=args.target)
            ws = memory.workspace
        write_scan_scope(ws, args.target, sha=args.sha or "")
        findings = run_scan(args.target, ws, args.config, sha=args.sha)
        if memory is not None:
            memory.update_status()
        print(f"{len(findings)} findings; reports in {ws.reports}")
        return 0

    if args.cmd == "memory":
        memory = RepoMemory.for_target(args.target)
        memory.ensure(target=args.target)
        if args.learn:
            path = memory.record_learning(args.learn, tag=args.tag)
            print(f"learning recorded: {path}")
            return 0
        st = memory.run_status()
        state = (
            "FINISHED"
            if st["finished"]
            else (f"RESUME at {st['next_phase']}" if st["resumable"] else "not started")
        )
        print(f"memory: {memory.root}")
        print(f"status: {state} (pass {st['pass_number']} @ {st['active_sha']})")
        print(f"stages done: {', '.join(st['stages_done']) or '(none)'}")
        return 0

    if args.cmd == "audit":
        from sec_overlay.driver import AuditContext, run_audit

        if args.workspace:
            ws = load_paths(workspace=args.workspace)
        else:
            memory = RepoMemory.for_target(args.target)
            memory.ensure(target=args.target)
            ws = memory.workspace
        sha = args.sha or ""
        # Pass lifecycle (begin_pass) is owned by the campaign supervisor, called
        # once before the first `audit` invocation — not here, since `audit` is
        # re-invoked repeatedly across a pass and must not wipe recorded stages.
        ctx = AuditContext(ws=ws, target=args.target, config=args.config, sha=sha)
        print(run_audit(ctx))
        return 0

    if args.cmd == "review":
        return run_review(
            args.base,
            args.head,
            args.root,
            profile=args.profile,
            rule_path=args.rule,
            excludes=args.exclude,
            prepare=args.prepare,
            concurrency=args.concurrency,
            timeout=args.timeout,
            max_git_procs=args.max_git_procs,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
