"""Driver helpers for a sec-overlay audit run.

Pure functions the command/orchestrator composes: a working-tree fence, a
per-phase receipt writer, a one-time token env writer, scan-profile role
inference, and manifest synthesis, plus the single-repo ``drive`` loop.
"""

import json
import subprocess
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.correlate.manifest import ROLES, validate_manifest
from sec_overlay.driver import AuditContext, run_audit
from sec_overlay.phases import PHASE_TABLE
from sec_overlay.profile import ScanProfile
from sec_overlay.repo_memory import RepoMemory
from sec_overlay.state import begin_pass, load_state
from sec_overlay.workspace import Workspace

_RBAC_SIGNALS = ("auth", "rbac", "iam", "policy", "interceptor", "middleware", "identity")
_SERVICE_SIGNALS = ("grpc", "http", "service", "handler", "endpoint", "network")


class WorkingTreeFenceError(RuntimeError):
    """The audited tree changed during the run. The run stops loudly."""


def fence(target: str | Path, baseline: str, *, runner=subprocess.run) -> None:
    """Stop the run if the audited working tree changed since the baseline.

    Args:
        target: Path to the audited repository.
        baseline: ``git status --porcelain`` output captured when the run opened.
        runner: Injectable process runner (defaults to ``subprocess.run``).

    Raises:
        WorkingTreeFenceError: The current porcelain status differs from the
            baseline; the message names the added/removed status lines.
    """
    proc = runner(
        ["git", "-C", str(target), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    if proc.stdout == baseline:
        return
    before = set(baseline.splitlines())
    after = set(proc.stdout.splitlines())
    delta = sorted((after - before) | (before - after))
    raise WorkingTreeFenceError(
        "audited tree changed during the run: " + "; ".join(delta)
    )


def infer_role(profile: ScanProfile) -> str:
    """Infer a correlation role from a repo's scan profile.

    Under-correlating is safer than over-correlating: a wrong ``rbac-source``
    label fabricates a ``control-enforces`` edge and drives a false verdict, so
    ambiguity falls through to ``infra``.

    Args:
        profile: The recon-produced scan profile.

    Returns:
        One of :data:`ROLES`.
    """
    subsystem_names = [s["name"] if isinstance(s, dict) else s for s in profile.subsystems]
    rbac_text = " ".join(subsystem_names + profile.frameworks + profile.attack_surface).lower()
    if any(sig in rbac_text for sig in _RBAC_SIGNALS):
        return "rbac-source"
    surface_text = " ".join(profile.attack_surface).lower()
    if any(sig in surface_text for sig in _SERVICE_SIGNALS):
        return "service-enforcer"
    assert "infra" in ROLES  # invariant: the default is a valid role
    return "infra"


def synthesize_manifest(product: str, members: list[dict]) -> dict:
    """Build a correlation manifest from per-repo members.

    Args:
        product: The product identifier the correlation groups under.
        members: One dict per repo/sub-service with keys ``slug``,
            ``repo_root``, ``scan_scope``, ``role``.

    Returns:
        A manifest dict ready for ``python -m sec_overlay.correlate``.

    Raises:
        ValueError: The synthesized manifest fails ``validate_manifest``.
    """
    manifest = {"product": product, "members": members}
    errs = validate_manifest(manifest)
    if errs:
        raise ValueError("synthesized invalid manifest: " + "; ".join(errs))
    return manifest


def receipt(
    ws: Workspace,
    phase: str,
    *,
    stdout: str = "",
    artifacts: list[str] | None = None,
    counts: dict | None = None,
) -> Path:
    """Persist a phase receipt so no stage advances without one on disk.

    Args:
        ws: The audit workspace.
        phase: The phase name (the receipt file stem).
        stdout: Captured phase stdout, verbatim (empty for in-process phases).
        artifacts: Paths the phase produced, as strings.
        counts: Small numeric summary (e.g. ``{"findings": 3}``).

    Returns:
        The path written: ``<ws.kb>/receipts/<phase>.json``.
    """
    out_dir = ws.kb / "receipts"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{phase}.json"
    path.write_text(
        json.dumps(
            {
                "phase": phase,
                "stdout": stdout,
                "artifacts": artifacts or [],
                "counts": counts or {},
            },
            indent=2,
        )
    )
    return path


def write_env(ws: Workspace, target, scope, sha):
    """Resolve the substitution tokens once and write ``run.env``.

    Agent phases read tokens from this file instead of the orchestrator
    re-substituting them by hand on every spawn.

    Args:
        ws: The audit workspace.
        target: Path to the audited repository.
        scope: Scanned scope relative to the repo root ("." for the whole repo).
        sha: The pinned target SHA for this pass.

    Returns:
        The path written: ``<ws.root>/run.env``.
    """
    path = ws.root / "run.env"
    path.write_text(
        f"TARGET={target}\n"
        f"WORKSPACE={ws.root}\n"
        f"SHA={sha}\n"
        f"SCAN_SCOPE={scope}\n"
        f"REPO_ROOT={target}\n"
    )
    return path


def _target_workspace(target) -> Workspace:
    """Return the in-repo sidecar workspace for a target (via RepoMemory)."""
    return RepoMemory.for_target(str(target)).workspace


def _load_baseline(ws: Workspace, target, runner) -> str:
    """Return the pass fence baseline, capturing and persisting it once.

    The baseline is the audited tree's porcelain status at pass start. It is
    persisted so every resume invocation fences against the pre-audit tree, not
    a fresh snapshot that would already contain an agent phase's write.
    """
    path = ws.kb / "fence-baseline"
    if path.exists():
        return path.read_text()
    baseline = runner(
        ["git", "-C", str(target), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(baseline)
    return baseline


def drive(target, config, *, scope=".", workspace=None, runner=subprocess.run, table=PHASE_TABLE):
    """Audit one repository, driving every phase with a fence and a receipt.

    Opens (or resumes) the workspace, pins the SHA, loads the persisted fence
    baseline (capturing it once at pass start), writes ``run.env`` once, then
    walks the phase table. Before each stage is recorded done, the tree is
    fenced and a receipt is written.

    Args:
        target: Path to the audited repository.
        config: Semgrep/ruleset config path for scanning phases.
        scope: Scanned scope relative to the repo root.
        workspace: Explicit workspace root; ``None`` uses the target sidecar.
        runner: Injectable process runner (git calls).
        table: Phase table to walk (defaults to ``PHASE_TABLE``).

    Returns:
        ``run_audit``'s result: ``"AUDIT COMPLETE"`` or the next dispatch block.
    """
    ws = Workspace(root=workspace) if workspace else _target_workspace(target)
    ws.ensure()
    sha = runner(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    state = load_state(ws)
    if not state.stages:
        begin_pass(ws, sha)
    else:
        sha = state.active_sha or sha  # stay pinned to the pass SHA on resume
    baseline = _load_baseline(ws, target, runner)
    write_env(ws, target, scope, sha)
    ctx = AuditContext(ws=ws, target=str(target), config=config, sha=sha)

    def on_complete(phase_name: str) -> None:
        fence(target, baseline, runner=runner)
        receipt(
            ws,
            phase_name,
            counts={"findings": len(list(ws.findings_dir.glob("F-*.json")))},
        )

    return run_audit(ctx, table=table, on_complete=on_complete)


def advance(target, phase: str, *, workspace=None, runner=subprocess.run) -> Path:
    """Fence, receipt, and record one agent phase the operator just ran.

    Agent phases do not auto-advance in ``drive``: the orchestrator runs the
    model, then calls this to close the fence (Goal 4) and the receipt (Goal 3)
    for that phase. The tree is fenced against the persisted pass baseline, a
    receipt is written, and the stage is recorded.

    Args:
        target: Path to the audited repository.
        phase: The agent phase name just completed.
        workspace: Explicit workspace root; ``None`` uses the target sidecar.
        runner: Injectable process runner (git calls).

    Returns:
        The receipt path written.
    """
    ws = Workspace(root=workspace) if workspace else _target_workspace(target)
    baseline = _load_baseline(ws, target, runner)
    fence(target, baseline, runner=runner)
    rcpt = receipt(
        ws,
        phase,
        counts={"findings": len(list(ws.findings_dir.glob("F-*.json")))},
    )
    record_stage(ws, phase)
    return rcpt
