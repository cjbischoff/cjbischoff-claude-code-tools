from __future__ import annotations

import inspect
import re
from pathlib import Path

from sec_overlay.cli import run_review
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
_PLUGIN_ROOT = Path(__file__).resolve().parents[4]

# Dated planning records are historical, like CHANGELOG entries — never corrected retroactively.
_HISTORICAL_DIR_MARKERS = ("/docs/plans/", "/docs/superpowers/plans/")
# Third-party vendored ruleset, only present locally when cloned — not this plugin's own docs.
_VENDORED_DIR_MARKERS = ("/rules/semgrep/",)
# The actionable false instruction, not a bare mention of the word "submodule" (a doc may
# correctly explain that something is *not* a submodule).
_SUBMODULE_INSTRUCTION_PHRASES = ("recurse-submodules", "submodule update", "is a git submodule")
# Matches "has no/does not support/lacks a `--workspace` override" (and minor markdown
# variants) — the false claim WR-01 found in three doc surfaces after `review` gained the flag
# in this same phase. The trailing "override" is optional so "does not support --workspace"
# (no "override" noun) still matches.
_STALE_WORKSPACE_CLAIM_PATTERN = re.compile(
    r"(?:has no|does not support|lacks(?: an?)?)\s*`?--workspace`?\s*(?:override)?",
    re.IGNORECASE,
)


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


def test_no_live_doc_claims_a_git_submodule_that_does_not_exist():
    """No live doc surface instructs a submodule-init step when no `.gitmodules` tracks one.

    Walks the whole plugin doc tree (no hardcoded path list) so a future doc that repeats the
    same false claim fails this test too, instead of relying on someone finding it by hand.
    """
    has_gitmodules = (_PLUGIN_ROOT.parent.parent / ".gitmodules").exists()
    assert not has_gitmodules, "a real .gitmodules now exists — this guard's premise is stale"

    offenders = []
    for md_file in _PLUGIN_ROOT.rglob("*.md"):
        rel = "/" + md_file.relative_to(_PLUGIN_ROOT).as_posix()
        if md_file.name == "CHANGELOG.md":
            continue
        if any(marker in rel for marker in _HISTORICAL_DIR_MARKERS + _VENDORED_DIR_MARKERS):
            continue
        txt = md_file.read_text().lower()
        if any(phrase in txt for phrase in _SUBMODULE_INSTRUCTION_PHRASES):
            offenders.append(rel)
    assert not offenders, f"live docs still claim a git submodule that doesn't exist: {offenders}"


def test_no_live_doc_denies_the_review_workspace_override():
    """No live doc claims `review` lacks a `--workspace` override — it has had one since WR-01.

    Pins the premise from real code (`run_review`'s signature) so a future removal of the flag
    fails this guard's premise loudly, instead of leaving a now-true claim unchecked forever.
    """
    assert "workspace" in inspect.signature(run_review).parameters, (
        "run_review no longer takes a workspace parameter — this guard's premise is stale"
    )

    offenders = []
    for md_file in _PLUGIN_ROOT.rglob("*.md"):
        rel = "/" + md_file.relative_to(_PLUGIN_ROOT).as_posix()
        if md_file.name == "CHANGELOG.md":
            continue
        if any(marker in rel for marker in _HISTORICAL_DIR_MARKERS + _VENDORED_DIR_MARKERS):
            continue
        txt = md_file.read_text()
        if _STALE_WORKSPACE_CLAIM_PATTERN.search(txt):
            offenders.append(rel)
    assert not offenders, f"live docs still deny review's --workspace override: {offenders}"


def test_stale_workspace_claim_pattern_matches_known_denial_phrasings():
    """The pattern must catch every denial wording review's doc surfaces could regress to."""
    denials = [
        "review has no `--workspace` override",
        "review does not support --workspace",
        "review lacks a `--workspace` override",
        "review lacks --workspace",
    ]
    for text in denials:
        assert _STALE_WORKSPACE_CLAIM_PATTERN.search(text), f"pattern missed denial: {text!r}"


