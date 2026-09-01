# sec-overlay Population Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every artifact of one run report the same finding population, and make one systemic cluster survive in every consumer.

**Architecture:** Two root causes share one repair surface. RC-11 is two readers that compute the same quantity from different fields or different populations, with nothing comparing them. Its repair extends the terminal `artifact-consistency` gate with three new clauses and corrects the three renderers the clauses would otherwise reject. RC-13 is a systemic cluster that survives in one consumer and is dropped by the rest. Its repair adds the cluster's sites to SARIF and stamps a fingerprint on every finding, whatever its status.

**Tech Stack:** Python 3.11 (standard library only in `sec_overlay/`), pytest, ruff, ty, `uv` for every command. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** docs/superpowers/specs/2026-09-01-sec-overlay-defect-repairs-design.md (Section 5, Group 4 and Group 5)

## Global Constraints

- `sec_overlay/` imports the standard library only. No new dependency.
- `sec_overlay/models.py` and `sec_overlay/evidence.py` are byte-pinned by `tests/test_frozen_contract.py:30-31`. Do not edit either file in this plan. No task needs to.
- `Finding` has no `title` field. Any requirement that names one must use `message`.
- One commit per red step and one commit per green step. The red commit must fail; the green commit must pass.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `version` in every commit. A test file under `helpers/tests/` is a shipping file, so a red commit bumps too.
- Derive the increment from the Conventional Commit type: `feat` bumps minor, every other type bumps patch.
- Stage explicit paths. Never `git add -A`. Never `--no-verify`.
- A commit that changes a file under `helpers/sec_overlay/` updates `helpers/sec_overlay/README.md` in the same commit. A commit that changes a file under `helpers/tests/` updates `helpers/tests/README.md` in the same commit.
- A commit that invalidates a statement in `helpers/README.md` updates that statement in the same commit.
- Add one entry to `plugins/sec-overlay/CHANGELOG.md` per commit. The plan touches no repo-level file, so the root `CHANGELOG.md` gets no entry.
- Run `prek run` before every commit.
- Do not merge and do not push. The branch is `docs/sec-overlay-defect-repairs-spec`.
- Do not edit a test this plan does not name. Two tests are reversed on purpose; they are named in the pre-flight scan.
- The plugin version at the start of this plan is 2.2.0, the version Plan 3 ends on. The versions below are prospective. Read the real value from `plugin.json` before each bump.
- Task order is REQ-53, REQ-54, REQ-55, REQ-56, REQ-57, REQ-58. Tasks 1 to 4 (RC-11) run before Tasks 5 and 6 (RC-13), per the specification's build order.

---

## Pre-flight scan

Every citation in Group 4 and Group 5 was opened at plugin 1.122.0, commit `3f3dc96`. The tables below record what differs from the specification.

### Corrections to the specification

| Requirement | Specification says | Plugin 1.122.0 holds |
|---|---|---|
| REQ-53 | The gate clause is the whole repair, at `artifact_consistency.py:175`. | The count gap originates in `report.py`. `write_report` sends `reportable + ndt` to SARIF at line 703, while `to_markdown` drops every `completeness_tier == "external-unverifiable"` finding from the triage population at lines 429-431. A gate clause alone would fail on every correct run. Task 1 therefore lands the gate clause and the report count fix together. |
| REQ-54 | Add clause (h) at `selfscore.py:18`, `:46`. | `build_self_score` starts at line 22 and its return block at line 45. Line 18 is `_REPORTED`. The clause itself belongs in `artifact_consistency.py`, not in `selfscore.py`. |
| REQ-56 | "Render `f.title` when it exists; fall back to `message` only when it does not." | `Finding` has no `title` field, and `models.py` is byte-pinned. Only the register's fallback shape is available: skip a leading sentence that matches a status vocabulary. |
| REQ-56 | Cites `report.py:253`, `:320-332`, `:351`, `:378`. | The real sites are `:435-446` (the severity sentence), `:317-330` (`_triage_row`), `:328` and `:495` (the identical "What" expression), and `:464-471` (the triage population). |
| REQ-58 | Cites `dedupe.py:14`, `:50-53`. | The stamping loop is lines 49-54. `_ACTIVE` is at line 14, as stated. |
| REQ-53, REQ-54, REQ-55 | "must block the pipeline on a contradiction, not warn." | Already true. `driver._act_artifact_consistency` at `driver.py:338-344` raises `PhaseHalt` when `run_artifact_consistency` returns a non-empty list. No driver change is needed. |

### Rulings taken against plugin HEAD

