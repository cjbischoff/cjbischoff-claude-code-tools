"""Scope incremental passes to changed files via git."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

_REF_RE = re.compile(r"^(?!-)[A-Za-z0-9._/~^-]+$")


def validate_ref(ref: str) -> str:
    """Validate a git ref against a strict allowlist before it reaches a git command.

    Rejects a ref starting with ``-`` (git would parse it as an option — the
    argument-injection vector D-06/D-07 close), an empty ref (the anchored
    one-or-more pattern already rejects it), and anything outside
    ``[A-Za-z0-9._/~^-]`` — which excludes every shell metacharacter while still
    allowing ``HEAD~1`` and ``HEAD^``-style ancestor refs (``^`` is safe in the
    list-form git call, which never touches a shell).

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

    Raises:
        ValueError: ``ref`` is syntactically valid but does not resolve (`git
            rev-parse --verify` exits non-zero) — a nonexistent branch/tag/SHA.
    """
    validate_ref(ref)
    completed = runner(
        ["git", "rev-parse", "--verify", ref], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(f"unresolvable ref: {ref!r}")
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
        ["git", "-c", "core.quotePath=false", "diff", "--name-status", base, head, "--"],
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


def dirty_file_records(*, runner=subprocess.run) -> list[ChangedFile]:
    """Return changed-file records for the working tree — staged, unstaged, and untracked.

    Backs ``--workspace-dirty`` review: files with uncommitted edits, against no ref pair.
    Parses ``git status --porcelain`` (XY status + path); an untracked ``??`` line becomes a
    ``"?"`` record (distinct so the caller reads its whole content, not a diff against HEAD),
    a rename ``R  old -> new`` carries ``old_path``.

    Args:
        runner: Injectable subprocess runner (for testing); the caller binds ``cwd``.

    Returns:
        One :class:`ChangedFile` per porcelain line, deduplicated by path (a file staged and
        then edited again reports one XY line, so no dedup is needed across lines).
    """
    completed = runner(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=False,
    )
    records: list[ChangedFile] = []
    for raw_line in completed.stdout.splitlines():
        if not raw_line.strip():
            continue
        xy, rest = raw_line[:2], raw_line[3:]
        if xy == "??":
            records.append(ChangedFile(path=rest, status="?"))
            continue
        kind = xy[0] if xy[0] != " " else xy[1]
        if kind in ("R", "C") and " -> " in rest:
            old_path, new_path = rest.split(" -> ", 1)
            records.append(ChangedFile(path=new_path, status=kind, old_path=old_path))
        else:
            records.append(ChangedFile(path=rest, status=kind))
    return records


def _diff_revs(base: str, head: str | None) -> list[str]:
    """Return the revision arguments for a git diff.

    ``head=None`` omits the second revision so git diffs ``base`` against the
    working tree (staged + unstaged) — the ``--workspace-dirty`` scope. A string
    ``head`` diffs the two resolved revisions.
    """
    return [base] if head is None else [base, head]


def file_diff_line_count(path: str, base: str, head: str | None, *, runner=subprocess.run) -> int:
    """Return the diff body line count for one path — a size proxy for the exclusion cap.

    Args:
        path: Repo-relative file path.
        base: Base revision, already resolved to a SHA.
        head: Head revision (resolved SHA), or ``None`` to diff ``base`` against
            the working tree.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The number of lines in the `git diff --unified=0` output for ``path``.
    """
    completed = runner(
        ["git", "diff", "--unified=0", *_diff_revs(base, head), "--", path],
        capture_output=True, text=True, check=False,
    )
    return len(completed.stdout.splitlines())


def binary_paths(base: str, head: str | None, *, runner=subprocess.run) -> frozenset[str]:
    """Return the paths git reports as binary between two resolved SHAs.

    Args:
        base: Base revision, already resolved to a SHA.
        head: Head revision (resolved SHA), or ``None`` to diff ``base`` against
            the working tree.
        runner: Injectable subprocess runner (for testing).

    Returns:
        Repo-relative paths whose `git diff --numstat` line reads ``-\t-`` (git's
        binary marker).
    """
    completed = runner(
        ["git", "diff", "--numstat", *_diff_revs(base, head), "--"],
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


def file_diff_text(path: str, base: str, head: str | None, *, runner=subprocess.run) -> str:
    """Return the unified diff text for one path between two resolved SHAs.

    Args:
        path: Repo-relative file path.
        base: Base revision, already resolved to a SHA.
        head: Head revision (resolved SHA), or ``None`` to diff ``base`` against
            the working tree.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The `git diff --unified=3` output text (empty string if no diff).
    """
    completed = runner(
        ["git", "diff", "--unified=3", *_diff_revs(base, head), "--", path],
        capture_output=True, text=True, check=False,
    )
    return completed.stdout


def file_text_at_ref(path: str, ref: str, *, runner=subprocess.run) -> str:
    """Return `path`'s whole file text at `ref` — the real content, not a claim about it.

    Backs the review-mode position gate's whole-file rung (`positioning.resolve_position`):
    a finding's claimed snippet is confirmed against this text, never trusted from the
    model that reported it.

    Args:
        path: Repo-relative file path.
        ref: A resolved SHA (or ref) to read the file at.
        runner: Injectable subprocess runner (for testing).

    Returns:
        The file's full text at `ref`, or `""` if `git show` fails — e.g. the path did not
        exist at that ref.
    """
    completed = runner(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=False)
    return completed.stdout if completed.returncode == 0 else ""


def changed_files(base: str, head: str = "HEAD", *, runner=subprocess.run) -> list[str]:
    """Return files changed between two revisions.

    Args:
        base: Base revision (e.g. the prior pass's pinned SHA).
        head: Head revision (default ``HEAD``).
        runner: Injectable subprocess runner (for testing).

    Returns:
        Repo-relative changed file paths.

    Raises:
        ValueError: The diff failed. An empty result would read as "nothing changed".
    """
    completed = runner(
        # `--` separates revisions from paths so a ref that looks like a path can't be misparsed.
        ["git", "-c", "core.quotePath=false", "diff", "--name-only", base, head, "--"],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip()
        raise ValueError(
            f"git diff --name-only failed between {base} and {head}"
            + (f": {detail}" if detail else "")
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
