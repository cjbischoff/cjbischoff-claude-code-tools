"""Tests for the bench eval harness (corpus, judge, tally, run)."""
import json
from dataclasses import replace

from bench.adapter import WorkspaceAdapter, reportable
from bench.corpus import Corpus, CorpusEntry, load_corpus
from bench.judge import deterministic_match, judge_all, judge_entry
from bench.run import run_benchmark
from bench.tally import tally
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings


def _entry(fid, **kw):
    base = CorpusEntry(finding_id=fid, kind="positive", source="real-confirmed", cls="xss",
                        repo_url="https://github.com/o/r", commit="a" * 40, file="app.js",
                        line=10, description="d")
    return replace(base, **kw) if kw else base


def _f(id_, cls, file, line, status=FindingStatus.CONFIRMED, message="m", rule_id="r"):
    return Finding(id=id_, rule_id=rule_id, cls=cls, status=status,
                   severity=Severity.HIGH, file=file, line=line, message=message)


# ---- corpus ----
def test_corpus_validate_and_grouping():
    c = Corpus([_entry("V1"), _entry("V2", kind="negative"),
                _entry("V3", repo_url="ftp://bad", commit="")])
    errs = c.validate()
    assert any("V3" in e for e in errs)         # bad url + missing commit
    assert len(c.positives()) == 2 and len(c.negatives()) == 1
    assert len(c.by_repo()) == 2                 # V3 differs by commit


def test_corpus_load(tmp_path):
    (tmp_path / "r.json").write_text(json.dumps([_entry("V1").__dict__]))
    c = load_corpus(tmp_path)
    assert c.entries[0].finding_id == "V1"


# ---- judge ----
def test_deterministic_match_class_file_line():
    e = _entry("V1", file="app.js", line=10, cls="xss")
    assert deterministic_match(e, [_f("C1", "xss", "src/app.js", 14)]) is not None   # within window
    assert deterministic_match(e, [_f("C1", "xss", "src/app.js", 99)]) is None        # too far
    assert deterministic_match(e, [_f("C1", "sqli", "src/app.js", 10)]) is None       # wrong class


def test_deterministic_match_dep_cve():
    e = _entry("V1", source="dep-cve", cls="deps", cve="GHSA-xxxx")
    assert deterministic_match(e, [_f("C1", "deps", "pkg.json", 1, rule_id="osv:GHSA-xxxx")]) is not None


def test_judge_positive_negative_and_llm_fallback():
    pos = _entry("V1", kind="positive")
    neg = _entry("V2", kind="negative")
    findings = [_f("C1", "xss", "app.js", 10)]
    rp = judge_entry(pos, findings); assert rp.detected and rp.is_correct and rp.method == "deterministic"
    # negative WRONGLY flagged -> detected True -> is_correct False (a false positive)
    rn = judge_entry(neg, findings); assert rn.detected is True and rn.is_correct is False
    # no deterministic match + llm fallback used
    called = {}
    def llm(entry, fs):
        called["x"] = True
        return True, "fuzzy root-cause match"
    r = judge_entry(_entry("V9", file="other.js"), findings, llm_judge=llm)
    assert called and r.method == "llm" and r.detected


# ---- tally ----
def test_tally_segments_and_regressions():
    entries = [_entry("V1", source="real-confirmed"),
               _entry("V2", source="synthetic"),
               _entry("V3", source="real-confirmed", kind="negative"),
               _entry("V4", source="real-confirmed", lifecycle="locked")]
    corpus = Corpus(entries)
    # V1 detected, V2 missed, V3 wrongly flagged (FP), V4 (locked) MISSED -> regression
    findings_by_repo = {("https://github.com/o/r", "a" * 40):
                        [_f("C1", "xss", "app.js", 10)]}   # matches V1/V3 loc; V2/V4 same loc too
    # make V2 (synthetic) and V4 not match by putting them on a different line
    entries[1].line = 500; entries[3].line = 600
    results = judge_all(entries, findings_by_repo)
    sc = tally(results, corpus)
    assert "V3" in sc.false_positives
    assert "V4" in sc.regressions and sc.to_dict()["regressed"] is True
    assert "synthetic" in sc.by_source and "real-confirmed" in sc.by_source
    assert "REGRESSIONS" in sc.to_markdown()


