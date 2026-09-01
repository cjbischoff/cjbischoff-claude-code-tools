# Group 5 — Render and Terminal Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the report's next-action point at the section that actually holds the finding, stop printing "(measured)" headers above empty bodies, and add a terminal gate that blocks AUDIT COMPLETE when the artifacts contradict each other.

**Architecture:** Two edits inside `helpers/sec_overlay/report.py` plus one new deterministic module, `helpers/sec_overlay/artifact_consistency.py`. The new module mirrors `artifact_gate.py`: a `run_artifact_consistency(ws) -> list[str]` function, a JSON audit trail under `kb/gates/`, and an argparse `main`. A new `PhaseSpec` runs it between `artifact-review` and `postflight`; the driver action raises `PhaseHalt` on any error.

**Tech Stack:** Python 3.11, stdlib only. Tests with `pytest`. Lint with `ruff`. Types with `ty`.

**Spec:** `docs/superpowers/specs/2026-08-23-sec-overlay-improvements-design.md` (REQ-03, REQ-05, REQ-31). Requirements source: `/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md`.

## Global Constraints

- Work on branch `feat/sec-overlay-improvements`. Never commit to `main`.
- One REQ per task. Each REQ ships as a red/green commit pair, with the REQ id in the body of both subjects.
- The commit-message hook caps the summary AFTER `type(scope): ` at 50 characters.
- Stage explicit paths only. Never `git add -A`, `git add .`, `git add -u`, or `git commit -a`. Never `--no-verify`.
- Run `prek run` before each commit.
- The prek folder-README hook binds a staged file to its **immediate** folder's `README.md`. Staging `helpers/sec_overlay/*.py` also stages `helpers/sec_overlay/README.md`. Staging `helpers/tests/*.py` also stages `helpers/tests/README.md`.
- `helpers/sec_overlay/README.md` and `helpers/tests/README.md` are append-only narrative logs.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` version in every commit that changes a shipping file. `feat` bumps minor; every other type bumps patch.
- Update `plugins/sec-overlay/CHANGELOG.md` in the same commit as the plugin change.
- The plugin core is stdlib-only. Add no dependency.
- Never edit `helpers/sec_overlay/models.py` or `helpers/sec_overlay/evidence.py`. `tests/test_frozen_contract.py` pins their SHA-256 digests.
- Never change the five never-silent report sections (`render_dropped_findings_section`, `render_position_review_section`, `render_reflection_retractions_section`, `render_reflection_skipped_section`, `render_review_source_skipped_section`). `tests/test_report.py:1058` pins them.
- Run every `git` command from the repository root. A stray nested git repository sits at `helpers/.git`.
- Gate commands, run from `plugins/sec-overlay/skills/sec-overlay/helpers/`: `uv run pytest -q`, `uv run ruff check sec_overlay/ bench/ tests/`, `uv run ty check`.

## File Structure

| File | Responsibility |
|------|----------------|
| `helpers/sec_overlay/report.py` | Task 1 adds the next-action lookup. Task 2 extracts the run-economics renderer. |
| `helpers/sec_overlay/artifact_consistency.py` | Task 3 creates it. Holds the six terminal consistency checks. |
| `helpers/sec_overlay/phases.py` | Task 3 adds the `artifact-consistency` phase spec and its path helper. |
| `helpers/sec_overlay/driver.py` | Task 3 adds the deterministic action that raises `PhaseHalt`. |
| `helpers/tests/test_report.py` | Tasks 1 and 2 add their acceptance tests. |
| `helpers/tests/test_artifact_consistency.py` | Task 3 creates it. |

---

### Task 1: REQ-03 — the next action names the section that holds the finding

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`

**Interfaces:**
- Consumes: `sec_overlay.redteam.discriminate(findings, min_risk=DEFAULT_MIN_RISK) -> dict` with keys `needs_runtime`, `static_settled`, `below_bar`, `unrunnable`, each a `list[Finding]`.
- Produces: `report._ndt_next_actions(ndt: list[Finding]) -> dict[str, str]` — finding id to next-action phrase. Task 3 reads the phrases through the report text, not through this function.

