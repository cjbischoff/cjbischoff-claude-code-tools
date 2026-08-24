"""Layer-C contract tests: agent-prompt JSON examples must match our real schema.

Catches producer<->schema drift (the finding_id/duplicate_of field-name-drift class)
WITHOUT running an LLM — grep JSON blocks out of the prompt .md files and validate
them against the actual Finding model + gate rules.
"""
import json
import re
from pathlib import Path

import pytest

from sec_overlay.findings_gate import validate_findings
from sec_overlay.models import Finding
from sec_overlay.workspace import Workspace, write_findings

SKILL = Path(__file__).resolve().parents[2]          # skills/sec-overlay
AGENTS = SKILL / "agents"
_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)


def _json_blocks(md_path):
    if not md_path.exists():
        return []
    out = []
    for m in _JSON_BLOCK.finditer(md_path.read_text()):
        raw = m.group(1)
        # tolerate <placeholder> tokens in prompt examples
        cleaned = re.sub(r"<[^>]+>", "null", raw)
        try:
            out.append(json.loads(cleaned))
        except json.JSONDecodeError:
            pass
    return out


def test_investigate_finding_example_matches_model():
    blocks = _json_blocks(AGENTS / "investigate.md")
    finding_blocks = [b for b in blocks if isinstance(b, dict) and "cls" in b and "status" in b]
    assert finding_blocks, "investigate.md must document a Finding JSON example"
    for b in finding_blocks:
        f = Finding.from_dict(b)            # must parse against the REAL model
        assert f.cls and f.id               # required fields present under real names
        # no unknown top-level keys (from_dict would tolerate, so check the drift set)
        allowed = set(Finding.from_dict(b).to_dict().keys())
        assert set(b.keys()) <= allowed, f"prompt example has keys the model drops: {set(b)-allowed}"


def test_investigate_example_passes_the_gate(tmp_path):
    blocks = _json_blocks(AGENTS / "investigate.md")
    finding_blocks = [b for b in blocks if isinstance(b, dict) and "cls" in b and "status" in b]
    ws = Workspace(tmp_path); ws.ensure()
    findings = []
    for i, b in enumerate(finding_blocks, 1):
        f = Finding.from_dict(b); f.id = f"C-{i:04d}"
        if not f.file:
            f.file = "x.py"
        f.line = max(f.line, 1)
        if "{{" in f.cls:
            f.cls = "sqli"  # the documented example carries the {{ATTACK_CLASS}} token
        findings.append(f)
    write_findings(ws, findings)
    # the documented example must be gate-clean (no raw+duplicate_of, valid shape)
    assert validate_findings(ws) == []


def test_golden_raw_finding_matches_model():
    golden = SKILL / "helpers" / "fixtures" / "golden_raw_finding.json"
    if not golden.exists():
        pytest.skip("no golden fixture")
    f = Finding.from_dict(json.loads(golden.read_text()))
    assert f.id and f.cls and f.status


def test_recon_prompt_requires_route_summary():
    assert "route" in (AGENTS / "recon.md").read_text().lower()


def test_recon_prompt_requires_the_absence_pack():
    """The vendored pack has no absence rule, so omitting rules/absence loses the class."""
    from pathlib import Path

    recon = (Path(__file__).resolve().parents[2] / "agents" / "recon.md").read_text()
    assert "rules/absence" in recon
    assert "always" in recon.lower().split("rules/absence")[0][-400:]


def test_golden_scan_profile_carries_the_absence_pack():
    import json
    from pathlib import Path

    profile = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / "golden_scan_profile.json").read_text()
    )
    assert any("rules/absence" in r for r in profile["sast_plan"]["semgrep"]["rulesets"])


def test_architecture_prompt_requires_all_controls():
    txt = (AGENTS / "architecture.md").read_text().lower()
    assert "all controls" in txt or "every control" in txt


def test_threat_model_retains_every_entrypoint():
    txt = (AGENTS / "threat-model.md").read_text().lower()
    assert "every entrypoint" in txt or "each entrypoint" in txt


def _proof_tuple_section(txt):
    marker = "## Proof tuple (required evidence)"
    start = txt.index(marker)
    rest = txt[start + len(marker) :]
    next_heading = rest.find("\n## ")
    end = start + len(marker) + (next_heading if next_heading != -1 else len(rest))
    return txt[start:end]


def test_ssrf_proof_tuple_admits_the_dependency_internal_sink():
    """Without this, an OPA http.send finding can never leave `raw`: there is no
    first-party line to cite for element 1."""
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "classes" / "ssrf.md").read_text()
    section = _proof_tuple_section(txt)
    assert "dependency-catalog" in section
    assert "sec-overlay.absence" in section


def test_investigate_tool_grounding_names_the_two_new_receipts():
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "investigate.md").read_text()
    assert "dependency-catalog" in txt
    assert "never confirms alone" in txt or "cannot confirm alone" in txt


def test_recall_adversary_prompt_exists_and_states_its_contract():
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "recall-adversary.md").read_text()
    assert "OMISSION" in txt
    assert "NO OMISSION FOUND" in txt
    assert "opus" in txt.lower()


def test_phase_adversary_verdict_tables_are_untouched_by_recall():
    """The count-invariant tables are load-bearing; recall gets its own agent."""
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "phase-adversary.md").read_text()
    assert "OMISSION" not in txt
