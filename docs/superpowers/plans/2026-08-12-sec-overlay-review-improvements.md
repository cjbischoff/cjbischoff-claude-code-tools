# sec-overlay Review-Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four measurable improvements to the `sec-overlay` plugin — per-run token/self-score accounting, systemic finding clustering, external-boundary disposition, and SARIF completeness — each closing a gap found in the lumedeodorant run comparison.

**Architecture:** All four are Python-core changes under `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/` plus prose changes to `SKILL.md` and two agent prompts. Each new deterministic pass is a no-LLM module with its own CLI, following the existing `dedupe.py`/`calibrate.py` shape. Nothing changes the `Finding` contract destructively — the two new fields are additive and nullable, like the existing `duplicate_of`.

**Tech Stack:** Python 3.13, `uv`, `pytest`, `ruff`, `ty`. Dataclass models in `sec_overlay/models.py`; workspace I/O via `sec_overlay/workspace.py`; JSON Schema at `references/finding.schema.json`.

## Global Constraints

- Runtime: Python 3.13; run tests with `uv run pytest -q` from `plugins/sec-overlay/skills/sec-overlay/helpers`.
- Absolute imports only (`from sec_overlay.x import y`); no relative `../` imports.
- ≤100 lines per function; ≤8 cyclomatic complexity; 100-char lines.
- Structured Google-style docstrings on every new public function and module.
- TDD: write the failing test first, confirm it fails, then the minimal implementation. A commit that adds a new behavior and its test together with no prior RED is a process failure.
- Branch: `feat/sec-overlay-review-improvements`. No direct commits to `main`.
- Every commit updates root `README.md` and adds a `CHANGELOG.md` entry (Common Changelog). A commit that changes a file inside a Directory-Guide folder updates that folder's `README.md` in the same commit. The relevant folder here is `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` and `.../helpers/tests/README.md`.
- Do NOT bump the plugin `version` field — the user bumps it manually per release.
- Conventional Commits: `<type>(<scope>): <summary under 50 chars>`. I1's schema addition is a `feat`. I4's default SARIF change is a `feat` with a `### Changed` CHANGELOG entry (behavior change on upgrade).

---

## File Structure

**Phase I3 — token accounting + self-score**
- Modify `sec_overlay/cost.py` — add `aggregate_by_model`.
- Create `sec_overlay/selfscore.py` — build + persist the per-run self-score into `state.budget["self_score"]`.
- Modify `sec_overlay/report.py` — rename the token section to "Run economics"; add model mix + USD estimate.
- Modify `SKILL.md` — orchestration proxy-fallback note + call `selfscore` in phase C2.

**Phase I1 — systemic clustering**
- Modify `sec_overlay/models.py` — add `cluster_id`, `affected_sites` to `Finding`.
- Modify `references/finding.schema.json` — add the two fields.
- Create `sec_overlay/cluster.py` — no-LLM clustering pass after `dedupe`.
- Modify `sec_overlay/report.py` — collapse clusters to one representative in each bucket.

**Phase I2 — external-boundary disposition**
- Create `sec_overlay/scope.py` — read `kb/scan-scope.json`; `is_external_package`.
- Modify `sec_overlay/calibrate.py` — cap `risk_score` for `external-boundary` findings.
- Modify `sec_overlay/report.py` — render the external-unverifiable lead bucket.
- Modify `agents/validate.md`, `agents/trace.md` — set `reachability.blocker="external-boundary"`.

**Phase I4 — SARIF completeness**
- Modify `sec_overlay/sarif.py` — populate `driver.rules`; add optional suppressed NDT results + a confirmed-only flag.
- Modify `sec_overlay/report.py` — pass NDT findings and the flag into `to_sarif`.

---

## Phase I3 — Per-stage token accounting and self-score

### Task 1: Model-mix aggregation + "Run economics" report section

**Files:**
- Modify: `sec_overlay/cost.py` (add `aggregate_by_model`)
- Modify: `sec_overlay/report.py:293-296` (the `if token_spend:` block near the end of `to_markdown`) and `write_report` at `sec_overlay/report.py:340-352`
- Test: `tests/test_cost.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `cost.aggregate_by_phase(state) -> dict[str,int]`, `cost.estimate_cost_usd(state, rates=None) -> float`, `CampaignState.budget["records"]` = list of `{"phase","model","tokens"}`.
- Produces: `cost.aggregate_by_model(state) -> dict[str,int]`; a `to_markdown(..., economics: dict | None = None)` parameter carrying `{"by_phase": dict, "by_model": dict, "usd_estimate": float}`.

- [ ] **Step 1: Write the failing test for `aggregate_by_model`**

Add to `tests/test_cost.py`:

```python
def test_aggregate_by_model():
    st = _state()
    cost.record_agent(st, "investigate", "sonnet", 1000)
    cost.record_agent(st, "validate", "opus", 2000)
    cost.record_agent(st, "investigate", "sonnet", 500)
    assert cost.aggregate_by_model(st) == {"sonnet": 1500, "opus": 2000}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_cost.py::test_aggregate_by_model -v`
Expected: FAIL with `AttributeError: module 'sec_overlay.cost' has no attribute 'aggregate_by_model'`.

- [ ] **Step 3: Implement `aggregate_by_model` in `sec_overlay/cost.py`**

Add after `aggregate_by_phase`:

```python
def aggregate_by_model(state: CampaignState) -> dict[str, int]:
    """Sum recorded token usage by model.

    Args:
        state: Campaign state holding budget records.

    Returns:
        ``{model: total_tokens}`` (empty when nothing was recorded).
    """
    out: dict[str, int] = {}
    for rec in state.budget.get("records", []):
        model = rec.get("model", "default")
        out[model] = out.get(model, 0) + int(rec.get("tokens", 0))
    return out
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_cost.py::test_aggregate_by_model -v`
Expected: PASS.

- [ ] **Step 5: Write the failing test for the report economics section**

Add to `tests/test_report.py` (match the file's existing import/fixture style; findings can be an empty list — the section renders from `economics`):

```python
from sec_overlay.report import to_markdown


def test_run_economics_section_renders_phase_model_and_usd_estimate():
    econ = {"by_phase": {"investigate": 1500}, "by_model": {"sonnet": 1500},
            "usd_estimate": 0.0045}
    md = to_markdown([], economics=econ)
    assert "## Run economics" in md
    assert "investigate" in md and "sonnet" in md
    assert "estimate" in md.lower()          # USD must be labelled an estimate
    assert "$0.0045" in md
