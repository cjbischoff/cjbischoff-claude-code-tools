"""Driver helpers for a sec-overlay audit run.

Pure functions the command/orchestrator composes: a working-tree fence, a
per-phase receipt writer, a one-time token env writer, scan-profile role
inference, and manifest synthesis, plus the single-repo ``drive`` loop.
"""

import subprocess
from pathlib import Path


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