1. **Clause (g) has two parts.** Part one compares the report's stated `Needs runtime proof:` count against the needs-runtime findings the report renders anywhere. That part fails at 1.122.0: the measured run states 20 against 22 rendered. Part two compares the SARIF result count against the total finding count the report renders anywhere. That part passes at 1.122.0 (27 against 27) and exists to catch a finding that reaches SARIF and no report section.
2. **"Rendered anywhere" means three places.** A finding id appears in a triage row, in a `## Detail` link, or in a `### <id> — ` section heading. The external-unverifiable leads appear only in the third. Clause (g) reads all three and intersects the result with the ids on disk, so a `### ` heading that names something other than a finding cannot inflate the count.
3. **The report must state the split.** REQ-53's report half changes `Needs runtime proof:` to count `ndt_all`, the pre-split population, and adds a `Leads pending external verification:` line when that bucket is non-empty. The triage table population is unchanged.
4. **Clause (h) fires only on a complete self-score.** Four existing tests in `tests/test_artifact_consistency.py` write a partial score, such as `{"confirmed": 0, "needs_runtime": 1}`, and one of them asserts the gate passes. Clause (h) therefore checks the partition only when the score carries `total` and `by_status`. A score written by `build_self_score` always carries both.
5. **REQ-54 reverses an existing docstring and an existing tolerance.** `_check_self_score` at `artifact_consistency.py:118-141` declares the mismatch expected: "The report collapses clusters and the self-score does not, so a report count below the self-score count is expected." Its check is `if reported > scored:`. REQ-54 removes the cause of the mismatch, so the docstring and the one-sided tolerance both go.
6. **`selfscore.py` may import `report.collapse_clusters`.** `report.py` does not import `selfscore`; only `driver.py` does. There is no cycle.
7. **`by_status` is the named key for `duplicate`.** The self-score gains three keys: `total`, `duplicate`, and `by_status`. `by_status` is a full partition by construction, so the measured `70 + 22 + 242 ≠ 338` cannot recur. The four flat status keys stay, because clause (d) and the bench read them.
8. **REQ-56 keeps the `Confirmed:` line confirmed-only.** `tests/test_report.py:672-678` asserts `conf_line == "Confirmed: 1 low"` with one needs-runtime medium present. REQ-56 changes only the bottom-line severity sentence, which counts the triage population. The two count lines are untouched by that half.
9. **The "What" cell becomes one shared helper.** `report.py:328` and `report.py:495` hold the identical expression, and `artifact_consistency._check_truncated_titles` at line 168 recomputes it a third time. REQ-56 adds `report.triage_what(f)` and all three call it. Without the third caller, clause (f) would reject every row the new helper shortens.
10. **REQ-57 reverses one test.** `tests/test_sarif.py:100` asserts `kind == "inSource"`. No in-source annotation exists for a needs-runtime finding, so the correct SARIF kind is `external`.
11. **REQ-58 removes the filter from the stamping loop only.** The three grouping passes at `dedupe.py:40-45`, `:56-72`, and `:78-93` keep `_ACTIVE`. `tests/test_dedupe.py:69` asserts only that a rejected finding is not marked, so it stays green.
12. **The fingerprint is 12 hex characters, not 16.** `tests/test_dedupe.py:101` pins the length. `sarif._sarif_fingerprint` uses 16 and is a separate function; REQ-57 does not touch it.

### Drift rows

| Cite | Drift |
|---|---|
| `report.py:429-431` | The register measured the split at 1.107.3. It is unchanged at 1.122.0. |
| `report.py:442-446` | The three summary sentences still say "source-provable". `helpers/sec_overlay/README.md:241` and `:247` and `helpers/README.md:165` describe the block. Task 4 updates all three. |
| `redteam.py:182`, `:251` | Both readers are unchanged at 1.122.0. `_bullets` at line 124 returns `"_not specified_"` at line 138. |
| `sarif.py:93-108` | A result carries exactly `ruleId`, `level`, `message`, `locations`, optional `suppressions`, and `partialFingerprints`. `affected_sites` is read nowhere in the module. |
| `selfscore.py:45-57` | No `duplicate` key and no total. The measured `70 + 22 + 242 = 334` against 338 findings on disk is reproducible from this block alone. |

### Adjacent findings this plan does not fix

1. `dedupe.py:54` sets `stamped = True` unconditionally, so `if marked or stamped:` at line 95 always writes every finding back. REQ-58 makes the flag honest by widening the loop, but the dead condition stays.
2. `sarif._sarif_fingerprint` does not Unicode-normalize evidence, which `tests/test_sarif.py:176` pins as current behaviour. Two canonically equal evidence strings produce two fingerprints.
3. `report.py:495` renders a detail link for `conf + ndt` only. An external-unverifiable lead has no `## Detail` link. Clause (g) accepts that, because the lead renders a `### ` heading.
4. `_check_coverage_claim` and `_check_next_actions` read the report text only. Neither is bound to `PHASE_TABLE`. REQ-61 in Plan 5 owns that binding.

---

## File Structure

**Created:** none.

**Modified:**

- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py` — three new clauses, one reversed clause, one shared-helper call.
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py` — the two count lines, the bottom-line sentence, and the `triage_what` helper.
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/selfscore.py` — three new score keys and cluster collapse.
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py` — one precondition reader.
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py` — related locations, the finding id, and the suppression kind.
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dedupe.py` — the stamping loop filter.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py` — clause (g) and clause (h) tests, one reversed test.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py` — the count split, the bottom-line sentence, and `triage_what`.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_selfscore.py` — the partition and the collapsed counts.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py` — the precondition fallback.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py` — related locations, the finding id, the reversed suppression kind.
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dedupe.py` — a rejected finding carries a fingerprint.
- The four folder READMEs and `plugins/sec-overlay/CHANGELOG.md`, per the global constraints.

---

## Task 1: REQ-53 — reconcile the SARIF and report populations

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:429-462`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py`

**Interfaces:**
- Consumes: `Workspace.sarif_path`, `Workspace.report_path`, `read_findings(ws)`, `_triage_rows(md)`, `_DETAIL_LINK`.
- Produces: `artifact_consistency._rendered_ids(ws, report_md) -> set[str]` and `artifact_consistency._check_sarif_population(ws, report_md) -> list[str]`. Task 2 adds a clause beside the second one. The report gains a `Leads pending external verification: <n>` line that Task 4 must not remove.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py`:

```python
def _external(fid="X-1"):
    return Finding(
        id=fid,
        rule_id="investigation:ssrf",
        cls="ssrf",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.MEDIUM,
        file="b.js",
        line=2,
        risk_score=4,
        message="sink crosses into an un-ingested package",
        completeness_tier="external-unverifiable",
    )