**Background.** `report.py:347` hardcodes `"run redteam-plan test"` for every needs-runtime row. A below-bar finding has no directive in `redteam-plan.md`; it appears under `## Runtime-validation gaps`. An above-bar finding whose payload is not traceable appears under `## Unrunnable preconditions (payload not traceable)`. The three reachable buckets each get their own phrase.

Import `redteam` inside the function. `redteam.py` does not import `report`, so there is no cycle today, but `report.py:565` already uses the local-import idiom for the same reason. Match it.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_report.py`:

```python
def _ndt_below_bar():
    """Low-severity, low-risk NDT finding — below the redteam-plan action bar."""
    return Finding(
        id="AUTHZ-0001",
        rule_id="investigation:authz",
        cls="authz",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.LOW,
        file="src/rbac/spec.js",
        line=7,
        risk_score=3,
        message="owner check may be advisory",
        dataflow=["a -> b"],
        preconditions=["handler unscoped"],
    )


def _ndt_unrunnable():
    """Above-bar NDT finding whose payload cannot be traced source->sink."""
    return Finding(
        id="SSRF-0002",
        rule_id="investigation:ssrf",
        cls="ssrf",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.HIGH,
        file="src/net/fetch.js",
        line=21,
        risk_score=8,
        message="outbound URL may be attacker controlled",
    )


def _triage_action(md: str, fid: str) -> str:
    """Return the 'Next action' cell of the triage row for ``fid``."""
    triage = md.split("## Triage")[1].split("\n## ")[0]
    row = next(l for l in triage.splitlines() if l.startswith(f"| {fid} "))
    return [c.strip() for c in row.strip().strip("|").split("|")][-1]


def test_below_bar_ndt_next_action_points_at_the_gaps_section():
    """REQ-03: a below-bar finding has no directive, so it must not be sent to one."""
    md = to_markdown([], needs_deployment=[_ndt_below_bar()])
    assert _triage_action(md, "AUTHZ-0001") == "see redteam-plan gaps"
    assert "run redteam-plan test" not in md


def test_unrunnable_ndt_next_action_points_at_the_preconditions_section():
    """REQ-03: an untraceable payload lands under 'Unrunnable preconditions', not 'gaps'."""
    md = to_markdown([], needs_deployment=[_ndt_unrunnable()])
    assert _triage_action(md, "SSRF-0002") == "see redteam-plan preconditions"


def test_directive_ndt_next_action_points_at_the_directive_section():
    """REQ-03: an above-bar, traceable finding keeps a directive-shaped action."""
    md = to_markdown([], needs_deployment=[_ndt_med()])
    assert _triage_action(md, "NDT-T4") == "run redteam-plan directive"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

```bash
uv run pytest tests/test_report.py -q -k "next_action"
```

Expected: 3 failed. Each reports the cell as `run redteam-plan test`.

- [ ] **Step 3: Commit the red tests**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "$(cat <<'EOF'
test(sec-overlay): pin next-action section routing

REQ-03. Three failing tests: a below-bar finding, an unrunnable
finding, and a directive finding must each name the redteam-plan
section that contains them.
EOF
)"
```

- [ ] **Step 4: Write the minimal implementation**

Add this helper to `helpers/sec_overlay/report.py`, directly above `_triage_row`:

```python
def _ndt_next_actions(ndt: list[Finding]) -> dict[str, str]:
    """Map each needs-runtime finding id to the redteam-plan section that holds it.

    The red-team plan files a needs-runtime finding under exactly one of three
    headings. The triage next-action must name that heading, so a reader who
    follows it finds the finding (REQ-03).

    Args:
        ndt: The needs-runtime findings the report renders.

    Returns:
        Finding id to next-action phrase. Ids absent from the plan are absent here.
    """
    from sec_overlay.redteam import discriminate  # local: avoid cycle

    buckets = discriminate(list(ndt))
    return {
        f.id: action
        for bucket, action in (
            ("needs_runtime", "run redteam-plan directive"),
            ("unrunnable", "see redteam-plan preconditions"),
            ("below_bar", "see redteam-plan gaps"),
        )
        for f in buckets[bucket]
    }
