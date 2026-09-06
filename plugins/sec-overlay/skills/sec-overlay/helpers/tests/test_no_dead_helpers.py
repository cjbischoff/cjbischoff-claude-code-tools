"""REQ-48: a public helper with no caller must be on a list, and a list entry must stay dead.

The scan resolves a reference to the module that defines the function, so a bare name in
an unrelated module no longer counts. ``mod.fn`` is referenced when a non-test
``sec_overlay/`` or ``bench/`` file imports it by name, imports ``mod`` and reads
``mod.fn``, or uses ``fn`` as a bare name inside ``mod.py`` itself. A docstring mention
does not count, and neither does a parameter of the same name.

The scan proves a reference, not a call. A name that is imported and never used still
reads as referenced, and a local variable that shadows ``fn`` inside ``mod.py`` reads the
same way. The guard is a floor against silent new dead code, not a reachability proof.

A test-only importer is not a caller. ``helpers/tests/`` stays outside the scan, because
a helper that only tests reach is what the two dictionaries exist to record.

Module keys are file basenames, so two modules of the same name in different packages
share one key. ``cli.py`` and ``workspace.py`` are the two cases in this tree.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

HELPERS = Path(__file__).resolve().parents[1]
SKILL_ROOT = HELPERS.parent
PLUGIN_ROOT = SKILL_ROOT.parents[1]

FENCED = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
INDENTED = re.compile(r"^(?: {4}|\t)\S.*$", re.MULTILINE)
INLINE = re.compile(r"`[^`\n]+`")

# Unreferenced at plugin 2.1.11. Each entry is a real gap, not a false positive.
# A name added here after this plan must carry its own one-line reason.
DEAD_ALLOWLIST: dict[str, str] = {
    "astgrep.py:astgrep_available": "unreferenced at 2.1.11",
    "calibrate.py:calibrate_score": "unreferenced at 2.1.11",
    "campaign.py:pass_report": "unreferenced at 2.1.12; prose mention only",
    "class_ext.py:class_extension_status": "unreferenced at 2.1.11",
    "codeguard.py:default_codeguard_dir": "unreferenced at 2.1.11",
    "codeguard.py:load_rules": "unreferenced at 2.1.11",
    "context.py:doc_coverage": "unreferenced at 2.1.11",
    "coverage_guide.py:should_stop": "unreferenced at 2.1.11",
    "crypto_policy.py:load_policy": "unreferenced at 2.1.11",
    "custom_checks.py:custom_check_classes": "unreferenced at 2.1.11",
    "detection_coverage.py:generate": "unreferenced at 2.1.12; prose mention only",
    "diagram_gate.py:restamp_derived": "recently added helper; re-stamps derived diagram SHAs",
    "diffhunks.py:added_line_numbers": "unreferenced at 2.1.11",
    "diffhunks.py:line_in_hunk": "unreferenced at 2.1.11",
    "diffscope.py:head_sha": "unreferenced at 2.1.12; test-only importer",
    "envelope.py:attribution_banner": "unreferenced at 2.1.11",
    "fix_disposition.py:compute_tier": "unreferenced at 2.1.11",
    "fix_disposition.py:validate": "unreferenced at 2.1.12; test-only importer",
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
    "phase_docs.py:note_keys": "unreferenced at 2.8.0; test-only importer",
    "phase_gate.py:attack_surface_gate": "unreferenced at 2.1.11",
    "phase_gate.py:claims_from_markdown": "unreferenced at 2.1.11",
    "phase_gate.py:ref_resolves": "unreferenced at 2.1.11",
    "prove.py:loopback_collector": "unreferenced at 2.1.11; adjacent finding A-3",
    "prove.py:run_prove": "unreferenced at 2.1.11; adjacent finding A-3",
    "reachability.py:blocker_of": "unreferenced at 2.1.11",
    "reachability.py:partition": "unreferenced at 2.1.12; test-only importer",
    "route_control.py:build_route_control_table": "unreferenced at 2.1.11",
    "route_control.py:check_architecture_controls": "unreferenced at 2.1.11",
    "route_control.py:check_recon_routes": "unreferenced at 2.1.11",
    "route_control.py:check_threat_entrypoints": "unreferenced at 2.1.11",
    "rule_matcher.py:build_guided_context": "unreferenced at 2.1.11",
    "rule_matcher.py:match_function": "unreferenced at 2.1.11",
}

# No Python importer, but a prompt names the function and runs it in a shell command.
PROMPT_ONLY: dict[str, str] = {
    "campaign.py:carry_forward": "SKILL.md",
    "campaign.py:salvage_partial": "SKILL.md",
    "context.py:control_findings": "agents/context-ingest.md",
    "context.py:control_worklist": "SKILL.md",
    "context.py:hunt_rows": "SKILL.md",
    "context.py:leads": "SKILL.md",
    "context.py:load": "agents/context-ingest.md",
    "context.py:manual_review_findings": "SKILL.md",
    "context.py:save": "agents/context-ingest.md",
    "crypto_policy.py:check": "agents/classes/crypto.md",
    "custom_checks.py:custom_check_instructions": "SKILL.md",
    "custom_checks.py:discover_custom_checks": "SKILL.md",
    "custom_checks.py:merge_custom_check_classes": "SKILL.md",
    "githist.py:security_fix_commits": "SKILL.md",
    "novelty.py:upstream_status": "SKILL.md",
    "partition.py:must_investigate": "SKILL.md",
    "phase_gate.py:claims_from_context": "SKILL.md",
    "phase_gate.py:claims_from_profile": "SKILL.md",
    "phase_gate.py:recall_claims": "agents/README.md",
    "phase_gate.py:run_phase_checks": "SKILL.md",
    "reflection.py:validate_verdict": "agents/README.md",
    "rule_gaps.py:emit_semgrep_rule": "SKILL.md",
    "run.py:advance": "commands/audit.md",
    "run.py:drive": "commands/audit.md",
    "run.py:infer_role": "commands/audit.md",
    "run.py:synthesize_manifest": "commands/audit.md",
    "scanscope.py:load_scope": "agents/context-ingest.md",
    "stage_validate.py:repair_prompt": "SKILL.md",
    "stage_validate.py:validate_stage": "SKILL.md",
    "tuning.py:gap_report": "SKILL.md",
    "tuning.py:is_improvement": "SKILL.md",
    "tuning.py:signal_snapshot": "SKILL.md",
    "variant.py:variant_seeds": "agents/variant-hunt.md",
    "workspace.py:record_agent_return": "SKILL.md",
}


def _public_functions(root: Path | None = None) -> dict[str, str]:
    """Map ``"<module>.py:<function>"`` to the module file name for every public def."""
    out: dict[str, str] = {}
    for path in sorted((root or HELPERS / "sec_overlay").rglob("*.py")):
        if path.name == "__init__.py":
            continue
        defs = (ast.FunctionDef, ast.AsyncFunctionDef)
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, defs) and not node.name.startswith("_"):
                out[f"{path.name}:{node.name}"] = path.name
    return out


def _package_modules() -> set[str]:
    """Every module name that ``sec_overlay/`` defines, without the ``.py`` suffix."""
    return {p.stem for p in (HELPERS / "sec_overlay").rglob("*.py") if p.name != "__init__.py"}


def _dotted(node: ast.Attribute) -> str:
    """Flatten an attribute chain to ``a.b.c``. Return ``""`` if the base is not a name."""
    parts = [node.attr]
    cur: ast.expr = node.value
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return ""
    parts.append(cur.id)
    return ".".join(reversed(parts))


def _referenced_keys() -> set[str]:
    """Every ``"<module>.py:<function>"`` that non-test code resolves to that module."""
    modules = _package_modules()
    keys: set[str] = set()
    own_names: dict[str, set[str]] = {}
    for root in ("sec_overlay", "bench"):
        for path in sorted((HELPERS / root).rglob("*.py")):
            if "test" in path.name:
                continue
            tree = ast.parse(path.read_text())
            aliases: dict[str, str] = {}
            loaded: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    owner = (node.module or "").rsplit(".", 1)[-1]
                    for alias in node.names:
                        if owner in modules:
                            keys.add(f"{owner}.py:{alias.name}")
                        if alias.name in modules:
                            aliases[alias.asname or alias.name] = alias.name
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        tail = alias.name.rsplit(".", 1)[-1]
                        if tail in modules:
                            aliases[alias.asname or tail] = tail
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    loaded.add(node.id)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    parts = _dotted(node).split(".")
                    if len(parts) > 1 and parts[-2] in aliases:
                        keys.add(f"{aliases[parts[-2]]}.py:{parts[-1]}")
            if root == "sec_overlay":
                own_names.setdefault(path.name, set()).update(loaded)
    for module, names in own_names.items():
        keys.update(f"{module}:{name}" for name in names)
    return keys


def _prompt_texts() -> list[tuple[str, str]]:
    """Every agent prompt, the skill playbook, and every slash command, as ``(label, text)``."""
    files = sorted((SKILL_ROOT / "agents").rglob("*.md")) + [SKILL_ROOT / "SKILL.md"]
    out = [(str(p.relative_to(SKILL_ROOT)), p.read_text()) for p in files]
    commands = sorted((PLUGIN_ROOT / "commands").rglob("*.md"))
    out += [(str(p.relative_to(PLUGIN_ROOT)), p.read_text()) for p in commands]
    return out


def _code_context(text: str) -> str:
    """Keep only the code of a Markdown file: fenced blocks, indented blocks, backtick spans."""
    fenced = FENCED.findall(text)
    rest = FENCED.sub("\n", text)
    return "\n".join(fenced + INDENTED.findall(rest) + INLINE.findall(rest))


def _invokes(key: str, code: str) -> bool:
    """Report whether ``code`` calls the helper or names it as ``<module>.<function>``."""
    module, name = key.split(":", 1)
    return bool(
        re.search(rf"\b{re.escape(name)}\s*\(", code)
        or re.search(rf"\b{re.escape(module[:-3])}\.{re.escape(name)}\b", code)
    )


def test_every_public_helper_has_a_caller_or_a_listed_reason():
    referenced = _referenced_keys()
    prompts = [(label, _code_context(text)) for label, text in _prompt_texts()]
    unlisted_dead: list[str] = []
    unlisted_prompt: list[str] = []
    for key in _public_functions():
        if key in referenced:
            continue
        invoked_by = [label for label, code in prompts if _invokes(key, code)]
        if invoked_by:
            if key not in PROMPT_ONLY:
                unlisted_prompt.append(f"{key} (invoked by {invoked_by[0]})")
        elif key not in DEAD_ALLOWLIST:
            unlisted_dead.append(key)
    assert not unlisted_dead, (
        "public helpers with no caller and no allowlist entry: " + ", ".join(sorted(unlisted_dead)))
    assert not unlisted_prompt, (
        "prompt-only helpers missing a PROMPT_ONLY entry: " + ", ".join(sorted(unlisted_prompt)))


def test_no_list_entry_has_gained_a_caller():
    referenced = _referenced_keys()
    stale = sorted(key for key in (DEAD_ALLOWLIST | PROMPT_ONLY) if key in referenced)
    assert not stale, (
        "these entries now have a Python caller and must be removed: " + ", ".join(stale))


def test_no_list_entry_names_a_function_that_is_gone():
    known = set(_public_functions())
    missing = sorted(key for key in (DEAD_ALLOWLIST | PROMPT_ONLY) if key not in known)
    assert not missing, "these entries no longer exist and must be removed: " + ", ".join(missing)


def test_every_dead_allowlist_entry_carries_a_reason():
    empty = sorted(key for key, reason in DEAD_ALLOWLIST.items() if not reason.strip())
    assert not empty, "allowlist entries with no reason: " + ", ".join(empty)


def test_a_dead_helper_masked_by_a_name_collision_is_still_listed():
    """A dead helper whose bare name also appears elsewhere must still carry a list entry."""
    listed = set(DEAD_ALLOWLIST) | set(PROMPT_ONLY)
    missing = [k for k in ("context.py:load", "fix_disposition.py:validate") if k not in listed]
    assert not missing, "dead helpers hidden by a name collision: " + ", ".join(missing)


def test_the_prompt_corpus_holds_the_command_files():
    """The slash command invokes helpers, so ``commands/`` must be citable."""
    labels = [label for label, _ in _prompt_texts()]
    assert "commands/audit.md" in labels


def test_prompt_only_cites_the_file_that_invokes_the_helper():
    """``commands/audit.md`` runs these four helpers, so each entry must cite that file."""
    keys = ("run.py:advance", "run.py:drive", "run.py:infer_role", "run.py:synthesize_manifest")
    wrong = [f"{key} -> {PROMPT_ONLY.get(key, 'absent')}" for key in keys
             if PROMPT_ONLY.get(key) != "commands/audit.md"]
    assert not wrong, "these entries must cite commands/audit.md: " + ", ".join(wrong)


def test_every_prompt_only_entry_cites_a_code_invocation():
    """A citation must invoke the helper in a code span. Prose that names it does not count."""
    texts = dict(_prompt_texts())
    prose_only: list[str] = []
    for key, label in PROMPT_ONLY.items():
        if not _invokes(key, _code_context(texts.get(label, ""))):
            prose_only.append(f"{key} (cited {label})")
    assert not prose_only, (
        "PROMPT_ONLY entries with no code invocation in the cited file: " + ", ".join(
            sorted(prose_only)))


def test_public_functions_reports_an_async_helper(tmp_path: Path):
    """An ``async def`` public helper must be visible to the scan."""
    (tmp_path / "sample.py").write_text("async def go():\n    return 1\n")
    assert _public_functions(tmp_path) == {"sample.py:go": "sample.py"}
