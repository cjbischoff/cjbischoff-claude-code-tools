"""Static patch verification: apply a fix to a copy, re-scan, confirm it's gone.

The target is never executed and never modified in place — patches apply to a
temp copy, then the configured SAST re-runs on the copy. A finding is only
verified when the scanner flagged its class before the patch and no longer does
after.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

# The cause of a verify verdict. ``Finding.verification`` is a closed enum owned by the
# frozen ``evidence.py``, so the cause cannot become a verification value — it is returned
# by ``verify_patch``, mapped below, and recorded in the finding's history.
VERIFY_CAUSES = frozenset({
    "verified-static", "not-fixed", "patch-not-applied", "rule-no-match", "unconfirmed",
})

_CAUSE_TO_VERIFICATION = {
    "verified-static": "verified-static",
    "not-fixed": "not-fixed",
    "patch-not-applied": "static-only",
    "rule-no-match": "static-only",
    "unconfirmed": "static-only",
}


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    """copytree ignore: skip ``.git`` and any non-regular entry (socket/fifo).

    ``git apply`` patches plain files and does not need a ``.git`` dir, so copying
    it is pure cost — and a live repo's ``.git`` can contain sockets (e.g. the
    fsmonitor ``fsmonitor--daemon.ipc`` IPC socket) that ``copytree`` cannot copy,
    which would crash the whole verify phase. Skipping ``.git`` avoids that and
    speeds the copy; the socket/fifo guard is defensive for any elsewhere.

    Args:
        directory: Directory being copied.
        names: Entry names within it.

    Returns:
        The subset of ``names`` to skip.
    """
    skip: set[str] = set()
    for n in names:
        if n == ".git":
            skip.add(n)
            continue
        try:
            mode = os.lstat(os.path.join(directory, n)).st_mode
        except OSError:
            continue
        if stat.S_ISSOCK(mode) or stat.S_ISFIFO(mode):
            skip.add(n)
    return skip

from sec_overlay.campaign import record_stage
from sec_overlay.codeql import CodeQLError, run_codeql
from sec_overlay.kb import read_profile
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.sast import run_semgrep
from sec_overlay.sca import ScaError, run_sca
from sec_overlay.scoring import score_fix
from sec_overlay.workspace import Workspace, read_findings, write_findings


def apply_patch(directory: str | Path, patch_diff: str, *, runner=subprocess.run) -> bool:
    """Apply a unified diff inside ``directory`` using ``git apply``.

    Args:
        directory: Directory to apply the patch in (a throwaway copy).
        patch_diff: Unified diff text (paths relative, ``a/`` ``b/`` prefixes).
        runner: Injectable subprocess runner (for testing).

    Returns:
        True if ``git apply`` succeeded.
    """
    directory = Path(directory)
    patch_file = directory / ".sec_overlay.patch"
    patch_file.write_text(patch_diff)
    try:
        result = runner(
            ["git", "apply", str(patch_file)],
            cwd=str(directory),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        if patch_file.exists():
            patch_file.unlink()
    return result.returncode == 0


def _source_rules(prefix: str, evidence_sources: list[str] | None) -> set[str]:
    """Extract the finding's own rule ids for a given evidence-source ``prefix``.

    Lets verification match the SPECIFIC rule that flagged the finding rather
    than the whole attack class — so a fix is credited when *that* signal clears,
    not falsely marked unfixed because an unrelated same-class lint still fires
    in the file (and not falsely credited when a sibling rule of the class is
    what actually went away).

    Args:
        prefix: Evidence-source prefix to match (e.g. ``"semgrep:"``, ``"codeql:"``).
        evidence_sources: The finding's ``evidence_sources`` (may be None/empty).

    Returns:
        The set of rule ids from matching receipts (empty if none).
    """
    out: set[str] = set()
    for s in evidence_sources or []:
        if s.startswith(prefix):
            out.add(s[len(prefix):])
    return out


def _pick_backend(evidence_sources: list[str] | None) -> str:
    """Pick which SAST backend to re-run based on the finding's own evidence source.

    Re-verification must use the SAME backend that originally flagged the
    finding — re-running semgrep on a codeql-only finding proves nothing about
    whether the codeql signal cleared. Defaults to semgrep when no codeql/sca
    receipt is present (keeps existing semgrep-only callers unaffected).

    Args:
        evidence_sources: The finding's ``evidence_sources`` (may be None/empty).

    Returns:
        ``"codeql"``, ``"sca"``, or ``"semgrep"``.
    """
    sources = evidence_sources or []
    if any(s.startswith("codeql:") for s in sources):
        return "codeql"
    if any(s.startswith("sca:") for s in sources):
        return "sca"
    return "semgrep"


def _file_has_hit(
    target_dir: str, config: str, file_basename: str, cls: str, rules: set[str],
    *, backend: str = "semgrep", language: str | None = None, db_dir: str | None = None,
) -> bool | None:
    """Return True if the finding's signal is present in ``file_basename``.

    Matches on the finding's own rule ids when known (``rules``); falls back to
    attack-class match when the finding carries no receipt for the backend.

    Args:
        target_dir: Directory to scan.
        config: SAST rules config path (semgrep only).
        file_basename: Base filename to match (e.g. ``app.py``).
        cls: Attack-class key (fallback matcher).
        rules: The finding's own rule ids (precise matcher); empty → class.
        backend: Which SAST backend to re-run (``"semgrep"``/``"codeql"``/``"sca"``).
        language: CodeQL language id — required for the ``codeql`` backend.
        db_dir: CodeQL database directory — required for the ``codeql`` backend.

    Returns:
        Whether at least one matching finding exists, or ``None`` if the
        finding's own backend is unavailable here (missing codeql binary/pack,
        missing osv-scanner) — the caller must treat that as "cannot verify",
        never as a false clean.
    """
    try:
        if backend == "codeql":
            work_dir = db_dir or tempfile.mkdtemp(prefix="sec-overlay-codeql-db-")
            findings = run_codeql(target_dir, language=language or "", db_dir=work_dir)
        elif backend == "sca":
            findings = run_sca(target_dir)
        else:
            findings = run_semgrep(target_dir, config)
    except (CodeQLError, ScaError):
        return None
    for f in findings:
        if os.path.basename(f.file) != file_basename:
            continue
        if f.rule_id in rules if rules else f.cls == cls:
            return True
    return False


def _check(
    target: str, configs: list[str], basename: str, cls: str, rules: set[str],
    backend: str, language: str | None, db_dir: str | None,
) -> bool | None:
    """Call ``_file_has_hit`` once per config, OR-combining the tri-state result.

    ``semgrep`` uses the original 5-positional-arg call (kept exact for
    backward compatibility with existing monkeypatches of ``_file_has_hit``);
    ``codeql``/``sca`` ignore ``configs`` entirely and run once, so a
    multi-ruleset plan never re-runs a database build per ruleset.
    """
    if backend != "semgrep":
        return _file_has_hit(
            target, configs[0], basename, cls, rules,
            backend=backend, language=language, db_dir=db_dir,
        )
    saw_none = False
    for config in configs:
        hit = _file_has_hit(target, config, basename, cls, rules)
        if hit:
            return True
        if hit is None:
            saw_none = True
    return None if saw_none else False


# Case-sensitive on purpose: the placeholder convention is uppercase ``X.Y.Z``. Matching
# case-insensitively flags real lowercase strings (e.g. a module path containing ``x.y.z``).
_PLACEHOLDER_VERSION_RE = re.compile(r"\bv?[XYZ]\.[XYZ]\.[XYZ]\b")


def _placeholder_version_bump(patch_diff: str) -> bool:
    """True if an added diff line contains an obviously non-functional version
    placeholder (e.g. ``vX.Y.Z``) instead of a real version number.

    A patch that bumps a dependency to a literal template string will never
    build; crediting it as "fixed" because the old vulnerable version string
    is no longer text-matched by the SCA re-scan is a false clean. This is a
    narrow, deliberately conservative heuristic — it only catches the
    X/Y/Z-placeholder shape, not every possible non-functional diff.

    Args:
        patch_diff: The unified diff text.

    Returns:
        True if any added line (``+`` prefix, not ``+++``) matches the
        placeholder-version pattern.
    """
    for line in patch_diff.splitlines():
        if (
            line.startswith("+")
            and not line.startswith("+++")
            and _PLACEHOLDER_VERSION_RE.search(line)
        ):
            return True
    return False


def verify_patch(
    target: str, patch_diff: str, config: str | list[str], file: str, cls: str,
    evidence_sources: list[str] | None = None,
    *, language: str | None = None, db_dir: str | None = None,
) -> str:
    """Statically verify a patch neutralizes a finding's class in a file.

    Copies ``target`` to a temp dir, applies the patch, re-runs the finding's
    own SAST backend, and compares the pre/post presence of a hit in
    ``file``. The original ``target`` is never modified.

    Args:
        target: Path to the (unmodified) target repo.
        patch_diff: Unified diff proposed for the finding.
        config: SAST rules config path, or a list of them (semgrep only).
        file: Finding's file path (only the basename is matched).
        cls: Finding's attack class.
        evidence_sources: The finding's evidence sources — picks the re-run backend.
        language: CodeQL language id, if the backend is codeql.
        db_dir: CodeQL database directory, if the backend is codeql.

    Returns:
        A member of :data:`VERIFY_CAUSES`. ``"verified-static"`` (was flagged, now
        gone), ``"not-fixed"`` (still flagged after a clean apply),
        ``"rule-no-match"`` (not detectable pre-patch), ``"patch-not-applied"``
        (the patch failed to apply to the copy), or ``"unconfirmed"`` (the
        post-patch re-scan could not run). :func:`verify_findings` maps each
        cause to a legal ``Finding.verification`` value.
    """
    # Cheap string check first: a placeholder-version deps bump can never be a real fix, so
    # short-circuit before the pre-scan, the repo copy, and the patch apply.
    if cls == "deps" and _placeholder_version_bump(patch_diff):
        return "not-fixed"

    configs = [config] if isinstance(config, str) else list(config) or [""]
    basename = os.path.basename(file)
    backend = _pick_backend(evidence_sources)
    rules = _source_rules(f"{backend}:", evidence_sources)
    # ponytail: basename match is fine for distinct filenames; a repo with two
    # same-named files in different dirs could alias — revisit with full paths then.
    pre = _check(target, configs, basename, cls, rules, backend, language, db_dir)
    if not pre:
        return "rule-no-match"

    tmp = tempfile.mkdtemp(prefix="sec-overlay-verify-")
    try:
        repo = Path(tmp) / "repo"
        shutil.copytree(target, repo, ignore=_copy_ignore)
        if not apply_patch(repo, patch_diff):
            return "patch-not-applied"
        post = _check(str(repo), configs, basename, cls, rules, backend, language, db_dir)
        if post is None:
            return "unconfirmed"
        return "not-fixed" if post else "verified-static"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def resolve_configs(ws: Workspace, fallback: str) -> list[str]:
    """Return the semgrep rulesets the scan profile planned, or the caller's fallback.

    Args:
        ws: The campaign workspace.
        fallback: The caller-supplied config path, used when the profile is absent,
            unreadable, or plans no rulesets.

    Returns:
        A non-empty list of ruleset paths.
    """
    try:
        profile = read_profile(ws)
    except (OSError, ValueError):
        return [fallback]
    semgrep = profile.sast_plan.get("semgrep")
    rulesets = semgrep.get("rulesets") if isinstance(semgrep, dict) else None
    if not isinstance(rulesets, list):
        rulesets = []
    return [str(r) for r in rulesets] or [fallback]


def apply_fix_gates(ws: Workspace) -> int:
    """Score the validate-fix agent's per-gate statuses and record each verdict.

    The agent supplies gate statuses only. ``scoring.score_fix`` computes the
    verdict, so an LLM cannot promote a finding by writing a status field. This
    function never sets ``status``: ``verify_findings`` owns promotion, and its
    ``verify:conflict`` branch reads the history event written here.

    Args:
        ws: The audit workspace. ``kb/gates/validate-fix.json`` must exist; the
            phase table declares it as verify's input, so a missing file is a
            driver-level halt, not a case to tolerate here.

    Returns:
        The number of findings stamped with a verdict.

    Raises:
        FileNotFoundError: The gate file is absent.
        json.JSONDecodeError: The gate file is not valid JSON.

    Example:
        >>> from sec_overlay.scoring import score_fix
        >>> score_fix({"root_cause": "pass", "instance_coverage": "pass",
        ...            "no_new_vulnerabilities": "pass", "best_practices": "pass"})[0]
        'fixed'
    """
    gates = json.loads((ws.kb / "gates" / "validate-fix.json").read_text())
    touched: list[Finding] = []
    for f in read_findings(ws):
        entry = gates.get(f.id)
        if not isinstance(entry, dict):
            continue
        verdict, score = score_fix(entry)
        f.history.append({"event": f"validate-fix:{verdict}", "score": score})
        if verdict in ("partial", "not_fixed"):
            f.verification = "not-fixed"
        elif verdict == "unverifiable":
            f.verification = "verify-error"
        touched.append(f)
    if touched:
        write_findings(ws, touched)
    return len(touched)


def verify_findings(
    ws: Workspace, target: str, config: str, *,
    verifier=verify_patch, language: str | None = None, db_dir: str | None = None,
) -> int:
    """Verify patches on confirmed findings and promote verified ones to fixed.

    For each ``CONFIRMED`` finding with a ``patch_diff``, run the verifier and
    record ``verification``; ``verified-static`` results become ``FIXED``.

    Args:
        ws: Workspace whose confirmed findings are verified in place.
        target: Path to the (unmodified) target repo.
        config: SAST rules config path.
        verifier: Injectable verify function (defaults to :func:`verify_patch`).
        language: CodeQL language id, threaded to the verifier for codeql findings.
        db_dir: CodeQL database directory, threaded to the verifier for codeql findings.

    Returns:
        The number of findings promoted to ``fixed``.
    """
    findings = read_findings(ws)
    configs = resolve_configs(ws, config)
    fixed = 0
    changed = False
    for f in findings:
        if f.status is not FindingStatus.CONFIRMED or not f.patch_diff:
            continue
        last_validate_fix = next(
            (h for h in reversed(f.history) if str(h.get("event", "")).startswith("validate-fix:")),
            None,
        )
        # Deliberately broad: ANY validate-fix verdict other than ``validate-fix:fixed``
        # blocks promotion — including ``validate-fix:unverifiable``. An unverifiable fix is
        # a verify-error, and a verify-error must never be laundered into a clean verdict.
        validate_fix_said_not_fixed = (
            last_validate_fix is not None
            and last_validate_fix.get("event") != "validate-fix:fixed"
        )
        cause = verifier(
            target, f.patch_diff, configs, f.file, f.cls, f.evidence_sources,
            language=language, db_dir=db_dir,
        )
        # An unmapped cause degrades to static-only: never launder an unknown verdict clean.
        verification = _CAUSE_TO_VERIFICATION.get(cause, "static-only")
        if verification == "verified-static" and validate_fix_said_not_fixed:
            # Idempotent: re-running verify on the same finding must not pile up duplicates.
            if f.history and f.history[-1].get("event") == "verify:conflict":
                continue
            f.history.append({
                "event": "verify:conflict",
                "reason": ("deterministic re-scan found the signal gone, but validate-fix "
                           f"explicitly said {last_validate_fix.get('event')!r} — leaving "
                           "status/verification as validate-fix left them for human review"),
            })
            changed = True
            continue
        f.history.append({"event": f"verify:cause:{cause}"})
        f.verification = verification
        changed = True
        if verification == "verified-static":
            f.status = FindingStatus.FIXED
            f.history.append({"event": "verify:fixed"})
            fixed += 1
        elif verification == "static-only":
            f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
            f.history.append({"event": "verify:needs-deployment-testing"})
    if changed:
        write_findings(ws, findings)
    record_stage(ws, "verify")
    return fixed


def main(argv: list[str] | None = None) -> int:
    """CLI: verify patches for a workspace's confirmed findings.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-verify")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    n = verify_findings(Workspace(Path(args.workspace)), args.target, args.config)
    print(f"fixed {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
