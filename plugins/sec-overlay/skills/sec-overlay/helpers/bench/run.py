"""Benchmark orchestrator: clone@commit -> scan (adapter) -> judge -> tally.

Resumable: a per-repo scan is skipped once its findings are cached in the run dir,
so an interrupted benchmark continues. The judge + tally always re-run (cheap,
deterministic) from cached findings.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from bench.adapter import BinaryAdapter, WorkspaceAdapter, reportable, tier1_detected
from bench.corpus import load_corpus
from bench.judge import judge_all
from bench.tally import Scorecard, aggregate_scorecards, tally
from sec_overlay.models import Finding
from sec_overlay.repo_memory import repo_slug
from sec_overlay.workspace import Workspace


def git_clone_at_commit(repo_url: str, commit: str, dest: Path, *, runner=subprocess.run) -> Path:
    """Clone ``repo_url`` at exactly ``commit`` into ``dest`` (shallow, with fallback).

    Mirrors VulnHunter: ``git fetch --depth=1 origin <commit>`` after an empty init,
    falling back to a full clone + checkout if the host disallows fetch-by-sha.

    Args:
        repo_url: HTTPS git URL.
        commit: Exact commit SHA.
        dest: Destination directory (created).
        runner: Injectable subprocess runner.

    Returns:
        ``dest`` on success.

    Raises:
        RuntimeError: if the checkout fails.
    """
    dest.mkdir(parents=True, exist_ok=True)
    def g(*args):
        return runner(["git", "-C", str(dest), *args], capture_output=True, text=True, check=False)
    g("init", "-q")
    g("remote", "add", "origin", repo_url)
    fetched = g("fetch", "--depth=1", "origin", commit)
    if fetched.returncode == 0:
        co = g("checkout", "-q", "FETCH_HEAD")
        if co.returncode == 0:
            return dest
    # fallback: full fetch + checkout
    g("fetch", "-q", "origin")
    co = g("checkout", "-q", commit)
    if co.returncode != 0:
        raise RuntimeError(f"clone@commit failed for {repo_url}@{commit}: {co.stderr.strip()[:200]}")
    return dest


def run_benchmark(corpus_dir, run_dir, adapter, *, clone_fn=git_clone_at_commit,
                  llm_judge=None, resume=True, only_local=False) -> dict:
    """Run the full benchmark and write a scorecard.

    Args:
        corpus_dir: Directory of corpus JSON files.
        run_dir: Working directory for clones, per-repo workspaces, cached findings,
            and the scorecard.
        adapter: A :class:`bench.adapter.ScanAdapter`.
        clone_fn: ``callable(repo_url, commit, dest) -> path`` (injectable).
        llm_judge: Optional fuzzy-match fallback for the judge.
        resume: Skip repos whose findings are already cached.

    Returns:
        The scorecard dict (also written to ``run_dir/scorecard.{json,md}``).

    Raises:
        ValueError: if the corpus fails validation.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus(corpus_dir)
    errs = corpus.validate()
    if errs:
        raise ValueError("invalid corpus:\n" + "\n".join(errs))

    findings_by_repo: dict[tuple[str, str], list[Finding]] = {}
    for key in corpus.by_repo():
        target, commit = key
        is_local = not target.startswith("http")
        if only_local and not is_local:
            continue
        if is_local:
            slug = repo_slug(target)
        else:
            slug = target.rstrip("/").rsplit("/", 1)[-1].replace(".git", "") + "-" + commit[:8]
        cache = run_dir / "findings_cache" / f"{slug}.json"
        if resume and cache.exists():
            findings_by_repo[key] = [Finding.from_dict(d) for d in json.loads(cache.read_text())]
            continue
        if is_local:
            repo_path = Path(target)           # scan the local checkout as-is
        else:
            repo_path = run_dir / "repos" / slug
            clone_fn(target, commit, repo_path)
        ws = Workspace(run_dir / "workspaces" / slug)
        findings = adapter.scan(str(repo_path), ws)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps([f.to_dict() for f in findings], indent=2))
        findings_by_repo[key] = findings

    results = judge_all(corpus.entries, findings_by_repo, llm_judge=llm_judge)
    scorecard = tally(results, corpus)
    (run_dir / "scorecard.json").write_text(json.dumps(scorecard.to_dict(), indent=2))
    (run_dir / "scorecard.md").write_text(scorecard.to_markdown())
    return scorecard.to_dict()