def test_gate_flags_a_stated_ndt_count_below_the_rendered_count(tmp_path):
    """Check (g): the report renders two needs-runtime findings and states one."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "## Leads — pending external-dependency verification\n\n"
        "### X-1 — ssrf — Medium · needs runtime proof\n\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("needs-runtime" in e and "renders" in e for e in errors)


def test_gate_flags_a_sarif_result_the_report_never_renders(tmp_path):
    """Check (g): a finding reaches SARIF and no report section."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
    )
    ws.sarif_path.parent.mkdir(parents=True, exist_ok=True)
    ws.sarif_path.write_text(
        json.dumps({"runs": [{"results": [{"ruleId": "r"}, {"ruleId": "r"}]}]})
    )
    errors = run_artifact_consistency(ws)
    assert any("SARIF" in e for e in errors)


def test_gate_passes_when_the_report_states_the_external_split(tmp_path):
    """Check (g): a report that names both buckets reconciles against SARIF."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _external()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 2\n"
        "Leads pending external verification: 1\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "## Leads — pending external-dependency verification\n\n"
        "### X-1 — ssrf — Medium · needs runtime proof\n\n"
    )
    ws.sarif_path.parent.mkdir(parents=True, exist_ok=True)
    ws.sarif_path.write_text(
        json.dumps({"runs": [{"results": [{"ruleId": "r"}, {"ruleId": "r"}]}]})
    )
    assert run_artifact_consistency(ws) == []
```

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`:

```python
def test_ndt_count_includes_the_external_leads_and_states_the_split():
    """REQ-53: the stated needs-runtime count covers every needs-runtime finding."""
    lead = dataclasses.replace(
        _ndt_med(), id="NDT-EXT", completeness_tier="external-unverifiable"
    )
    out = to_markdown([], needs_deployment=[_ndt_med(), lead])
    assert "Needs runtime proof: 2" in out
    assert "Leads pending external verification: 1" in out
```

- [ ] **Step 2: Run the tests to check they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_artifact_consistency.py -k "stated_ndt_count or sarif_result_the_report or states_the_external_split" -q
uv run pytest tests/test_report.py -k "external_leads_and_states_the_split" -q
```

Expected: the first two artifact-consistency tests fail, because no clause reads SARIF or the rendered count. The third fails, because the report has no `Leads pending external verification:` line. The report test fails on the same missing line.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.2.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(gate): pin the REQ-53 population reconciliation"
```

- [ ] **Step 4: State the split in the report**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py`, replace line 460:

```python
        f"Needs runtime proof: {len(ndt)}",
```

with:

```python
        f"Needs runtime proof: {len(ndt_all)}",
    ]
    if external:
        lines.append(f"Leads pending external verification: {len(external)}")
    lines += [
```

Check the surrounding list literal still closes. The block at lines 455-462 builds one `lines +=` list; the insertion splits it into two.

- [ ] **Step 5: Add clause (g)**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py`, add a heading pattern beside `_DETAIL_LINK` at line 24:

```python
_SECTION_ID = re.compile(r"^### (\S+) — ", re.MULTILINE)
```

Add both functions above `run_artifact_consistency`:

```python
def _rendered_ids(ws: Workspace, report_md: str) -> set[str]:
    """Return the finding ids the report renders in any section.

    A finding id reaches the reader through a triage row, a ``## Detail`` link,
    or a ``### <id> — `` section heading. Ids not on disk are dropped, so a
    heading that names something other than a finding cannot inflate the count.

    Args:
        ws: The finished-run workspace.
        report_md: The rendered report text.

    Returns:
        The set of rendered finding ids.
    """
    known = {f.id for f in read_findings(ws)}
    ids = {row[0] for row in _triage_rows(report_md)}
    ids |= {link.removesuffix(".md") for link in _DETAIL_LINK.findall(report_md)}
    ids |= set(_SECTION_ID.findall(report_md))
    return ids & known


def _check_sarif_population(ws: Workspace, report_md: str) -> list[str]:
    """Check (g): SARIF and the report describe one population.

    Part one: the stated ``Needs runtime proof`` count equals the needs-runtime
    findings the report renders. Part two: the SARIF result count equals the
    total finding count the report renders. A missing SARIF file degrades part
    two to a pass.

    Args:
        ws: The finished-run workspace.
        report_md: The rendered report text.

    Returns:
        Contradiction strings; empty when both counts agree.
    """
    rendered = _rendered_ids(ws, report_md)
    by_id = {f.id: f for f in read_findings(ws)}
    errors: list[str] = []
    match = re.search(r"^Needs runtime proof: (\d+)$", report_md, re.MULTILINE)
    if match is not None:
        stated = int(match.group(1))
        shown = sum(
            1
            for fid in rendered
            if by_id[fid].status is FindingStatus.NEEDS_DEPLOYMENT_TESTING
        )
        if stated != shown:
            errors.append(
                f"artifact-consistency: report states {stated} needs-runtime "
                f"finding(s) but renders {shown}"
            )
    if ws.sarif_path.exists():
        doc = json.loads(ws.sarif_path.read_text())
        runs = doc.get("runs") or [{}]
        results = runs[0].get("results") or []
        if len(results) != len(rendered):
            errors.append(
                f"artifact-consistency: SARIF holds {len(results)} result(s) "
                f"but the report renders {len(rendered)} finding(s)"
            )
    return errors
```

Import the status enum at line 22:

```python
from sec_overlay.models import FindingStatus
```

Add the clause to the concatenation at line 189, after `_check_next_actions`:

```python
        + _check_sarif_population(ws, report_md)
```

- [ ] **Step 6: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_artifact_consistency.py tests/test_report.py tests/test_report_split.py -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: every test passes. If `tests/test_report.py` reports a failure on a stated count, read the failing assertion before changing it; only the two count lines moved.

- [ ] **Step 7: Run the whole suite**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
```

Expected: no failure. The baseline before this plan is 1766 passing plus the tests each task adds.

- [ ] **Step 8: Commit the green change**

Update `helpers/sec_overlay/README.md` with the new clause and the new count line. Update the `report.py` row in `helpers/README.md:165`, which describes the bottom-line count block.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.3.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(gate): reconcile SARIF and report populations"
```

---

## Task 2: REQ-54 — one self-score population, with a named duplicate key

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/selfscore.py:45-57`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py:118-141`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_selfscore.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py`

**Interfaces:**
- Consumes: `report.collapse_clusters(findings)`, `read_findings(ws)`, `load_state(ws).budget["self_score"]`.
- Produces: three new self-score keys — `total: int`, `duplicate: int`, `by_status: dict[str, int]` — and `reported_collapsed: int`, `needs_runtime_collapsed: int`. Adds `artifact_consistency._check_self_score_partition(ws) -> list[str]`. No later task reads them.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_selfscore.py`:

```python
def test_self_score_buckets_partition_the_finding_population(tmp_path):
    """REQ-54: every finding on disk lands under exactly one by_status key."""
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    write_findings(
        ws,
        [
            _f("F-1", FindingStatus.CONFIRMED),
            _f("F-2", FindingStatus.REJECTED),
            _f("F-3", FindingStatus.DUPLICATE),
            _f("F-4", FindingStatus.NEEDS_DEPLOYMENT_TESTING),
        ],
    )
    score = build_self_score(ws)
    assert score["total"] == 4
    assert sum(score["by_status"].values()) == 4
    assert score["by_status"]["duplicate"] == 1
    assert score["duplicate"] == 1


def test_self_score_reports_collapsed_counts(tmp_path):
    """REQ-54: the collapsed counts match the report, which collapses clusters."""
    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    a = _f("F-1", FindingStatus.CONFIRMED)
    b = _f("F-2", FindingStatus.CONFIRMED)
    a.cluster_id = b.cluster_id = "C-1"
    a.affected_sites = [{"id": "F-1", "file": "a.py", "line": 1}]
    write_findings(ws, [a, b])
    score = build_self_score(ws)
    assert score["confirmed"] == 2
    assert score["reported_collapsed"] == 1
```

Add a `_f` helper to that file only if it has none; reuse the existing one when it does. The helper must return a `Finding` with the given id and status, `rule_id="r"`, `cls="authz"`, `severity=Severity.MEDIUM`, `file="a.py"`, `line=1`, `message="m"`.

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py`:

```python
def test_gate_flags_a_self_score_that_loses_findings(tmp_path):
    """Check (h): the score's buckets must cover every finding on disk."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(), _ndt("N-2")])
    _selfscore(
        ws,
        {
            "confirmed": 0,
            "needs_runtime": 2,
            "duplicate": 0,
            "total": 2,
            "by_status": {"needs-deployment-testing": 1},
        },
    )
    ws.report_path.write_text(
        "# sec-overlay Report\n\nConfirmed: 0\nNeeds runtime proof: 2\n\n"
        + _triage("N-1", "owner check may be advisory", "see redteam-plan gaps")
        + "### N-2 — authz — Low · needs runtime proof\n\n"
    )
    errors = run_artifact_consistency(ws)
    assert any("by_status" in e for e in errors)