```

Then replace the hardcoded action at `report.py:347`. Change:

```python
    all_triage = [(f, "needs-runtime", "run redteam-plan test") for f in ndt] + [
```

to:

```python
    ndt_actions = _ndt_next_actions(ndt)
    all_triage = [
        (f, "needs-runtime", ndt_actions.get(f.id, "see redteam-plan gaps")) for f in ndt
    ] + [
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
uv run pytest tests/test_report.py -q
uv run ruff check sec_overlay/ tests/
```

Expected: all pass, no lint finding.

- [ ] **Step 6: Update the folder README, the changelog, and the version**

Append one line to `helpers/sec_overlay/README.md` recording that the triage next-action now routes through `redteam.discriminate`. Add a `CHANGELOG.md` entry. Bump `plugin.json` to the next patch version.

- [ ] **Step 7: Commit the implementation**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "$(cat <<'EOF'
fix(sec-overlay): route next action to its plan section

REQ-03. The triage next-action reads redteam.discriminate and names
the heading that contains the finding: directive, preconditions, or
gaps. A below-bar finding is no longer sent to a directive it lacks.
EOF
)"
```

---

### Task 2: REQ-05 (narrowed) — no "(measured)" header above an empty body

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:412-424`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`

**Interfaces:**
- Produces: `report._render_economics(economics: dict) -> list[str]` — Markdown lines, `[]` when nothing was measured.

**Scope ruling.** REQ-05's other clause tells the report to suppress empty "No X" sections. Five such sections render when empty on purpose under D-13, D-14, and D-15, pinned by `tests/test_report.py:1058`. The user chose to keep D-14 and narrow REQ-05 to the run-economics clause. Do not touch those five sections. The word-boundary truncation clause is already satisfied by `_short_title` at `report.py:224-239`; it needs no change.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_report.py`:

```python
def test_run_economics_omits_a_measured_header_with_no_body():
    """REQ-05: a measurement that was not collected prints no header."""
    md = to_markdown([], economics={"by_phase": {}, "by_phase_seconds": {"report": 1.5}})
    assert "**Tokens by phase** (measured):" not in md
    assert "**Tokens by model** (measured):" not in md
    assert "**Wall-clock by phase, seconds** (measured):" in md


def test_run_economics_section_absent_when_nothing_was_measured():
    """REQ-05: an empty economics payload renders no section at all."""
    md = to_markdown([], economics={"by_phase": {}, "by_model": {}})
    assert "## Run economics" not in md
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
uv run pytest tests/test_report.py -q -k "run_economics"
```

Expected: 2 failed, 1 passed. The two new tests fail because both headers print unconditionally.

- [ ] **Step 3: Commit the red tests**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "$(cat <<'EOF'
test(sec-overlay): pin empty run-economics suppression

REQ-05. Two failing tests: an uncollected measurement prints no
"(measured)" header, and an empty payload renders no section.
EOF
)"
```

- [ ] **Step 4: Write the minimal implementation**

Add this helper to `helpers/sec_overlay/report.py`, directly above `to_markdown`:

```python
def _render_economics(economics: dict) -> list[str]:
    """Render the run-economics section, omitting every measurement that is absent.

    A "(measured)" header above an empty body claims a measurement the run never
    took. Each group renders only when it holds data, and the section itself
    disappears when no group does (REQ-05).

    Args:
        economics: Cost aggregate with optional ``by_phase``, ``by_model``,
            ``by_phase_seconds``, and ``usd_estimate`` keys.

    Returns:
        Markdown lines for the section, or ``[]`` when nothing was measured.
    """
    groups = (
        ("**Tokens by phase** (measured):",
         [f"- **{k}**: {v}" for k, v in (economics.get("by_phase") or {}).items()]),
        ("**Tokens by model** (measured):",
         [f"- **{k}**: {v}" for k, v in (economics.get("by_model") or {}).items()]),
        ("**Wall-clock by phase, seconds** (measured):",
         [f"- **{k}**: {v:.2f}" for k, v in (economics.get("by_phase_seconds") or {}).items()]),
    )
    body: list[str] = []
    for header, items in groups:
        if items:
            body += ([""] if body else []) + [header] + items
    usd = economics.get("usd_estimate")
    if usd is not None:
        cost = f"**Estimated cost:** ${usd:.4f} (estimate, not a billed figure)."
        body += ([""] if body else []) + [cost]
    return ["", "## Run economics", ""] + body if body else []
```

Then replace the whole `if economics:` block at `report.py:412-424`:

```python
    if economics:
        lines += ["", "## Run economics", ""]
        lines += ["**Tokens by phase** (measured):"]
        lines += [f"- **{phase}**: {n}" for phase, n in economics.get("by_phase", {}).items()]
        lines += ["", "**Tokens by model** (measured):"]
        lines += [f"- **{model}**: {n}" for model, n in economics.get("by_model", {}).items()]
        by_secs = economics.get("by_phase_seconds") or {}
        if by_secs:
            lines += ["", "**Wall-clock by phase, seconds** (measured):"]
            lines += [f"- **{phase}**: {secs:.2f}" for phase, secs in by_secs.items()]
        usd = economics.get("usd_estimate")
        if usd is not None:
            lines += ["", f"**Estimated cost:** ${usd:.4f} (estimate, not a billed figure)."]
    elif token_spend:
```

with:

```python
    if economics:
        lines += _render_economics(economics)
    elif token_spend:
```

- [ ] **Step 5: Run the tests and confirm they pass**

```bash
uv run pytest tests/test_report.py -q
uv run ruff check sec_overlay/ tests/
```

Expected: all pass, including the pre-existing `test_run_economics_section_renders_phase_model_and_usd_estimate`.

- [ ] **Step 6: Update the folder README, the changelog, and the version**

Append one line to `helpers/sec_overlay/README.md`. Add a `CHANGELOG.md` entry. Bump `plugin.json` to the next patch version.

- [ ] **Step 7: Commit the implementation**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "$(cat <<'EOF'
fix(sec-overlay): drop empty run-economics headers

REQ-05. _render_economics emits a group only when it holds data and
the section only when a group does. R-41, R-42, and R-43's "No X"
half stays open: five sections render when empty by D-14 design.
EOF
)"
```

---

### Task 3: REQ-31 — terminal artifact-consistency gate

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py`

**Interfaces:**
- Consumes: `Workspace` (`.report_path`, `.findings_dir`, `.reports`, `.kb`, `.root`), `workspace.read_findings`, `state.load_state`, `report._short_title`.
- Produces: `artifact_consistency.run_artifact_consistency(ws: Workspace) -> list[str]`, `artifact_consistency.main(argv=None) -> int`, the phase name `"artifact-consistency"`, and the gate file `kb/gates/artifact-consistency.json` holding `{"passed": bool, "errors": [str]}`.

**Design rulings, made during the group pre-check.**

1. **Flag.** `scan_options.consistency_gate` defaults to `True`. Set it to `false` in `kb/scan-profile.json` to skip the gate. Part G requires the gate to run in the pipeline and block, so on is the default.
2. **Degradation.** A workspace without `report.md` returns `[]`. The gate never raises on a missing input; it degrades to today's behaviour.
3. **Check (b) needs four phrases, not three.** `redteam.discriminate` has four buckets and `render_plan` gives three of them their own heading. Task 1 emits exactly three phrases. Check (b) maps each phrase to its heading and looks the finding id up inside that section. Check (b) runs only when `redteam-plan.md` exists.
4. **Check (d) is a contradiction check, not equality.** `write_report` applies `select_reportable` and `collapse_clusters`; `build_self_score` counts every finding uncollapsed. Report counts are therefore less than or equal to selfscore counts by design, and literal equality would block every run that has a cluster. The gate flags three contradictions: a missing or null `self_score`, a zero selfscore count against a non-zero report count, and a report count above the selfscore count. A difference explained by collapse passes. Cost if wrong: a non-zero miscount in the safe direction passes the gate.
5. **Check (f) compares against the source message.** A truncated title alone cannot show a mid-word cut. For each triage cell ending in `…`, the gate normalizes the finding's own message the way `_triage_row` does and asserts the prefix ends on a word boundary.

- [ ] **Step 1: Write the failing tests**

Create `helpers/tests/test_artifact_consistency.py`:

```python
"""Tests for the terminal artifact-consistency gate (REQ-31)."""

import json
from pathlib import Path

from sec_overlay.artifact_consistency import run_artifact_consistency
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, write_findings

_REPORT_HEAD = "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"


def _ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "wsp")
    ws.ensure()
    return ws