# ---- run (end-to-end with injected clone + workspace adapter) ----
def test_run_benchmark_end_to_end(tmp_path):
    corpus_dir = tmp_path / "corpus"; corpus_dir.mkdir()
    (corpus_dir / "r.json").write_text(json.dumps([
        _entry("V1", file="app.js", line=10).__dict__,
        _entry("V2", kind="negative", file="safe.js", line=5, cls="sqli").__dict__,
    ]))
    # pre-populate a workspace with the scan's findings; WorkspaceAdapter reads it
    scanned = Workspace(tmp_path / "pre"); scanned.ensure()
    write_findings(scanned, [_f("C1", "xss", "app.js", 10)])
    adapter = WorkspaceAdapter(lambda repo: scanned)
    clones = []
    def fake_clone(url, commit, dest):
        clones.append((url, commit)); dest.mkdir(parents=True, exist_ok=True); return dest
    sc = run_benchmark(corpus_dir, tmp_path / "run", adapter, clone_fn=fake_clone)
    assert sc["overall"]["tp"] == 1 and sc["overall"]["fp"] == 0
    assert (tmp_path / "run" / "scorecard.md").exists()
    assert clones  # cloned once
    # resume: second run skips clone (cache hit)
    clones.clear()
    run_benchmark(corpus_dir, tmp_path / "run", adapter, clone_fn=fake_clone)
    assert clones == []


def test_run_benchmark_only_local_skips_http(tmp_path):
    corpus_dir = tmp_path / "corpus"; corpus_dir.mkdir()
    (corpus_dir / "r.json").write_text(json.dumps([
        _entry("H1", file="app.js", line=10).__dict__,                       # http target
        _entry("L1", repo_url="", commit="", local_path="fix", file="a.py",
               line=1, cls="sqli").__dict__,                                  # local target
    ]))
    scanned = Workspace(tmp_path / "pre"); scanned.ensure()
    write_findings(scanned, [_f("C1", "sqli", "a.py", 1)])
    adapter = WorkspaceAdapter(lambda repo: scanned)
    clones = []
    def fake_clone(url, commit, dest):
        clones.append(url); dest.mkdir(parents=True, exist_ok=True); return dest
    sc = run_benchmark(corpus_dir, tmp_path / "run", adapter, clone_fn=fake_clone,
                       only_local=True)
    assert clones == []                       # http target never cloned
    assert sc["overall"]["tp"] == 1           # local target still graded


def test_run_repeated_writes_aggregate(tmp_path):
    from bench.run import run_repeated
    corpus_dir = tmp_path / "corpus"; corpus_dir.mkdir()
    (corpus_dir / "r.json").write_text(json.dumps([
        _entry("L1", repo_url="", commit="", local_path="fix", file="a.py",
               line=1, cls="sqli").__dict__,
    ]))
    scanned = Workspace(tmp_path / "pre"); scanned.ensure()
    write_findings(scanned, [_f("C1", "sqli", "a.py", 1)])
    adapter = WorkspaceAdapter(lambda repo: scanned)
    agg = run_repeated(corpus_dir, tmp_path / "run", adapter, repeats=2, only_local=True)
    assert agg["repeats"] == 2
    assert (tmp_path / "run" / "run-1" / "scorecard.md").exists()
    assert (tmp_path / "run" / "run-2" / "scorecard.md").exists()
    assert (tmp_path / "run" / "scorecard_agg.json").exists()
    assert (tmp_path / "run" / "scorecard_agg.md").exists()


def test_reportable_filters_status(tmp_path):
    ws = Workspace(tmp_path); ws.ensure()
    write_findings(ws, [_f("C1", "xss", "a.js", 1, status=FindingStatus.CONFIRMED),
                        _f("C2", "xss", "a.js", 2, status=FindingStatus.REJECTED)])
    assert [f.id for f in reportable(ws)] == ["C1"]