```

Reverse the existing tolerance. Replace `test_gate_flags_a_zero_self_score_against_a_reported_finding` with:

```python
def test_gate_flags_any_self_score_mismatch_against_the_report(tmp_path):
    """Check (d), reversed by REQ-54: the counts must be equal, not bounded.

    The old check tolerated a report count below the score, because the report
    collapsed clusters and the score did not. REQ-54 collapses both sides, so
    a difference in either direction is a contradiction.
    """
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt()])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 0})
    ws.report_path.write_text(_REPORT_HEAD)
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 2})
    errors = run_artifact_consistency(ws)
    assert any("needs_runtime" in e for e in errors)
```

- [ ] **Step 2: Run the tests to check they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_selfscore.py -k "partition or collapsed" -q
uv run pytest tests/test_artifact_consistency.py -k "loses_findings or any_self_score_mismatch" -q
```

Expected: the two self-score tests fail with `KeyError`. The partition test fails, because no clause reads `by_status`. The reversed test fails on its second half, because `if reported > scored:` accepts a report count below the score.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.3.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_selfscore.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(selfscore): pin the REQ-54 population partition"
```

- [ ] **Step 4: Add the partition and the collapsed counts**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/selfscore.py`, add the import:

```python
from collections import Counter

from sec_overlay.report import collapse_clusters
```

Insert before the `return` block at line 45:

```python
    by_status = Counter(f.status.value for f in findings)
    reported = [f for f in findings if f.status in _REPORTED]
    runtime = [f for f in findings if f.status is FindingStatus.NEEDS_DEPLOYMENT_TESTING]
```

Add five keys to the returned dict:

