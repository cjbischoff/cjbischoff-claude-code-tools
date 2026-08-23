"""CLI entry point orchestrating the deterministic scan pipeline."""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import partial
from pathlib import Path

from sec_overlay.background import load_background
from sec_overlay.bundle import group_bundles
from sec_overlay.campaign import record_stage
from sec_overlay.diffhunks import parse_hunks
from sec_overlay.diffscope import (
    binary_paths,
    changed_file_records,
    dirty_file_records,
    file_diff_line_count,
    file_diff_text,
    file_text_at_ref,
    resolve_ref_sha,
)
from sec_overlay.file_select import ExcludedFile, partition
from sec_overlay.models import Finding
from sec_overlay.normalize import normalize
from sec_overlay.phase_gate import review_position_gate
from sec_overlay.redactor import SecretsPresent
from sec_overlay.reflection import (
    SKIPPED_REASON,
    ReflectionSkip,
    apply_verdict,
    build_payload,
    recorded_verdict_source,
    reflection_label,
    render_reflection_prompt,
)
from sec_overlay.repo_memory import RepoMemory, repo_slug
from sec_overlay.report import to_markdown, write_report
from sec_overlay.review_agent import (
    PLAN_LINE_THRESHOLD,
    SOURCE_SKIPPED_REASON,
    ReviewPlanEntry,
    ReviewSourceSkip,
    agent_label,
    plan_agent_label,
    plan_guidance_from_return,
    recorded_return_source,
    render_plan_prompt,
    render_review_prompt,
    write_review_plan,
)
from sec_overlay.review_budget import (
    BUDGET_SKIP_NOTE,
    FILE_BUDGET_FRACTION,
    BudgetGate,
    estimate_review_cost,
)
from sec_overlay.review_comments import comment_from_finding, write_review_comments
from sec_overlay.review_coverage import (
    MANIFEST_FILENAME,
    CoverageManifest,
    ResumeIdentityError,
    check_resume_identity,
)
from sec_overlay.review_findings import GatedFinding, apply_profile, classify
from sec_overlay.review_result import write_review_result
from sec_overlay.rule_glob import RuleSafetyError, build_resolution, glob_match, resolve_rule_doc
from sec_overlay.sarif import to_sarif
from sec_overlay.sast import run_semgrep
from sec_overlay.scanscope import resolve as _resolve_scope
from sec_overlay.scanscope import write_scope
from sec_overlay.workspace import (
    Workspace,
    _atomic_write,
    load_paths,
    read_agent_return,
    write_findings,
)

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


def _fetch_review_unit_files(paths, base, head, runner, timeout):
    """Fetch every member file of one ``ReviewUnit``, one exception per file.

    Each member's own fetch failure is caught individually (delegated to
    :func:`_fetch_file_review_inputs`) so a normal per-file error only fails
    that file, not its unit-mates. Only the caller's ``future.result(timeout=
    ...)`` — timing out this whole call — fails every member together
    (SCALE-02).

    The deadline is computed here, at this call's own entry, not when the
    unit was submitted to the pool — a queued unit's wait in the pool would
    otherwise silently consume its own budget. Once past the deadline, this
    worker stops fetching remaining members instead of doing pointless work
    the caller has already abandoned (SCALE-02).

    Args:
        paths: The unit's member file paths.
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).
        timeout: Seconds this unit's fetch is allowed, matching the caller's
            own ``future.result(timeout=timeout)`` budget.

    Returns:
        A dict mapping each path to its ``(diff_text, hunks, file_text)``
        tuple on success, or the caught exception on failure.
    """
    deadline = time.monotonic() + timeout
    result = {}
    for path in paths:
        if time.monotonic() > deadline:
            result[path] = TimeoutError(TIMEOUT_NOTE)
            continue
        result[path] = _fetch_file_review_inputs(path, base, head, runner)
    return result


