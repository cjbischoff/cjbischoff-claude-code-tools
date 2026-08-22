"""Frozen-contract tripwires (D-15, REL-03).

``models.py`` and ``evidence.py`` are byte-identical mirrors of a separate Go
port and must never be edited independently — the sha256 guards below catch
any drift at the byte level. ``fingerprint()``'s golden-value tests pin its
*behavior* (the digest a given identity always produces) independent of that
byte check: a golden test would still pass after a whitespace-only reformat
of ``models.py`` (the byte guard would fail; the behavior would not), and the
byte guard would still pass if someone reimplemented ``fingerprint()`` to
return a different value for the same identity (the golden test would catch
that). Finally, the REL-03 test pins the helper's zero-runtime-dependency
claim by reading the real ``pyproject.toml`` at test time.
"""

from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

from sec_overlay.fingerprint import fingerprint
from sec_overlay.models import Finding, FindingStatus, Severity

_HELPERS_ROOT = Path(__file__).parent.parent

# Pinned sha256 of the Go-port mirror files (D-15). A mismatch means the file's
# bytes changed. If the edit is intentional: apply the identical change to the
# Go port by hand, get sign-off, then update the constant below to the new digest
# (`python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>`).
_MODELS_SHA256 = "7aefd93957d2a2d91731c5a0120cbbab1efa5e0623e0623674ed2bd44212ad6f"
_EVIDENCE_SHA256 = "7632308e59a34bc2723655ef4c2f7dbefc188c604d909063f3d44fa84dfc0136"


def _sha256_of(relative_path: str) -> str:
    return hashlib.sha256((_HELPERS_ROOT / relative_path).read_bytes()).hexdigest()


def test_models_byte_identity_pinned_to_go_port_mirror():
    actual = _sha256_of("sec_overlay/models.py")
    assert actual == _MODELS_SHA256, (
        "sec_overlay/models.py's sha256 changed — this file is a frozen, "
        "byte-identical mirror of a separate Go port (D-15) and must never be "
        "edited on its own. If this edit is intentional: apply the identical "
        "change to the Go port by hand, get sign-off, then update _MODELS_SHA256 "
        f"in this test to the new digest (got {actual})."
    )


def test_evidence_byte_identity_pinned_to_go_port_mirror():
    actual = _sha256_of("sec_overlay/evidence.py")
    assert actual == _EVIDENCE_SHA256, (
        "sec_overlay/evidence.py's sha256 changed — this file is a frozen, "
        "byte-identical mirror of a separate Go port (D-15) and must never be "
        "edited on its own. If this edit is intentional: apply the identical "
        "change to the Go port by hand, get sign-off, then update _EVIDENCE_SHA256 "
        f"in this test to the new digest (got {actual})."
    )


# fingerprint() = sha256(f"{rule_id}|{cls}|{anchor}")[:12] — those three fields are
# its only inputs (see sec_overlay/fingerprint.py). The golden value below is
# reached three independent ways (fully-populated, minimally-populated, and
# field-order-permuted) to prove every other Finding field, and the order
# fields are passed in, is inert to the result.
_GOLDEN_FINGERPRINT = "b90035da86f7"  # sha256("R100|sqli|my_func")[:12]


def test_fingerprint_golden_value_fully_populated():
    finding = Finding(
        id="F-9001",
        rule_id="R100",
        cls="sqli",
        status=FindingStatus.CONFIRMED,
        severity=Severity.CRITICAL,
        file="app/db.py",
        line=88,
        message="SQL built from unsanitized input",
        dataflow=["req.body -> query"],
        risk_score=9,
        verification="verified-static",
        patch_diff="--- a\n+++ b\n",
        discovery_sha="deadbeef",
        duplicate_of="F-9000",
        history=[{"pass": 1}],
        fingerprint="stale-stamp",
        priority="P1",
        cvss_vector="CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
        evidence="cursor.execute(q)",
        evidence_sources=["codeql:dataflow"],
        asvs_ids=["V5.3.4"],
        codeguard_ids=["CG-1"],
        completeness_tier="FULL",
        runtime_disposition="static-settled",
        runtime_test={"objective": "x"},
        preconditions=["authenticated"],
        reachability={"reachable": True},
        judge_verdict="uphold",
        runtime_dependent=True,
        open_questions=[{"question": "q"}],
        cluster_id="C-1",
        affected_sites=[{"id": "s"}],
        receipt_tier=1,
        impact="data exfiltration",
    )
    assert fingerprint(finding, anchor="my_func") == _GOLDEN_FINGERPRINT


def test_fingerprint_golden_value_minimally_populated():
    """All optional fields absent (dataclass defaults) — every field after ``message``."""
    finding = Finding(
        id="F-1",
        rule_id="R100",
        cls="sqli",
        status=FindingStatus.RAW,
        severity=Severity.LOW,
        file="unrelated.py",
        line=1,
        message="",
    )
    assert fingerprint(finding, anchor="my_func") == _GOLDEN_FINGERPRINT


def test_fingerprint_golden_value_field_order_permuted():
    """Same required fields as the minimal case, passed in reverse keyword order."""
    finding = Finding(
        message="",
        line=1,
        file="unrelated.py",
        severity=Severity.LOW,
        status=FindingStatus.RAW,
        cls="sqli",
        rule_id="R100",
        id="F-1",
    )
    assert fingerprint(finding, anchor="my_func") == _GOLDEN_FINGERPRINT


def test_helpers_declare_zero_runtime_dependencies():
    """REL-03: helpers/pyproject.toml's [project] dependencies stay empty."""
    with (_HELPERS_ROOT / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    assert pyproject["project"]["dependencies"] == []