```python
        "total": len(findings),
        "duplicate": by_status.get("duplicate", 0),
        "by_status": dict(by_status),
        "reported_collapsed": len(collapse_clusters(reported)),
        "needs_runtime_collapsed": len(collapse_clusters(runtime)),
```

Update the `Returns:` block of the docstring to list them.

- [ ] **Step 5: Add clause (h) and reverse clause (d)**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py`, replace `_check_self_score` at lines 118-141:

```python
def _check_self_score(ws: Workspace, report_md: str) -> list[str]:
    """Check (d): the self-score does not contradict the report's own counts.

    Both sides collapse clusters (REQ-54), so the two counts must be equal. A
    missing score is a contradiction; a report with no count line is not.
    """
    score = load_state(ws).budget.get("self_score")
    if not isinstance(score, dict):
        return ["artifact-consistency: report exists but state.budget.self_score is missing"]
    match = re.search(r"^Needs runtime proof: (\d+)$", report_md, re.MULTILINE)
    if match is None:
        return []
    reported = int(match.group(1))
    scored = score.get("needs_runtime_collapsed", score.get("needs_runtime", 0))
    if reported != scored:
        return [
            (
                f"artifact-consistency: report shows {reported} needs-runtime "
                f"finding(s) but self_score.needs_runtime is {scored}"
            )
        ]
    return []


def _check_self_score_partition(ws: Workspace) -> list[str]:
    """Check (h): the self-score's buckets cover every finding on disk.

    Runs only when the score carries ``total`` and ``by_status``. A score
    written before REQ-54 carries neither and degrades to a pass.

    Args:
        ws: The finished-run workspace.

    Returns:
        Contradiction strings; empty when the buckets partition the population.
    """
    score = load_state(ws).budget.get("self_score")
    if not isinstance(score, dict):
        return []
    by_status = score.get("by_status")
    total = score.get("total")
    if not isinstance(by_status, dict) or not isinstance(total, int):
        return []
    errors: list[str] = []
    on_disk = len(read_findings(ws))
    if total != on_disk:
        errors.append(
            f"artifact-consistency: self_score.total is {total} but "
            f"{on_disk} finding(s) are on disk"
        )
    bucketed = sum(by_status.values())
    if bucketed != total:
        errors.append(
            f"artifact-consistency: self_score.by_status covers {bucketed} "
            f"finding(s) against a total of {total}"
        )
    return errors
```

Add the clause to the concatenation, after `_check_self_score`:

```python
        + _check_self_score_partition(ws)
```

- [ ] **Step 6: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_selfscore.py tests/test_artifact_consistency.py -q
uv run pytest -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: no failure. A circular-import error means `report.py` gained a `selfscore` import; revert that import rather than moving `collapse_clusters`.

- [ ] **Step 7: Commit the green change**

Update `helpers/sec_overlay/README.md` with the five new keys and the reversed clause (d).

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/selfscore.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(selfscore): partition the finding population"
```

---

## Task 3: REQ-55 — one preconditions field for the heading and the body

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py:182`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py`

**Interfaces:**
- Consumes: `Finding.preconditions`, `Finding.runtime_test`, `redteam._bullets`.
- Produces: no new symbol. `_directive_block` reads `runtime_test["preconditions"]` first and `Finding.preconditions` second.

- [ ] **Step 1: Write the failing test**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py`:

```python
def test_directive_falls_back_to_the_finding_preconditions():
    """REQ-55: the heading and the directive body read one preconditions field.

    A finding with dataflow and preconditions is grouped "Code-settled" by
    render_plan. Its directive must not then say the preconditions are absent.
    """
    f = Finding(
        id="F-1",
        rule_id="investigation:authz",
        cls="authz",
        status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
        severity=Severity.HIGH,
        file="a.js",
        line=1,
        risk_score=8,
        message="cross-tenant write",
        dataflow=["req.body -> db.write"],
        preconditions=["two tenants", "low-privilege token in tenant A"],
        runtime_test=None,
    )
    md = render_plan(discriminate([f]))
    assert "Code-settled, runtime-impact-pending" in md
    block = md.split("Code-settled, runtime-impact-pending")[1]
    assert "low-privilege token in tenant A" in block
    assert "_not specified_" not in block.split("**Payload")[0]
```

- [ ] **Step 2: Run the test to check it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_redteam.py -k "falls_back_to_the_finding_preconditions" -q
```

Expected: FAIL. `rt.get('preconditions')` is `None`, so `_bullets` renders `_not specified_`.

- [ ] **Step 3: Commit the red test**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(redteam): pin the REQ-55 preconditions fallback"
```

- [ ] **Step 4: Read one field**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py`, replace line 182:

```python
        f"- **Preconditions / access:**\n{_bullets(rt.get('preconditions'))}",
```

with:

```python
        f"- **Preconditions / access:**\n{_bullets(rt.get('preconditions') or f.preconditions)}",
```

Keep `_bullets`. It already handles a list, a bare string, and an empty value, and `tests/test_redteam.py:342` pins the string branch.

- [ ] **Step 5: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_redteam.py tests/test_redteam_gate_paths.py -q
uv run pytest -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: no failure.

- [ ] **Step 6: Commit the green change**

Update the `redteam.py` row in `helpers/sec_overlay/README.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.2"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(redteam): read one preconditions field"
```

---

## Task 4: REQ-56 — count the bottom line over the triage population

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:274-330`, `:435-446`, `:495`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py:158-172`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`

**Interfaces:**
- Consumes: `report._short_title(text, limit=72)`, `Finding.message`, `Finding.severity`.
- Produces: `report.triage_what(f: Finding) -> str` — the triage "What" cell, with any leading status sentence removed and the result passed through `_short_title`. `artifact_consistency._check_truncated_titles` calls it instead of recomputing the expression.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py`:

```python
def test_bottom_line_counts_the_triage_population():
    """REQ-56: a high-severity needs-runtime finding cannot read as medium/low."""
    high = dataclasses.replace(_ndt_med(), id="NDT-HI", severity=Severity.HIGH)
    out = to_markdown([_confirmed_dep()], needs_deployment=[high])
    assert "High-severity findings require immediate remediation." in out
    assert "medium/low" not in out.split("## Triage")[0]


def test_triage_what_drops_a_leading_status_sentence():
    """REQ-56: the What column carries the finding, never its status word."""
    assert triage_what(
        dataclasses.replace(
            _confirmed_dep(), message="Provenance unresolved. Sink reads user input."
        )
    ) == "Sink reads user input."
    assert triage_what(
        dataclasses.replace(_confirmed_dep(), message="Confirmed. Sink reads user input.")
    ) == "Sink reads user input."


def test_triage_row_carries_no_status_word_in_the_what_column():
    """REQ-56: the rendered row shows the finding, not its lifecycle state."""
    f = dataclasses.replace(
        _confirmed_dep(), message="Provenance unresolved. Sink reads user input."
    )
    out = to_markdown([f])
    row = next(l for l in out.splitlines() if l.startswith(f"| {f.id} "))
    assert "Provenance unresolved" not in row
    assert "Sink reads user input." in row
```

Add `triage_what` and `Severity` to the imports at the top of the file if they are absent.

- [ ] **Step 2: Run the tests to check they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_report.py -k "bottom_line_counts_the_triage or triage_what or no_status_word" -q
```

Expected: the first test fails, because `conf_counts` covers `findings` only and the sentence says "source-provable". The second and third fail on `ImportError`, because `triage_what` does not exist.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.3"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(report): pin the REQ-56 triage counts"
```

- [ ] **Step 4: Add the shared What helper**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py`, add the vocabulary beside `_ORDER` at line 31:

```python
# A message may open with the finding's lifecycle state. The triage "What" column
# describes the defect, so a leading status sentence is dropped, not rendered.
_STATUS_LEAD = frozenset(
    {
        "candidate",
        "confirmed",
        "duplicate",
        "fixed",
        "needs runtime proof",
        "provenance unresolved",
        "rejected",
        "stale",
        "unconfirmed",
        "verified",
    }
)
```

Add the helper below `_short_title`:

```python
def triage_what(f: Finding) -> str:
    """Return the triage "What" cell for a finding.

    The cell describes the defect. A message that opens with the finding's
    lifecycle state ("Confirmed. ", "Provenance unresolved. ") has that sentence
    dropped, because the row already carries a Status column. ``Finding`` has no
    ``title`` field, so ``message`` is the only source.

    Args:
        f: The finding to describe.

    Returns:
        The first non-status sentence of the message, clipped by ``_short_title``.

    Example:
        >>> triage_what(Finding(message="Confirmed. Sink reads user input."))
        'Sink reads user input.'
    """
    parts = (f.message or "").split("|", 1)[0].strip().split(". ")
    while len(parts) > 1 and parts[0].strip().rstrip(".").lower() in _STATUS_LEAD:
        parts = parts[1:]
    return _short_title(parts[0].strip())
```

Replace line 328 with:

```python
    what = triage_what(f)
```

Replace the expression at line 495 with `{triage_what(f)}`.

- [ ] **Step 5: Count the sentence over the triage population**

Replace lines 435-446 of `report.py`:

```python
    conf_counts = Counter(f.severity.value for f in findings)
    crit = conf_counts.get("critical", 0)
    high = conf_counts.get("high", 0)
    med = conf_counts.get("medium", 0)
    low = conf_counts.get("low", 0)
    total_conf = sum(conf_counts.values())
    triage_counts = Counter(f.severity.value for f in list(ndt) + list(conf))
    t_crit = triage_counts.get("critical", 0)
    t_high = triage_counts.get("high", 0)
    if sum(triage_counts.values()) == 0:
        summary_sentence = "No reportable findings."
    elif t_crit or t_high:
        summary_sentence = (
            f"{'Critical' if t_crit else 'High'}-severity findings require "
            "immediate remediation."
        )
    else:
        summary_sentence = "Reportable findings at medium/low severity."
```

`crit`, `high`, `med`, `low`, and `total_conf` stay. The `Confirmed:` counts phrase below still reads them, and `tests/test_report.py:678` pins its output.

- [ ] **Step 6: Point clause (f) at the same helper**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py`, replace lines 166-168:

```python
        source = (finding.message or "").split("|", 1)[0].split(". ")[0].strip()
        if what != _short_title(source):
```

with:

```python
        if what != triage_what(finding):
```

Change the import at line 20 to:

```python
from sec_overlay.report import triage_what
```

Remove `_short_title` from that import if no other clause uses it.

- [ ] **Step 7: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_report.py tests/test_report_split.py tests/test_report_optional_sections.py tests/test_artifact_consistency.py -q
uv run pytest -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: no failure. A failure on the mid-word truncation test means clause (f) and `_triage_row` disagree; both must call `triage_what`.

- [ ] **Step 8: Commit the green change**