```

- [ ] **Step 6: Run it and confirm it fails**

Run: `uv run pytest tests/test_report.py::test_run_economics_section_renders_phase_model_and_usd_estimate -v`
Expected: FAIL — `to_markdown` has no `economics` parameter (TypeError) or the assertions miss.

- [ ] **Step 7: Add the `economics` parameter and section to `to_markdown`**

Change the `to_markdown` signature at `sec_overlay/report.py:192` to add `economics: dict | None = None` (keep `token_spend` for back-compat). Replace the existing `if token_spend:` block near line 293 with:

```python
    if economics:
        lines += ["", "## Run economics", ""]
        lines += ["**Tokens by phase** (measured):"]
        lines += [f"- **{phase}**: {n}" for phase, n in economics.get("by_phase", {}).items()]
        lines += ["", "**Tokens by model** (measured):"]
        lines += [f"- **{model}**: {n}" for model, n in economics.get("by_model", {}).items()]
        usd = economics.get("usd_estimate")
        if usd is not None:
            lines += ["", f"**Estimated cost:** ${usd:.4f} (estimate, not a billed figure)."]
    elif token_spend:
        lines += ["", "## Token spend by phase", ""]
        lines += [f"- **{phase}**: {n}" for phase, n in token_spend.items()]
```

- [ ] **Step 8: Run the report test and confirm it passes**

Run: `uv run pytest tests/test_report.py::test_run_economics_section_renders_phase_model_and_usd_estimate -v`
Expected: PASS.

- [ ] **Step 9: Wire `write_report` to build and pass `economics`**

In `write_report` (`sec_overlay/report.py`), replace the `token_spend = cost.aggregate_by_phase(load_state(ws)) or None` line with:

```python
    state = load_state(ws)
    by_phase = cost.aggregate_by_phase(state)
    economics = {
        "by_phase": by_phase,
        "by_model": cost.aggregate_by_model(state),
        "usd_estimate": cost.estimate_cost_usd(state),
    } if by_phase else None
```

Then change the `to_markdown(...)` call to pass `economics=economics` instead of `token_spend=token_spend`.

- [ ] **Step 10: Run the full report + cost suites**

Run: `uv run pytest tests/test_report.py tests/test_cost.py -q`
Expected: PASS (no regressions).

- [ ] **Step 11: Commit**

```bash
git add sec_overlay/cost.py sec_overlay/report.py tests/test_cost.py tests/test_report.py
# from repo root, also stage governance docs (see Step 12)
git commit -m "feat(sec-overlay): add run-economics report section"
```

- [ ] **Step 12: Update governance docs in the same commit**

Before committing, update from the repo root: root `README.md` Status line, `CHANGELOG.md` `## Unreleased` → `### Added`, and `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md` (new `aggregate_by_model`) and `.../helpers/tests/README.md` if it lists test files. Stage all with `git add -A` before the commit above.

---

### Task 2: Per-run self-score persisted to state

**Files:**
- Create: `sec_overlay/selfscore.py`
- Test: `tests/test_selfscore.py`

**Interfaces:**
- Consumes: `read_findings(ws) -> list[Finding]`, `load_state(ws)`, `save_state(ws, state)`, `FindingStatus`, finding fields `status`, `cluster_id`, `reachability`.
- Produces: `selfscore.build_self_score(ws) -> dict`, `selfscore.write_self_score(ws) -> dict`. The dict keys: `reported`, `confirmed`, `needs_runtime`, `rejected`, `clusters`, `external_boundary`. Persisted at `state.budget["self_score"]`.

> Note: `cluster_id` and `reachability.blocker` are read defensively with `getattr`/`.get`, so this task lands before I1/I2 and simply reports 0 for those counts until they exist.

- [ ] **Step 1: Write the failing test**

Create `tests/test_selfscore.py`:

```python
from sec_overlay import selfscore
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace, write_findings


def _f(id_, status, **kw):
    return Finding(id=id_, rule_id="r", cls="authz", status=status,
                   severity=Severity.MEDIUM, file="a.py", line=1, message="m", **kw)


def test_self_score_counts_by_status_and_persists(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        _f("F-1", FindingStatus.CONFIRMED),
        _f("F-2", FindingStatus.FIXED),
        _f("F-3", FindingStatus.NEEDS_DEPLOYMENT_TESTING),
        _f("F-4", FindingStatus.REJECTED),
        _f("F-5", FindingStatus.NEEDS_DEPLOYMENT_TESTING, cluster_id="cluster:F-5"),
        _f("F-6", FindingStatus.NEEDS_DEPLOYMENT_TESTING, cluster_id="cluster:F-5",
           reachability={"reachable": False, "blocker": "external-boundary"}),
    ])
    score = selfscore.write_self_score(ws)
    assert score == {"reported": 2, "confirmed": 1, "needs_runtime": 3,
                     "rejected": 1, "clusters": 1, "external_boundary": 1}
    assert load_state(ws).budget["self_score"] == score
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_selfscore.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.selfscore'`.

- [ ] **Step 3: Implement `sec_overlay/selfscore.py`**

```python
"""Per-run self-score: post-gate finding counts written back to state.

The self-score reads finding records after the gate, so its counts match
``findings`` exactly. It is a run-quality signal (reported vs needs-runtime,
cluster count, rejected count, external-boundary count), not a re-score.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sec_overlay.models import FindingStatus
from sec_overlay.state import load_state, save_state
from sec_overlay.workspace import Workspace, read_findings

_REPORTED = {FindingStatus.CONFIRMED, FindingStatus.FIXED}


def build_self_score(ws: Workspace) -> dict:
    """Compute the per-run self-score from workspace findings.

    Args:
        ws: Finished-scan workspace.

    Returns:
        ``{reported, confirmed, needs_runtime, rejected, clusters,
        external_boundary}`` — all ints.
    """
    findings = read_findings(ws)
    clusters = {f.cluster_id for f in findings if getattr(f, "cluster_id", None)}
    external = sum(
        1 for f in findings
        if (f.reachability or {}).get("blocker") == "external-boundary"
    )
    return {
        "reported": sum(1 for f in findings if f.status in _REPORTED),
        "confirmed": sum(1 for f in findings if f.status is FindingStatus.CONFIRMED),
        "needs_runtime": sum(
            1 for f in findings if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING
        ),
        "rejected": sum(1 for f in findings if f.status is FindingStatus.REJECTED),
        "clusters": len(clusters),
        "external_boundary": external,
    }


def write_self_score(ws: Workspace) -> dict:
    """Build the self-score and persist it at ``state.budget['self_score']``.

    Args:
        ws: Finished-scan workspace.

    Returns:
        The self-score dict that was persisted.
    """
    score = build_self_score(ws)
    state = load_state(ws)
    state.budget["self_score"] = score
    save_state(ws, state)
    return score


def main(argv: list[str] | None = None) -> int:
    """CLI: write the per-run self-score into state.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-selfscore")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    score = write_self_score(Workspace(Path(args.workspace)))
    print(f"self-score: {score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_selfscore.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): add per-run self-score module"
```
Include in the same commit: root `README.md` Status, `CHANGELOG.md` `### Added`, `sec_overlay/README.md` (new module), `tests/README.md` (new test file).