def _fetch_dirty_file_inputs(record, base: str, root: str, runner):
    """Fetch one working-tree file's review inputs for ``--workspace-dirty``.

    A tracked record (staged or unstaged) diffs ``base`` against the working tree
    (``file_diff_text(head=None)``). An untracked record (status ``"?"``) has no
    ``base`` side, so its whole current content becomes an all-added synthetic
    hunk. ``file_text`` is always the on-disk working-tree content — the review
    target is the uncommitted tree, not any committed ref.

    Args:
        record: A :class:`ChangedFile` from :func:`dirty_file_records`.
        base: HEAD SHA, the working tree's diff base.
        root: Target repo root; the working-tree file is read from here.
        runner: Injectable subprocess runner (for testing).

    Returns:
        A ``(diff_text, hunks, file_text)`` tuple on success, or the caught
        exception on failure — never re-raised here.
    """
    try:
        file_text = (Path(root) / record.path).read_text(encoding="utf-8", errors="replace")
        if record.status == "?":
            lines = file_text.splitlines()
            diff_text = f"@@ -0,0 +1,{len(lines)} @@\n" + "".join(f"+{ln}\n" for ln in lines)
        else:
            diff_text = file_diff_text(record.path, base, None, runner=runner)
        return diff_text, parse_hunks(diff_text), file_text
    except Exception as exc:  # noqa: BLE001 - reported to the caller, not raised here
        return exc