def _ndt(fid="N-1", message="owner check may be advisory"):
    return Finding(
        id=fid,
        rule_id="investigation:authz",
        cls="authz",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.LOW,
        file="a.js",
        line=1,
        risk_score=3,
        message=message,
    )


def _triage(fid: str, what: str, action: str) -> str:
    return (
        "## Triage\n\n"
        "| ID | Risk | What | Location | Status | Next action |\n"
        "|----|------|------|----------|--------|-------------|\n"
        f"| {fid} | 3 | {what} | a.js:1 | needs-runtime | {action} |\n\n"
    )


def _selfscore(ws: Workspace, score) -> None:
    state = json.loads((ws.root / "state.json").read_text())
    state["budget"]["self_score"] = score
    (ws.root / "state.json").write_text(json.dumps(state))


def test_missing_report_degrades_to_no_op(tmp_path):
    """A workspace with no report is not a contradiction — the gate stays silent."""
    assert run_artifact_consistency(_ws(tmp_path)) == []


def test_gate_flags_a_detail_link_with_no_file(tmp_path):
    """Check (a): every findings/<id>.md cross-reference must resolve."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD + "## Detail\n\n- [N-1](findings/N-1.md) — risk 3\n")
    errors = run_artifact_consistency(ws)
    assert any("findings/N-1.md" in e for e in errors)


def test_gate_flags_a_next_action_whose_section_lacks_the_finding(tmp_path):
    """Check (b): 'run redteam-plan directive' must resolve to a real directive."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "owner check may be advisory", "run redteam-plan directive")
    )
    (ws.reports / "redteam-plan.md").write_text(
        "## Manual test directives\n\n_none_\n\n## Runtime-validation gaps\n\n- `N-1` (authz)\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("N-1" in e and "Manual test directives" in e for e in errors)


def test_gate_passes_when_the_next_action_names_the_right_section(tmp_path):
    """Check (b): the matching artifacts pass."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
    )
    (ws.reports / "redteam-plan.md").write_text(
        "## Manual test directives\n\n_none_\n\n## Runtime-validation gaps\n\n- `N-1` (authz)\n"
    )
    assert run_artifact_consistency(ws) == []


def test_gate_flags_a_coverage_claim_the_ledger_denies(tmp_path):
    """Check (c): the report's completeness line must match the ledger."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD + "## Coverage completeness\n\nCompleteness: **complete**\n")
    (ws.kb / "coverage-ledger.json").write_text(json.dumps({"completeness": "partial"}))
    errors = run_artifact_consistency(ws)
    assert any("completeness" in e.lower() for e in errors)


def test_gate_flags_a_null_self_score(tmp_path):
    """Check (d): a report exists but selfscore never landed — N-2."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("self_score" in e for e in errors)


def test_gate_flags_a_zero_self_score_against_a_reported_finding(tmp_path):
    """Check (d): selfscore says zero needs-runtime, the report renders one."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 0})
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)


