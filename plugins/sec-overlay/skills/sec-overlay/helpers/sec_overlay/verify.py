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
    "rule-no-target-file", "rule-no-discriminate",
})

_CAUSE_TO_VERIFICATION = {
    "verified-static": "verified-static",
    "not-fixed": "not-fixed",
    "patch-not-applied": "static-only",
    "rule-no-match": "static-only",
    "unconfirmed": "static-only",
    "rule-no-target-file": "static-only",
    "rule-no-discriminate": "static-only",
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


def _rel_path(path: str, root: str) -> str:
    """Return ``path`` in POSIX form with ``root``'s prefix removed.

    Pure string work on purpose: a CodeQL SARIF URI is already repo-relative and
    does not exist relative to this process's CWD, so a ``realpath`` round-trip
    would corrupt it. semgrep prefixes the scan target, osv-scanner reports an
    absolute source path, and CodeQL reports neither.

    Args:
        path: A scanner-reported or finding-reported file path.
        root: The directory the scan ran against; may be empty.

    Returns:
        ``path`` relative to ``root`` when ``root`` prefixes it, else ``path``
        unchanged, with ``os.sep`` rewritten to ``/`` and no leading ``./``. On
        POSIX ``os.sep`` is already ``/``, so a Windows-style input passes
        through with its backslashes — a backslash is a legal POSIX filename
        character, and rewriting it would corrupt a real path.
    """
    q = path.replace(os.sep, "/").removeprefix("./")
    r = root.replace(os.sep, "/").rstrip("/")
    return q[len(r) + 1 :] if r and q.startswith(r + "/") else q


def _path_matches(scanner_path: str, finding_path: str, root: str) -> bool:
    """Return True when two paths name the same file after normalization.

    Matches on a path-segment suffix in both directions rather than on equality.
    ``verify_patch``'s ``target`` may be the scan scope while the finding cites a
    repo-root-relative path, and no helper reconciles the two prefixes. A suffix
    match survives that difference and still separates ``a/util.py`` from
    ``b/util.py``, which a base-filename match could not.

    Args:
        scanner_path: The path the re-scan reported.
        finding_path: The path the finding cites.
        root: The directory the re-scan ran against.

    An empty path names no file, so it never matches: without the guard, an empty
    ``b`` makes ``a.endswith("/")`` true for every directory-like counterpart.

    Returns:
        Whether both paths name one file.
    """
    a = _rel_path(scanner_path, root)
    b = _rel_path(finding_path, root)
    if not a or not b:
        return False
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)


