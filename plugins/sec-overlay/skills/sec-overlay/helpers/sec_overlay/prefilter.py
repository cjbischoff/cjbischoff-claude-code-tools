"""Profile-driven prefilter: run the SAST backends recon selected, merge results."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.codeql import CodeQLError, codeql_config_trusted, qlpack_installed, run_codeql
from sec_overlay.coverage import compute_coverage
from sec_overlay.exclusions import apply_exclusions, load_exclusions
from sec_overlay.models import Finding
from sec_overlay.normalize import normalize
from sec_overlay.profile import ScanProfile
from sec_overlay.sast import run_semgrep
from sec_overlay.sca import ScaError, run_sca
from sec_overlay.secrets import scan_secrets
from sec_overlay.workspace import Workspace, write_findings


def _assign_candidate_ids(kept: list[Finding]) -> None:
    """Assign per-class candidate ids ``C-<PREFIX>-####`` in canonical order.

    Sorts ``kept`` in place by ``(file, line, rule_id, cls)`` — the same canonical
    order used before — then numbers each class independently so ids never collide
    across rulesets and carry the attack class (ISSUE-013).

    Args:
        kept: Findings to number, mutated in place.
    """
    kept.sort(key=lambda f: (f.file, f.line, f.rule_id, f.cls))
    counters: dict[str, int] = {}
    for f in kept:
        prefix = re.sub(r"[^A-Z0-9]+", "-", f.cls.upper()).strip("-") or "UNKNOWN"
        counters[prefix] = counters.get(prefix, 0) + 1
        f.id = f"C-{prefix}-{counters[prefix]:04d}"


def _raise_on_incomplete_backends(
    *, skipped_reasons: dict[str, str], failed: list[dict], strict: bool
) -> None:
    """Raise when a planned backend did not run (strict never-silent contract).

    Args:
        skipped_reasons: Backend -> reason for backends that did not run.
        failed: Backend failure records.
        strict: When True, any skipped or failed backend is a hard error.

    Raises:
        RuntimeError: ``strict`` and at least one backend is skipped or failed.
    """
    if not strict:
        return
    problems = list(skipped_reasons.items()) + [(f.get("backend"), f.get("error")) for f in failed]
    if problems:
        joined = ", ".join(f"{b}: {r}" for b, r in problems)
        raise RuntimeError(
            f"prefilter: planned backend(s) did not run — {joined}. "
            "A partial scan is a coverage hole, not 'no findings'."
        )


def run_prefilter(
    ws: Workspace,
    target: str,
    profile: ScanProfile,
    *,
    semgrep=run_semgrep,
    codeql=run_codeql,
    has_tool=shutil.which,
    trust_fn=codeql_config_trusted,
    qlpack_fn=qlpack_installed,
    secrets_fn=scan_secrets,
    sca_fn=run_sca,
    exclusions_fn=load_exclusions,
    max_workers: int | None = None,
    strict: bool = True,
) -> dict:
    """Run the profile's enabled SAST backends concurrently and persist merged candidates.

    For each backend marked ``run: true`` in ``profile.sast_plan`` whose binary
    is available, run it; skip (and record) backends whose binary is absent.
    Each backend unit (one per semgrep ruleset, one per codeql language) runs
    in a thread pool. Results are merged, sorted by ``(file, line, rule_id)``
    for determinism, and given fresh contiguous ``C-####`` ids — this also
    fixes a latent bug where each ruleset's parser numbered its findings from
    C-0001 independently, causing id collisions across rulesets. Findings are
    then normalized, noise-floor exclusions applied, and kept findings written
    to the workspace.

    Args:
        ws: Target workspace.
        target: Source root to scan.
        profile: The scan profile from recon.
        semgrep: Injectable semgrep runner.
        codeql: Injectable codeql runner.
        has_tool: Injectable binary-presence resolver.
        trust_fn: Injectable CodeQL config trust checker; returns (trusted, reason).
        exclusions_fn: Injectable exclusion loader; called with workspace.
        max_workers: Thread pool size; defaults to ``cpu_count - 1`` (capped at 8).
        strict: When True (default), any planned backend left in ``skipped_reasons``
            or ``failed`` raises ``RuntimeError`` instead of returning a silent
            partial result (ISSUE-034). Pass False only for a deliberately partial
            run (e.g. a test exercising one backend's skip/failure path).

    A backend whose binary is absent is recorded in ``skipped``. A backend that
    ran but errored (e.g. a CodeQL build/analyze failure) is recorded in
    ``failed`` — never swallowed as an empty result, so a broken scan is
    distinguishable from a clean one. Other backends still run. CodeQL is only
    run if its config passes the trust check. Whether a backend counts as run
    is decided when its units are built, not by completion order. Results are
    byte-identical between serial (``max_workers=1``) and concurrent runs because
    ``ThreadPoolExecutor.map`` returns results in submission order and the unit
    list is built deterministically — thread scheduling never affects output.

    Returns:
        ``{"candidates", "backends_run", "skipped", "failed", "excluded", "dropped_nonsecurity",
        "skipped_reasons", "coverage"}`` where ``failed`` is a list of ``{"backend", "error"}``,
        ``excluded`` is the count of suppressed findings, ``dropped_nonsecurity`` is the count of
        unknown-class semgrep findings dropped when security_only is enabled, ``skipped_reasons``
        records why each backend was not run, and ``coverage`` is the per-language dataflow/
        pattern-only/none breakdown from :func:`sec_overlay.coverage.compute_coverage` (also
        persisted to ``kb/coverage.json``).

    Raises:
        RuntimeError: ``strict`` (the default) and a planned backend is skipped or failed.
    """
    plan = profile.sast_plan
    codeql_db_root = tempfile.mkdtemp(prefix="sec-overlay-codeql-")
    ran: list[str] = []
    skipped: list[str] = []
    failed: list[dict] = []
    skipped_reasons: dict[str, str] = {}
    units: list = []  # zero-arg callables, each returns ("backend", findings, error_or_None)
    codeql_unit_count = 0

    sem = plan.get("semgrep", {})
    sem_enabled = sem.get("run", None)
    rulesets = sem.get("rulesets", [])
    if sem_enabled is False or (sem_enabled is None and not rulesets):
        skipped_reasons["semgrep"] = "disabled"
    elif not has_tool("semgrep"):
        skipped.append("semgrep")
        skipped_reasons["semgrep"] = "absent"
    else:
        for cfg in rulesets:
            units.append(lambda cfg=cfg: ("semgrep", semgrep(target, cfg), None))
        ran.append("semgrep")

    cql = plan.get("codeql", {})
    if cql.get("run"):
        if has_tool("codeql"):
            trusted, reason = trust_fn(target)
            if not trusted:
                failed.append({"backend": "codeql", "error": f"untrusted codeql config: {reason}"})
                skipped_reasons["codeql"] = "untrusted"
            else:
                for lang in cql.get("languages", []):
                    if not qlpack_fn(lang):
                        failed.append({
                            "backend": "codeql",
                            "error": (
                                f"query pack codeql/{lang}-queries not installed "
                                f"(codeql binary present but the {lang} pack is not "
                                f"in the local cache); run: codeql pack download "
                                f"codeql/{lang}-queries"
                            ),
                        })
                        skipped_reasons["codeql"] = "pack-missing"
                        continue
                    def _codeql_unit(lang=lang):
                        # Build the CodeQL DB in a temp dir, NOT ws.root — the workspace
                        # is now durable per-repo memory, and the DB is a large (100s of
                        # MB) rebuildable artifact that must not bloat/pollute it.
                        db_dir = str(Path(codeql_db_root) / f"codeql-db-{lang}")
                        try:
                            return ("codeql", codeql(target, lang, db_dir), None)
                        except CodeQLError as exc:
                            return ("codeql", [], str(exc))
                    units.append(_codeql_unit)
                    codeql_unit_count += 1
        else:
            skipped.append("codeql")
            skipped_reasons["codeql"] = "absent"
    elif "codeql" in plan:
        skipped_reasons["codeql"] = "disabled"

    # secrets — in-house, offline, no external binary; always runs when enabled.
    sec_cfg = plan.get("secrets", {})
    if sec_cfg.get("run"):
        def _secrets_unit():
            try:
                return ("secrets", secrets_fn(target), None)
            except OSError as exc:
                return ("secrets", [], str(exc))
        units.append(_secrets_unit)
        ran.append("secrets")
    elif "secrets" in plan:
        skipped_reasons["secrets"] = "disabled"

    # sca — delegates to osv-scanner; absent/errored is recorded, never silent.
    sca_cfg = plan.get("sca", {})
    sca_unit_count = 0
    if sca_cfg.get("run"):
        def _sca_unit():
            try:
                return ("sca", sca_fn(target), None)
            except ScaError as exc:
                return ("sca", [], str(exc))
        units.append(_sca_unit)
        sca_unit_count = 1
    elif "sca" in plan:
        skipped_reasons["sca"] = "disabled"

    workers = max_workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    raw: list = []
    codeql_completed = 0
    sca_completed = 0
    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(lambda u: u(), units))
    finally:
        shutil.rmtree(codeql_db_root, ignore_errors=True)  # never keep the CodeQL DB
    for backend, backend_findings, error in results:
        raw.extend(backend_findings)
        if backend == "codeql":
            if error is not None:
                failed.append({"backend": "codeql", "error": error})
            else:
                codeql_completed += 1
        elif backend == "sca":
            if error is not None:
                failed.append({"backend": "sca", "error": error})
                # "not installed" is an absence, not a crash — record it as such.
                skipped_reasons["sca"] = "absent" if "not installed" in error else "error"
            else:
                sca_completed += 1
    if codeql_unit_count and codeql_completed:
        ran.append("codeql")
    if sca_unit_count and sca_completed and "sca" not in ran:
        ran.append("sca")

    # Never-silent contract: any backend the profile declared run:true that did not
    # actually run must appear in skipped_reasons. Guards against a declared backend
    # (or a future one) becoming a silent no-op.
    for backend in ("semgrep", "codeql", "sca", "secrets"):
        cfg = plan.get(backend)
        if cfg and cfg.get("run") and backend not in ran and backend not in skipped_reasons:
            skipped_reasons[backend] = "not-run"

    security_only = sem.get("security_only", True)
    dropped_nonsecurity = 0
    if security_only:
        def _is_semgrep(f):
            return any(s.startswith("semgrep:") for s in f.evidence_sources)
        before = len(raw)
        raw = [f for f in raw if not (_is_semgrep(f) and f.cls == "unknown")]
        dropped_nonsecurity = before - len(raw)

    findings = normalize(raw)
    kept, dropped = apply_exclusions(findings, exclusions_fn(ws))

    # Serial and concurrent runs are byte-identical because ThreadPoolExecutor.map
    # yields results in SUBMISSION order (not completion order) and `units` is
    # built in a fixed order, so `raw` never depends on thread scheduling. The
    # sort below is a stable canonical ordering (total key incl. cls, so ties
    # can't reorder), and the id reassignment fixes the latent bug where each
    # ruleset's parser numbered its findings from C-0001, colliding across rulesets.
    _assign_candidate_ids(kept)

    write_findings(ws, kept)
    coverage = compute_coverage(profile, ran, target)
    ws.kb.mkdir(parents=True, exist_ok=True)
    (ws.kb / "coverage.json").write_text(json.dumps(coverage, indent=2))
    _raise_on_incomplete_backends(skipped_reasons=skipped_reasons, failed=failed, strict=strict)
    record_stage(ws, "prefilter")
    return {
        "candidates": len(kept),
        "backends_run": ran,
        "skipped": skipped,
        "failed": failed,
        "excluded": len(dropped),
        "dropped_nonsecurity": dropped_nonsecurity,
        "skipped_reasons": skipped_reasons,
        "coverage": coverage,
    }
