"""Postflight: distill a finished scan into durable cross-scan context (Phase C2).

Preflight context is volatile (regenerated each scan); postflight is what STICKS. It
writes ``kb/prior_context.json`` (accretes across scans, drift-keyed by SHA) that the
NEXT scan's context-ingest reads as higher-trust prior context: confirmed findings,
rejected-with-rationale (so we don't re-litigate settled non-findings), and a short
codebase security profile. Our own conclusions are higher-trust than repo docs, but
still re-validated on drift (changed files re-open; unchanged files persist).
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.context import Context, ContextItem, prior_context_path
from sec_overlay.diffscope import changed_files as changed_files_between
from sec_overlay.diffscope import validate_ref
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.workspace import Workspace, read_findings


def _rejection_rationale(f: Finding) -> str:
    """Best rationale for a rejected finding, from its history events."""
    for h in reversed(f.history):
        ev = str(h.get("event", ""))
        if "reject" in ev:
            return h.get("reason") or ev
    return (f.message or "rejected")[:160]


def build_prior_context(ws: Workspace, sha: str | None) -> Context:
    """Build the durable prior-context from a workspace's settled findings.

    Args:
        ws: The finished scan's workspace.
        sha: The scanned SHA (stamped into provenance + each item's ``where`` note).

    Returns:
        A :class:`sec_overlay.context.Context` of ``prior-scan``-trust items.
    """
    items: list[ContextItem] = []
    for f in read_findings(ws):
        fp = f.fingerprint or f"{f.file}:{f.line}:{f.cls}"
        if f.status in (FindingStatus.CONFIRMED, FindingStatus.FIXED):
            items.append(ContextItem(
                kind="prior_finding", trust="prior-scan", cls=f.cls,
                text=f"{f.status.value} {f.cls}: {(f.message or '')[:120]} [fp:{fp}]",
                where=f"{f.file}:{f.line}", source_doc=f"scan@{sha}"))
        elif f.status is FindingStatus.REJECTED:
            items.append(ContextItem(
                kind="note", trust="prior-scan", cls=f.cls,
                text=f"settled non-finding ({f.cls}): {_rejection_rationale(f)} "
                     f"— do not re-litigate unless this file changed [fp:{fp}]",
                where=f"{f.file}:{f.line}", source_doc=f"scan@{sha}"))
    return Context(items=items, provenance={"sha": sha, "kind": "postflight"})


def _file_of(where: str) -> str:
    """Return the file part of a ``ContextItem.where`` note, base-normalized.

    ``Finding.file`` is repo-relative by contract (``models.py``), and ``git diff
    --name-only`` returns top-level-relative paths, so both sides share a base. A
    leading ``./`` or ``/`` is the only remaining difference, and this strips it.

    Args:
        where: A ``ContextItem.where`` value, normally ``"<file>:<line>"``.

    Returns:
        The file path with any leading ``./`` or ``/`` removed.
    """
    return where.split(":", 1)[0].removeprefix("./").lstrip("/")


def _merge(old: Context, new: Context, changed_files: set[str]) -> Context:
    """Merge new postflight over old prior-context, drift-aware.

    Old items whose file is in ``changed_files`` are dropped (re-opened this pass); the
    rest are kept. New items are appended (deduped by (kind, where, text-prefix)).
    """
    def key(i: ContextItem):
        return (i.kind, i.where, i.text[:60])
    drift = {_file_of(f) for f in changed_files}
    kept = [i for i in old.items if _file_of(i.where) not in drift]
    seen = {key(i) for i in kept}
    for i in new.items:
        if key(i) not in seen:
            kept.append(i)
            seen.add(key(i))
    return Context(items=kept, provenance=new.provenance)


def _drift_since(old: Context, sha: str | None, target: str, runner) -> set[str]:
    """Return the files changed between the prior pass's SHA and this pass's SHA.

    Args:
        old: The prior context, whose provenance holds the last postflight's SHA.
        sha: This pass's SHA; ``None`` falls back to ``HEAD``.
        target: The audited repository, bound as the git working directory.
        runner: Injectable process runner.

    Returns:
        Repo-relative changed paths, or an empty set when the prior context carries
        no SHA — the first pass has nothing to drift against.
    """
    base = str(old.provenance.get("sha") or "")
    if not base:
        return set()
    validate_ref(base)
    head = validate_ref(sha) if sha else "HEAD"

    def git(cmd, **kwargs):
        return runner(cmd, cwd=target, **kwargs)

    return set(changed_files_between(base, head, runner=git))


def run_postflight(
    ws: Workspace,
    sha: str | None,
    *,
    changed_files: set[str] | None = None,
    target: str | None = None,
    runner=subprocess.run,
) -> int:
    """Distill the scan and merge into the durable prior_context.json.

    Args:
        ws: Finished scan workspace.
        sha: Scanned SHA.
        changed_files: Repo-relative files changed since the last postflight (drift);
            old conclusions on these are dropped so the next scan re-examines them.
            Wins over ``target`` when both are given.
        target: The audited repository. With no explicit ``changed_files``, the drift
            set is computed from it against the prior context's SHA.
        runner: Injectable process runner for the git call.

    Returns:
        Total item count in the merged prior context.
    """
    new = build_prior_context(ws, sha)
    p = prior_context_path(ws)
    old = Context.from_dict(json.loads(p.read_text())) if p.exists() else Context()
    if changed_files is None:
        changed_files = _drift_since(old, sha, target, runner) if target else set()
    merged = _merge(old, new, changed_files)
    ws.kb.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(merged.to_dict(), indent=2))
    record_stage(ws, "postflight")
    return len(merged.items)


def main(argv: list[str] | None = None) -> int:
    """CLI: run postflight distillation for a workspace."""
    ap = argparse.ArgumentParser(prog="sec-overlay-postflight")
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--sha", default=None)
    ap.add_argument("--target", default=None,
                    help="Audited repository; enables the drift-set computation.")
    args = ap.parse_args(argv)
    n = run_postflight(Workspace(Path(args.workspace)), args.sha, target=args.target)
    print(f"prior_context.json now holds {n} item(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
