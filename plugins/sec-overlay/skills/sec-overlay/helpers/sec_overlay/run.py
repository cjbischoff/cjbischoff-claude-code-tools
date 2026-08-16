"""Driver helpers for a sec-overlay audit run.

Pure functions the command/orchestrator composes: a working-tree fence, a
per-phase receipt writer, a one-time token env writer, scan-profile role
inference, and manifest synthesis, plus the single-repo ``drive`` loop.
"""

import json
import subprocess
from pathlib import Path

from sec_overlay.correlate.manifest import ROLES
from sec_overlay.profile import ScanProfile
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
