"""Tally judge results into a scorecard: precision/recall by source & class, plus
Layer-B regressions (a locked finding that stopped being detected = hard failure).

Synthetic recall is reported as its own row and never folded into the headline, so a
corpus padded with easy seeded bugs can't flatter the score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from sec_overlay.models import FindingStatus


def _metrics(results) -> dict:
    """Compute tp/fn/fp/tn + precision/recall for a set of JudgeResults."""
    tp = sum(1 for r in results if r.kind == "positive" and r.detected)
    fn = sum(1 for r in results if r.kind == "positive" and not r.detected)
    fp = sum(1 for r in results if r.kind == "negative" and r.detected)  # wrongly flagged
    tn = sum(1 for r in results if r.kind == "negative" and not r.detected)
    recall = tp / (tp + fn) if (tp + fn) else None
    precision = tp / (tp + fp) if (tp + fp) else None
    fp_rate = fp / (fp + tn) if (fp + tn) else None
    f1 = None
    if precision is not None and recall is not None and (precision + recall):
        f1 = 2 * precision * recall / (precision + recall)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "recall": recall, "precision": precision, "fp_rate": fp_rate, "f1": f1}


@dataclass
class Scorecard:
    """The benchmark result."""

    overall: dict
    by_source: dict
    by_class: dict
    regressions: list = field(default_factory=list)   # locked positives now missed
    missed: list = field(default_factory=list)         # all missed positives (for analyze-misses)
    false_positives: list = field(default_factory=list)
    cost: dict = field(default_factory=dict)  # {tokens, wall_time_s, usd_per_confirmed_tp} (REQ-M6)
    verified_fix: dict = field(default_factory=dict)  # {fixed, confirmed, rate} (REQ-T3c/T3h)
    coverage_honesty: dict = field(default_factory=dict)  # {runs, unsupported, rate} (REQ-T3d)

    @property
    def verified_fix_rate(self) -> float | None:
        """Share of confirmed true-positives that were fixed or statically verified-fixed."""
        return self.verified_fix.get("rate")

    def to_dict(self) -> dict:
        d = {
            "overall": self.overall,
            "by_source": self.by_source,
            "by_class": self.by_class,
            "regressions": self.regressions,
            "missed": self.missed,
            "false_positives": self.false_positives,
            "regressed": bool(self.regressions),
        }
        if self.cost:
            d["cost"] = self.cost
        if self.verified_fix:
            d["verified_fix"] = self.verified_fix
        if self.coverage_honesty:
            d["coverage_honesty"] = self.coverage_honesty
        return d

    def to_markdown(self) -> str:
        def pct(x):
            return "-" if x is None else f"{x * 100:.0f}%"
        o = self.overall
        lines = ["# sec-overlay benchmark scorecard", "",
                 "## Headline (real-confirmed only)",
                 "",
                 (f"- Recall: **{pct(self._real.get('recall'))}** "
                  f"({self._real.get('tp',0)}/{self._real.get('tp',0)+self._real.get('fn',0)})"),
                 (f"- Precision: **{pct(self._real.get('precision'))}**  |  "
                  f"F1: **{pct(self._real.get('f1'))}**  |  "
                  f"FP-rate: {pct(self._real.get('fp_rate'))}"),
                 "",
                 "## Overall (all sources)", "",]
        if self.verified_fix:
            vf = self.verified_fix
            lines[6:6] = [(f"- Verified-fix rate: **{pct(vf.get('rate'))}** "
                           f"({vf.get('fixed', 0)}/{vf.get('confirmed', 0)} confirmed fixed "
                           f"or statically verified-fixed)")]
        lines += [
                 (f"- Recall {pct(o['recall'])} | Precision {pct(o['precision'])} | "
                  f"F1 {pct(o['f1'])} | "
                  f"FP-rate {pct(o['fp_rate'])} | tp={o['tp']} fn={o['fn']} fp={o['fp']} tn={o['tn']}"),
                 "", "## By source", "",
                 "| source | recall | precision | f1 | fp-rate | tp | fn | fp | tn |",
                 "|--------|--------|-----------|----|---------|----|----|----|----|"]
        for src, m in sorted(self.by_source.items()):
            lines.append(f"| {src} | {pct(m['recall'])} | {pct(m['precision'])} | "
                         f"{pct(m['f1'])} | "
                         f"{pct(m['fp_rate'])} | {m['tp']} | {m['fn']} | {m['fp']} | {m['tn']} |")
        lines += ["", "## By class", "",
                  "| class | recall | fp-rate | tp | fn | fp |",
                  "|-------|--------|---------|----|----|----|"]
        for cls, m in sorted(self.by_class.items()):
            lines.append(f"| {cls} | {pct(m['recall'])} | {pct(m['fp_rate'])} | "
                         f"{m['tp']} | {m['fn']} | {m['fp']} |")
        if self.regressions:
            lines += ["", "## ❌ REGRESSIONS (locked findings no longer detected)", ""]
            lines += [f"- {fid}" for fid in self.regressions]
        if self.false_positives:
            lines += ["", "## False positives (flagged a known-negative)", ""]
            lines += [f"- {fid}" for fid in self.false_positives]
        if self.cost:
            c = self.cost
            per_tp = c.get("usd_per_confirmed_tp")
            usd = "n/a" if per_tp is None else f"${per_tp:.4f}"
            lines += ["", "## Cost & latency (estimates)", "",
                      f"- Tokens: {c.get('tokens', 0)}",
                      f"- Wall-time: {c.get('wall_time_s', 0.0):.1f}s",
                      f"- $ / confirmed-TP: {usd} (estimate — token-rate table, not billed)"]
        if self.coverage_honesty:
            ch = self.coverage_honesty
            lines += ["", "## Coverage honesty (REQ-T3d)", "",
                      (f"- Honest-coverage rate: **{pct(ch.get('rate'))}** "
                       f"({ch.get('runs', 0) - len(ch.get('unsupported', []))}"
                       f"/{ch.get('runs', 0)} runs claimed complete only when the ledger held "
                       "no open surfaces, deferred items, or open questions)")]
            if ch.get("unsupported"):
                lines += ["", "Unsupported coverage claims (ledger claimed complete with gaps):"]
                lines += [f"- {slug}" for slug in ch["unsupported"]]
        lines += ["", "## Scope confound", "",
                  ("This score carries a scope confound: a deterministic file selection "
                   "reviews less code, so a lower token count partly measures doing less, "
                   "not doing better. A cross-tool token gap is not a pure efficiency signal.")]
        lines += ["", "## Judging statement", "",
                  ("Every finding above — sec-overlay and any cross-tool (OCR) findings — "
                   "is scored by the same judge (`bench.judge`: deterministic match, then an "
                   "optional injected LLM judge)."),
                  ("A cross-tool comparison therefore shares one judge for both tools. Read "
                   "the same-judge caveat: the judge can favour output shaped like its own "
                   "expectations, so a head-to-head number carries shared-judge bias and is not "
                   "a neutral referee's verdict.")]
        return "\n".join(lines) + "\n"

    _real: dict = field(default_factory=dict)


def _verified_fix(results, findings_by_id: dict) -> dict:
    """Compute the verified-fix block over confirmed real true-positives (REQ-T3c/T3h).

    Denominator: matched findings for detected real-confirmed positives (the confirmed
    true-positives). Numerator: those whose status is ``FIXED`` or whose ``verification``
    is ``verified-static``. Returns ``{}`` when no confirmed true-positive has fix data.
    """
    matched = [findings_by_id.get(r.matched_id) for r in results
               if r.source == "real-confirmed" and r.kind == "positive"
               and r.detected and r.matched_id]
    matched = [f for f in matched if f is not None]
    if not matched:
        return {}
    fixed = sum(1 for f in matched
                if f.status == FindingStatus.FIXED or f.verification == "verified-static")
    return {"fixed": fixed, "confirmed": len(matched), "rate": fixed / len(matched)}


def _unsupported_claim(ledger: dict) -> bool:
    """True when a ledger claims ``complete`` while gaps remain (REQ-T3d).

    A gap is any surface with ``disposition == "needs_follow_up"``, a non-empty
    ``deferred`` list, or a non-empty ``open_questions`` list.
    """
    if ledger.get("completeness") != "complete":
        return False
    has_open = any(s.get("disposition") == "needs_follow_up"
                   for s in ledger.get("surfaces", []))
    return bool(has_open or ledger.get("deferred") or ledger.get("open_questions"))


def _coverage_honesty(coverage_ledgers: dict) -> dict:
    """Compute the coverage-honesty block over per-run coverage ledgers (REQ-T3d).

    Args:
        coverage_ledgers: ``{run_slug: ledger_dict}``.

    Returns:
        ``{runs, unsupported, rate}`` where ``unsupported`` is the sorted list of
        run slugs whose ledger claimed complete with open gaps, and ``rate`` is the
        honest share. ``{}`` when no ledgers are supplied.
    """
    if not coverage_ledgers:
        return {}
    unsupported = sorted(slug for slug, led in coverage_ledgers.items()
                         if _unsupported_claim(led))
    runs = len(coverage_ledgers)
    return {"runs": runs, "unsupported": unsupported,
            "rate": (runs - len(unsupported)) / runs}


def tally(results, corpus, *, cost: dict | None = None,
          findings_by_id: dict | None = None,
          coverage_ledgers: dict | None = None) -> Scorecard:
    """Aggregate judge results into a :class:`Scorecard`.

    Args:
        results: List of :class:`bench.judge.JudgeResult`.
        corpus: The :class:`bench.corpus.Corpus` (for lifecycle/regression checks).
        cost: Optional run cost record ``{tokens, wall_time_s, usd_estimate}`` (REQ-M6).
            ``usd_per_confirmed_tp`` is derived as ``usd_estimate / real-confirmed TP``
            (``None`` when no TP), and reported as an estimate.
        findings_by_id: Optional ``{finding_id: Finding}`` for the verified-fix block (REQ-T3c/T3h).
        coverage_ledgers: Optional ``{run_slug: coverage_ledger_dict}`` for the coverage-honesty
            block (REQ-T3d); a run claiming ``complete`` with open gaps is an unsupported claim.

    Returns:
        A :class:`Scorecard`. ``.regressions`` lists locked positives now missed —
        a hard failure gate for CI/tuning ratchets.
    """
    overall = _metrics(results)
    by_source: dict = {}
    for src in {r.source for r in results}:
        by_source[src] = _metrics([r for r in results if r.source == src])
    by_class: dict = {}
    for cls in {r.cls for r in results}:
        by_class[cls] = _metrics([r for r in results if r.cls == cls])

    locked_ids = {e.finding_id for e in corpus.locked()}
    regressions = [r.finding_id for r in results
                   if r.finding_id in locked_ids and r.kind == "positive" and not r.detected]
    missed = [r.finding_id for r in results if r.kind == "positive" and not r.detected]
    fps = [r.finding_id for r in results if r.kind == "negative" and r.detected]

    sc = Scorecard(overall=overall, by_source=by_source, by_class=by_class,
                   regressions=regressions, missed=missed, false_positives=fps)
    sc._real = _metrics([r for r in results if r.source == "real-confirmed"]) or {}
    if cost:
        real_tp = sc._real.get("tp", 0)
        usd = cost.get("usd_estimate")
        per_tp = usd / real_tp if (usd is not None and real_tp) else None
        sc.cost = {"tokens": int(cost.get("tokens", 0)),
                   "wall_time_s": float(cost.get("wall_time_s", 0.0)),
                   "usd_per_confirmed_tp": per_tp}
    if findings_by_id:
        sc.verified_fix = _verified_fix(results, findings_by_id)
    if coverage_ledgers:
        sc.coverage_honesty = _coverage_honesty(coverage_ledgers)
    return sc


_AGG_METRICS = ("precision", "recall", "f1", "fp_rate")


def aggregate_scorecards(cards: list[Scorecard]) -> dict:
    """Summarise the headline metrics across repeated benchmark runs (REQ-M5).

    Args:
        cards: One :class:`Scorecard` per repeat.

    Returns:
        ``{"repeats": N, "<metric>": {"mean", "min", "max"}}`` for precision,
        recall, f1, and fp_rate. ``None`` values (undefined metrics) are skipped;
        a metric with no defined value across any run yields all-``None``.
    """
    agg: dict = {"repeats": len(cards)}
    for metric in _AGG_METRICS:
        vals = [cast(float, v) for c in cards if (v := c.overall.get(metric)) is not None]
        if vals:
            agg[metric] = {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}
        else:
            agg[metric] = {"mean": None, "min": None, "max": None}
    return agg