def _agg_markdown(agg: dict) -> str:
    """Render an aggregate scorecard (mean ± range across repeats) as markdown."""
    def cell(v):
        return "n/a" if v is None else f"{v:.4f}"
    lines = [f"# Aggregate scorecard ({agg['repeats']} repeats)", "",
             "| metric | mean | min | max |", "|--------|------|-----|-----|"]
    for metric in ("precision", "recall", "f1", "fp_rate"):
        m = agg[metric]
        lines.append(f"| {metric} | {cell(m['mean'])} | {cell(m['min'])} | {cell(m['max'])} |")
    return "\n".join(lines) + "\n"


def run_repeated(corpus_dir, run_dir, adapter, *, repeats, **kwargs) -> dict:
    """Run the benchmark ``repeats`` times into ``run_dir/run-<n>/`` and aggregate.

    Args:
        corpus_dir: Directory of corpus JSON files.
        run_dir: Parent directory; each repeat gets its own ``run-<n>`` subdir.
        adapter: A :class:`bench.adapter.ScanAdapter`.
        repeats: Number of runs (>= 1).
        **kwargs: Forwarded to :func:`run_benchmark`.

    Returns:
        The aggregate dict from :func:`bench.tally.aggregate_scorecards`, also
        written to ``run_dir/scorecard_agg.{json,md}``.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for n in range(1, repeats + 1):
        d = run_benchmark(corpus_dir, run_dir / f"run-{n}", adapter, **kwargs)
        cards.append(Scorecard(overall=d["overall"], by_source=d["by_source"],
                               by_class=d["by_class"]))
    agg = aggregate_scorecards(cards)
    (run_dir / "scorecard_agg.json").write_text(json.dumps(agg, indent=2))
    (run_dir / "scorecard_agg.md").write_text(_agg_markdown(agg))
    return agg


def main(argv: list[str] | None = None) -> int:
    """CLI: run the benchmark. ``--binary`` drives a scanner binary; default reads
    an already-scanned workspace per repo (operator/CC-skill flow)."""
    p = argparse.ArgumentParser(prog="sec-overlay-bench")
    p.add_argument("--corpus", required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--binary", default=None, help="scanner binary argv (space-joined) to drive")
    p.add_argument("--workspaces", default=None, help="dir of pre-scanned workspaces (one per repo slug)")
    p.add_argument("--grade-mode", choices=("real", "detection"), default="real",
                   help="real = confirmed/fixed (default); detection = Tier-1-receipt candidates (CI)")
    p.add_argument("--only-local", action="store_true",
                   help="grade only local fixtures; skip http clone targets (offline CI gate)")
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--repeats", type=int, default=1,
                   help="run N times into run-<n>/ and write scorecard_agg.{json,md} (REQ-M5)")
    args = p.parse_args(argv)
    if args.repeats < 1:
        p.error("--repeats must be >= 1")
    reader = tier1_detected if args.grade_mode == "detection" else reportable
    if args.binary:
        if args.grade_mode == "detection":
            p.error("--grade-mode detection requires --workspaces, not --binary")
        adapter = BinaryAdapter(args.binary.split())
    elif args.workspaces:
        base = Path(args.workspaces)
        adapter = WorkspaceAdapter(lambda repo: Workspace(base / Path(repo).name), reader=reader)
    else:
        p.error("supply --binary or --workspaces")
    if args.repeats > 1:
        agg = run_repeated(args.corpus, args.run_dir, adapter, repeats=args.repeats,
                           resume=not args.no_resume, only_local=args.only_local)
        print(f"aggregate ({agg['repeats']} repeats): "
              f"recall mean={agg['recall']['mean']} precision mean={agg['precision']['mean']}")
        return 0
    sc = run_benchmark(args.corpus, args.run_dir, adapter, resume=not args.no_resume,
                       only_local=args.only_local)
    print(f"scorecard: real recall={sc['overall']['recall']} regressed={sc['regressed']}")
    return 1 if sc["regressed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