---

### Task 3: SKILL.md orchestration — reliable recording + proxy fallback + C2 call

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md` (orchestration section around line 125; phase C2 around line 549)

This task is prose (LLM orchestration instructions), so it has no unit test. Its deliverable is the documented, unambiguous instruction.

- [ ] **Step 1: Add the proxy-fallback instruction near line 125**

After the existing `cost.record_agent(...)` guidance, add:

```markdown
If the harness does not surface a subagent's token usage, record a labelled proxy
instead of a fabricated token count: call
`cost.record_agent(state, <phase>, <model>, 0)` and additionally note the agent
count and output byte size in the run log. Never write an invented number into the
`tokens` field. The Run-economics section states "measured" only for real usage.
```

- [ ] **Step 2: Add the self-score call to phase C2**

In the phase C2 block (after the postflight command near line 549), add:

```markdown
After postflight, write the per-run self-score:
`python -m sec_overlay.selfscore --workspace "$WS"`. It persists post-gate counts
(reported, needs-runtime, rejected, clusters, external-boundary) to
`state.json` `budget.self_score` for the next run to calibrate against.
```

- [ ] **Step 3: Commit (with governance docs)**

```bash
git add -A
git commit -m "docs(sec-overlay): wire token proxy + self-score into SKILL"
```
Update root `README.md` Status and `CHANGELOG.md` `### Added` in the same commit. `SKILL.md` is not inside a Directory-Guide subfolder that has its own README, so no folder-README update is required beyond the skill directory's own if one exists — check `plugins/sec-overlay/skills/sec-overlay/README.md` and update if it describes the orchestration.

---

## Phase I1 — Systemic finding clustering

### Task 4: Add `cluster_id` and `affected_sites` to the model and schema

**Files:**
- Modify: `sec_overlay/models.py` (the `Finding` dataclass field block, after `open_questions`)
- Modify: `references/finding.schema.json` (properties block)
- Test: `tests/test_models.py` (or wherever `Finding.from_dict` round-trips are tested — otherwise add there), `tests/test_finding_schema.py`

**Interfaces:**
- Produces: `Finding.cluster_id: str | None = None`; `Finding.affected_sites: list[dict] = field(default_factory=list)`. Both survive `to_dict`/`from_dict` round-trips and validate against the schema.

- [ ] **Step 1: Write the failing round-trip test**

Add to `tests/test_models.py`:

```python
from sec_overlay.models import Finding, FindingStatus, Severity


def test_cluster_fields_round_trip():
    f = Finding(id="F-1", rule_id="r", cls="authz", status=FindingStatus.RAW,
                severity=Severity.MEDIUM, file="a.py", line=1, message="m",
                cluster_id="cluster:F-1",
                affected_sites=[{"id": "F-2", "file": "b.py", "line": 5}])
    d = f.to_dict()
    assert d["cluster_id"] == "cluster:F-1"
    assert d["affected_sites"] == [{"id": "F-2", "file": "b.py", "line": 5}]
    back = Finding.from_dict(d)
    assert back.cluster_id == "cluster:F-1"
    assert back.affected_sites == [{"id": "F-2", "file": "b.py", "line": 5}]
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_models.py::test_cluster_fields_round_trip -v`
Expected: FAIL — `TypeError: Finding.__init__() got an unexpected keyword argument 'cluster_id'`.

- [ ] **Step 3: Add the two fields to `Finding` in `sec_overlay/models.py`**

After `open_questions: list[dict] = field(default_factory=list)` add:

```python
    cluster_id: str | None = None
    affected_sites: list[dict] = field(default_factory=list)
```

Also extend the `Attributes:` docstring with one line each: `cluster_id` — id of the systemic cluster this finding belongs to (set by the cluster pass); `affected_sites` — on a cluster primary only, the list of member sites `{"id","file","line"}`.

- [ ] **Step 4: Run the round-trip test and confirm it passes**

Run: `uv run pytest tests/test_models.py::test_cluster_fields_round_trip -v`
Expected: PASS.

- [ ] **Step 5: Write the failing schema test**

Add to `tests/test_finding_schema.py` (mirror the file's existing validation helper — it loads `references/finding.schema.json` and validates a finding dict):

```python
def test_schema_accepts_cluster_fields(schema):   # reuse the module's schema fixture/loader
    import jsonschema
    doc = {"id": "F-1", "rule_id": "r", "cls": "authz", "status": "raw",
           "severity": "medium", "file": "a.py", "line": 1, "message": "m",
           "cluster_id": "cluster:F-1",
           "affected_sites": [{"id": "F-2", "file": "b.py", "line": 5}]}
    jsonschema.validate(doc, schema)   # must not raise
```

If the test module has no `schema` fixture, load it inline: `schema = json.loads((Path(__file__).parents[1] / "references" / "finding.schema.json").read_text())` — match the existing pattern in the file.

- [ ] **Step 6: Run it and confirm it fails or passes-vacuously**

Run: `uv run pytest tests/test_finding_schema.py::test_schema_accepts_cluster_fields -v`
Expected: If the schema sets `additionalProperties: false`, FAIL (unknown field). If it does not, the test passes but does not yet assert the fields are *typed*. Either way, proceed to Step 7 to declare the fields explicitly.

- [ ] **Step 7: Add the two properties to `references/finding.schema.json`**

In the `properties` block (after `open_questions`) add:

```json
    "cluster_id": {"type": ["string", "null"]},
    "affected_sites": {"type": "array", "items": {"type": "object"}}
```

- [ ] **Step 8: Run the schema suite and confirm green**

Run: `uv run pytest tests/test_finding_schema.py -q`
Expected: PASS.

- [ ] **Step 9: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): add cluster fields to finding model"
```
Update root `README.md`, `CHANGELOG.md` `### Added`. `references/` has its own README if listed in the Directory Guide — update `references/README.md` if it documents the schema fields. Update `sec_overlay/README.md` for the model change and `tests/README.md` for the new tests.