def test_gate_flags_a_measured_header_with_an_empty_body(tmp_path):
    """Check (e): a '(measured):' header must be followed by data."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + "## Run economics\n\n**Tokens by phase** (measured):\n\n## Detail\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("measured" in e for e in errors)


def test_gate_flags_a_title_truncated_mid_word(tmp_path):
    """Check (f): a triage title must not cut its source message inside a word."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(message="owner check may be advisory")])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD + _triage("N-1", "owner check may be advi…", "see redteam-plan gaps"))
    errors = run_artifact_consistency(ws)
    assert any("mid-word" in e for e in errors)


def test_gate_writes_its_audit_trail(tmp_path):
    """The gate records its verdict under kb/gates/ like every other gate."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(_REPORT_HEAD)
    run_artifact_consistency(ws)
    payload = json.loads((ws.kb / "gates" / "artifact-consistency.json").read_text())
    assert payload["passed"] is True
    assert payload["errors"] == []


def test_gate_is_skippable_through_scan_options(tmp_path):
    """The lane ships behind a profile flag; a target can opt out."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    ws.report_path.write_text(_REPORT_HEAD + "## Detail\n\n- [N-1](findings/N-1.md) — risk 3\n")
    (ws.kb / "scan-profile.json").write_text(json.dumps({"scan_options": {"consistency_gate": False}}))
    assert run_artifact_consistency(ws) == []


