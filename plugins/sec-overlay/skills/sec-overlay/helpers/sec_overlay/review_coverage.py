"""Per-file review-coverage tracking and the terminal manifest seal (D-01, D-03, D-04).

Never touches the shipped `coverage.py` — that module is a separate, frozen milestone
contract (D-01). Only `CoverageManifest` edits the coverage-manifest JSON (D-03); the seal
is a 2-state terminal (`complete`/`partial`), not the 4-state enum an earlier tool used (D-04).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sec_overlay.workspace import _atomic_write

MANIFEST_FILENAME = "coverage_manifest.json"
MANIFEST_VERSION = 1
STATES: frozenset[str] = frozenset({"pending", "in_review", "done", "failed"})
SEALS: frozenset[str] = frozenset({"complete", "partial"})

# D-03: one table gates every transition, so "illegal transitions raise" is a property
# of the module, not of four separate call sites.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"in_review", "failed"}),
    "in_review": frozenset({"done", "failed"}),
    "done": frozenset(),
    "failed": frozenset(),
}


class CoverageTransitionError(RuntimeError):
    """Raised for an unknown path or an illegal state transition."""


@dataclass
class FileCoverage:
    """One reviewable file's coverage state."""

    path: str
    state: str = "pending"
    note: str | None = None


class CoverageManifest:
    """Tracks per-file review coverage across a run and its terminal seal.

    Persists to ``path`` after every transition, reusing
    :func:`sec_overlay.workspace._atomic_write` for a crash-safe write (mkstemp
    in the same directory, then ``os.replace``).
    """

    def __init__(self, base_sha: str, head_sha: str, path: Path) -> None:
        """Start a manifest for one run.

        Args:
            base_sha: Resolved base SHA for this run.
            head_sha: Resolved head SHA for this run.
            path: File the manifest persists to (``ws.artifacts / MANIFEST_FILENAME``).
        """
        self.version = MANIFEST_VERSION
        self.base_sha = base_sha
        self.head_sha = head_sha
        self.path = path
        self._seal: str | None = None
        self.files: list[FileCoverage] = []

    def entries(self) -> list[FileCoverage]:
        """Return every entry in first-seen order."""
        return list(self.files)

    def _find(self, file_path: str) -> FileCoverage:
        for entry in self.files:
            if entry.path == file_path:
                return entry
        raise CoverageTransitionError(f"unknown path: {file_path}")

    def add(self, file_path: str) -> None:
        """Register a reviewable file at ``pending``.

        Raises:
            CoverageTransitionError: If ``file_path`` was already added.
        """
        if any(entry.path == file_path for entry in self.files):
            raise CoverageTransitionError(f"already added: {file_path}")
        self.files.append(FileCoverage(path=file_path))
        self._persist()

    def start(self, file_path: str) -> None:
        """Transition ``pending`` to ``in_review``."""
        self._transition(file_path, "in_review")

    def finish(self, file_path: str) -> None:
        """Transition ``in_review`` to ``done``."""
        self._transition(file_path, "done")

    def fail(self, file_path: str, note: str | None = None) -> None:
        """Transition ``pending`` or ``in_review`` to ``failed``, recording ``note``."""
        self._transition(file_path, "failed", note=note)

    def _transition(self, file_path: str, to_state: str, *, note: str | None = None) -> None:
        entry = self._find(file_path)
        if to_state not in _ALLOWED_TRANSITIONS[entry.state]:
            raise CoverageTransitionError(
                f"cannot move {file_path} from {entry.state!r} to {to_state!r}"
            )
        entry.state = to_state
        if note is not None:
            entry.note = note
        self._persist()

    def failed_entries(self) -> list[FileCoverage]:
        """Return every entry currently in the ``failed`` state."""
        return [entry for entry in self.files if entry.state == "failed"]

    def seal(self) -> str:
        """Set, persist, and return the terminal seal.

        A ``pending``/``in_review`` entry means the run never reached a terminal
        outcome for that file, so it raises rather than sealing (T-02-05) — the
        run must never claim coverage it did not perform.

        Returns:
            ``"complete"`` when every entry is ``done``; ``"partial"`` when every
            entry is ``done`` or ``failed`` with at least one ``failed``.

        Raises:
            CoverageTransitionError: If any entry is still ``pending`` or
                ``in_review``, or if the manifest has no entries.
        """
        if not self.files:
            raise CoverageTransitionError("cannot seal: manifest has no entries")
        unfinished = [entry.path for entry in self.files if entry.state in {"pending", "in_review"}]
        if unfinished:
            raise CoverageTransitionError(f"cannot seal: unfinished entries remain: {unfinished}")
        self._seal = "complete" if all(entry.state == "done" for entry in self.files) else "partial"
        self._persist()
        return self._seal

    def to_dict(self) -> dict:
        """Serialize to the Task-1-resolved manifest shape."""
        return {
            "version": self.version,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "seal": self._seal,
            "files": [asdict(entry) for entry in self.files],
        }

    def _persist(self) -> None:
        _atomic_write(self.path, json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> CoverageManifest:
        """Load a manifest from disk.

        Args:
            path: The manifest file to read.

        Returns:
            The reconstructed :class:`CoverageManifest`.
        """
        data = json.loads(path.read_text())
        manifest = cls(base_sha=data["base_sha"], head_sha=data["head_sha"], path=path)
        manifest.version = data.get("version", 1)
        manifest._seal = data.get("seal")
        manifest.files = [
            FileCoverage(path=entry["path"], state=entry["state"], note=entry.get("note"))
            for entry in data.get("files", [])
        ]
        return manifest