---

### Task 5: The clustering pass

**Files:**
- Create: `sec_overlay/cluster.py`
- Test: `tests/test_cluster.py`

**Interfaces:**
- Consumes: `read_findings`/`write_findings`, `load_graph`/`symbol_at` (optional graph), `FindingStatus.RAW`, the severity order, `record_stage`.
- Produces: `cluster.cluster_findings(ws) -> int` (number of findings stamped with a `cluster_id`). Elects a `cluster_primary` per group of ≥3, stamps `cluster_id` on all members, and sets `affected_sites` on the primary.

**Invariant:** every member of a cluster shares one `cluster_id`; exactly one member per cluster carries non-empty `affected_sites`; only `RAW` findings are clustered (never `CONFIRMED`); a group needs ≥3 sites.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cluster.py`:

```python
"""Tests for the systemic clustering pass."""

from sec_overlay.cluster import cluster_findings
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, read_findings, write_findings


def _f(id_, sev, line, status=FindingStatus.RAW, cls="authz", sink="ownsResource"):
    # No graph in tmp_path -> sink symbol resolves from the last dataflow hop.
    return Finding(id=id_, rule_id="r", cls=cls, status=status, severity=sev,
                   file=f"route_{id_}.py", line=line, message="missing owner check",
                   dataflow=["req.params.id", sink])


def test_clusters_three_or_more_same_class_same_sink(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        _f("F-1", Severity.MEDIUM, 10),
        _f("F-2", Severity.HIGH, 11),
        _f("F-3", Severity.MEDIUM, 12),
    ])
    n = cluster_findings(ws)
    assert n == 3
    by_id = {f.id: f for f in read_findings(ws)}
    # Primary is highest severity, tiebreak smallest id -> F-2.
    assert by_id["F-2"].cluster_id == "cluster:F-2"
    assert by_id["F-1"].cluster_id == "cluster:F-2"
    assert by_id["F-3"].cluster_id == "cluster:F-2"
    assert len(by_id["F-2"].affected_sites) == 3          # primary carries all sites
    assert by_id["F-1"].affected_sites == []              # members do not
    site_ids = {s["id"] for s in by_id["F-2"].affected_sites}
    assert site_ids == {"F-1", "F-2", "F-3"}


def test_two_sites_do_not_cluster(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [_f("F-1", Severity.HIGH, 10), _f("F-2", Severity.HIGH, 11)])
    assert cluster_findings(ws) == 0
    assert all(f.cluster_id is None for f in read_findings(ws))


def test_different_sink_does_not_cluster(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        _f("F-1", Severity.HIGH, 10, sink="ownsResource"),
        _f("F-2", Severity.HIGH, 11, sink="ownsResource"),
        _f("F-3", Severity.HIGH, 12, sink="somethingElse"),
    ])
    assert cluster_findings(ws) == 0     # only 2 share ownsResource; needs 3


def test_confirmed_findings_are_never_clustered(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        _f("F-1", Severity.HIGH, 10, status=FindingStatus.CONFIRMED),
        _f("F-2", Severity.HIGH, 11),
        _f("F-3", Severity.HIGH, 12),
    ])
    assert cluster_findings(ws) == 0     # only 2 RAW share the sink; F-1 excluded
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_cluster.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.cluster'`.

- [ ] **Step 3: Implement `sec_overlay/cluster.py`**

```python
"""Deterministic systemic clustering: group ≥3 same-class, same-sink RAW findings.

The lumedeodorant run reported 12 findings that were one authorization pattern
across 12 routes. Dedupe only merges exact ``(file, line, cls)`` collisions, so
distinct-file siblings never merged. This pass groups them into one systemic
cluster without dropping any member: each route stays individually addressable,
but the report and machine consumers see one headline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sec_overlay.campaign import record_stage
from sec_overlay.graph import load_graph, symbol_at
from sec_overlay.models import Finding, FindingStatus
from sec_overlay.workspace import Workspace, read_findings, write_findings

_SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
_MIN_CLUSTER = 3


def _sink_symbol(graph, f: Finding) -> str | None:
    """Resolve the sink symbol for a finding.

    Prefers the enclosing symbol from the graph substrate (refactor-resistant);
    falls back to the last dataflow hop when no graph is available.

    Args:
        graph: Loaded graph or ``None``.
        f: The finding.

    Returns:
        The sink symbol name, or ``None`` when it cannot be resolved.
    """
    if graph is not None:
        sym = symbol_at(graph, f.file, f.line)
        if sym:
            return sym
    return f.dataflow[-1] if f.dataflow else None


def cluster_findings(ws: Workspace) -> int:
    """Group RAW findings that share ``(cls, sink_symbol)`` into systemic clusters.

    A group of ≥3 elects a primary (highest severity, tiebreak smallest id),
    stamps every member with ``cluster_id = "cluster:<primary-id>"``, and records
    all member sites on the primary's ``affected_sites``. Only ``RAW`` findings are
    considered; ``CONFIRMED`` and every other status are left untouched.

    Args:
        ws: Workspace whose findings are clustered in place.

    Returns:
        The number of findings stamped with a ``cluster_id``.
    """
    findings = read_findings(ws)
    graph = load_graph(ws) if (ws.kb / "graph.json").exists() else None

    groups: dict[tuple[str, str], list[Finding]] = {}
    for f in findings:
        if f.status is not FindingStatus.RAW:
            continue
        sink = _sink_symbol(graph, f)
        if sink is None:
            continue
        groups.setdefault((f.cls, sink), []).append(f)

    stamped = 0
    for members in groups.values():
        if len(members) < _MIN_CLUSTER:
            continue
        primary = min(members, key=lambda f: (-_SEVERITY_ORDER[f.severity.value], f.id))
        cid = f"cluster:{primary.id}"
        sites = [{"id": m.id, "file": m.file, "line": m.line} for m in members]
        for m in members:
            m.cluster_id = cid
            m.history.append({"event": f"cluster:{cid}"})
            stamped += 1
        primary.affected_sites = sites

    if stamped:
        write_findings(ws, findings)
    record_stage(ws, "cluster")
    return stamped


def main(argv: list[str] | None = None) -> int:
    """CLI: cluster a workspace's RAW findings.

    Args:
        argv: Optional argument vector.

    Returns:
        0 on success.
    """
    parser = argparse.ArgumentParser(prog="sec-overlay-cluster")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    n = cluster_findings(Workspace(Path(args.workspace)))
    print(f"clustered {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the cluster tests and confirm they pass**

Run: `uv run pytest tests/test_cluster.py -v`
Expected: PASS (all four).

- [ ] **Step 5: Document the pipeline position in SKILL.md**

Add a one-line instruction after the `dedupe` step in `SKILL.md`: run `python -m sec_overlay.cluster --workspace "$WS"` immediately after dedupe and before the critic/gate ladder.

- [ ] **Step 6: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): add systemic clustering pass"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md` (new module + CLI), `tests/README.md`, and the `SKILL.md` pipeline order.