def _dirty_line_count(record, base: str, root: str, runner) -> int:
    """Return the diff-size proxy for one working-tree record (untracked = file lines)."""
    if record.status == "?":
        try:
            text = (Path(root) / record.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return 0
        return len(text.splitlines())
    return file_diff_line_count(record.path, base, None, runner=runner)


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
    base: str | None,
    head: str,
    root: str,
    *,
    commit: str | None = None,
    workspace_dirty: bool = False,
    profile: str = "security",
    rule_path: str | None = None,
    excludes: list[str] | None = None,
    runner=None,
    review_source=None,
    reflection_source=None,
    prepare: bool = False,
    prepare_reflection: bool = False,
    plan: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_git_procs: int = DEFAULT_MAX_GIT_PROCS,
    model: str | None = None,
    workspace: str | None = None,
    token_budget: int = 0,
    background: str = "",
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

    With ``prepare_reflection=True``, the pass runs the position gate and profile as
    usual, then for each file with kept findings renders a `review-filter` prompt
    under ``runs/reflection_prompts/`` and lists it in ``runs/reflection_plan.json``
    (path, agent label). No verdict is applied; SKILL.md owns dispatching the filter
    agent, whose recorded verdicts a later run consumes via ``reflection_source``.

    Args:
        base: Base ref. Validated and resolved to a SHA before any other git call.
            Ignored on a resumed run (a prior manifest already exists at
            ``root``'s workspace) in favor of that manifest's sealed
            ``base_sha`` (SCALE-03).
        head: Head ref, same treatment -- ignored on resume in favor of the
            prior manifest's sealed ``head_sha``.
        commit: A single commit ref (``--commit``); reviews that commit alone by
            diffing its parent (``<sha>^``) against it. Mutually exclusive with
            ``base`` and ``workspace_dirty`` (exit 2 if more than one is given).
        workspace_dirty: When true (``--workspace-dirty``), review the uncommitted
            working tree — staged, unstaged, and untracked files — against HEAD,
            instead of a ref pair. Mutually exclusive with ``base`` and ``commit``.
        root: Target repo under review; the workspace and its ``artifacts/`` dir live in
            the per-repo sidecar resolved beneath it (``<root>/.sec-overlay/<slug>/``),
            not at ``root`` itself. Must already exist as a directory -- a missing,
            empty, or non-directory value exits 2 before any git subprocess runs
            (WR-01), rather than surfacing as an unhandled filesystem error from the
            sidecar's own directory creation.
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
        reflection_source: Callable taking one file path and returning that file's
            recorded retract-verdict mapping; defaults to
            :func:`reflection.recorded_verdict_source` reading verdicts from ``ws``.
            A raise (missing, stale, or malformed verdict) is caught per file as a
            :class:`reflection.ReflectionSkip` — never a silent keep-all (D-15).
        prepare: When true, write the prompt/plan files described above and return
            before any gate runs.
        prepare_reflection: When true, run the gate and profile, then write the
            per-file `review-filter` prompts and ``reflection_plan.json`` described
            above and return before any verdict is applied.
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
        workspace: Explicit workspace override (``--workspace``, mirrors ``audit``'s
            flag), resolved via :func:`workspace.load_paths`. ``None`` (default)
            falls back to the existing per-repo sidecar resolved beneath ``root``
            via :func:`repo_memory.RepoMemory.for_target`. The SCALE-03 resume
            guard applies identically either way -- it checks the resolved
            workspace's manifest, not how that workspace was resolved.

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

    if not root or not Path(root).is_dir():
        print(f"error: --root must be an existing directory (got {root!r})", file=sys.stderr)
        return 2

    import subprocess

    # A bare `subprocess.run` leaves a hung git child running past --timeout;
    # binding the process-level timeout here reaches every git call the
    # review path makes, since `r` is the shared runner passed through the
    # rest of this function (SCALE-02). An injected `runner` is untouched.
    # `cwd=root` scopes every diffscope git call to the target repo instead of
    # the CLI process's own cwd, which diffscope.py never passes explicitly.
    r = runner or partial(subprocess.run, timeout=timeout, cwd=root)

    if workspace:
        ws = load_paths(workspace=workspace)
    else:
        memory = RepoMemory.for_target(root, runner=r)
        memory.ensure(target=root)
        ws = memory.workspace

    manifest_path = ws.artifacts / MANIFEST_FILENAME
    prior_manifest: CoverageManifest | None = None
    if manifest_path.exists():
        prior_manifest = CoverageManifest.load(manifest_path)
        try:
            check_resume_identity(prior_manifest, model=model, profile=profile)
        except ResumeIdentityError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    # Exactly one review scope: a base ref (the default), a single commit, or the
    # dirty working tree. A resumed run reads its scope from the sealed manifest,
    # so the flags are ignored there.
    if prior_manifest is None:
        scopes_given = sum([base is not None, commit is not None, workspace_dirty])
        if scopes_given != 1:
            print(
                "error: pass exactly one of --base, --commit, --workspace-dirty",
                file=sys.stderr,
            )
            return 2

    dirty = workspace_dirty and prior_manifest is None
    try:
        if prior_manifest is not None:
            # Resumed run: read at the SHAs the prior run sealed, not fresh
            # refs -- HEAD may have moved since (SCALE-03). Each persisted SHA
            # still round-trips through resolve_ref_sha, so a rewritten or
            # collected SHA fails loudly (T-04-12) instead of reading a
            # different tree as an empty diff.
            base_sha = resolve_ref_sha(prior_manifest.base_sha, runner=r)
            head_sha = resolve_ref_sha(prior_manifest.head_sha, runner=r)
        elif dirty:
            # The dirty tree has no head ref; HEAD is both the diff base and the
            # recorded head identity (the review target is HEAD + uncommitted).
            base_sha = head_sha = resolve_ref_sha("HEAD", runner=r)
        elif commit is not None:
            base_sha = resolve_ref_sha(f"{commit}^", runner=r)
            head_sha = resolve_ref_sha(commit, runner=r)
        else:
            assert base is not None  # mutual-exclusion check above guarantees the base scope
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

    # In dirty mode git diffs `base` against the working tree (head omitted); a
    # committed ref pair otherwise.
    head_ref = None if dirty else head_sha
    if dirty:
        records = dirty_file_records(runner=r)
        line_counts = _bounded_map(
            records,
            max_git_procs,
            lambda record: _dirty_line_count(record, base_sha, root, r),
        )
    else:
        records = changed_file_records(base_sha, head_sha, runner=r)
        line_counts = _bounded_map(
            records,
            max_git_procs,
            lambda record: file_diff_line_count(record.path, base_sha, head_ref, runner=r),
        )
    diff_line_counts = dict(zip((record.path for record in records), line_counts))
    excluded_binary = binary_paths(base_sha, head_ref, runner=r)
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
    if reflection_source is None:
        reflection_source = recorded_verdict_source(ws, base=base_sha, head=head_sha)

    manifest = CoverageManifest(base_sha, head_sha, manifest_path, model=model, profile=profile)
    hunks_by_path: dict[str, list] = {}
    diff_text_by_path: dict[str, str] = {}
    file_text_by_path: dict[str, str] = {}
    rule_docs: list[dict] = []
    fetch_by_path = {}
    if dirty:
        # The working tree has no head ref to bundle diffs against, so fetch each
        # reviewable file serially: git diff HEAD for tracked edits, a synthetic
        # all-add diff read from disk for untracked files (_fetch_dirty_file_inputs).
        # ponytail: serial fetch, no timeout bundling -- fine for working-tree file counts.
        record_by_path = {record.path: record for record in selection.reviewable}
        for unit in units:
            for member_path in unit.files:
                fetch_by_path[member_path] = _fetch_dirty_file_inputs(
                    record_by_path[member_path], base_sha, root, r
                )
    elif units:
        # Context-managed `with ThreadPoolExecutor(...) as ex:` blocks on exit
        # until every submitted worker finishes, even one already reported as
        # timed out via `future.result(timeout=...)` above -- holding
        # run_review open past --timeout (SCALE-02). `shutdown(wait=False)`
        # lets this function return without waiting for an abandoned worker;
        # the production-runner change above bounds what that worker's own
        # git child can do with the time it's abandoned in.
        ex = ThreadPoolExecutor(max_workers=min(max_git_procs, len(units)))
        try:
            futures = [
                ex.submit(_fetch_review_unit_files, unit.files, base_sha, head_sha, r, timeout)
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
        finally:
            ex.shutdown(wait=False)

    # P4a: a single file whose projected review cost exceeds the per-file
    # fraction of the whole budget is excluded before review — one oversized
    # file must not consume the budget every other file shares. Estimates need
    # the fetched diff, so this reclassification runs post-fetch. Excluded files
    # never enter the coverage manifest.
    gate = BudgetGate(token_budget)
    if token_budget > 0:
        per_file_cap = FILE_BUDGET_FRACTION * token_budget
        over_cap: list[str] = []
        for record in selection.reviewable:
            fetched = fetch_by_path[record.path]
            if isinstance(fetched, Exception):
                continue
            diff_text = fetched[0]
            if estimate_review_cost(diff_text) > per_file_cap:
                over_cap.append(record.path)
        if over_cap:
            over_cap_set = frozenset(over_cap)
            selection = replace(
                selection,
                reviewable=[r for r in selection.reviewable if r.path not in over_cap_set],
                excluded=[
                    *selection.excluded,
                    *(ExcludedFile(path=p, reason="too-large-tokens") for p in over_cap),
                ],
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
        if not gate.admit(estimate_review_cost(diff_text)):
            # Budget latched closed: this file and every later one seal as a
            # coverage gap, not a crash — the run reports "partial", not "clean".
            manifest.fail(record.path, note=BUDGET_SKIP_NOTE)
            manifest.budget_exceeded = True
            continue
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

    if prepare and plan:
        # Plan half: emit a plan prompt for each over-threshold unit for SKILL.md
        # to dispatch. A subsequent normal `--prepare` consumes the recorded
        # returns and injects their guidance (D3 shape parity).
        rule_text_by_path = {d["path"]: d["text"] for d in rule_docs}
        overlay_root = str(Path(__file__).resolve().parents[2])
        plan_dir = ws.runs / "plan_prompts"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_manifest: list[dict[str, str]] = []
        for record in selection.reviewable:
            if record.path not in hunks_by_path:
                continue
            if diff_line_counts.get(record.path, 0) < PLAN_LINE_THRESHOLD:
                continue
            label = plan_agent_label(record.path)
            prompt = render_plan_prompt(
                record.path,
                rule_text_by_path[record.path],
                diff_text_by_path[record.path],
                repo_root=root,
                overlay_root=overlay_root,
            )
            prompt_path = plan_dir / f"{label}.md"
            _atomic_write(prompt_path, prompt)
            plan_manifest.append(
                {
                    "path": record.path,
                    "prompt_path": str(prompt_path),
                    "agent_label": label,
                    "base": base_sha,
                    "head": head_sha,
                }
            )
        _atomic_write(ws.runs / "plan_manifest.json", json.dumps(plan_manifest, indent=2))
        return 0

    if prepare:
        rule_text_by_path = {d["path"]: d["text"] for d in rule_docs}
        overlay_root = str(Path(__file__).resolve().parents[2])
        prompts_dir = ws.runs / "review_prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        entries: list[ReviewPlanEntry] = []
        plan_skips: list[dict[str, str]] = []
        for record in selection.reviewable:
            if record.path not in hunks_by_path:
                continue
            label = agent_label(record.path)
            # Over-threshold units may carry recorded plan guidance from a prior
            # `--prepare --plan` step. A missing or invalid return fails open:
            # the review prompt renders without guidance and the skip is ledgered
            # (D-15) — a plan failure is never a coverage failure.
            plan_guidance = ""
            if diff_line_counts.get(record.path, 0) >= PLAN_LINE_THRESHOLD:
                raw = read_agent_return(ws, plan_agent_label(record.path))
                if raw is None:
                    plan_skips.append({"path": record.path, "error": "no recorded plan return"})
                else:
                    try:
                        plan_guidance = plan_guidance_from_return(raw)
                    except ValueError as exc:
                        plan_skips.append({"path": record.path, "error": str(exc)})
            unit_mate_diffs = {
                mate: diff_text_by_path[mate]
                for mate in bundle_paths_by_path.get(record.path, frozenset())
                if mate != record.path and mate in diff_text_by_path
            }
            prompt = render_review_prompt(
                record.path,
                rule_text_by_path[record.path],
                diff_text_by_path[record.path],
                [r.path for r in selection.reviewable if r.path != record.path],
                sibling_diffs=unit_mate_diffs,
                repo_root=root,
                overlay_root=overlay_root,
                plan_guidance=plan_guidance,
                background=background,
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
                    token_estimate=estimate_review_cost(diff_text_by_path[record.path]),
                )
            )
        if plan_skips:
            _atomic_write(ws.runs / "plan_skips.json", json.dumps(plan_skips, indent=2))
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

    if prepare_reflection:
        prompts_dir = ws.runs / "reflection_prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        plan: list[dict[str, str]] = []
        for record in selection.reviewable:
            kept_for_file = [
                rf.finding for rf in review_findings if rf.finding.file == record.path
            ]
            if not kept_for_file:
                continue
            label = reflection_label(record.path)
            prompt = render_reflection_prompt(
                record.path,
                diff_text_by_path.get(record.path, ""),
                build_payload(record.path, kept_for_file, file_text_by_path),
            )
            _atomic_write(prompts_dir / f"{label}.md", prompt)
            plan.append({"path": record.path, "agent_label": label})
        _atomic_write(ws.runs / "reflection_plan.json", json.dumps(plan, indent=2))
        return 0

    reflection_retractions: list = []
    reflection_skips: list[ReflectionSkip] = []
    retracted_ids: set[str] = set()
    for record in selection.reviewable:
        kept_for_file = [rf.finding for rf in review_findings if rf.finding.file == record.path]
        if not kept_for_file:
            continue
        try:
            surviving, retractions = apply_verdict(
                kept_for_file, reflection_source(record.path), path=record.path
            )
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

    def _emit_review_result() -> None:
        write_review_result(
            ws,
            findings=review_findings,
            dropped=dropped,
            declines=declines,
            retractions=reflection_retractions,
            skips=reflection_skips,
            manifest=manifest,
            budget_exceeded=manifest.budget_exceeded,
            tokens={},
            base=base_sha,
            head=head_sha,
            model=model,
            profile=profile,
            tier=None,
        )

    comments = [comment_from_finding(rf.finding) for rf in review_findings]

    if not selection.reviewable:
        write_review_comments(ws, comments, manifest.to_dict())
        _emit_review_result()
        return 0

    seal = manifest.seal()
    write_review_comments(ws, comments, manifest.to_dict())
    _emit_review_result()

    if seal == "complete":
        return 0

    non_done = [e for e in manifest.entries() if e.state != "done"]
    if manifest.budget_exceeded and all(e.note == BUDGET_SKIP_NOTE for e in non_done):
        for entry in non_done:
            print(f"budget-skipped file: {entry.path}")
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

    sessions_p = sub.add_parser("sessions", help="List/show read-only sidecar session state.")
    sessions_sub = sessions_p.add_subparsers(dest="sessions_cmd", required=True)
    sessions_list = sessions_sub.add_parser("list", help="One row per sidecar session.")
    sessions_list.add_argument("--target", required=True)
    sessions_show = sessions_sub.add_parser("show", help="Detail for one session.")
    sessions_show.add_argument("session", help="A slug, or 'latest'.")
    sessions_show.add_argument("--target", required=True)
    sessions_show.add_argument("--severity", default=None, help="Filter findings by severity.")

    audit = sub.add_parser("audit", help="run the deterministic audit driver")
    audit.add_argument("--target", required=True)
    audit.add_argument("--workspace")
    audit.add_argument("--config", required=True)
    audit.add_argument("--sha")

    review = sub.add_parser("review", help="Run a diff-scoped review pass (tracer path).")
    review.add_argument("--base", default=None, help="Base ref; diff base..head. One scope only.")
    review.add_argument(
        "--commit", default=None, help="Review one commit alone (its parent..commit diff)."
    )
    review.add_argument(
        "--workspace-dirty",
        action="store_true",
        help="Review uncommitted changes (staged, unstaged, untracked) against HEAD.",
    )
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
        "--prepare-reflection",
        action="store_true",
        help="Write review-filter prompts and reflection_plan.json from post-profile "
        "kept findings; skip the reflection verdict apply.",
    )
    review.add_argument(
        "--plan",
        action="store_true",
        help="With --prepare: write plan prompts for units at or over the diff-line "
        "threshold; skip review-prompt rendering. Recorded plan returns are injected "
        "on the next --prepare run.",
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
    review.add_argument(
        "--model",
        default=None,
        help="Opaque model identity string recorded on the coverage manifest; a resumed "
        "run with a different --model is rejected (exit 2).",
    )
    review.add_argument(
        "--workspace",
        default=None,
        help="Override the workspace; mirrors `audit`'s flag "
        "(default: per-repo sidecar beneath --root).",
    )
    review.add_argument(
        "--token-budget",
        type=int,
        default=0,
        help="Hard review token budget; 0 (default) means unlimited. A file whose projected "
        "cost exceeds the budget latches the gate: later files seal 'partial' and exit 0.",
    )
    background = review.add_mutually_exclusive_group()
    background.add_argument(
        "--background",
        default=None,
        help="Developer-supplied background context (inline). Sanitized (1 MB cap, control-char "
        "strip, delimiter guard, secret abort, redaction) and wrapped in the trust envelope.",
    )
    background.add_argument(
        "--background-file",
        default=None,
        help="Read background context from a file; same sanitization as --background.",
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

    if args.cmd == "sessions":
        from sec_overlay import sessions as sessions_mod
        from sec_overlay.repo_memory import memory_root

        root = memory_root(args.target)
        if args.sessions_cmd == "list":
            print(sessions_mod.render_rows(sessions_mod.session_rows(root)))
            return 0
        try:
            session_dir = sessions_mod.resolve_session(root, args.session)
        except KeyError:
            print(f"sessions: no session {args.session!r} under {root}", file=sys.stderr)
            return 2
        detail = sessions_mod.session_detail(session_dir, severity=args.severity)
        print(sessions_mod.render_detail(detail))
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
        try:
            background_text = (
                load_background(args.background)
                if args.background is not None
                else load_background(path=args.background_file)
                if args.background_file is not None
                else ""
            )
        except (ValueError, SecretsPresent) as exc:
            print(f"background: {exc}", file=sys.stderr)
            return 2
        return run_review(
            args.base,
            args.head,
            args.root,
            commit=args.commit,
            workspace_dirty=args.workspace_dirty,
            profile=args.profile,
            rule_path=args.rule,
            excludes=args.exclude,
            prepare=args.prepare,
            prepare_reflection=args.prepare_reflection,
            plan=args.plan,
            concurrency=args.concurrency,
            timeout=args.timeout,
            max_git_procs=args.max_git_procs,
            model=args.model,
            workspace=args.workspace,
            token_budget=args.token_budget,
            background=background_text,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
