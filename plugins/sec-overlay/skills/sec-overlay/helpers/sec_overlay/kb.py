"""Knowledge-base (workspace/kb) file paths and profile read/write helpers."""

from __future__ import annotations

from pathlib import Path

from sec_overlay.profile import ScanProfile, load_profile, save_profile
from sec_overlay.workspace import Workspace


def profile_path(ws: Workspace) -> Path:
    """Path to the scan profile within the KB."""
    return ws.kb / "scan-profile.json"


def arch_dir(ws: Workspace) -> Path:
    """Directory holding the architecture tree (arc42 doc, diagrams, entity notes)."""
    return ws.root / "architecture"


def arc42_path(ws: Workspace) -> Path:
    """Path to the arc42-structured architecture document."""
    return arch_dir(ws) / "arc42.md"


def container_diagram_path(ws: Workspace) -> Path:
    """Path to the container-level architecture diagram (mermaid)."""
    return arch_dir(ws) / "container-diagram.mmd"


def threat_dir(ws: Workspace) -> Path:
    """Directory holding the threat-model tree (threat model doc, DFD, attack sequences)."""
    return ws.root / "threat-model"


def threat_model_path(ws: Workspace) -> Path:
    """Path to the threat model document."""
    return threat_dir(ws) / "threat-model.md"


def dfd_path(ws: Workspace) -> Path:
    """Path to the data-flow diagram (mermaid)."""
    return threat_dir(ws) / "dfd.mmd"


def entities_dir(ws: Workspace) -> Path:
    """Directory holding per-component entity notes."""
    return ws.kb / "entities"


def write_profile(ws: Workspace, profile: ScanProfile) -> None:
    """Persist a scan profile into the KB.

    Args:
        ws: Target workspace.
        profile: Profile to write.
    """
    ws.kb.mkdir(parents=True, exist_ok=True)
    save_profile(profile_path(ws), profile)


def read_profile(ws: Workspace) -> ScanProfile:
    """Load and validate the scan profile from the KB.

    Args:
        ws: Source workspace.

    Returns:
        The parsed :class:`ScanProfile`.
    """
    return load_profile(profile_path(ws))


def kb_status(ws: Workspace) -> dict[str, bool]:
    """Report which KB artifacts exist.

    Args:
        ws: Workspace to inspect.

    Returns:
        Presence flags for ``profile``, ``architecture``, ``threat_model``.
    """
    return {
        "profile": profile_path(ws).exists(),
        "architecture": arc42_path(ws).exists(),
        "threat_model": threat_model_path(ws).exists(),
    }