---

### Task 6: Collapse clusters to one representative in the report

**Files:**
- Modify: `sec_overlay/report.py` (`render_ndt` at line 147; `write_report` NDT selection near line 340; add a `collapse_clusters` helper)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `Finding.cluster_id`, `Finding.affected_sites`, `_risk_sort_key`.
- Produces: `report.collapse_clusters(findings: list[Finding]) -> list[Finding]` — returns one representative per `cluster_id` (the member carrying `affected_sites`, else the highest-risk member, with sites synthesized), plus all un-clustered findings unchanged.

**Invariant:** the reported headline count treats one cluster as one item; the representative renders a sites table listing every member.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_report.py`:

```python
from sec_overlay.report import collapse_clusters, render_ndt
from sec_overlay.models import Finding, FindingStatus, Severity


def _ndt(id_, cluster_id=None, affected=None):
    return Finding(id=id_, rule_id="r", cls="authz",
                   status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                   severity=Severity.MEDIUM, file=f"r_{id_}.py", line=1,
                   message="missing owner check", cluster_id=cluster_id,
                   affected_sites=affected or [])


def test_collapse_clusters_keeps_one_representative():
    sites = [{"id": "F-1", "file": "r_F-1.py", "line": 1},
             {"id": "F-2", "file": "r_F-2.py", "line": 1},
             {"id": "F-3", "file": "r_F-3.py", "line": 1}]
    findings = [_ndt("F-1", "cluster:F-2"),
                _ndt("F-2", "cluster:F-2", sites),   # primary carries affected_sites
                _ndt("F-3", "cluster:F-2"),
                _ndt("F-9")]                          # un-clustered
    reps = collapse_clusters(findings)
    assert len(reps) == 2                             # one cluster + one singleton
    rep_ids = {f.id for f in reps}
    assert rep_ids == {"F-2", "F-9"}


def test_render_ndt_shows_affected_sites_table():
    sites = [{"id": "F-1", "file": "r_F-1.py", "line": 1},
             {"id": "F-2", "file": "r_F-2.py", "line": 1},
             {"id": "F-3", "file": "r_F-3.py", "line": 1}]
    md = render_ndt(_ndt("F-2", "cluster:F-2", sites))
    assert "Affected sites" in md
    assert "r_F-1.py" in md and "r_F-3.py" in md
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_report.py::test_collapse_clusters_keeps_one_representative tests/test_report.py::test_render_ndt_shows_affected_sites_table -v`
Expected: FAIL — `ImportError: cannot import name 'collapse_clusters'` and the sites table assertion.

- [ ] **Step 3: Add `collapse_clusters` to `sec_overlay/report.py`**

```python
def collapse_clusters(findings: list[Finding]) -> list[Finding]:
    """Reduce each systemic cluster to a single representative finding.

    Un-clustered findings pass through unchanged. For each ``cluster_id`` group the
    representative is the member carrying ``affected_sites`` (the elected primary);
    if that member is absent from this bucket, the highest-risk member is chosen and
    its ``affected_sites`` is synthesized from the group so the sites table is intact.

    Args:
        findings: Findings in one report bucket.

    Returns:
        One representative per cluster plus every un-clustered finding.
    """
    singletons = [f for f in findings if not f.cluster_id]
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        if f.cluster_id:
            groups.setdefault(f.cluster_id, []).append(f)
    reps: list[Finding] = list(singletons)
    for members in groups.values():
        primary = next((m for m in members if m.affected_sites), None)
        if primary is None:
            primary = min(members, key=_risk_sort_key)
            primary.affected_sites = [
                {"id": m.id, "file": m.file, "line": m.line} for m in members
            ]
        reps.append(primary)
    return reps
```

- [ ] **Step 4: Render the sites table in `render_ndt`**

In `render_ndt` (`sec_overlay/report.py:147`), before the trailing `_Runnable payloads..._` line, add:

```python
    if f.affected_sites:
        out += ["", f"**Affected sites ({len(f.affected_sites)}).** One systemic pattern:",
                "", "| id | location |", "|----|----------|"]
        out += [f"| {s['id']} | `{s['file']}:{s['line']}` |" for s in f.affected_sites]
        out += [""]
```

- [ ] **Step 5: Apply collapse in `write_report`**

In `write_report` (`sec_overlay/report.py` near line 343), after `ndt = [f for f in all_findings if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING]`, wrap both buckets:

```python
    reportable = collapse_clusters(reportable)
    ndt = collapse_clusters(ndt)
```

Place these after `reportable`/`ndt` are first computed and before they are counted or rendered.

- [ ] **Step 6: Run the report suite and confirm green**

Run: `uv run pytest tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 7: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): collapse clusters in the report"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md`, `tests/README.md`.

---

## Phase I2 — External-boundary confidence disposition

### Task 7: Ingested-package manifest + boundary check

**Files:**
- Create: `sec_overlay/scope.py`
- Test: `tests/test_scope.py`

**Interfaces:**
- Consumes: `ws.kb / "scan-scope.json"` with shape `{"ingested_packages": [str, ...]}`.
- Produces: `scope.is_external_package(pkg: str, ws: Workspace) -> bool` — `True` when `pkg` is not in the ingested manifest (i.e. its source was not scanned). Returns `False` (cannot decide it is external) when no manifest exists, so the check never invents a boundary.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scope.py`:

```python
import json

from sec_overlay import scope
from sec_overlay.workspace import Workspace


def _ws(tmp_path, packages=None):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    if packages is not None:
        ws.kb.mkdir(parents=True, exist_ok=True)
        (ws.kb / "scan-scope.json").write_text(json.dumps({"ingested_packages": packages}))
    return ws


def test_package_absent_from_manifest_is_external(tmp_path):
    ws = _ws(tmp_path, packages=["@lume/web"])
    assert scope.is_external_package("@lume/account-portal-core", ws) is True