def test_tier1_detected_reads_receipt_candidates(tmp_path):
    from bench.adapter import tier1_detected
    ws = Workspace(tmp_path); ws.ensure()
    cand = _f("D1", "sqli", "app.py", 18, status=FindingStatus.CANDIDATE)
    cand.evidence_sources = ["semgrep:rules.python-sqli-string-format"]
    tier2 = _f("D2", "sqli", "app.py", 20, status=FindingStatus.CANDIDATE)
    tier2.evidence_sources = ["ripgrep:match"]
    write_findings(ws, [cand, tier2])
    # detection mode grades a Tier-1 candidate; reportable() (confirmation) sees neither
    assert [f.id for f in tier1_detected(ws)] == ["D1"]
    assert reportable(ws) == []


def test_seed_corpus_is_valid():
    from pathlib import Path

    from bench.corpus import load_corpus
    seed = Path(__file__).resolve().parents[1] / "bench" / "corpus_seed"
    c = load_corpus(seed)
    assert c.validate() == []
    assert len(c.positives()) >= 5 and len(c.negatives()) >= 3
    assert any(e.source == "dep-cve" for e in c.entries)


def test_seed_corpus_has_min_entries():
    from pathlib import Path

    from bench.corpus import load_corpus
    seed = Path(__file__).resolve().parents[1] / "bench" / "corpus_seed"
    c = load_corpus(seed)
    assert c.validate() == []
    assert len(c.entries) >= 30
    assert sum(1 for e in c.entries if e.source == "dep-cve") >= 3
    assert sum(1 for e in c.entries if e.source == "public-app") >= 5
    assert len(c.negatives()) >= 1
    assert len(c.locked()) >= 1


# ---- f1 (REQ-M1) ----
def _jr(fid, kind, detected, source="real-confirmed", cls="xss"):
    from bench.judge import JudgeResult
    return JudgeResult(finding_id=fid, kind=kind, source=source, cls=cls,
                       detected=detected, method="deterministic", matched_id=None, reasoning="")


def test_f1_computed():
    from bench.tally import _metrics
    results = ([_jr(f"P{i}", "positive", True) for i in range(3)]
               + [_jr("P3", "positive", False)]
               + [_jr("N0", "negative", True)])
    m = _metrics(results)
    assert abs(m["f1"] - 0.75) < 1e-9


def test_f1_none_when_undefined():
    from bench.tally import _metrics
    assert _metrics([])["f1"] is None
    # precision defined (0.0), recall defined (0.0) -> P+R == 0 -> None
    m = _metrics([_jr("P0", "positive", False), _jr("N0", "negative", True)])
    assert m["f1"] is None


def test_f1_rendered_in_markdown():
    corpus = Corpus([_entry("V1")])
    sc = tally([_jr("V1", "positive", True)], corpus)
    assert "F1" in sc.to_markdown()
    assert "f1" in sc.to_dict()["overall"]


# ---- variance across repeats (REQ-M5) ----
def _card(precision, recall, f1, fp_rate):
    from bench.tally import Scorecard
    overall = {"tp": 0, "fn": 0, "fp": 0, "tn": 0,
               "recall": recall, "precision": precision, "fp_rate": fp_rate, "f1": f1}
    return Scorecard(overall=overall, by_source={}, by_class={})


def test_aggregate_scorecards_mean_and_range():
    from bench.tally import aggregate_scorecards
    cards = [_card(0.2, 0.4, 0.3, 0.1),
             _card(0.4, 0.6, 0.5, 0.3),
             _card(0.6, 0.8, 0.7, 0.2)]
    agg = aggregate_scorecards(cards)
    assert agg["repeats"] == 3
    for metric, (mean, lo, hi) in {
        "precision": (0.4, 0.2, 0.6),
        "recall": (0.6, 0.4, 0.8),
        "f1": (0.5, 0.3, 0.7),
        "fp_rate": (0.2, 0.1, 0.3),
    }.items():
        assert abs(agg[metric]["mean"] - mean) < 1e-9
        assert abs(agg[metric]["min"] - lo) < 1e-9
        assert abs(agg[metric]["max"] - hi) < 1e-9