def test_stale_workspace_claim_pattern_does_not_match_corrected_wording():
    """The pattern must not flag the corrected text this task ships in SKILL.md/README.md."""
    corrected = [
        "review now takes a `--workspace` override, mirroring scan/audit",
        "review takes an optional `--workspace` override",
    ]
    for text in corrected:
        assert not _STALE_WORKSPACE_CLAIM_PATTERN.search(text), f"pattern false-positived: {text!r}"


def test_evidence_vocabulary_block_lists_all_values():
    text = _CONSTS.read_text()
    assert "## EVIDENCE_VOCABULARY" in text
    block = text.split("## EVIDENCE_VOCABULARY", 1)[1].split("\n## ", 1)[0]
    for value in TIER1_RECEIPTS | TIER2_RECEIPTS | SHIPPING_STATUSES | RUNTIME_DISPOSITIONS:
        assert value in block, f"{value} missing from EVIDENCE_VOCABULARY block"


# The CLAUDE.md phase-order block is a condensed operator view: it deliberately omits
# some PHASE_TABLE rows (factcheck, demote-noise), so the enforced invariant
# is relative order — every doc-labelled phase must appear in PHASE_TABLE order (T-06-02-06).
_CLAUDE_MD = Path(__file__).resolve().parents[2] / "CLAUDE.md"
_PHASE_DOC_LABELS = {
    "route-census": "Route census",
    "recon": "Recon",
    "recall-gate": "Recall gate",
    "architecture": "Architecture",
    "arch-gate": "Arch gate",
    "threat_model": "Threat model",
    "tm-gate": "TM gate",
    "prefilter": "Prefilter",
    "investigate": "Investigate",
    "dedupe": "Dedupe",
    "critic": "Critic",
    "judge": "Judge",
    "validate": "Validate",
    "trace": "Trace",
    "calibrate": "Calibrate",
    "patch": "Patch",
    "verify": "Verify",
    "report": "Report",
    "selfscore": "Selfscore",
    "redteam": "Red Team",
    "artifact-gate": "Artifact gate",
    "artifact-review": "Artifact review",
    "postflight": "Postflight",
}


def test_claude_md_phase_order_tracks_phase_table():
    from sec_overlay.phases import PHASE_TABLE

    text = _CLAUDE_MD.read_text()
    assert "### Phase order (one pass)" in text
    block = text.split("### Phase order (one pass)", 1)[1].split("\n### ", 1)[0]
    pos = -1
    for spec in PHASE_TABLE:
        label = _PHASE_DOC_LABELS.get(spec.name)
        if label is None:
            continue
        found = block.find(label, pos + 1)
        assert found > pos, (
            f"phase '{spec.name}' (doc label '{label}') is missing from, or out of order in, "
            "CLAUDE.md's phase-order block relative to PHASE_TABLE"
        )
        pos = found


_ATTACK_CLASSES = Path(__file__).resolve().parents[2] / "references" / "attack-classes.md"


def test_every_catalog_indicator_appears_in_the_attack_class_table():
    """Recon selects a class from attack-classes.md, so a catalogued dependency
    whose tokens are absent there is a routing gap the catalog cannot close alone."""
    from sec_overlay.dependency_sinks import load_catalog

    text = _ATTACK_CLASSES.read_text()
    missing = []
    for entry in load_catalog():
        for token in (entry.sink, *entry.indicators):
            if token not in text:
                missing.append(f"{entry.id}: {token}")
    assert not missing, f"catalog tokens absent from attack-classes.md: {missing}"


def _table_row_for_cls(text: str, cls: str) -> str:
    for line in text.splitlines():
        if line.startswith(f"| `{cls}` |"):
            return line
    raise AssertionError(f"no table row found for cls `{cls}`")


