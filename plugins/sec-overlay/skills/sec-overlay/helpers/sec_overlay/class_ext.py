"""Check class-extension coverage; a coarse file counts for its aliased keys.

Investigate/patch fall back to the base prompt for an uncovered class; this
records the gap so coverage is never silently lost. Authoring the missing
files is a spec-9 follow-on.
"""

from __future__ import annotations

from pathlib import Path

# canonical key -> the coarse extension file that covers it (user-approved alias map)
_ALIASES: dict[str, str] = {"sqli": "injection", "cmdi": "injection", "xss": "injection"}


def class_extension_status(classes, classes_dir) -> dict:
    """Report which classes have an extension file and which are gaps.

    Args:
        classes: Attack-class keys dispatched this run.
        classes_dir: ``agents/classes`` directory.

    Returns:
        ``{"present": {cls: filename}, "gaps": [gap dict]}``. A class is present
        if ``<cls>.md`` exists or its alias file exists.
    """
    root = Path(classes_dir)
    present: dict[str, str] = {}
    gaps: list[dict] = []
    for cls in classes:
        stem = _ALIASES.get(cls, cls)
        fname = f"{stem}.md"
        if (root / fname).exists():
            present[cls] = fname
        else:
            gaps.append({
                "id": cls,
                "disposition": "needs_follow_up",
                "reason": f"no class-extension file for {cls!r}; investigate/patch use the base prompt",
                "next_step": f"author agents/classes/{cls}.md (spec §9 follow-on)",
            })
    return {"present": present, "gaps": gaps}