def test_package_in_manifest_is_not_external(tmp_path):
    ws = _ws(tmp_path, packages=["@lume/web", "@lume/account-portal-core"])
    assert scope.is_external_package("@lume/account-portal-core", ws) is False


def test_no_manifest_never_invents_a_boundary(tmp_path):
    ws = _ws(tmp_path, packages=None)
    assert scope.is_external_package("@lume/anything", ws) is False
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_scope.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sec_overlay.scope'`.

- [ ] **Step 3: Implement `sec_overlay/scope.py`**

```python
"""Ingested-source scope: decide whether a dependency was scanned or is external.

A dataflow sink that resolves into a package whose source was never ingested cannot
be confirmed from source. This module makes that boundary check deterministic via a
``kb/scan-scope.json`` manifest instead of guessing.
"""

from __future__ import annotations

import json

from sec_overlay.workspace import Workspace


def _ingested_packages(ws: Workspace) -> set[str] | None:
    """Load the ingested-package set from the manifest, or ``None`` if absent.

    Args:
        ws: Workspace holding ``kb/scan-scope.json``.

    Returns:
        The set of ingested package names, or ``None`` when no manifest exists.
    """
    path = ws.kb / "scan-scope.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return set(data.get("ingested_packages", []))


def is_external_package(pkg: str, ws: Workspace) -> bool:
    """Report whether ``pkg`` was outside the ingested source set.

    Args:
        pkg: Dependency/package name a sink resolves into.
        ws: Workspace holding the scan-scope manifest.

    Returns:
        ``True`` only when a manifest exists and ``pkg`` is not in it. Without a
        manifest, returns ``False`` — the check never invents a boundary.
    """
    ingested = _ingested_packages(ws)
    if ingested is None:
        return False
    return pkg not in ingested
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `uv run pytest tests/test_scope.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): add ingested-package scope check"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md`, `tests/README.md`.

---

### Task 8: Cap risk for external-boundary findings in calibrate

**Files:**
- Modify: `sec_overlay/calibrate.py` (`calibrate_findings` loop near line 130; add a cap constant + helper)
- Test: `tests/test_calibrate.py`

**Interfaces:**
- Consumes: `Finding.reachability` (`{"blocker": "external-boundary"}`), `Finding.completeness_tier`.
- Produces: an external-boundary finding's `risk_score` is capped at `_EXTERNAL_CAP = 3` (below the medium floor of 4) and its `completeness_tier` is set to `"external-unverifiable"`, so it can never present as a confirmed medium.

**Invariant:** a finding whose `reachability.blocker == "external-boundary"` ends calibration with `risk_score <= 3` and `completeness_tier == "external-unverifiable"`, regardless of its claimed severity.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_calibrate.py` (match its workspace/write_findings pattern):

```python
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.calibrate import calibrate_findings
from sec_overlay.workspace import Workspace, read_findings, write_findings