def test_aggregate_scorecards_ignores_none_metrics():
    from bench.tally import aggregate_scorecards
    cards = [_card(0.2, None, None, 0.1), _card(0.4, None, None, 0.3)]
    agg = aggregate_scorecards(cards)
    assert abs(agg["precision"]["mean"] - 0.3) < 1e-9
    assert agg["recall"] == {"mean": None, "min": None, "max": None}
    assert agg["f1"] == {"mean": None, "min": None, "max": None}


# ---- cost/latency columns (REQ-M6) ----
def test_scorecard_carries_cost_columns():
    corpus = Corpus([_entry("V1")])
    cost = {"tokens": 120_000, "wall_time_s": 42.5, "usd_estimate": 0.5}
    sc = tally([_jr("V1", "positive", True)], corpus, cost=cost)
    d = sc.to_dict()["cost"]
    assert d["tokens"] == 120_000
    assert abs(d["wall_time_s"] - 42.5) < 1e-9
    # one real-confirmed TP → $/TP == usd_estimate / 1
    assert abs(d["usd_per_confirmed_tp"] - 0.5) < 1e-9


def test_scorecard_cost_none_per_tp_when_no_tp():
    corpus = Corpus([_entry("V1")])
    cost = {"tokens": 5, "wall_time_s": 1.0, "usd_estimate": 0.5}
    sc = tally([_jr("V1", "positive", False)], corpus, cost=cost)  # missed → 0 TP
    assert sc.to_dict()["cost"]["usd_per_confirmed_tp"] is None


def test_scorecard_markdown_renders_cost_and_per_class_fp():
    corpus = Corpus([_entry("V1"), _entry("N1", kind="negative", cls="sqli", file="s.js")])
    cost = {"tokens": 120_000, "wall_time_s": 42.5, "usd_estimate": 0.5}
    md = tally([_jr("V1", "positive", True), _jr("N1", "negative", True, cls="sqli")],
               corpus, cost=cost).to_markdown().lower()
    assert "tokens" in md and "wall-time" in md
    assert "estimate" in md  # $/TP labeled estimate
    assert "## by class" in md and "fp-rate" in md


def test_scorecard_markdown_omits_cost_when_absent():
    sc = tally([_jr("V1", "positive", True)], Corpus([_entry("V1")]))
    assert "cost" not in sc.to_dict()
    assert "wall-time" not in sc.to_markdown().lower()


def test_scorecard_markdown_states_scope_confound():
    corpus = Corpus([_entry("V1")])
    md = tally([_jr("V1", "positive", True)], corpus).to_markdown().lower()
    assert "confound" in md
    assert "reviews less" in md


# ---- verified-fix rate (REQ-T3c/T3h) ----
def _jrm(fid, matched_id, **kw):
    from bench.judge import JudgeResult
    base = dict(kind="positive", source="real-confirmed", cls="xss", detected=True,
                method="deterministic", reasoning="")
    base.update(kw)
    return JudgeResult(finding_id=fid, matched_id=matched_id, **base)


def test_verified_fix_rate_counts_fixed_and_verified_static():
    """REQ-T3c/T3h: verified_fix_rate = (fixed ∪ verified-static) / confirmed TPs."""
    corpus = Corpus([_entry("V1"), _entry("V2"), _entry("V3")])
    results = [_jrm("V1", "f1"), _jrm("V2", "f2"), _jrm("V3", "f3")]
    findings_by_id = {
        "f1": _f("f1", "xss", "app.js", 10, status=FindingStatus.FIXED),
        "f2": replace(_f("f2", "xss", "app.js", 10), verification="verified-static"),
        "f3": _f("f3", "xss", "app.js", 10),   # confirmed, not fixed
    }
    sc = tally(results, corpus, findings_by_id=findings_by_id)
    assert sc.verified_fix_rate == 2 / 3
    vf = sc.to_dict()["verified_fix"]
    assert vf == {"fixed": 2, "confirmed": 3, "rate": 2 / 3}
    assert "verified-fix rate" in sc.to_markdown().lower()


def test_verified_fix_rate_absent_without_fix_data():
    corpus = Corpus([_entry("V1")])
    sc = tally([_jr("V1", "positive", True)], corpus)
    assert sc.verified_fix_rate is None
    assert "verified_fix" not in sc.to_dict()
