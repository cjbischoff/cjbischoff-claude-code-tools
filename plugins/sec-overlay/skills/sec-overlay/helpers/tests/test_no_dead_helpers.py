"""REQ-48: a public helper with no caller must be on a list, and a list entry must stay dead.

The scan is AST-precise. A name counts as referenced when it appears as a loaded
``Name``, an ``Attribute`` attribute, or an ``ImportFrom`` name anywhere in non-test
``sec_overlay/`` or ``bench/`` code. A docstring mention does not count, and neither
does a parameter of the same name.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

HELPERS = Path(__file__).resolve().parents[1]
SKILL_ROOT = HELPERS.parent

# Unreferenced at plugin 2.1.11. Each entry is a real gap, not a false positive.
# A name added here after this plan must carry its own one-line reason.
DEAD_ALLOWLIST: dict[str, str] = {
    "astgrep.py:astgrep_available": "unreferenced at 2.1.11",
    "calibrate.py:calibrate_score": "unreferenced at 2.1.11",
    "class_ext.py:class_extension_status": "unreferenced at 2.1.11",
    "codeguard.py:default_codeguard_dir": "unreferenced at 2.1.11",
    "codeguard.py:load_rules": "unreferenced at 2.1.11",
    "context.py:doc_coverage": "unreferenced at 2.1.11",
    "coverage_guide.py:should_stop": "unreferenced at 2.1.11",
    "crypto_policy.py:load_policy": "unreferenced at 2.1.11",
    "custom_checks.py:custom_check_classes": "unreferenced at 2.1.11",
    "diffhunks.py:added_line_numbers": "unreferenced at 2.1.11",
    "diffhunks.py:line_in_hunk": "unreferenced at 2.1.11",
    "envelope.py:attribution_banner": "unreferenced at 2.1.11",
    "fix_disposition.py:compute_tier": "unreferenced at 2.1.11",
    "gates.py:run_gates": "unreferenced at 2.1.11",
    "githist.py:files_in_commit": "unreferenced at 2.1.11",
    "graph.py:attacker_controls": "unreferenced at 2.1.11; adjacent finding A-4",
    "graph.py:build_and_write_tier1": "unreferenced at 2.1.11; adjacent finding A-4",
    "graph.py:entry_point_nodes": "unreferenced at 2.1.11; adjacent finding A-4",
    "graph.py:is_unresolvable": "unreferenced at 2.1.11; adjacent finding A-4",
    "graph.py:merge_tier2": "unreferenced at 2.1.11; adjacent finding A-4",
    "kb.py:kb_status": "unreferenced at 2.1.11",
    "kb.py:write_profile": "unreferenced at 2.1.11",
    "parse.py:fallback_list": "unreferenced at 2.1.11",
    "phase_gate.py:attack_surface_gate": "unreferenced at 2.1.11",
    "phase_gate.py:claims_from_markdown": "unreferenced at 2.1.11",
    "phase_gate.py:ref_resolves": "unreferenced at 2.1.11",
    "prove.py:loopback_collector": "unreferenced at 2.1.11; adjacent finding A-3",
    "prove.py:run_prove": "unreferenced at 2.1.11; adjacent finding A-3",
    "reachability.py:blocker_of": "unreferenced at 2.1.11",
    "route_control.py:build_route_control_table": "unreferenced at 2.1.11",
    "route_control.py:check_architecture_controls": "unreferenced at 2.1.11",
    "route_control.py:check_recon_routes": "unreferenced at 2.1.11",
    "route_control.py:check_threat_entrypoints": "unreferenced at 2.1.11",
    "rule_matcher.py:build_guided_context": "unreferenced at 2.1.11",
    "rule_matcher.py:match_function": "unreferenced at 2.1.11",
    "run.py:infer_role": "unreferenced at 2.1.11",
    "run.py:synthesize_manifest": "unreferenced at 2.1.11",
}

# No Python importer, but a prompt names the function and runs it in a shell command.
PROMPT_ONLY: dict[str, str] = {
    "campaign.py:carry_forward": "SKILL.md",
    "campaign.py:pass_report": "SKILL.md",
    "campaign.py:salvage_partial": "SKILL.md",
    "context.py:control_findings": "agents/context-ingest.md",
    "context.py:control_worklist": "SKILL.md",
    "context.py:hunt_rows": "SKILL.md",
    "context.py:leads": "agents/redteam.md",
    "context.py:manual_review_findings": "SKILL.md",
    "context.py:save": "agents/context-ingest.md",
    "custom_checks.py:custom_check_instructions": "SKILL.md",
    "custom_checks.py:discover_custom_checks": "SKILL.md",
    "custom_checks.py:merge_custom_check_classes": "SKILL.md",
    "detection_coverage.py:generate": "agents/tune-config.md",
    "githist.py:security_fix_commits": "agents/recon.md",
    "novelty.py:upstream_status": "SKILL.md",
    "partition.py:must_investigate": "SKILL.md",
    "phase_gate.py:claims_from_context": "SKILL.md",
    "phase_gate.py:claims_from_profile": "SKILL.md",
    "phase_gate.py:recall_claims": "agents/README.md",
    "phase_gate.py:run_phase_checks": "SKILL.md",
    "reflection.py:validate_verdict": "agents/README.md",
    "rule_gaps.py:emit_semgrep_rule": "SKILL.md",
    "run.py:advance": "SKILL.md",
    "run.py:drive": "agents/classes/prompt-injection.md",
    "scanscope.py:load_scope": "agents/context-ingest.md",
    "stage_validate.py:repair_prompt": "SKILL.md",
    "stage_validate.py:validate_stage": "SKILL.md",
    "tuning.py:gap_report": "SKILL.md",
    "tuning.py:is_improvement": "SKILL.md",
    "tuning.py:signal_snapshot": "SKILL.md",
    "variant.py:variant_seeds": "agents/variant-hunt.md",
    "workspace.py:record_agent_return": "SKILL.md",
}


def _public_functions() -> dict[str, str]:
    """Map ``"<module>.py:<function>"`` to the module file name for every public def."""
    out: dict[str, str] = {}
    for path in sorted((HELPERS / "sec_overlay").rglob("*.py")):
        if path.name == "__init__.py":
            continue
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                out[f"{path.name}:{node.name}"] = path.name
    return out


def _referenced_names() -> set[str]:
    """Every identifier loaded, attribute-accessed, or imported in non-test code."""
    names: set[str] = set()
    for root in ("sec_overlay", "bench"):
        for path in (HELPERS / root).rglob("*.py"):
            if "test" in path.name:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    names.add(node.attr)
                elif isinstance(node, ast.ImportFrom):
                    names.update(alias.name for alias in node.names)
    return names


def _prompt_texts() -> list[tuple[str, str]]:
    """Every agent prompt and the skill playbook, as ``(label, text)`` pairs."""
    files = sorted((SKILL_ROOT / "agents").rglob("*.md")) + [SKILL_ROOT / "SKILL.md"]
    return [(str(p.relative_to(SKILL_ROOT)), p.read_text()) for p in files]


def test_every_public_helper_has_a_caller_or_a_listed_reason():
    referenced = _referenced_names()
    prompts = _prompt_texts()
    unlisted_dead: list[str] = []
    unlisted_prompt: list[str] = []
    for key in _public_functions():
        name = key.split(":", 1)[1]
        if name in referenced:
            continue
        named_by = [label for label, text in prompts if re.search(rf"\b{re.escape(name)}\b", text)]
        if named_by:
            if key not in PROMPT_ONLY:
                unlisted_prompt.append(f"{key} (named by {named_by[0]})")
        elif key not in DEAD_ALLOWLIST:
            unlisted_dead.append(key)
    assert not unlisted_dead, (
        "public helpers with no caller and no allowlist entry: " + ", ".join(sorted(unlisted_dead)))
    assert not unlisted_prompt, (
        "prompt-only helpers missing a PROMPT_ONLY entry: " + ", ".join(sorted(unlisted_prompt)))


def test_no_list_entry_has_gained_a_caller():
    referenced = _referenced_names()
    stale = sorted(
        key for key in (DEAD_ALLOWLIST | PROMPT_ONLY)
        if key.split(":", 1)[1] in referenced
    )
    assert not stale, "these entries now have a Python caller and must be removed: " + ", ".join(stale)


def test_no_list_entry_names_a_function_that_is_gone():
    known = set(_public_functions())
    missing = sorted(key for key in (DEAD_ALLOWLIST | PROMPT_ONLY) if key not in known)
    assert not missing, "these entries no longer exist and must be removed: " + ", ".join(missing)


def test_every_dead_allowlist_entry_carries_a_reason():
    empty = sorted(key for key, reason in DEAD_ALLOWLIST.items() if not reason.strip())
    assert not empty, "allowlist entries with no reason: " + ", ".join(empty)