def test_external_boundary_finding_is_capped_and_tagged(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    f = Finding(id="F-1", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.MEDIUM, file="a.py", line=1, message="m",
                reachability={"reachable": False, "blocker": "external-boundary"})
    write_findings(ws, [f])
    calibrate_findings(ws)
    out = read_findings(ws)[0]
    assert out.risk_score <= 3                         # below the medium floor of 4
    assert out.completeness_tier == "external-unverifiable"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_calibrate.py::test_external_boundary_finding_is_capped_and_tagged -v`
Expected: FAIL — `risk_score` floors at 4 (medium) and `completeness_tier` is `None`.

- [ ] **Step 3: Add the cap in `sec_overlay/calibrate.py`**

Add near the other module constants:

```python
_EXTERNAL_CAP = 3  # external-boundary leads cannot present as a confirmed medium (>=4)
```

Add a small helper above `calibrate_findings`:

```python
def _is_external_boundary(finding: Finding) -> bool:
    """True when the finding's sink crosses into an un-ingested dependency."""
    return (finding.reachability or {}).get("blocker") == "external-boundary"
```

Inside the `for f in findings:` loop of `calibrate_findings`, after `f.risk_score` is set (and after the judge-downgrade block), add:

```python
                if _is_external_boundary(f):
                    f.risk_score = min(f.risk_score, _EXTERNAL_CAP)
                    f.completeness_tier = "external-unverifiable"
                    if not any(h.get("event") == "calibrate:external-boundary"
                               for h in f.history):
                        f.history.append({"event": "calibrate:external-boundary"})
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_calibrate.py::test_external_boundary_finding_is_capped_and_tagged -v`
Expected: PASS.

- [ ] **Step 5: Run the full calibrate suite for regressions**

Run: `uv run pytest tests/test_calibrate.py -q`
Expected: PASS.

- [ ] **Step 6: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): cap external-boundary finding risk"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md`, `tests/README.md`.

---

### Task 9: Render the external-unverifiable lead bucket

**Files:**
- Modify: `sec_overlay/report.py` (`to_markdown` near line 192; `write_report` near line 340)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `Finding.completeness_tier == "external-unverifiable"`.
- Produces: a distinct report section, "Leads — pending external-dependency verification", separate from the source-provable NDT bucket.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_report.py`:

```python
def test_external_leads_render_in_their_own_bucket():
    f = Finding(id="F-1", rule_id="r", cls="authz",
                status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                severity=Severity.MEDIUM, file="a.py", line=1,
                message="owner check may live in @lume/account-portal-core",
                completeness_tier="external-unverifiable",
                preconditions=["ownership check in @lume/account-portal-core"])
    md = to_markdown([], needs_deployment=[f])
    assert "pending external-dependency verification" in md.lower()
    assert "@lume/account-portal-core" in md
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_report.py::test_external_leads_render_in_their_own_bucket -v`
Expected: FAIL — the external heading is absent.

- [ ] **Step 3: Split the external bucket in `to_markdown`**

In `to_markdown`, where `needs_deployment` is sorted into `ndt` (line ~222), partition it:

```python
    ndt_all = sorted(needs_deployment or [], key=_risk_sort_key)
    external = [f for f in ndt_all if f.completeness_tier == "external-unverifiable"]
    ndt = [f for f in ndt_all if f.completeness_tier != "external-unverifiable"]
```

Keep the existing NDT rendering driven by `ndt`. After that section, add:

```python
    if external:
        lines += ["", "## Leads — pending external-dependency verification", "",
                  ("These findings' sinks cross into a package whose source was not "
                   "ingested. They are capped leads, not confirmed findings.")]
        for f in external:
            lines += ["", render_ndt(f)]
```

Use the actual local variable name the function uses for its output list (it is `lines` in this module).

- [ ] **Step 4: Apply the same partition in `write_report`**

`write_report` already passes the full NDT list into `to_markdown`, which now partitions internally — no change needed there beyond the Task 6 `collapse_clusters(ndt)` call, which stays. Confirm `collapse_clusters` runs before `to_markdown` so external leads are also cluster-collapsed.

- [ ] **Step 5: Run the report suite and confirm green**

Run: `uv run pytest tests/test_report.py -q`
Expected: PASS.

- [ ] **Step 6: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): render external-dependency lead bucket"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md`, `tests/README.md`.

---

### Task 10: Agent prompts set the external-boundary blocker

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/validate.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/trace.md`

This task is prose (agent instructions), no unit test. Its deliverable is the unambiguous instruction that produces the `reachability.blocker` value Task 8 consumes.

- [ ] **Step 1: Add the instruction to `agents/trace.md`**

In the dataflow-tracing section, add:

```markdown
When a sink resolves into a dependency whose source is not in the ingested set
(check `kb/scan-scope.json`), set `reachability.blocker = "external-boundary"` and
record the package name in `preconditions` (e.g. "ownership check in
@lume/account-portal-core"). Do not mark the finding reachable or confirmed from
source you cannot read.
```

- [ ] **Step 2: Add the matching instruction to `agents/validate.md`**

Add a line telling the validate agent not to promote an `external-boundary` finding to `confirmed`; it stays a lead that the calibrate cap and the report's external bucket handle.

- [ ] **Step 3: Commit (with governance docs)**

```bash
git add -A
git commit -m "docs(sec-overlay): set external-boundary blocker in agents"
```
`agents/` has its own README per the Directory Guide — update `agents/README.md` if it summarizes prompt behavior. Update root `README.md` and `CHANGELOG.md` `### Added`.

---

## Phase I4 — SARIF completeness

### Task 11: Populate `driver.rules` from the finding set

**Files:**
- Modify: `sec_overlay/sarif.py` (`to_sarif`)
- Test: `tests/test_sarif.py`

**Interfaces:**
- Consumes: `Finding.rule_id`, `Finding.cls`, `Finding.asvs_ids`, `Finding.codeguard_ids`.
- Produces: `to_sarif` emits a de-duplicated `driver.rules` array; each rule has `id` (the `rule_id`), a `name` (the `cls`), and `properties` with `asvs_ids`/`codeguard_ids`. Strictly additive — `results` are unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_sarif.py` (match its `Finding` construction style):

```python
def test_driver_rules_populated_from_findings():
    findings = [
        Finding(id="F-1", rule_id="authz-owner", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="a.py", line=1, message="m",
                asvs_ids=["4.2.1"], codeguard_ids=["CG-12"]),
        Finding(id="F-2", rule_id="authz-owner", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="b.py", line=2, message="m"),
    ]
    doc = to_sarif(findings)
    rules = doc["runs"][0]["tool"]["driver"]["rules"]
    assert len(rules) == 1                              # deduped by rule_id
    rule = rules[0]
    assert rule["id"] == "authz-owner"
    assert rule["properties"]["asvs_ids"] == ["4.2.1"]
    assert rule["properties"]["codeguard_ids"] == ["CG-12"]
```

Import `Finding`, `FindingStatus`, `Severity` at the top of the test if not already present.

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_sarif.py::test_driver_rules_populated_from_findings -v`
Expected: FAIL — `rules` is `[]`.

- [ ] **Step 3: Build the rules array in `to_sarif`**

Add a helper above `to_sarif`:

```python
def _rules(findings: list[Finding]) -> list[dict]:
    """Build a de-duplicated SARIF rule array from the finding set.

    Args:
        findings: Findings to derive rules from.

    Returns:
        One rule per distinct ``rule_id``, carrying ``cls`` as the name and
        ASVS/CodeGuard ids as properties. First occurrence of a ``rule_id`` wins.
    """
    by_id: dict[str, dict] = {}
    for f in findings:
        if f.rule_id in by_id:
            continue
        by_id[f.rule_id] = {
            "id": f.rule_id,
            "name": f.cls,
            "properties": {"asvs_ids": list(f.asvs_ids),
                           "codeguard_ids": list(f.codeguard_ids)},
        }
    return list(by_id.values())
```

In `to_sarif`, replace `"rules": []` with `"rules": _rules(findings)`.

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/test_sarif.py::test_driver_rules_populated_from_findings -v`
Expected: PASS.

- [ ] **Step 5: Run the full sarif suite**

Run: `uv run pytest tests/test_sarif.py -q`
Expected: PASS.

- [ ] **Step 6: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): populate SARIF driver.rules"
```
Update root `README.md`, `CHANGELOG.md` `### Added`, `sec_overlay/README.md`, `tests/README.md`.

---

### Task 12: Suppressed-full SARIF default + confirmed-only flag

**Files:**
- Modify: `sec_overlay/sarif.py` (`to_sarif` gains suppression support)
- Modify: `sec_overlay/report.py` (`write_report` passes NDT + a flag)
- Test: `tests/test_sarif.py`, `tests/test_report.py`

**Interfaces:**
- Consumes: `FindingStatus.NEEDS_DEPLOYMENT_TESTING`.
- Produces: `to_sarif(findings, tool_name="sec-overlay", suppressed=None)` — findings in the `suppressed` list get a `suppressions: [{"kind": "inSource", "justification": "needs runtime proof"}]` entry on their result; others carry none. `write_report` defaults to passing NDT findings as `suppressed`; a `confirmed_only` option restores the prior output.

**Invariant:** SARIF results carrying a `suppressions` entry are exactly the `needs-deployment-testing` findings; `confirmed`/`fixed` results carry no suppression.

- [ ] **Step 1: Write the failing SARIF test**

Add to `tests/test_sarif.py`:

```python
def test_suppressed_findings_carry_insource_suppression():
    confirmed = Finding(id="F-1", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
                        severity=Severity.HIGH, file="a.py", line=1, message="m")
    ndt = Finding(id="F-2", rule_id="r", cls="authz",
                  status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                  severity=Severity.MEDIUM, file="b.py", line=2, message="m")
    doc = to_sarif([confirmed, ndt], suppressed=[ndt])
    results = {r["ruleId"]: r for r in doc["runs"][0]["results"]}
    by_id = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]: r
             for r in doc["runs"][0]["results"]}
    assert "suppressions" not in by_id["a.py"]
    assert by_id["b.py"]["suppressions"][0]["kind"] == "inSource"
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `uv run pytest tests/test_sarif.py::test_suppressed_findings_carry_insource_suppression -v`
Expected: FAIL — `to_sarif` has no `suppressed` parameter.

- [ ] **Step 3: Add suppression support to `to_sarif`**

Change the signature to `def to_sarif(findings: list[Finding], tool_name: str = "sec-overlay", suppressed: list[Finding] | None = None) -> dict:` and build a suppressed-id set. In the result comprehension, add the suppression conditionally:

```python
    suppressed_ids = {f.id for f in (suppressed or [])}
    results = []
    for f in findings:
        result = {
            "ruleId": f.rule_id,
            "level": _level(f.severity),
            "message": {"text": f.message},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line},
                }
            }],
        }
        if f.id in suppressed_ids:
            result["suppressions"] = [
                {"kind": "inSource", "justification": "needs runtime proof"}
            ]
        results.append(result)
