"""Headless driver for the Claude-Code skill (REQ-M2).

Shells the `claude` CLI (or any compatible agent runner) once per corpus target, the
same way the harness shells a SAST binary: subprocess out, artifacts on disk, no SDK
import. The benchmark then grades the workspace the run produced. A driver failure is
recorded and skipped — findings are never fabricated.
"""

from __future__ import annotations

import subprocess

# The default template documents the expected shape; operators override per environment.
# `{target}` and `{workspace}` substitute per run.
DEFAULT_ARGV_TEMPLATE = [
    "claude",
    "-p",
    (
        "Run the sec-overlay skill's deterministic review/scan flow over the repository "
        "at {target}, writing every artifact into the workspace at {workspace}. "
        "Do not modify the target."
    ),
    "--permission-mode",
    "acceptEdits",
]

DEFAULT_TIMEOUT_SECONDS = 3600


class HeadlessDriver:
    """Run one headless skill pass per target; record failures, never raise.

    Args:
        argv_template: Argv whose elements may carry ``{target}`` / ``{workspace}``
            placeholders, substituted per :meth:`run` call.
        runner: Injectable subprocess runner (tests); defaults to ``subprocess.run``.
        timeout: Per-run wall-clock ceiling in seconds.
    """

    def __init__(
        self,
        argv_template: list[str] | None = None,
        *,
        runner=subprocess.run,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.argv_template = list(argv_template or DEFAULT_ARGV_TEMPLATE)
        self.runner = runner
        self.timeout = timeout
        self.failures: list[dict] = []

    def run(self, target, workspace) -> bool:
        """Drive one pass. Returns True on exit 0; False (recorded) otherwise."""
        argv = [a.format(target=target, workspace=workspace) for a in self.argv_template]
        try:
            result = self.runner(
                argv, capture_output=True, text=True, timeout=self.timeout, check=False
            )
        except Exception as exc:  # noqa: BLE001 - any driver failure is a recorded skip
            self.failures.append({"target": str(target), "error": str(exc)})
            return False
        if result.returncode != 0:
            self.failures.append(
                {
                    "target": str(target),
                    "error": f"exit {result.returncode}: {getattr(result, 'stderr', '')[:500]}",
                }
            )
            return False
        return True