def test_attack_class_table_names_the_policy_engine_class_for_every_catalog_entry():
    """A presence-anywhere check would pass even if a token sat under the wrong
    cls, so this pins every token inside the row `reconcile_plan` actually routes by."""
    from sec_overlay.dependency_sinks import load_catalog

    text = _ATTACK_CLASSES.read_text()
    for entry in load_catalog():
        row = _table_row_for_cls(text, entry.cls)
        for token in (entry.sink, *entry.indicators):
            assert token in row, f"{entry.id}: {token} not in the `{entry.cls}` row"


_CLASSES_DIR = Path(__file__).resolve().parents[2] / "agents" / "classes"


def test_expr_eval_rce_class_file_carries_the_required_sections():
    txt = (_CLASSES_DIR / "expr-eval-rce.md").read_text()
    for heading in (
        "Canonical fix shape",
        "Discrimination requirement",
        "Class boundary",
        "Proof tuple (required evidence)",
        "Instance preservation",
    ):
        assert heading in txt, heading


def test_every_catalogued_expr_eval_class_has_a_class_file():
    from sec_overlay.dependency_sinks import load_catalog

    for entry in load_catalog():
        assert (_CLASSES_DIR / f"{entry.cls}.md").exists(), entry.cls


_BENCH_README = Path(__file__).resolve().parents[1] / "bench" / "README.md"


def test_bench_readme_documents_annotation_and_reproducibility():
    txt = _BENCH_README.read_text()
    for heading in (
        "## Annotation protocol",
        "## Reproducing the benchmark",
        "## Scope confound",
    ):
        assert heading in txt, heading
    assert "single-maintainer" in txt


def test_review_budget_constants_match_ocr_shape():
    """Task 12 (REQ-P4): the round-cost shape constants are pinned to OCR's values so a
    silent drift in the projection is caught here, not only in the unit suite."""
    from sec_overlay import review_budget as rb

    assert (rb.PLAN_PROMPT, rb.PLAN_OUT, rb.ROUNDS, rb.ROUND_OUT) == (2000, 400, 7, 700)
    assert rb.FILE_BUDGET_FRACTION == 0.8


def test_plan_line_threshold_is_pinned():
    """Task 14 (REQ-P3): the per-file plan phase fires at a documented diff-line
    threshold (OCR shape D3). A drift here changes the shape parity claim, so it
    is pinned, not tunable."""
    from sec_overlay import review_agent as ra

    assert ra.PLAN_LINE_THRESHOLD == 100


_ASSURANCE = Path(__file__).resolve().parents[2] / "ASSURANCE_CASE.md"
_CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.py):(\d+)`")


def test_assurance_case_has_required_sections():
    """REQ-S3: the assurance case carries OCR's shape — actors, trust boundaries,
    threats, a principle/CWE mapping, the automated-check list, and the honest
    open-code-review contrast."""
    txt = _ASSURANCE.read_text()
    for heading in (
        "## Actors",
        "## Trust boundaries",
        "## Threats",
        "## Countermeasures",
        "## Automated checks",
        "## Contrast with open-code-review",
    ):
        assert heading in txt, heading
    assert "Saltzer" in txt
    assert "CWE" in txt


def test_assurance_case_citations_resolve():
    """Every file:line countermeasure citation resolves to an existing line."""
    skill_root = _ASSURANCE.parent
    txt = _ASSURANCE.read_text()
    cites = _CITATION.findall(txt)
    assert len(cites) >= 3, "assurance case must cite concrete file:line countermeasures"
    for rel, line in cites:
        target = skill_root / rel
        assert target.exists(), f"cited file missing: {rel}"
        n = len(target.read_text().splitlines())
        assert 1 <= int(line) <= n, f"cited line out of range: {rel}:{line} (has {n})"


def test_assurance_case_ste_lint_clean():
    """REQ-S3 acceptance: the prose passes the STE structural lint (no errors)."""
    from sec_overlay.ste_lint import lint_prose

    errors, _ = lint_prose(_ASSURANCE.read_text())
    assert errors == [], errors