```

Keep `"rules": _rules(findings)` from Task 11.

- [ ] **Step 4: Run the SARIF test and confirm it passes**

Run: `uv run pytest tests/test_sarif.py::test_suppressed_findings_carry_insource_suppression -v`
Expected: PASS.

- [ ] **Step 5: Write the failing `write_report` test**

Add to `tests/test_report.py` (build a workspace with one confirmed + one NDT finding, run `write_report`, read `report.sarif`):

```python
import json
from sec_overlay.report import write_report
from sec_overlay.workspace import Workspace, write_findings


def test_write_report_defaults_to_suppressed_full_sarif(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        Finding(id="F-1", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="a.py", line=1, message="m", risk_score=7),
        Finding(id="F-2", rule_id="r", cls="authz",
                status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                severity=Severity.MEDIUM, file="b.py", line=2, message="m", risk_score=4),
    ])
    write_report(ws)
    doc = json.loads(ws.sarif_path.read_text())
    uris = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            for r in doc["runs"][0]["results"]}
    assert uris == {"a.py", "b.py"}                    # NDT now reaches SARIF


def test_write_report_confirmed_only_flag_restores_prior_output(tmp_path):
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    write_findings(ws, [
        Finding(id="F-1", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="a.py", line=1, message="m", risk_score=7),
        Finding(id="F-2", rule_id="r", cls="authz",
                status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                severity=Severity.MEDIUM, file="b.py", line=2, message="m", risk_score=4),
    ])
    write_report(ws, confirmed_only=True)
    doc = json.loads(ws.sarif_path.read_text())
    uris = {r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
            for r in doc["runs"][0]["results"]}
    assert uris == {"a.py"}                             # NDT excluded again
```

- [ ] **Step 6: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_report.py::test_write_report_defaults_to_suppressed_full_sarif tests/test_report.py::test_write_report_confirmed_only_flag_restores_prior_output -v`
Expected: FAIL — `write_report` has no `confirmed_only` parameter and SARIF currently carries confirmed only.

- [ ] **Step 7: Update `write_report` to emit suppressed-full by default**

Change the signature to `def write_report(ws: Workspace, *, target: str | None = None, confirmed_only: bool = False) -> dict:`. Where SARIF is written (line ~350):

```python
    if confirmed_only:
        sarif_findings, suppressed = reportable, None
    else:
        sarif_findings, suppressed = reportable + ndt, ndt
    ws.sarif_path.write_text(json.dumps(to_sarif(sarif_findings, suppressed=suppressed), indent=2))
```

Update the `write_report` docstring line that currently reads "SARIF carries confirmed/fixed only" to describe the new default (all reportable + suppressed NDT; `confirmed_only=True` restores the old behavior).

- [ ] **Step 8: Add the CLI flag**

In `report.main`, add `parser.add_argument("--confirmed-only", action="store_true")` and pass `confirmed_only=args.confirmed_only` into `write_report`.

- [ ] **Step 9: Run the report + sarif suites and confirm green**

Run: `uv run pytest tests/test_report.py tests/test_sarif.py -q`
Expected: PASS.

- [ ] **Step 10: Commit (with governance docs)**

```bash
git add -A
git commit -m "feat(sec-overlay): default SARIF to suppressed-full"
```
This is a behavior change on upgrade — the `CHANGELOG.md` entry goes under `### Changed`, not `### Added`, and states that default SARIF now includes suppressed `needs-deployment-testing` results, restorable with `--confirmed-only`. Update root `README.md`, `sec_overlay/README.md`, `tests/README.md`.

---

## Final verification

- [ ] **Run the full helper suite**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest -q`
Expected: prior green count plus the new tests; the two known env-only failures (gitignored bench corpus, excluded semgrep submodule) remain and are unrelated.

- [ ] **Lint and type-check**

Run: `uv run ruff check sec_overlay tests && uv run ruff format --check sec_overlay tests && uv run ty check sec_overlay`
Expected: no findings. Fix every warning before the final commit.

- [ ] **Validate the plugin manifest**

Run: `cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools && claude plugin validate .`
Expected: plugin and marketplace manifests validate.

- [ ] **Confirm no stray files and clean status**

Run: `git status --short`
Expected: clean tree; every change committed on `feat/sec-overlay-review-improvements`.

---

## Self-review notes (author check against the spec)

- **Spec coverage:** I3 → Tasks 1-3 (economics section, self-score, orchestration proxy). I1 → Tasks 4-6 (model+schema, cluster pass, report collapse). I2 → Tasks 7-10 (scope manifest, calibrate cap, external bucket, agent prompts). I4 → Tasks 11-12 (driver.rules, suppressed-full + flag). Every spec change point maps to a task.
- **Spec deviation resolved:** the spec said "select_reportable counts the cluster as one headline item," but `select_reportable` filters to CONFIRMED/FIXED while the 12-way pattern lives in the NDT tier. Task 6 collapses clusters in *both* buckets via `collapse_clusters`, which covers the real inflation case (NDT) and confirmed clusters alike. This is a faithful, more-complete reading; flag it during user/spec review if a stricter reading is wanted.
- **External-boundary status invariant:** the spec's "never reported as confirmed" is enforced in prose (Task 10 validate prompt) plus the calibrate cap + report bucket (Tasks 8-9). The Python guarantee is the cap and the bucket; the status guarantee is the agent's, matching how the existing NDT tier is assigned.
- **Ordering dependency:** Task 2's self-score reads `cluster_id`/`reachability` defensively, so it is correct before I1/I2 land (reports 0) and picks them up automatically after.