Update the `report.py` row in `helpers/README.md:165` and the two bottom-line statements in `helpers/sec_overlay/README.md:241` and `:247`. All three still say "Confirmed (source-provable)" for the summary sentence.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.4"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(report): count the bottom line over triage"
```

---

## Task 5: REQ-57 — carry the cluster's sites and the finding id into SARIF

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py:75-116`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py`

**Interfaces:**
- Consumes: `Finding.affected_sites` (a list of `{"id", "file", "line"}` dicts), `Finding.id`.
- Produces: each SARIF result gains `properties.findingId`, gains `relatedLocations` when `affected_sites` is non-empty, and a suppressed result carries `kind: "external"`.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py`:

```python
def test_a_cluster_emits_one_related_location_per_affected_site():
    """REQ-57: a systemic cluster must not shrink to one location in SARIF."""
    f = _f(Severity.HIGH)
    f.cluster_id = "C-1"
    f.affected_sites = [
        {"id": "F-0002", "file": "a.py", "line": 18},
        {"id": "F-0003", "file": "b.py", "line": 42},
        {"id": "F-0004", "file": "c.py", "line": 7},
    ]
    result = to_sarif([f])["runs"][0]["results"][0]
    related = result["relatedLocations"]
    assert len(related) == 3
    uris = [r["physicalLocation"]["artifactLocation"]["uri"] for r in related]
    assert uris == ["a.py", "b.py", "c.py"]
    assert related[1]["physicalLocation"]["region"]["startLine"] == 42


def test_a_singleton_finding_has_no_related_locations():
    """REQ-57: the key appears only when the finding carries sites."""
    assert "relatedLocations" not in to_sarif([_f(Severity.LOW)])["runs"][0]["results"][0]


def test_every_result_carries_its_finding_id():
    """REQ-57: a SARIF consumer must be able to name the finding."""
    result = to_sarif([_f(Severity.HIGH)])["runs"][0]["results"][0]
    assert result["properties"]["findingId"] == "F-0001"
```

Reverse the suppression-kind assertion. Rename `test_suppressed_findings_carry_insource_suppression` to `test_suppressed_findings_carry_an_external_suppression`, keep its body, and replace its last line with:

```python
    assert by_id["b.py"]["suppressions"][0]["kind"] == "external"
```

Add a docstring naming the reversal:

```python
    """REQ-57: a needs-runtime suppression is external, not inSource.

    The prior contract emitted ``inSource``, which asserts an annotation in the
    reviewed file. No such annotation exists; the reason is out-of-repo.
    """
```

- [ ] **Step 2: Run the tests to check they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_sarif.py -q
```

Expected: four failures. Three raise `KeyError` on `relatedLocations` or `properties`. The renamed test fails on `'inSource' != 'external'`.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.4.5"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sarif): pin the REQ-57 cluster locations"
```

- [ ] **Step 4: Emit the sites, the id, and the right suppression kind**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py`, add the helper above `to_sarif`:

```python
def _related_locations(finding: Finding) -> list[dict]:
    """Return one SARIF location per site of a systemic cluster.

    A cluster representative carries every member's site in ``affected_sites``.
    Without these, a 66-site cluster reaches a SARIF consumer as one location.

    Args:
        finding: The finding to expand.

    Returns:
        One location dict per site, in the order the finding records them. An
        entry missing ``file`` is skipped; ``line`` defaults to 1.
    """
    out: list[dict] = []
    for site in finding.affected_sites or []:
        uri = site.get("file")
        if not uri:
            continue
        out.append(
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": site.get("line") or 1},
                }
            }
        )
    return out
```

In the result loop, add the related locations and the id after the `result` literal at lines 93-106:

```python
        related = _related_locations(f)
        if related:
            result["relatedLocations"] = related
        result["properties"] = {"findingId": f.id}
```

Replace line 107:

```python
            result["suppressions"] = [{"kind": "inSource", "justification": "needs runtime proof"}]
```

with:

```python
            result["suppressions"] = [
                {"kind": "external", "justification": "needs runtime proof"}
            ]
```

Update the `suppressed` parameter docstring at line 83 to say `external`.

- [ ] **Step 5: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_sarif.py tests/test_correlate_xrepo_sarif.py tests/test_report.py -q
uv run pytest -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: no failure. `test_to_sarif_empty_list_has_no_results_and_no_fingerprint_key_anywhere` must stay green; the new keys sit inside the result loop, which an empty list never enters.

- [ ] **Step 6: Commit the green change**

Update the `sarif.py` row in `helpers/sec_overlay/README.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sarif): emit cluster sites and finding ids"
```

---

## Task 6: REQ-58 — fingerprint every finding, whatever its status

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dedupe.py:49-54`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dedupe.py`

**Interfaces:**
- Consumes: `fingerprint(f, anchor=...)`, `symbol_at(graph, file, line)`, `_ACTIVE`.
- Produces: every finding on disk carries a 12-character `fingerprint` after `dedupe_findings` runs. `postflight._merge` no longer falls back to a `file:line:cls` key. No new symbol.

- [ ] **Step 1: Write the failing test**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dedupe.py`:

```python
def test_dedupe_stamps_a_fingerprint_on_a_rejected_finding(tmp_path):
    """REQ-58: two rejected findings at one site must not share a prior-context key.

    postflight._merge falls back to `file:line:cls` when the fingerprint is
    absent, which collapses distinct rejections onto one key and drops a note.
    """
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    a = _f("F-0001", "cmdi", "s.ts", 23, Severity.MEDIUM, status=FindingStatus.REJECTED)
    b = _f("F-0002", "cmdi", "s.ts", 23, Severity.MEDIUM, status=FindingStatus.REJECTED)
    a.rule_id = "rules.semgrep.javascript.lang.security.detect-child-process"
    b.rule_id = "js/indirect-command-line-injection"
    write_findings(ws, [a, b])
    dedupe_findings(ws)
    prints = {f.id: f.fingerprint for f in read_findings(ws)}
    assert all(p is not None and len(p) == 12 for p in prints.values())
    assert prints["F-0001"] != prints["F-0002"]
```

