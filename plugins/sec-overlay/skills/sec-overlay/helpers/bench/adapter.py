"""Scan adapters — the one seam that lets the benchmark drive different scanners.

``ScanAdapter.scan(repo_path, workspace) -> list[Finding]`` runs a full harness pass
over a cloned repo and returns its confirmed/fixed findings. The benchmark, judge,
and tally are adapter-agnostic, so the SAME corpus grades:
  - the current Claude-Code skill now (``CCSkillAdapter`` — driven by the operator/SDK),
  - the future standalone Go binary later (``BinaryAdapter``),
without changing anything downstream. That is how the migration gets a regression
oracle: run both adapters over the corpus, compare scorecards.
"""

from __future__ import annotations

import subprocess
from typing import Protocol

from sec_overlay.models import Finding, FindingStatus
from sec_overlay.workspace import Workspace, read_findings


class ScanAdapter(Protocol):
    """A driver that scans a repo and yields the harness's reportable findings."""

    def scan(self, repo_path: str, workspace: Workspace) -> list[Finding]:
        ...


def reportable(ws: Workspace) -> list[Finding]:
    """Read confirmed/fixed findings from a workspace (what the benchmark grades)."""
    return [f for f in read_findings(ws)
            if f.status in (FindingStatus.CONFIRMED, FindingStatus.FIXED)]


class WorkspaceAdapter:
    """Adapter for an ALREADY-scanned workspace — reads its findings, runs no scan.

    Use when a scan already ran (e.g. re-tally a prior run, or grade findings the
    operator produced by driving the CC skill by hand into this workspace).
    """

    def __init__(self, workspace_for):
        # workspace_for: callable(repo_path) -> Workspace with existing findings
        self._workspace_for = workspace_for

    def scan(self, repo_path: str, workspace: Workspace) -> list[Finding]:
        return reportable(self._workspace_for(repo_path))


class BinaryAdapter:
    """Adapter that shells out to a standalone scanner binary (the Go migration).

    The binary must accept ``<argv> --target <repo> --workspace <ws>`` and write the
    standard ``findings/*.json`` into the workspace; we then read the reportable set.
    """

    def __init__(self, argv: list[str], *, runner=subprocess.run):
        self.argv = argv
        self.runner = runner

    def scan(self, repo_path: str, workspace: Workspace) -> list[Finding]:
        workspace.ensure()
        self.runner([*self.argv, "--target", str(repo_path),
                     "--workspace", str(workspace.root)], check=False)
        return reportable(workspace)


class CCSkillAdapter:
    """Drive the Claude-Code skill headlessly, then grade the workspace (REQ-M2).

    Wraps a :class:`bench.driver.HeadlessDriver` (``claude -p`` shelled like a SAST
    binary). A driver failure yields ``[]`` for that target — recorded on
    ``driver.failures``, never fabricated. ``bench.run``'s findings cache makes runs
    resumable per target.
    """

    def __init__(self, driver=None):
        if driver is None:
            from bench.driver import HeadlessDriver

            driver = HeadlessDriver()
        self.driver = driver

    def scan(self, repo_path: str, workspace: Workspace) -> list[Finding]:
        workspace.ensure()
        if not self.driver.run(repo_path, workspace.root):
            return []
        return reportable(workspace)