def test_phase_table_runs_the_gate_before_postflight():
    """The gate is terminal: after artifact-review, before AUDIT COMPLETE."""
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("artifact-consistency") > names.index("artifact-review")
    assert names.index("artifact-consistency") < names.index("postflight")
```

- [ ] **Step 2: Run the tests and confirm they fail**

```bash
uv run pytest tests/test_artifact_consistency.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'sec_overlay.artifact_consistency'`.

- [ ] **Step 3: Commit the red tests**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "$(cat <<'EOF'
test(sec-overlay): pin the artifact-consistency gate

REQ-31. Twelve failing tests covering the six terminal checks, the
gate's audit trail, its scan_options opt-out, its degrade-to-no-op
path, and its position between artifact-review and postflight.
EOF
)"
```

- [ ] **Step 4: Write the module**

Create `helpers/sec_overlay/artifact_consistency.py`:

```python
"""Terminal artifact-consistency gate (REQ-31).

Runs after artifact-review and before AUDIT COMPLETE. It reconciles a finished
run's own artifacts against each other: every cross-reference resolves, every
next-action names a section that contains its finding, the coverage claim
matches the ledger, the self-score does not contradict the report, no
"(measured)" header sits above an empty body, and no rendered title cuts its
source message inside a word.

It never judges a finding and never deletes one. A missing artifact is not a
contradiction — an incomplete workspace degrades to a silent pass.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from sec_overlay.state import load_state
from sec_overlay.workspace import Workspace, read_findings

_DETAIL_LINK = re.compile(r"\]\(findings/([^)]+)\)")

# Task 1 emits exactly these phrases; each names one redteam-plan heading.
_ACTION_SECTIONS = {
    "run redteam-plan directive": "## Manual test directives",
    "see redteam-plan preconditions": "## Unrunnable preconditions",
    "see redteam-plan gaps": "## Runtime-validation gaps",
}


def _section(md: str, heading: str) -> str:
    """Return the body under the first heading that starts with ``heading``."""
    out: list[str] = []
    inside = False
    for line in md.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line.startswith(heading)
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


def _triage_rows(md: str) -> list[list[str]]:
    """Return the report's triage data rows as lists of stripped cells."""
    rows: list[list[str]] = []
    for line in _section(md, "## Triage").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells[0] == "ID" or set("".join(cells)) <= set("-| "):
            continue
        rows.append(cells)
    return rows


def _enabled(ws: Workspace) -> bool:
    """True unless ``scan_options.consistency_gate`` is set to false."""
    path = ws.kb / "scan-profile.json"
    if not path.exists():
        return True
    try:
        options = json.loads(path.read_text()).get("scan_options") or {}
    except (json.JSONDecodeError, AttributeError):
        return True
    return options.get("consistency_gate", True) is not False


def _check_cross_references(ws: Workspace, report_md: str) -> list[str]:
    """Check (a): every ``findings/<id>.md`` link resolves to a file on disk."""
    return [
        f"artifact-consistency: report links findings/{name} but the file does not exist"
        for name in sorted(set(_DETAIL_LINK.findall(report_md)))
        if not (ws.findings_dir / name).exists()
    ]


def _check_next_actions(ws: Workspace, report_md: str) -> list[str]:
    """Check (b): every next-action names a plan section that holds the finding."""
    plan = ws.reports / "redteam-plan.md"
    if not plan.exists():
        return []
    plan_md = plan.read_text()
    errors: list[str] = []
    for row in _triage_rows(report_md):
        heading = _ACTION_SECTIONS.get(row[-1])
        if heading and row[0] not in _section(plan_md, heading):
            errors.append(
                f"artifact-consistency: next action for {row[0]} names "
                f"{heading!r}, which does not contain it"
            )
    return errors


def _check_coverage_claim(ws: Workspace, report_md: str) -> list[str]:
    """Check (c): the rendered completeness matches the coverage ledger."""
    path = ws.kb / "coverage-ledger.json"
    match = re.search(r"^Completeness: \*\*(.+?)\*\*$", report_md, re.MULTILINE)
    if not path.exists() or match is None:
        return []
    claimed = match.group(1)
    actual = json.loads(path.read_text()).get("completeness", "unknown")
    if claimed != actual:
        return [
            f"artifact-consistency: report claims completeness {claimed!r} "
            f"but the ledger records {actual!r}"
        ]
    return []


def _check_self_score(ws: Workspace, report_md: str) -> list[str]:
    """Check (d): the self-score does not contradict the report's own counts.

    The report collapses clusters and the self-score does not, so a report count
    below the self-score count is expected. Only a missing score, a zero score
    against rendered rows, or a report count above the score is a contradiction.
    """
    score = load_state(ws).budget.get("self_score")
    if not isinstance(score, dict):
        return ["artifact-consistency: report exists but state.budget.self_score is missing"]
    match = re.search(r"^Needs runtime proof: (\d+)$", report_md, re.MULTILINE)
    if match is None:
        return []
    reported = int(match.group(1))
    scored = score.get("needs_runtime", 0)
    if reported > scored:
        return [
            f"artifact-consistency: report shows {reported} needs-runtime "
            f"finding(s) but self_score.needs_runtime is {scored}"
        ]
    return []


def _check_measured_sections(report_md: str) -> list[str]:
    """Check (e): no "(measured)" header stands above an empty body."""
    lines = report_md.splitlines()
    errors: list[str] = []
    for i, line in enumerate(lines):
        if not line.rstrip().endswith("(measured):"):
            continue
        body = next((n for n in lines[i + 1:] if n.strip()), "")
        if not body.startswith("- "):
            errors.append(f"artifact-consistency: measured section {line.strip()!r} has an empty body")
    return errors


def _check_truncated_titles(ws: Workspace, report_md: str) -> list[str]:
    """Check (f): a truncated triage title ends on a word boundary of its source."""
    from sec_overlay.report import _short_title  # local: avoid cycle

    by_id = {f.id: f for f in read_findings(ws)}
    errors: list[str] = []
    for row in _triage_rows(report_md):
        what = row[2] if len(row) > 2 else ""
        finding = by_id.get(row[0])
        if not what.endswith("…") or finding is None:
            continue
        source = (finding.message or "").split("|", 1)[0].split(". ")[0].strip()
        if what != _short_title(source):
            errors.append(
                f"artifact-consistency: triage title for {row[0]} is truncated mid-word: {what!r}"
            )
    return errors


def run_artifact_consistency(ws: Workspace) -> list[str]:
    """Reconcile a finished run's artifacts against each other.

    Args:
        ws: The finished-run workspace.

    Returns:
        Contradiction strings; empty when the artifacts agree, when the run
        opted out through ``scan_options.consistency_gate``, or when no report
        was rendered. Also writes ``kb/gates/artifact-consistency.json``.
    """
    if not ws.report_path.exists() or not _enabled(ws):
        return []
    report_md = ws.report_path.read_text()
    errors = (
        _check_cross_references(ws, report_md)
        + _check_next_actions(ws, report_md)
        + _check_coverage_claim(ws, report_md)
        + _check_self_score(ws, report_md)
        + _check_measured_sections(report_md)
        + _check_truncated_titles(ws, report_md)
    )
    (ws.kb / "gates").mkdir(parents=True, exist_ok=True)
    (ws.kb / "gates" / "artifact-consistency.json").write_text(
        json.dumps({"passed": not errors, "errors": errors}, indent=2)
    )
    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI: run the artifact-consistency gate on a workspace.

    Args:
        argv: Optional argument vector.

    Returns:
        0 when the artifacts agree, 1 otherwise.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="sec-overlay-artifact-consistency")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)
    errors = run_artifact_consistency(Workspace(Path(args.workspace)))
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Wire the phase**

In `helpers/sec_overlay/phases.py`, add the path helper beside `_artifact_gate_json`:

```python
def _artifact_consistency_json(ws: Workspace) -> Path:
    return ws.kb / "gates" / "artifact-consistency.json"