Read `_f` in that file first. If it does not accept `status`, it does — `tests/test_dedupe.py:73` already passes `status=FindingStatus.REJECTED`.

- [ ] **Step 2: Run the test to check it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_dedupe.py -k "rejected_finding" -q
```

Expected: FAIL. Both fingerprints are `None`, because the stamping loop filters on `_ACTIVE`.

If the second assertion fails while the first passes, `fingerprint()` does not read `rule_id`. Report that before changing the fingerprint function; the register's trigger relies on the two rules differing.

- [ ] **Step 3: Commit the red test**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dedupe.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(dedupe): pin the REQ-58 rejected fingerprint"
```

- [ ] **Step 4: Widen the stamping loop**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dedupe.py`, replace lines 49-54:

```python
    graph = load_graph(ws) if (ws.kb / "graph.json").exists() else None
    for f in findings:
        if f.status in _ACTIVE:
            anchor = symbol_at(graph, f.file, f.line) if graph is not None else None
            f.fingerprint = fingerprint(f, anchor=anchor)
    stamped = True
```

with:

```python
    graph = load_graph(ws) if (ws.kb / "graph.json").exists() else None
    for f in findings:
        anchor = symbol_at(graph, f.file, f.line) if graph is not None else None
        f.fingerprint = fingerprint(f, anchor=anchor)
    stamped = True
```

Leave `_ACTIVE` in place. The three grouping passes still read it, and only findings in that set may be marked duplicate.

Update the docstring at line 24: "All findings are stamped with a stable fingerprint, whatever their status, so the prior-context merge in `postflight` never falls back to a `file:line:cls` key."

- [ ] **Step 5: Run the tests to check they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_dedupe.py tests/test_postflight.py -q
uv run pytest -q
uv run ruff check sec_overlay/ tests/ && uv run ty check
```

Expected: no failure. `test_dedupe_ignores_non_active_statuses` asserts a marked count of zero, not an absent fingerprint, so it stays green.

- [ ] **Step 6: Commit the green change**

Update the `dedupe.py` row in `helpers/sec_overlay/README.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.2"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dedupe.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(dedupe): fingerprint every finding"
```

---

## Self-review

**1. Specification coverage.** Group 4's four requirements and Group 5's two requirements each have one task. REQ-53 is Task 1, and its two-part clause (g) covers both halves of the specification's row: the SARIF-against-report count and the report's own stated count. REQ-54 is Task 2, which adds the named `duplicate` key, the `by_status` partition, and the cluster collapse the row demands on both sides. REQ-55 is Task 3. REQ-56 is Task 4, covering both the bottom-line population and the "What" column. REQ-57 is Task 5, covering all three of its clauses — related locations, the finding id, and the suppression kind. REQ-58 is Task 6. Section 6's constraint that REQ-53, REQ-54, and REQ-55 block rather than warn is satisfied without a code change: `driver._act_artifact_consistency` already raises `PhaseHalt` on a non-empty list, which the pre-flight scan records. Section 6's re-run against `/Users/christopher/Workspace/review_comply/Comply` belongs after Group 7 and is out of scope here. Two specification rows are corrected rather than implemented as written: REQ-56's `f.title` clause, because the field does not exist, and REQ-53's single-site claim, because the count gap originates in `report.py`. Both corrections are in the pre-flight tables.

**2. Placeholder scan.** Every code step carries the real code. No step says "add error handling" or "similar to Task N". Two steps direct the implementer to read a file before editing: Task 4's README updates and Task 6's `_f` helper check. Both name the exact file and line. Task 1's Step 4 names the line to replace and the risk of breaking the list literal.

**3. Type consistency.** `triage_what(f: Finding) -> str` is defined in Task 4 and called from `report._triage_row`, the `## Detail` loop, and `artifact_consistency._check_truncated_titles`. All three take a `Finding` and use the returned string directly. `_rendered_ids(ws, report_md) -> set[str]` is defined and consumed in Task 1 only. `_check_sarif_population` and `_check_self_score_partition` both return `list[str]`, matching the other six clauses and the concatenation in `run_artifact_consistency`. `_related_locations(finding) -> list[dict]` returns SARIF location dicts of the same shape as the `locations` entry beside it. The self-score keys are `total: int`, `duplicate: int`, `by_status: dict[str, int]`, `reported_collapsed: int`, `needs_runtime_collapsed: int`; clause (d) reads `needs_runtime_collapsed` with `needs_runtime` as the fallback, and clause (h) reads `total` and `by_status`.

**4. Ordering.** Task 1 must precede Task 2, because clause (h) sits beside clause (g) in the same concatenation. Task 4 must precede nothing, but it must follow Task 1: Task 1 edits the same `lines +=` block at `report.py:455-462` that Task 4's sentence feeds. Task 4 also changes `artifact_consistency` clause (f), which Task 1 and Task 2 leave alone. Tasks 5 and 6 touch neither `report.py` nor `artifact_consistency.py` and could run in any order, but they run last to keep the specification's RC-11 before RC-13 sequence. Task 5's SARIF change adds keys to a result and does not change the result count, so clause (g) from Task 1 stays green through it.
