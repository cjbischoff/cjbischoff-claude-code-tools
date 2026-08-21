from __future__ import annotations

from pathlib import Path

from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    SHIPPING_STATUSES,
    TIER1_RECEIPTS,
    TIER2_RECEIPTS,
)
from sec_overlay.models import FindingStatus

_SKILL = Path(__file__).resolve().parents[2] / "SKILL.md"
_CONSTS = Path(__file__).resolve().parents[2] / "references" / "prompt-constants.md"
_REDTEAM_AGENT = Path(__file__).resolve().parents[2] / "agents" / "redteam.md"


def test_skill_documents_scope_tokens():
    txt = _SKILL.read_text()
    assert "{{REPO_ROOT}}" in txt
    assert "{{SCAN_SCOPE}}" in txt


def test_prompt_constants_states_repo_root_invariant():
    txt = _CONSTS.read_text().lower()
    assert "repo-root-relative" in txt
    assert "repo_root" in txt


def test_skill_documents_methodology_playbook():
    txt = _SKILL.read_text()
    assert "adversary_depth" in txt
    assert "gate-by-exception" in txt
    assert "model_tier_map" in txt
    # family-diversity must remain a hard invariant, not a knob
    assert "family" in txt.lower()


def test_cross_repo_adversary_prompt_exists_and_carries_rules():
    p = Path(__file__).resolve().parents[2] / "agents" / "cross-repo-adversary.md"
    txt = p.read_text().lower()
    assert "deterministic" in txt          # promote needs a deterministic join
    assert "tool receipt" in txt or "mechanical" in txt
    assert "weaken" in txt or "demote" in txt  # reasoning-only can only weaken/demote
    assert "promote" in txt


def test_correlate_combiner_prompt_exists_and_carries_rules():
    p = Path(__file__).resolve().parents[2] / "agents" / "correlate-combiner.md"
    txt = p.read_text().lower()
    assert "narrative" in txt                        # fills narrative markers only
    assert "must not" in txt and ("mermaid" in txt or "diagram" in txt)  # don't touch diagrams
    assert "evidence_chain" in txt or "evidence chain" in txt            # cite provenance
    assert "$shell_var" in txt or "shell_var" in txt                     # no literal secrets
    for slot in ("architecture", "threat_model", "redteam", "findings"):
        assert slot in txt.replace("-", "_")         # names the four docs


def test_finding_template_documents_triage_ndt_dep_views():
    p = Path(__file__).resolve().parents[2] / "references" / "finding-template.md"
    txt = p.read_text().lower()
    assert "triage line" in txt                       # skim layer documented
    assert "ndt-view" in txt or "needs-runtime view" in txt
    assert "dep-view" in txt or "dependency view" in txt
    assert "reachability" in txt                       # dep-view binding
    assert "renumber" in txt                           # condensed tier no-gap note


def test_redteam_agent_describes_the_real_two_way_wants_runtime_predicate():
    """`wants_runtime()`'s OR-predicate has two triggers and no opt-out third bucket.

    Pins both trigger values from real code (no hardcoded copy), and asserts the prompt
    doesn't claim a third disposition that keeps a finding out of the runtime plan.
    """
    needs_runtime_value = next(iter(RUNTIME_DISPOSITIONS - {"static-settled", "unassessed"}))
    needs_deployment_value = FindingStatus.NEEDS_DEPLOYMENT_TESTING.value
    txt = _REDTEAM_AGENT.read_text()
    assert needs_runtime_value in txt
    assert needs_deployment_value in txt
    assert "OR" in txt or " or " in txt
    assert "no third disposition value" in txt
    assert "neither static-settled nor a live-exploit test" not in txt


def test_evidence_vocabulary_block_lists_all_values():
    text = _CONSTS.read_text()
    assert "## EVIDENCE_VOCABULARY" in text
    block = text.split("## EVIDENCE_VOCABULARY", 1)[1].split("\n## ", 1)[0]
    for value in TIER1_RECEIPTS | TIER2_RECEIPTS | SHIPPING_STATUSES | RUNTIME_DISPOSITIONS:
        assert value in block, f"{value} missing from EVIDENCE_VOCABULARY block"
