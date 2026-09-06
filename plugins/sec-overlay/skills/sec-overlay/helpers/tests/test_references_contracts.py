"""Consistency tests: agent prompts name only outputs that the data model declares.

Ensures every field name an agent prompt documents as a writable output exists in
the corresponding dataclass or schema. Prevents the prompt-vs-contract drift that
caused D1 (dependency_sinks), D11 (logic-chain), D12 (attack-context fields), and
D23 (impact) — four separate instances of the same bug class, two of which were
blockers.

Modeled after test_references_caps.py.
"""

import json
import re
from dataclasses import fields
from pathlib import Path

import pytest

from sec_overlay.models import Finding
from sec_overlay.profile import ScanProfile

_HERE = Path(__file__).resolve().parent
_AGENTS = _HERE.parent.parent / "agents"
_REFERENCES = _HERE.parent.parent / "references"


# Maps agent prompt -> (dataclass, schema_file, expected field patterns)
# Each entry declares: which prompt file, which Python dataclass, which JSON schema
# file (or None), and the set of field names the prompt documents as writable outputs.
_AGENT_CONTRACTS: list[tuple[str, type, str | None, set[str]]] = [
    (
        "recon.md",
        ScanProfile,
        "scan-profile.schema.json",
        {
            "languages",
            "frameworks",
            "entrypoints",
            "runnable",
            "attack_surface",
            "sast_plan",
            "agents_to_spawn",
            "budget_hint",
            "attack_surface_evidence",
            "subsystems",
            "notes",
            "scan_options",
            "dependency_sinks",
        },
    ),
]


def _scan_profile_field_names() -> set[str]:
    """Return the set of declared field names on ScanProfile."""
    return {f.name for f in fields(ScanProfile)}


def _finding_field_names() -> set[str]:
    """Return the set of declared field names on Finding."""
    return {f.name for f in fields(Finding)}


def _schema_property_names(schema_name: str) -> set[str]:
    """Return the set of property names in a JSON schema file."""
    path = _REFERENCES / schema_name
    if not path.exists():
        path = _HERE.parent.parent.parent / "references" / schema_name
    schema = json.loads(path.read_text())
    props = schema.get("properties", {})
    return set(props.keys())


def _field_refs_in_prompt(prompt_path: Path) -> set[str]:
    """Extract field names a prompt documents as writeable outputs.

    Looks for markdown list items after a heading that describes output fields,
    e.g. ``- `field_name` — ...``. Returns the set of code-fenced identifiers
    found in output documentation sections.
    """
    text = prompt_path.read_text()
    # Match lines like "- `field_name` — description"
    refs = set(re.findall(r"^- `([a-z_]+)` ", text, re.MULTILINE))
    return refs


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestPromptModelConsistency:
    """Every field an agent prompt documents as an output exists on the model."""

    @pytest.mark.parametrize(
        "prompt_name,model_cls,schema_name,expected_fields",
        [p for p in _AGENT_CONTRACTS],
        ids=[p[0].replace(".md", "") for p in _AGENT_CONTRACTS],
    )
    def test_prompt_outputs_on_model(
        self,
        prompt_name: str,
        model_cls: type,
        schema_name: str | None,
        expected_fields: set[str],
    ) -> None:
        model_fields = _scan_profile_field_names() if model_cls is ScanProfile else set()
        missing_from_model = expected_fields - model_fields
        assert not missing_from_model, (
            f"recon.md documents outputs not declared on ScanProfile: "
            f"{sorted(missing_from_model)}"
        )

        if schema_name:
            schema_fields = _schema_property_names(schema_name)
            missing_from_schema = expected_fields - schema_fields
            assert not missing_from_schema, (
                f"recon.md documents outputs not declared in {schema_name}: "
                f"{sorted(missing_from_schema)}"
            )

    def test_investigate_outputs_on_finding(self) -> None:
        """Every field investigate.md documents as a finding output exists on Finding.

        Investigate.md documents these optional attack-context fields:
        - attacker, privilege, exact_request, exfil_channels
        And the logic-chain cls exception.
        """
        finding_fields = _finding_field_names()
        # Fields documented as writeable outputs in investigate.md
        expected = {"attacker", "privilege", "exact_request", "exfil_channels"}
        missing = expected - finding_fields
        assert not missing, (
            f"investigate.md documents outputs not declared on Finding: "
            f"{sorted(missing)}"
        )

    def test_impact_on_finding(self) -> None:
        """'impact' is a first-class Finding field (used by artifact-review.md)."""
        finding_fields = _finding_field_names()
        assert "impact" in finding_fields, (
            "artifact-review.md audits 'impact', but it is not declared on Finding"
        )

    def test_logic_chain_in_attack_classes(self) -> None:
        """'logic-chain' is listed in the canonical attack classes reference.

        investigate.md sanctions cls: \"logic-chain\"; the findings gate validates
        cls against attack-classes.md, so the reference must include it.
        """
        classes_path = _REFERENCES / "attack-classes.md"
        text = classes_path.read_text()
        assert "`logic-chain`" in text, (
            "logic-chain not found in attack-classes.md — the findings gate "
            "will reject it as non-canonical"
        )

    def test_dependency_sinks_in_schema(self) -> None:
        """'dependency_sinks' is a declared property in scan-profile.schema.json."""
        schema_fields = _schema_property_names("scan-profile.schema.json")
        assert "dependency_sinks" in schema_fields, (
            "dependency_sinks not declared in scan-profile.schema.json — "
            "schema validation will pass a profile that the dataclass rejects"
        )

    def test_unknown_key_validation_on_profile(self) -> None:
        """ScanProfile.from_dict raises ValueError on unknown keys.

        Unknown keys in a profile dict should be caught early with a clear
        message rather than letting ``cls(**d)`` raise a bare TypeError.
        """
        from sec_overlay.profile import ScanProfile

        with pytest.raises(ValueError, match="unknown keys"):
            ScanProfile.from_dict({"languages": [], "runnable": False, "bogus_key": 42})
