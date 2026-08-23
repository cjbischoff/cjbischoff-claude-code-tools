"""Tests for Bucket B: variant seeds, bug-chain links, novelty, git-history, rule emission."""

from types import SimpleNamespace

from sec_overlay import bugchain, githist, novelty, variant
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.rule_gaps import emit_semgrep_rule


def _f(fid, cls="sqli", file="app/db.py", line=10, dataflow=None, evidence="",
       status=FindingStatus.CONFIRMED, sev=Severity.HIGH):
    return Finding(id=fid, rule_id="r", cls=cls, status=status, severity=sev,
                   file=file, line=line, message=f"{fid} msg", dataflow=dataflow or [],
                   evidence=evidence)


def _runner(stdout, returncode=0):
    def run(cmd, capture_output=True, text=True, check=False):
        return SimpleNamespace(stdout=stdout, returncode=returncode)
    return run


# ---- variant (B1) ----

def test_variant_seeds_from_dataflow():
    f = _f("SQLI-1", dataflow=["req.args['q'] @ app/api.py:3", "-> db.execute(sql) @ app/db.py:10"])
    seeds = variant.variant_seeds(f)
    assert len(seeds) == 1
    assert seeds[0]["pattern"] == "db.execute(sql)" and seeds[0]["cls"] == "sqli"


def test_variant_seeds_empty_when_no_signal():
    assert variant.variant_seeds(_f("X-1", dataflow=[], evidence="")) == []


# ---- bug-chain (B3) ----

def test_bugchain_links_shared_node_and_file():
    a = _f("A", file="a.py", line=1, dataflow=["src @ a.py:1", "-> mid @ shared.py:5"])
    b = _f("B", file="b.py", line=2, dataflow=["src @ shared.py:5", "-> sink @ b.py:2"])
    c = _f("C", file="a.py", line=9)  # same file as A
    links = bugchain.link_candidates([a, b, c])
    pairs = {(x["a"], x["b"]) for x in links}
    assert ("A", "B") in pairs  # shared node shared.py:5
    assert ("A", "C") in pairs  # same file a.py


def test_bugchain_ignores_non_confirmed():
    a = _f("A", status=FindingStatus.RAW, file="a.py")
    b = _f("B", status=FindingStatus.CANDIDATE, file="a.py")
    assert bugchain.link_candidates([a, b]) == []
    assert bugchain.assemble([a, b])["findings"] == []


# ---- novelty (B6) ----

def test_novelty_fixed_unfixed_unknown():
    assert novelty.upstream_status("/t", "abc", "f.py", runner=_runner("d1 fix\n")) == "FIXED"
    assert novelty.upstream_status("/t", "abc", "f.py", runner=_runner("")) == "UNFIXED"
    assert novelty.upstream_status("/t", None, "f.py", runner=_runner("x")) == "UNKNOWN"
    assert novelty.upstream_status("/t", "abc", "f.py", runner=_runner("", 128)) == "UNKNOWN"


# ---- git-history (B2) ----

def test_githist_parses_commits():
    out = "deadbeef\x1ffix CVE-2024-1 in parser\ncafef00d\x1frefactor\x1fnope"
    # only well-formed (has \x1f) lines parse; second line has an extra field but still splits once
    commits = githist.security_fix_commits("/t", runner=_runner(out))
    assert commits[0] == {"sha": "deadbeef", "subject": "fix CVE-2024-1 in parser"}
    assert commits[1]["sha"] == "cafef00d"


def test_githist_empty_on_error():
    assert githist.security_fix_commits("/t", runner=_runner("x", 1)) == []
    assert githist.files_in_commit("/t", "sha", runner=_runner("a.py\nb.py\n")) == ["a.py", "b.py"]


# ---- rule emission (B5) ----

def test_emit_semgrep_rule():
    f = _f("SQLI-1", file="app/db.py", evidence="cursor.execute('SELECT ' + q)", sev=Severity.HIGH)
    rule = emit_semgrep_rule(f)
    assert rule is not None
    r = rule["rules"][0]
    assert r["languages"] == ["python"] and r["severity"] == "ERROR"
    assert r["patterns"][0]["pattern"] == "cursor.execute('SELECT ' + q)"
    assert r["metadata"]["origin_finding"] == "SQLI-1"


def test_emit_semgrep_rule_none_without_evidence_or_lang():
    assert emit_semgrep_rule(_f("X", file="app/db.py", evidence="")) is None       # no evidence
    assert emit_semgrep_rule(_f("Y", file="Makefile", evidence="x")) is None        # no lang


def test_emit_semgrep_rule_emits_the_absence_shape_when_a_safe_option_is_named():
    """Codifying a finding as a presence-only rule reports every call site, so the
    next run drowns in noise on already-fixed code."""
    f = _f("SSRF-1", cls="ssrf", file="policy.go", line=12, evidence="rego.New(")
    result = emit_semgrep_rule(f, safe_option="rego.Capabilities")
    assert result is not None
    rule = result["rules"][0]
    assert rule["id"].startswith("sec-overlay.absence.")
    patterns = rule["patterns"]
    assert any("pattern-not" in p for p in patterns)
    assert any("rego.Capabilities" in str(p) for p in patterns)
    assert rule["metadata"]["safe_option"] == "rego.Capabilities"


def test_emit_semgrep_rule_without_a_safe_option_is_unchanged():
    f = _f("SQLI-2", cls="sqli", file="db.py", line=4, evidence="cur.execute(")
    result = emit_semgrep_rule(f)
    assert result is not None
    rule = result["rules"][0]
    assert rule["id"].startswith("sec-overlay.sqli.")
    assert not any("pattern-not" in p for p in rule["patterns"])
