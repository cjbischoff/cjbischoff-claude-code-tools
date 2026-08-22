"""Write shipped review findings as diff-anchored comment payloads (OUT-01).

`review_comments.json` is the artifact a Result Management System or a
comment-posting client reads to place one comment per shipped finding on the
diff it was found in, alongside the coverage manifest that says whether the
run producing it was complete.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sec_overlay.models import Finding
from sec_overlay.workspace import Workspace, _atomic_write

DEFAULT_SIDE = "RIGHT"
COMMENTS_FILENAME = "review_comments.json"


@dataclass(frozen=True)
class DiffComment:
    """One diff-anchored comment payload for a shipped review finding."""

    path: str
    line: int
    side: str
    existing_code: str
    content: str


def comment_from_finding(finding: Finding) -> DiffComment:
    """Map a shipped review finding onto its diff comment payload.

    Args:
        finding: A finding that survived the gate chain; `line` is the
            position-gate-confirmed line and `evidence` is the harness-derived
            real file text at that line, never a model-supplied snippet.

    Returns:
        The `DiffComment` for this finding.
    """
    return DiffComment(
        path=finding.file,
        line=finding.line,
        side=DEFAULT_SIDE,
        existing_code=finding.evidence,
        content=finding.message,
    )


def write_review_comments(
    ws: Workspace, comments: Sequence[DiffComment], manifest_dict: dict
) -> Path:
    """Write `artifacts/review_comments.json`, atomically, exactly once per run.

    Args:
        ws: Workspace whose `artifacts/` directory receives the file.
        comments: One `DiffComment` per shipped review finding.
        manifest_dict: `CoverageManifest.to_dict()`'s output, embedded verbatim
            so a consumer can tell a complete run's comments from a partial
            one without inferring it from the file's mere presence.

    Returns:
        The path written.
    """
    payload = {
        "comments": [
            {
                "path": c.path,
                "line": c.line,
                "side": c.side,
                "existing_code": c.existing_code,
                "content": c.content,
            }
            for c in comments
        ],
        "coverage_manifest": manifest_dict,
    }
    path = ws.artifacts / COMMENTS_FILENAME
    _atomic_write(path, json.dumps(payload, indent=2))
    return path
