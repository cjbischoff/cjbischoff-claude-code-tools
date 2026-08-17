"""Scope incremental passes to changed files via git."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

_REF_RE = re.compile(r"^(?!-)[A-Za-z0-9._/~-]+$")


def validate_ref(ref: str) -> str:
    """Validate a git ref against a strict allowlist before it reaches a git command.

    Rejects a ref starting with ``-`` (git would parse it as an option — the
    argument-injection vector D-06/D-07 close), an empty ref (the anchored
    one-or-more pattern already rejects it), and anything outside
    ``[A-Za-z0-9._/~-]`` — which excludes every shell metacharacter while still
    allowing ``HEAD~1``-style ancestor refs.

    Args:
        ref: The candidate ref (branch, tag, or SHA).

    Returns:
        The validated ref, unchanged.

    Raises:
        ValueError: If ``ref`` fails the allowlist.
    """
    if not _REF_RE.match(ref):
        raise ValueError(f"invalid ref: {ref!r}")
    return ref


def resolve_ref_sha(ref: str, *, runner=subprocess.run) -> str:
    """Resolve a validated ref to its full commit SHA.

    Args:
        ref: A ref, validated via :func:`validate_ref` before use.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The stripped SHA `git rev-parse --verify` resolves ``ref`` to.
    """
    validate_ref(ref)
    completed = runner(
        ["git", "rev-parse", "--verify", ref], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip()


@dataclass(frozen=True)
class ChangedFile:
    """One changed-file record from ``git diff --name-status``."""

    path: str
    status: str
    old_path: str | None = None


def changed_file_records(base: str, head: str, *, runner=subprocess.run) -> list[ChangedFile]:
    """Return changed-file records (status + path) between two resolved SHAs.

    Args:
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        One :class:`ChangedFile` per changed-file line; a rename carries
        ``old_path``.
    """
    completed = runner(
        ["git", "diff", "--name-status", base, head, "--"],
        capture_output=True, text=True, check=False,
    )
    records: list[ChangedFile] = []
    for raw_line in completed.stdout.splitlines():
        if not raw_line.strip():
            continue
        columns = raw_line.split("\t")
        kind = columns[0][0]
        if kind in ("R", "C") and len(columns) == 3:
            records.append(ChangedFile(path=columns[2], status=kind, old_path=columns[1]))
        else:
            records.append(ChangedFile(path=columns[1], status=kind))
    return records


def file_diff_line_count(path: str, base: str, head: str, *, runner=subprocess.run) -> int:
    """Return the diff body line count for one path — a size proxy for the exclusion cap.

    Args:
        path: Repo-relative file path.
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The number of lines in the `git diff --unified=0` output for ``path``.
    """
    completed = runner(
        ["git", "diff", "--unified=0", base, head, "--", path],
        capture_output=True, text=True, check=False,
    )
    return len(completed.stdout.splitlines())


def binary_paths(base: str, head: str, *, runner=subprocess.run) -> frozenset[str]:
    """Return the paths git reports as binary between two resolved SHAs.

    Args:
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        Repo-relative paths whose `git diff --numstat` line reads ``-\t-`` (git's
        binary marker).
    """
    completed = runner(
        ["git", "diff", "--numstat", base, head, "--"],
        capture_output=True, text=True, check=False,
    )
    paths: set[str] = set()
    for raw_line in completed.stdout.splitlines():
        if not raw_line.strip():
            continue
        columns = raw_line.split("\t")
        if len(columns) == 3 and columns[0] == "-" and columns[1] == "-":
            paths.add(columns[2])
    return frozenset(paths)


def file_diff_text(path: str, base: str, head: str, *, runner=subprocess.run) -> str:
    """Return the unified diff text for one path between two resolved SHAs.

    Args:
        path: Repo-relative file path.
        base: Base revision, already resolved to a SHA.
        head: Head revision, already resolved to a SHA.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The `git diff --unified=3` output text (empty string if no diff).
    """
    completed = runner(
        ["git", "diff", "--unified=3", base, head, "--", path],
        capture_output=True, text=True, check=False,
    )
    return completed.stdout


def changed_files(base: str, head: str = "HEAD", *, runner=subprocess.run) -> list[str]:
    """Return files changed between two revisions.

    Args:
        base: Base revision (e.g. the prior pass's pinned SHA).
        head: Head revision (default ``HEAD``).
        runner: Injectable subprocess runner (for testing).

    Returns:
        Repo-relative changed file paths.
    """
    completed = runner(
        # `--` separates revisions from paths so a ref that looks like a path can't be misparsed.
        ["git", "diff", "--name-only", base, head, "--"], capture_output=True, text=True, check=False
    )
    return [line for line in completed.stdout.splitlines() if line.strip()]


def head_sha(*, runner=subprocess.run) -> str:
    """Return the current ``HEAD`` commit SHA.

    Args:
        runner: Injectable subprocess runner (for testing).

    Returns:
        The stripped HEAD SHA.
    """
    completed = runner(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
    return completed.stdout.strip()