def _file_has_hit(
    target_dir: str, config: str, file_path: str, cls: str, rules: set[str],
    *, backend: str = "semgrep", language: str | None = None, db_dir: str | None = None,
    detail: list[Finding] | None = None,
) -> bool | None:
    """Return True if the finding's signal is present in ``file_path``.

    Matches on the finding's own rule ids when known (``rules``); falls back to
    attack-class match when the finding carries no receipt for the backend.

    Args:
        target_dir: Directory to scan.
        config: SAST rules config path (semgrep only).
        file_path: The finding's own file path, matched by path segment (e.g.
            ``src/app.py``); a bare filename still matches as a one-segment suffix.
        cls: Attack-class key (fallback matcher).
        rules: The finding's own rule ids (precise matcher); empty → class.
        backend: Which SAST backend to re-run (``"semgrep"``/``"codeql"``/``"sca"``).
        language: CodeQL language id — required for the ``codeql`` backend.
        db_dir: CodeQL database directory — required for the ``codeql`` backend.
        detail: When given, every matching scanner finding is appended, so the
            caller can compare pre-patch and post-patch matches rather than only
            their presence. A monkeypatched stub that ignores it leaves it empty,
            and the caller falls back to the boolean comparison.

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
    matched = False
    for f in findings:
        if not _path_matches(f.file, file_path, target_dir):
            continue
        if f.rule_id in rules if rules else f.cls == cls:
            matched = True
            if detail is None:
                return True
            detail.append(f)
    return matched


def _check(
    target: str, configs: list[str], file_path: str, cls: str, rules: set[str],
    backend: str, language: str | None, db_dir: str | None,
    *, detail: list[Finding] | None = None,
) -> bool | None:
    """Call ``_file_has_hit`` once per config, OR-combining the tri-state result.

    ``semgrep`` uses the original 5-positional-arg call (kept exact for
    backward compatibility with existing monkeypatches of ``_file_has_hit``);
    ``codeql``/``sca`` ignore ``configs`` entirely and run once, so a
    multi-ruleset plan never re-runs a database build per ruleset. ``detail``
    rides as a keyword so a 5-positional monkeypatch still binds.

    When the caller asked for ``detail``, every config runs even after one hits:
    stopping early leaves the pre-patch and post-patch detail drawn from
    different rulesets, and comparing disjoint evidence yields a false
    ``rule-no-discriminate``. The detail-free path keeps the early return.
    """
    if backend != "semgrep":
        return _file_has_hit(
            target, configs[0], file_path, cls, rules,
            backend=backend, language=language, db_dir=db_dir, detail=detail,
        )
    saw_none = False
    saw_hit = False
    for config in configs:
        hit = _file_has_hit(target, config, file_path, cls, rules, detail=detail)
        if hit:
            if detail is None:
                return True
            saw_hit = True
        elif hit is None:
            saw_none = True
    if saw_hit:
        return True
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


def _unquote_path(path: str) -> str:
    """Decode git's C-style quoting on a diff path (see ``core.quotePath``).

    Git wraps a path in double quotes and escapes its bytes when the path holds a
    non-ASCII byte, a space, or a control character. Each byte becomes an octal
    escape, so the quoted form is pure ASCII.

    Args:
        path: One path field from a diff header, quotes included if git added them.

    Returns:
        The decoded path. An unquoted path comes back unchanged. A quoted body that
        does not decode comes back with its quotes stripped and nothing else changed.
    """
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    try:
        body = path[1:-1].encode("utf-8").decode("unicode_escape")
        return body.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return path[1:-1]


def _patch_files(patch_diff: str) -> set[str]:
    """Return the post-image paths a unified diff writes to.

    Reads ``+++ b/<path>`` headers only. ``/dev/null`` (a deletion) contributes
    nothing, and a diff with no header at all yields an empty set, which the
    caller reads as "unknown" and skips the check.

    Args:
        patch_diff: The unified diff text.

    Returns:
        The set of POSIX paths the diff writes, with a ``b/`` prefix stripped.
    """
    files = set()
    for line in patch_diff.splitlines():
        if not line.startswith("+++ "):
            continue
        path = _unquote_path(line[4:].split("\t", 1)[0].strip())
        if path == "/dev/null":
            continue
        files.add(_rel_path(path.removeprefix("b/"), ""))
    return files


def _post_verdict(pre: list[Finding], post: list[Finding]) -> str:
    """Return ``not-fixed`` or ``rule-no-discriminate`` for a surviving hit.

    Compares matched source text, never line numbers: a patch that inserts a
    line shifts every later line, so a line comparison would call a genuinely
    unfixed finding a new construction. Disjoint evidence sets mean the rule
    fires on something the patch introduced — the rule does not separate the
    vulnerable construction from the safe one (REQ-60). Overlapping sets mean the
    original construction survives.

    Args:
        pre: Findings the pre-patch scan matched; empty when a stub supplied none.
        post: Findings the post-patch scan matched; empty on the same condition.

    Returns:
        ``"rule-no-discriminate"`` when both sets are non-empty and share no
        evidence text, else ``"not-fixed"``.
    """
    if not pre or not post:
        return "not-fixed"
    before = {f.evidence.strip() for f in pre if f.evidence}
    after = {f.evidence.strip() for f in post if f.evidence}
    _LAST_LINES.clear()
    if before and after and not (before & after):
        _LAST_LINES.update({"pre": pre[0].line, "post": post[0].line})
        return "rule-no-discriminate"
    return "not-fixed"


# The lines the last ``verify_patch`` call matched, pre-patch and post-patch. The
# cause is a plain string, so the numbers the register asks for cannot ride on the
# return value; ``verify_findings`` reads them here immediately after the call.
_LAST_LINES: dict[str, int] = {}


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
        file: Finding's file path, matched by path segment against the re-scan hit.
        cls: Finding's attack class.
        evidence_sources: The finding's evidence sources — picks the re-run backend.
        language: CodeQL language id, if the backend is codeql.
        db_dir: CodeQL database directory, if the backend is codeql.

    Returns:
        A member of :data:`VERIFY_CAUSES`. ``"verified-static"`` (was flagged, now
        gone), ``"not-fixed"`` (still flagged after a clean apply),
        ``"rule-no-match"`` (not detectable pre-patch), ``"rule-no-target-file"``
        (the patch touches no file the finding's rule fires in), ``"rule-no-discriminate"``
        (the rule still fires, but on evidence text the pre-patch scan never matched),
        ``"patch-not-applied"`` (the patch failed to apply to the copy), or
        ``"unconfirmed"`` (the post-patch re-scan could not run). :func:`verify_findings`
        maps each cause to a legal ``Finding.verification`` value.
    """
    _LAST_LINES.clear()
    # Cheap string check first: a placeholder-version deps bump can never be a real fix, so
    # short-circuit before the pre-scan, the repo copy, and the patch apply.
    if cls == "deps" and _placeholder_version_bump(patch_diff):
        return "not-fixed"

    configs = [config] if isinstance(config, str) else list(config) or [""]
    backend = _pick_backend(evidence_sources)
    rules = _source_rules(f"{backend}:", evidence_sources)
    pre_detail: list[Finding] = []
    pre = _check(
        target, configs, file, cls, rules, backend, language, db_dir, detail=pre_detail
    )
    if not pre:
        return "rule-no-match"

    tmp = tempfile.mkdtemp(prefix="sec-overlay-verify-")
    try:
        repo = Path(tmp) / "repo"
        shutil.copytree(target, repo, ignore=_copy_ignore)
        if not apply_patch(repo, patch_diff):
            return "patch-not-applied"
        post_detail: list[Finding] = []
        post = _check(
            str(repo), configs, file, cls, rules, backend, language, db_dir,
            detail=post_detail,
        )
        if post is None:
            return "unconfirmed"
        if not post:
            return "verified-static"
        # A cross-file fix — a sanitizer added beside the sink — leaves the sink line
        # byte-identical, so OSS semgrep's intra-file taint reports the identical hit
        # after the patch. That is not evidence the patch failed (REQ-59). This runs
        # AFTER the re-scan so it can only downgrade a surviving hit: a cross-file
        # backend that proves the patch clean still reaches ``verified-static``.
        touched = _patch_files(patch_diff)
        if touched and not any(_path_matches(t, file, target) for t in touched):
            return "rule-no-target-file"
        return _post_verdict(pre_detail, post_detail)
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
    touched: list[Finding] = []
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
        # Cleared before every call: a stub ``verifier`` that never touches ``_LAST_LINES``
        # must not inherit a prior finding's or a prior run's stale pre/post line numbers.
        _LAST_LINES.clear()
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
            touched.append(f)
            continue
        entry = {"event": f"verify:cause:{cause}"}
        if _LAST_LINES:
            entry["reason"] = f"pre line {_LAST_LINES['pre']}, post line {_LAST_LINES['post']}"
        f.history.append(entry)
        f.verification = verification
        touched.append(f)
        if verification == "verified-static":
            f.status = FindingStatus.FIXED
            f.history.append({"event": "verify:fixed"})
            fixed += 1
        elif verification == "static-only":
            f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
            f.history.append({"event": "verify:needs-deployment-testing"})
    if touched:
        write_findings(ws, touched)
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