```

Then insert the phase spec into `PHASE_TABLE` between `artifact-review` and `postflight`:

```python
    PhaseSpec(
        name="artifact-consistency",
        kind="deterministic",
        inputs=(_report,),
        outputs=(_artifact_consistency_json,),
    ),
```

In `helpers/sec_overlay/driver.py`, add the action beside `_act_artifact_gate`:

```python
def _act_artifact_consistency(ctx: AuditContext) -> None:
    from sec_overlay.artifact_consistency import run_artifact_consistency  # local: avoid import cycle

    errors = run_artifact_consistency(ctx.ws)
    if errors:
        raise PhaseHalt(
            f"artifact-consistency rejected {len(errors)} contradiction(s): " + "; ".join(errors)
        )
```

and register it in the `DETERMINISTIC_ACTIONS.update({...})` call:

```python
    "artifact-consistency": _act_artifact_consistency,
```

Check the real `PhaseSpec` field names and the real `DETERMINISTIC_ACTIONS.update` block before editing; copy the neighbouring `artifact-gate` entry's exact shape.

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
uv run pytest tests/test_artifact_consistency.py tests/test_phases.py tests/test_driver.py -q
uv run ruff check sec_overlay/ tests/
uv run ty check
```

Expected: all pass, no lint or type finding.

- [ ] **Step 7: Update the folder READMEs, the changelog, and the version**

Append to `helpers/sec_overlay/README.md`: the new module, its CLI entry point, and its position in the pipeline. Add a `CHANGELOG.md` entry. Bump `plugin.json` to the next minor version — this is a `feat`.

- [ ] **Step 8: Commit the implementation**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "$(cat <<'EOF'
feat(sec-overlay): add artifact-consistency gate

REQ-31. A terminal deterministic phase between artifact-review and
postflight reconciles report, findings, redteam-plan, coverage
ledger, and self-score. It halts the run on a contradiction, and
degrades to a silent pass when an artifact is absent.
EOF
)"
```

---

## Group gate

- [ ] Run the full suite, the linter, and the type checker from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Expected: every test passes, no lint finding, no type finding. Record the totals in the ledger.
