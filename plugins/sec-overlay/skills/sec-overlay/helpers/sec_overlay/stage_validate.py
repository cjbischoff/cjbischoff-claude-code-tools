"""Per-stage output validation + the in-session repair contract (Bucket C1, from audit).

audit's highest-leverage idea: validate EVERY structured stage output against a schema, and
on failure feed the exact errors back to the SAME subagent for a repair turn (re-emit only the
broken fields). sec-overlay validated only findings; this dispatches the same discipline over
the other structured stage outputs, reusing the validators that already exist.

Usage in the orchestrator (documented in SKILL.md): after a stage emits JSON, call
``validate_stage(stage, obj)``; if it returns errors, re-prompt the subagent with
``repair_prompt(stage, obj, errors)`` and re-validate (bounded attempts).
"""

from __future__ import annotations

import json

from sec_overlay.context import Context, cited_source_docs
from sec_overlay.coverage_ledger import validate_coverage_ledger
from sec_overlay.discovery_ledger import validate_discovery_ledger
from sec_overlay.profile import validate_profile
from sec_overlay.reachability import validate_reachability


def _validate_runtime_test(obj: object) -> list[str]:
    if not isinstance(obj, dict):
        return ["runtime_test must be an object"]
    errs = []
    if not obj.get("objective"):
        errs.append("runtime_test.objective is required")
    if "payloads" in obj and not isinstance(obj["payloads"], list):
        errs.append("runtime_test.payloads must be a list")
    return errs


def _validate_context(obj: dict) -> list[str]:
    try:
        errors = Context.from_dict(obj).validate()
    except (TypeError, KeyError, AttributeError) as e:
        return [f"context is not a valid Context document: {e}"]
    prov = obj.get("provenance", {}) if isinstance(obj, dict) else {}
    read = set(prov.get("docs_read", []) or [])
    for doc in sorted(cited_source_docs(obj) - read):
        errors.append(f"context: source_doc {doc!r} cited but absent from provenance.docs_read")
    return errors


# stage name -> validator(obj) -> error list. An unregistered stage is a hard error
# (validate_stage raises) — see ISSUE-034.
_VALIDATORS = {
    "recon": validate_profile,
    "scan-profile": validate_profile,
    "context": _validate_context,
    "reachability": validate_reachability,
    "runtime_test": _validate_runtime_test,
    "discovery-ledger": validate_discovery_ledger,
    "coverage-ledger": validate_coverage_ledger,
}


def validate_stage(stage: str, obj: object) -> list[str]:
    """Validate a stage's structured output; empty list == valid.

    Raises:
        ValueError: ``stage`` has no registered validator — a silent pass here
            masked mis-named stages (ISSUE-034), so it is now an error.
    """
    fn = _VALIDATORS.get(stage)
    if fn is None:
        raise ValueError(f"validate_stage: no validator for stage {stage!r}")
    return fn(obj)


def repair_prompt(stage: str, obj: object, errors: list[str]) -> str:
    """Build the in-session repair turn: quote the exact errors, ask to re-emit only fixes."""
    return (
        f"Your `{stage}` output failed schema validation with these errors:\n"
        + "\n".join(f"  - {e}" for e in errors)
        + "\n\nRe-emit ONLY a corrected JSON object fixing exactly these fields; keep everything "
        "else identical. Current output:\n```json\n"
        + json.dumps(obj, indent=2, default=str)
        + "\n```"
    )
