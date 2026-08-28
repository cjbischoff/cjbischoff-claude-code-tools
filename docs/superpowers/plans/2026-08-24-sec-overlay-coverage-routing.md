# sec-overlay Coverage and Routing Implementation Plan (Part E group 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the four coverage-and-routing requirements — REQ-04, REQ-11, REQ-25, REQ-24 — so the report carries one coverage source, `ScanProfile` accepts a derived `route_summary`, an indicator hit routes an attack class without a manifest, and the investigate saturation loop runs mechanically.

**Architecture:** Each requirement is a small change to one deterministic module plus its prompt or report surface. REQ-04 deletes a contradicting artifact and its producer. REQ-11 adds one dataclass field and derives it in the recall gate. REQ-25 adds one indicator matcher and unions it into the existing routing call. REQ-24 folds the existing `discovery_ledger` library into two driver sites.

**Tech Stack:** Python 3.11+, standard library only. Test runner `pytest`. Lint `ruff`. Types `ty`. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `docs/superpowers/specs/2026-08-23-sec-overlay-improvements-design.md` (group-4 REQ table at `:161-164`). The binding requirement text is `/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md`, blocks REQ-04 (`:250-264`), REQ-11 (`:342-356`), REQ-24 (`:492-506`), REQ-25 (`:508-521`).

**Base commit:** `f406553` (version `1.115.5`, suite 1699 passed).

---

## Global Constraints

- Never commit to `main`. All work lands on branch `feat/sec-overlay-improvements`.
- Conventional Commits: `<type>(sec-overlay): <imperative summary>`. The 50-character cap applies to the summary **after** the `type(scope): ` prefix. The REQ id goes in the commit **body**, never the subject.
- Two commits per requirement: a RED commit (`test(sec-overlay): ...`) that adds the failing test, then a GREEN commit (`fix(sec-overlay): ...` or `feat(sec-overlay): ...`) that makes it pass.
- Stage explicit paths only. Never `git add -A`, `git add .`, `git add -u`, or `git commit -a`. Never `--no-verify`.
- No `Co-Authored-By` trailer.
- Run `prek run` before every commit.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `version` in the same commit as any shipping-file change. `feat` bumps minor; every other type bumps patch. A `CHANGELOG.md` is not a shipping file.
- Add a `plugins/sec-overlay/CHANGELOG.md` entry to every commit.
- The prek hook binds a staged file to its **immediate** folder `README.md`. Staging a file under `helpers/sec_overlay/` requires `helpers/sec_overlay/README.md`; under `helpers/tests/` requires `helpers/tests/README.md`; under `agents/` requires `agents/README.md`.
- Run every `git` command from the repository root. A stray nested git repository exists at `helpers/.git`.
- The plugin core is standard-library only. Do not add a dependency.
- `sec_overlay/models.py` and `sec_overlay/evidence.py` are byte-frozen by `tests/test_frozen_contract.py`. Do not touch either file. `sec_overlay/coverage.py` is **not** frozen — the past-tense sentence at `sec_overlay/README.md:580` is a historical changelog note, not a live freeze.
- Hard limits: functions under 100 lines, cyclomatic complexity under 8, at most 5 positional parameters, 100-character lines, structured docstrings on public functions.
- Written files use Simplified Technical English. Chat replies do not.

## Gate command block (run from `helpers/`)

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

## Expected suite count per task

The suite does **not** grow monotonically in this group. Task 1 deletes five tests.

| After task | Expected `pytest -q` count |
|------------|----------------------------|
| BASE `f406553` | 1699 |
| Task 1 RED | 1702 (2 failing) |
| Task 1 GREEN | 1697 |
| Task 2 GREEN | 1700 |
| Task 3 GREEN | 1702 |
| Task 4 GREEN | 1706 |

---

## File Structure

| File | Responsibility after this group |
|------|--------------------------------|
| `helpers/sec_overlay/coverage.py` | **Deleted.** Its per-language accounting contradicted the per-sink ledger. |
| `helpers/sec_overlay/report.py` | Renders coverage from `kb/coverage-ledger.json` only. |
| `helpers/sec_overlay/prefilter.py` | No longer computes or persists `kb/coverage.json`. |
| `helpers/sec_overlay/profile.py` | `ScanProfile` carries a `route_summary` dict field. |
| `helpers/sec_overlay/driver.py` | `_act_recall_gate` derives `route_summary`; `_act_findings_gate` folds a discovery wave; the dispatch loop stops re-dispatching a saturated investigate phase. |
| `helpers/sec_overlay/route_control.py` | `check_recon_routes` guards against a non-list `route_summary`. |
| `helpers/sec_overlay/dependency_sinks.py` | New `indicator_classes` matcher over target source. |
| `helpers/sec_overlay/partition.py` | `reconcile_plan` unions manifest matches with indicator matches. |
| `agents/investigate.md` | Carries wave and saturation language. |

---

## Rulings carried into this plan

These were decided before the plan and are binding on every task.

- **Ruling 50 (REQ-04).** REQ-04 builds literally. Delete the file-based coverage line, the `coverage` parameter, the `coverage.json` artifact, and the now-dead `sec_overlay/coverage.py` with its test file. The design spec's stated REQ-04 test ("the report renders coverage with no `coverage.json` present") is already green at BASE and cannot serve as a red test; the binding red test comes from the requirements document instead.
- **Ruling 51 (REQ-11).** "A route with an assigned investigator class" means "a route the recon profile mentions", reusing `route_control.check_census_routes`. The codebase carries no per-route class mapping, so no other definition is code-grounded. Cost if wrong: `covered` overstates coverage when recon names a route but assigns it no class — smaller than today's `TypeError`.
- **Ruling 52 (REQ-24).** Wave granularity is one wave per `findings-gate` run, folded in `_act_findings_gate`. The "stop on `terminal_reason`" half lands at the investigate dispatch site. Cost if wrong: a multi-wave investigate phase records one wave, not several, so saturation needs more passes; the loop still terminates on the `max_waves` cap.
- **Ruling 53 (REQ-25).** An entry routes its class when **any one** of its indicators appears in target source. The requirement's own example routes `ssrf` with `rego.Capabilities` absent, so the rule cannot be "every indicator present".
- **Cite drift (REQ-25).** The requirement cites `dependency_sinks.py:114` as the change site. That line is the `indicators=tuple(...)` constructor argument. The real change site is `partition.reconcile_plan` (`partition.py:95-132`) plus a new matcher in `dependency_sinks.py`. Record this drift in the GREEN commit body.

---

## Task 1: REQ-04 — one coverage metric

**Files:**
- Delete: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage.py`
- Delete: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_coverage.py`
- Modify: `helpers/sec_overlay/report.py:262`, `:286-288`, `:407-429`, `:590-591`, `:628`
- Modify: `helpers/sec_overlay/prefilter.py:15`, `:157-158`, `:308-310`, `:316`, `:326`
- Modify: `helpers/tests/test_report.py:158-179` (delete the test)
- Modify: `helpers/tests/test_prefilter.py:263-274` (delete the test)
- Modify: `helpers/README.md:195-197` (remove the `coverage.py` module row)
- Test: `helpers/tests/test_report.py`, `helpers/tests/test_prefilter.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `to_markdown` loses its `coverage` keyword parameter. `run_prefilter`'s result dict loses its `"coverage"` key. No later task in this group calls either.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_report.py`:

```python
def test_report_renders_no_dataflow_percentage_line(tmp_path):
    """A stale coverage.json must not resurrect the file-based percentage (REQ-04).

    The per-sink ledger is the single coverage source. A second percentage beside
    it contradicted the ledger whenever the two disagreed.
    """
    import json

    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    (ws.kb / "coverage.json").write_text(
        json.dumps(
            {
                "languages": [{"language": "liquid", "files": 194, "tier": "none"}],
                "dataflow_pct": 17,
                "uncovered": ["liquid"],
            }
        )
    )
    write_report(ws)
    md = ws.report_path.read_text()
    assert "Dataflow coverage" not in md
    assert "of counted source" not in md


def test_a_partial_ledger_claims_no_full_coverage(tmp_path):
    """A partial ledger must not print a full-coverage claim anywhere (REQ-04)."""
    import json

    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    (ws.kb / "coverage-ledger.json").write_text(
        json.dumps(
            {
                "completeness": "partial",
                "surfaces": [
                    {
                        "id": "http-api",
                        "disposition": "needs_follow_up",
                        "reason": "no investigator ran",
                        "next_step": "route an investigator",
                    }
                ],
                "deferred": [],
                "open_questions": [],
            }
        )
    )
    write_report(ws)
    md = ws.report_path.read_text()
    assert "partial" in md
    assert "100%" not in md
    assert "Dataflow coverage" not in md
```

Append to `helpers/tests/test_prefilter.py`:

```python
def test_run_prefilter_writes_no_coverage_artifact(tmp_path):
    """kb/coverage.json contradicted the per-sink ledger and is gone (REQ-04)."""
    ws = Workspace(tmp_path / "ws"); ws.ensure()
    sem = lambda target, config, **k: [_cand("sqli", "a.go", 1)]
    cql = lambda target, language, db_dir, **k: [_cand("ssrf", "b.go", 2)]
    res = run_prefilter(ws, str(tmp_path), _profile(), semgrep=sem, codeql=cql,
                        has_tool=lambda n: "/x", qlpack_fn=lambda lang: True)
    assert "coverage" not in res
    assert not (ws.kb / "coverage.json").exists()
```

- [ ] **Step 2: Run the tests and confirm two fail**

Run: `uv run pytest tests/test_report.py tests/test_prefilter.py -q`

Expected: `test_report_renders_no_dataflow_percentage_line` FAILS (the report still prints the line) and `test_run_prefilter_writes_no_coverage_artifact` FAILS (the key and the file still exist). `test_a_partial_ledger_claims_no_full_coverage` PASSES at this commit — it is a pre-existing regression guard, not a red test. Record that split in the report.

- [ ] **Step 3: Commit RED**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prefilter.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sec-overlay): add failing coverage-source tests"
```

Version `1.115.5` becomes `1.115.6`. The CHANGELOG entry goes under `### Added`.

- [ ] **Step 4: Delete the file-based coverage block in `report.py`**

Delete the whole `if coverage:` block (currently `report.py:407-429`), the `coverage: dict | None = None,` parameter (currently `:262`), and its docstring entry (currently `:286-288`):

```
        coverage: Optional ``compute_coverage`` output (``kb/coverage.json``); when given,
            appends a "Coverage & limitations" section so a clean scan carries its
            denominator (O-007/O-033). Omitted entirely when ``None``.
```

Delete the read (currently `:590-591`):

```python
    coverage_path = ws.kb / "coverage.json"
    coverage = json.loads(coverage_path.read_text()) if coverage_path.exists() else None
```

Delete the `coverage=coverage,` argument in the `to_markdown(...)` call (currently `:628`).

- [ ] **Step 5: Delete the producer sites in `prefilter.py`**

Delete the import at `:15`:

```python
from sec_overlay.coverage import compute_coverage
```

Delete the docstring sentence at `:157-158`:

```
    ``coverage`` is the per-language dataflow/ pattern-only/none breakdown from
    :func:`sec_overlay.coverage.compute_coverage` (also persisted to ``kb/coverage.json``).
```

Delete the compute-and-persist block at `:308-310`:

```python
    coverage = compute_coverage(profile, ran, target)
    ws.kb.mkdir(parents=True, exist_ok=True)
    (ws.kb / "coverage.json").write_text(json.dumps(coverage, indent=2))
```

Reduce the receipt call at `:316` to drop the deleted artifact:

```python
    receipt(ws, "prefilter", counts=finding_counts(ws))
```

Delete the `"coverage": coverage,` entry from the return dict at `:326`.

- [ ] **Step 6: Delete the dead module and the tests that pin the deleted behaviour**

```bash
git rm plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage.py \
       plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_coverage.py
```

Delete `test_report_renders_coverage_section` (currently `tests/test_report.py:158-179`) and `test_run_prefilter_result_has_coverage` (currently `tests/test_prefilter.py:263-274`). Both assert the behaviour REQ-04 removes; per the standing ruling, a test that pins deleted behaviour is deleted with it, and a gate is never loosened to keep one green.

- [ ] **Step 7: Update the module map**

In `helpers/README.md`, remove the table row:

```
| `coverage.py` | Per-language SAST coverage accounting (dataflow vs pattern-only vs none). |
```

Add one paragraph to `helpers/sec_overlay/README.md` recording that `coverage.py` is gone, that `kb/coverage.json` is no longer written, and that `kb/coverage-ledger.json` is the single coverage source. Reword `sec_overlay/README.md:580` so it no longer reads as a live freeze declaration covering `coverage.py`; only `models.py` and `evidence.py` are pinned by `tests/test_frozen_contract.py`.

- [ ] **Step 8: Run the gate**

Run the gate command block. Expected: 1697 passed, ruff clean, ty clean.

If `ty` reports an unused `json` import in `prefilter.py`, check whether `json` still has another use in that file before removing it. Remove only imports this change made unused.

- [ ] **Step 9: Commit GREEN**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prefilter.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_coverage.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(sec-overlay): render coverage from the ledger only"
```

Version `1.115.6` becomes `1.115.7`. The commit body names REQ-04 and records that `coverage.json` was the transcript's last surviving backend-provenance trace before REQ-16 made the receipt survive a fence abort.

---

## Task 2: REQ-11 — accept and derive `route_summary`

**Files:**
- Modify: `helpers/sec_overlay/profile.py:40-43` (docstring), `:46-57` (fields), `:71` (`_OPTIONAL_DICT_FIELDS`)
- Modify: `helpers/sec_overlay/driver.py:344-367` (`_act_recall_gate`)
- Modify: `helpers/sec_overlay/route_control.py:76-90` (`check_recon_routes` shape guard and docstring)
- Modify: `agents/recon.md:118-121`, `agents/README.md:271`
- Test: `helpers/tests/test_profile.py`, `helpers/tests/test_driver.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `ScanProfile.route_summary: dict` with keys `total: int`, `covered: int`, `uncovered: list[str]`. `_act_recall_gate` writes the derived value back into `kb/scan-profile.json`. No later task in this group reads it.

**Note on scope:** `references/schemas/` does not exist in this repository, so there is no scan-profile JSON schema file to update. Do not create one — that would be new scope.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_profile.py`:

```python
def test_from_dict_accepts_a_route_summary_key():
    """A recon payload carrying route_summary must not crash from_dict (REQ-11)."""
    from sec_overlay.profile import ScanProfile

    p = ScanProfile.from_dict(
        {"route_summary": {"total": 2, "covered": 1, "uncovered": ["GET /health"]}}
    )
    assert p.route_summary["uncovered"] == ["GET /health"]


def test_validate_profile_rejects_a_non_object_route_summary():
    """route_summary is a derived object, not the old list of route strings (REQ-11)."""
    from sec_overlay.profile import validate_profile

    errors = validate_profile({"route_summary": ["/health"]})
    assert any("route_summary" in e for e in errors)
```

Append to `helpers/tests/test_driver.py`:

```python
def test_recall_gate_derives_route_summary_from_the_census(tmp_path):
    """route_summary must report census coverage, not restate entrypoints (REQ-11).

    A census route the profile never names is uncovered; a route it names is not.
    """
    from sec_overlay.driver import DETERMINISTIC_ACTIONS

    ctx = _ctx(tmp_path, target=str(_ROUTE_FIXTURE))
    DETERMINISTIC_ACTIONS["route-census"](ctx)
    (ctx.ws.kb / "scan-profile.json").write_text(
        json.dumps({"entrypoints": ["/policy/evaluate"], "attack_surface": []})
    )
    DETERMINISTIC_ACTIONS["recall-gate"](ctx)
    summary = json.loads((ctx.ws.kb / "scan-profile.json").read_text())["route_summary"]
    assert summary["total"] >= 2
    assert any("/health" in u for u in summary["uncovered"])
    assert not any("/policy/evaluate" in u for u in summary["uncovered"])
    assert summary["covered"] == summary["total"] - len(summary["uncovered"])
```

- [ ] **Step 2: Run the tests and confirm all three fail**

Run: `uv run pytest tests/test_profile.py tests/test_driver.py -q`

Expected: `test_from_dict_accepts_a_route_summary_key` FAILS with `TypeError: ... unexpected keyword argument 'route_summary'`; `test_validate_profile_rejects_a_non_object_route_summary` FAILS on the `any(...)` assertion (no error mentions the key today); `test_recall_gate_derives_route_summary_from_the_census` FAILS with `KeyError: 'route_summary'`.

- [ ] **Step 3: Commit RED**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_profile.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sec-overlay): add failing route_summary tests"
```

- [ ] **Step 4: Add the field to `ScanProfile`**

In `helpers/sec_overlay/profile.py`, add one field after `scan_options` (currently `:57`):

```python
    route_summary: dict = field(default_factory=dict)
```

Add it to the optional-object validation tuple (currently `:71`):

```python
_OPTIONAL_DICT_FIELDS = ("scan_options", "route_summary")
```

Add one entry to the class docstring `Args:` block, after the `scan_options` entry:

```
        route_summary: Derived census coverage the recall gate writes back:
            ``total`` census routes, ``covered`` routes the profile mentions, and
            ``uncovered`` route ids it never mentions. Never hand-authored by recon.
```

- [ ] **Step 5: Derive the value in the recall gate**

In `helpers/sec_overlay/driver.py`, change `_act_recall_gate`'s body so the census gaps are captured separately, then written back:

```python
    profile_dict = json.loads((ctx.ws.kb / "scan-profile.json").read_text())
    sites = load_census(ctx.ws)
    route_gaps = check_census_routes(sites, profile_dict)
    gaps = list(route_gaps)
    gaps += check_catalog_classes(match_manifests(ctx.target), profile_dict)
    record_route_gaps(ctx.ws, gaps)
    profile_dict["route_summary"] = {
        "total": len(sites),
        "covered": len(sites) - len(route_gaps),
        "uncovered": [g["id"] for g in route_gaps],
    }
    (ctx.ws.kb / "scan-profile.json").write_text(json.dumps(profile_dict, indent=2))
    _write_gate(ctx.ws, "recall-gate", [], [])
```

Add one sentence to the function docstring naming the write-back:

```
    Also derives ``route_summary`` from the census and writes it back into the
    profile: total census routes, routes the profile mentions, and routes it does
    not. The field reports coverage of the census, never a copy of it (REQ-11).
```

The invariant this must hold: `covered == total - len(uncovered)`, and every id in `uncovered` is a census route the profile never mentions.

- [ ] **Step 6: Guard the old list reader**

`route_control.check_recon_routes` reads `route_summary` as a list of route strings. Iterating the new dict would yield its key names and silently mark routes as summarised. In `helpers/sec_overlay/route_control.py`, replace the read (currently `:87`):

```python
    raw = profile.get("route_summary")
    summarised = {str(r) for r in raw} if isinstance(raw, list) else set()
```

Replace the docstring paragraph naming the field so it states the current shape:

```python
def check_recon_routes(table: dict, profile: dict) -> list[dict]:
    """Gap for any table route the recon profile does not summarise.

    ``route_summary`` is now a derived object the recall gate writes
    (``total``/``covered``/``uncovered``), not the legacy list of route strings.
    Only the legacy list form is read here; any other shape leaves every table
    route flagged as a logged gap (never-drop invariant).
    A census-sourced table returns no gaps here: ``check_census_routes`` owns
    that comparison, since a census route carries a method prefix
    ``route_summary`` can never contain.
    """
```

Do not change the two existing tests at `tests/test_route_control.py:131-152`. They pass the legacy list form, which the guard still accepts.

- [ ] **Step 7: Correct the prompt contract**

`agents/recon.md:118-121` instructs recon to emit `route_summary` itself. The field is now derived, so the prompt must stop claiming ownership. Rewrite that block to state that the recall gate derives `route_summary` from the route census after recon finishes, and that recon must instead name every route it investigates in `entrypoints` and `attack_surface`, because the derivation counts a route as covered only when the profile mentions it.

Update the matching line at `agents/README.md:271` to describe the derived field.

`tests/test_contracts.py:75-76` asserts only that `recon.md` contains the substring `route`. The rewrite keeps that true. Confirm it still passes rather than assuming it.

- [ ] **Step 8: Run the gate**

Run the gate command block. Expected: 1700 passed, ruff clean, ty clean.

- [ ] **Step 9: Commit GREEN**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/profile.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/recon.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): derive route_summary from the census"
```

This is a `feat`, so the version bumps by a minor increment.

---

## Task 3: REQ-25 — route on a dependency-sink indicator

**Files:**
- Modify: `helpers/sec_overlay/dependency_sinks.py` (new `indicator_classes`, new `_source_files`)
- Modify: `helpers/sec_overlay/partition.py:129-131`
- Test: `helpers/tests/test_dependency_sinks.py`, `helpers/tests/test_partition.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `dependency_sinks.indicator_classes(root, *, path=CATALOG_PATH) -> list[str]` — the sorted, deduplicated attack classes of every catalog entry with at least one indicator hit in target source.

**Catalog fixture fact:** `references/dependency-sinks.json` holds the entry `opa-rego-http-send`, class `ssrf`, package `github.com/open-policy-agent/opa`, manifests `["go.mod", "go.sum"]`, indicators `["rego.New", "rego.Module", "http.send", "rego.Capabilities"]`. A target that calls `rego.New` with no `go.mod` is the requirement's stated test case.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_dependency_sinks.py`:

```python
def test_indicator_classes_routes_without_a_manifest(tmp_path):
    """A Bazel or vendored target has no manifest but still calls the sink (REQ-25)."""
    from sec_overlay.dependency_sinks import indicator_classes, match_manifests

    (tmp_path / "policy.go").write_text(
        "package main\n\nfunc run() { r := rego.New(rego.Query(\"x\")) ; _ = r }\n"
    )
    assert match_manifests(tmp_path) == []
    assert "ssrf" in indicator_classes(tmp_path)


def test_indicator_classes_is_empty_without_an_indicator(tmp_path):
    """No indicator in source means no extra routing (REQ-25)."""
    from sec_overlay.dependency_sinks import indicator_classes

    (tmp_path / "main.go").write_text("package main\n\nfunc main() {}\n")
    assert indicator_classes(tmp_path) == []
```

Append to `helpers/tests/test_partition.py`:

```python
def test_reconcile_plan_routes_a_class_on_an_indicator_hit(tmp_path):
    """An indicator hit routes the entry's class even with no manifest match (REQ-25)."""
    from sec_overlay.partition import reconcile_plan
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path / "ws")
    ws.ensure()
    target = tmp_path / "t"
    target.mkdir()
    (target / "policy.go").write_text(
        "package main\n\nfunc run() { r := rego.New(rego.Query(\"x\")) ; _ = r }\n"
    )
    assert "ssrf" in reconcile_plan(ws, ["authz"], target_root=target)
```

- [ ] **Step 2: Run the tests and confirm all three fail**

Run: `uv run pytest tests/test_dependency_sinks.py tests/test_partition.py -q`

Expected: both `indicator_classes` tests FAIL with `ImportError: cannot import name 'indicator_classes'`; the `reconcile_plan` test FAILS because `ssrf` is absent from the returned list.

- [ ] **Step 3: Commit RED**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_partition.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sec-overlay): add failing indicator routing tests"
```

- [ ] **Step 4: Add the indicator matcher**

In `helpers/sec_overlay/dependency_sinks.py`, add after `matched_classes` (currently `:218-220`):

```python
_SOURCE_SUFFIXES = {".go", ".py", ".js", ".ts", ".rb", ".java", ".rs", ".php", ".cs", ".rego"}


def _source_files(root: Path) -> list[Path]:
    """Collect source files under ``root``, skipping vendored and cache trees."""
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in _SKIP_DIRS:
                    stack.append(child)
            elif child.suffix in _SOURCE_SUFFIXES:
                found.append(child)
    return found


def indicator_classes(root: str | Path, *, path: Path = CATALOG_PATH) -> list[str]:
    """Return the attack classes of every catalog entry an indicator API reaches.

    A manifest match is not the only evidence a target uses a dependency sink. A
    Bazel or vendored build declares no manifest, so routing on manifests alone
    leaves the whole attack surface unrouted (R-34).

    Args:
        root: Target repository root.
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        The sorted, deduplicated classes of every entry with at least one
        indicator hit. One hit is enough: an entry lists alternative call shapes,
        not a conjunction.

    Example:
        >>> indicator_classes("/repo/with/rego/New/call")  # doctest: +SKIP
        ['ssrf']
    """
    entries = load_catalog(path)
    texts: list[str] = []
    for source in _source_files(Path(root)):
        try:
            texts.append(source.read_text(errors="replace"))
        except OSError:
            continue
    return sorted(
        {
            e.cls
            for e in entries
            if any(ind in text for ind in e.indicators for text in texts)
        }
    )
```

Check the generator's clause order before committing: `any(ind in text for ind in e.indicators for text in texts)` reads every indicator against every text. Confirm the comprehension binds as written by running the two new `test_dependency_sinks.py` tests, not by inspection alone.

- [ ] **Step 5: Union the matcher into routing**

In `helpers/sec_overlay/partition.py`, replace the `target_root` branch (currently `:129-131`):

```python
    if target_root is not None:
        planned = set(base) | set(extra)
        found = list(
            dict.fromkeys(matched_classes(target_root) + indicator_classes(target_root))
        )
        extra = sorted(extra + [c for c in found if c not in planned])
```

Import `indicator_classes` beside the existing `matched_classes` import.

Extend the `reconcile_plan` docstring paragraph that names the catalog so it records both routes into the plan:

```
    catalog entry is added too — either because a manifest declares the package,
    or because one of the entry's indicator APIs appears in target source. A
    Bazel or vendored target has the second and not the first.
```

- [ ] **Step 6: Run the gate**

Run the gate command block. Expected: 1702 passed, ruff clean, ty clean.

- [ ] **Step 7: Commit GREEN**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/partition.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): route a class on an indicator hit"
```

The commit body names REQ-25 and records the cite drift: the requirement points at `dependency_sinks.py:114`, which is the `indicators` constructor argument; the change site is `reconcile_plan` plus a new matcher.

---

## Task 4: REQ-24 — enforce the saturation loop

**Files:**
- Modify: `helpers/sec_overlay/driver.py:224-231` (`_act_findings_gate`), `:431-461` (the dispatch loop)
- Modify: `agents/investigate.md`, `agents/README.md`
- Test: `helpers/tests/test_driver.py`, `helpers/tests/test_contracts.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-3.
- Produces: `kb/discovery-ledger.json` written on every `findings-gate` run. No later task in this group reads it.

**Library facts (already built, do not rewrite):** `discovery_ledger.new_ledger(k=2, max_waves=5)`, `record_wave(ledger, fingerprints) -> dict`, `is_terminal(ledger) -> bool`, `save_ledger(ws, ledger) -> Path`, `load_ledger(ws) -> dict`. `terminal_reason` becomes `"saturated"` after `k` consecutive waves with no new fingerprint, or `"capped"` at `max_waves` waves. `fingerprint.fingerprint(finding)` works with no `anchor` argument.

**Deferred defect (record, do not build):** `profile.py:42` documents `scan_options.wave_k` and `scan_options.max_waves` as investigate-saturation knobs. Nothing reads them. This task uses `new_ledger()`'s defaults. Wiring the knobs is a separate requirement.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_driver.py`:

```python
def test_findings_gate_records_a_discovery_wave(tmp_path):
    """The saturation loop must be mechanical, not a prose instruction (REQ-24)."""
    from sec_overlay.driver import DETERMINISTIC_ACTIONS

    ctx = _ctx(tmp_path)
    DETERMINISTIC_ACTIONS["findings-gate"](ctx)
    ledger = json.loads((ctx.ws.kb / "discovery-ledger.json").read_text())
    assert len(ledger["waves"]) == 1


def test_repeated_findings_gate_runs_reach_a_terminal_reason(tmp_path):
    """Waves that add nothing new must saturate and stop the loop (REQ-24)."""
    from sec_overlay.driver import DETERMINISTIC_ACTIONS

    ctx = _ctx(tmp_path)
    for _ in range(3):
        DETERMINISTIC_ACTIONS["findings-gate"](ctx)
    ledger = json.loads((ctx.ws.kb / "discovery-ledger.json").read_text())
    assert ledger["terminal_reason"] == "saturated"


def test_a_saturated_ledger_stops_re_dispatching_investigate(tmp_path):
    """A terminal ledger records the stage instead of dispatching another wave (REQ-24)."""
    from sec_overlay.discovery_ledger import new_ledger, save_ledger
    from sec_overlay.driver import _investigate_is_saturated

    ctx = _ctx(tmp_path)
    assert _investigate_is_saturated(ctx.ws) is False
    ledger = new_ledger()
    ledger["terminal_reason"] = "saturated"
    save_ledger(ctx.ws, ledger)
    assert _investigate_is_saturated(ctx.ws) is True
```

Append to `helpers/tests/test_contracts.py`:

```python
def test_investigate_prompt_carries_wave_language():
    """The agent must know it participates in a bounded loop (REQ-24)."""
    text = (AGENTS / "investigate.md").read_text().lower()
    assert "wave" in text
    assert "saturat" in text
```

- [ ] **Step 2: Run the tests and confirm all four fail**

Run: `uv run pytest tests/test_driver.py tests/test_contracts.py -q`

Expected: the first two FAIL with `FileNotFoundError` on `discovery-ledger.json`; the third FAILS with `ImportError: cannot import name '_investigate_is_saturated'`; the prompt test FAILS on both substring assertions (a grep of `agents/investigate.md` for `wave|saturat|discovery-ledger|until-dry` returns nothing today).

Confirm `AGENTS` is already defined in `tests/test_contracts.py` before relying on it. If it is not, use the verified prompt-file idiom `Path(__file__).resolve().parents[2] / "agents" / "investigate.md"`.

- [ ] **Step 3: Commit RED**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(sec-overlay): add failing saturation loop tests"
```

- [ ] **Step 4: Fold a wave in the findings gate**

In `helpers/sec_overlay/driver.py`, add the fold helper above `_act_findings_gate`:

```python
def _record_discovery_wave(ctx: AuditContext) -> None:
    """Fold this pass's finding fingerprints into the discovery ledger (REQ-24).

    ``findings-gate`` is the first deterministic phase after ``investigate``, so it
    is the only mechanical hook the bounded discovery loop has. One gate run is one
    wave. Runs before the gate's own validation, so a rejected wave still counts.
    """
    from sec_overlay.discovery_ledger import load_ledger, new_ledger, record_wave, save_ledger
    from sec_overlay.fingerprint import fingerprint

    try:
        ledger = load_ledger(ctx.ws)
    except (FileNotFoundError, json.JSONDecodeError):
        ledger = new_ledger()
    prints = [f.fingerprint or fingerprint(f) for f in read_findings(ctx.ws)]
    record_wave(ledger, prints)
    save_ledger(ctx.ws, ledger)
```

Call it first inside `_act_findings_gate`:

```python
def _act_findings_gate(ctx: AuditContext) -> None:
    _record_discovery_wave(ctx)
    errors = validate_findings(ctx.ws)  # records its own stage too
    errors += validate_citations(ctx.ws, ctx.target)
    if errors:
        raise PhaseHalt(
            f"findings-gate rejected {len(errors)} finding(s): " + "; ".join(errors)
        )
```

Confirm `read_findings` is already imported in `driver.py`. If it is not, import it at module scope beside the other `sec_overlay` imports.

- [ ] **Step 5: Stop re-dispatching a saturated investigate phase**

Add the predicate beside the fold helper:

```python
def _investigate_is_saturated(ws) -> bool:
    """True once the discovery ledger reached a terminal_reason (REQ-24).

    Args:
        ws: The campaign workspace.

    Returns:
        ``True`` when the ledger exists and carries a ``terminal_reason``;
        ``False`` when it is absent or unreadable, so a missing ledger never
        stops a wave that has not run yet.
    """
    from sec_overlay.discovery_ledger import is_terminal, load_ledger

    try:
        return is_terminal(load_ledger(ws))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
```

In the dispatch loop, insert this branch immediately before the existing `if phase.name in ("investigate", "patch"):` block (currently `driver.py:444`):

```python
        if phase.name == "investigate" and _investigate_is_saturated(ctx.ws):
            if on_complete is not None:
                on_complete(phase.name)
            record_stage(ctx.ws, phase.name)
            continue
```

The invariant this must hold: the loop advances past `investigate` only when the phase's outputs exist, or the ledger is terminal. Both branches record the stage before continuing, so `next_actionable_phase` cannot return the same phase again.

- [ ] **Step 6: Add wave language to the prompt**

Add a section to `agents/investigate.md` telling the agent it runs inside a bounded discovery loop:

- Each dispatch is one wave. The harness folds the wave's fingerprints into `kb/discovery-ledger.json` at the findings gate.
- The loop stops on saturation (two consecutive waves add no new fingerprint) or at the wave cap.
- Report a class as exhausted only when a wave adds nothing new, never because the wave felt long enough.

Update `agents/README.md` to describe the loop the investigate prompt now names.

Preserve every existing hard rule in `investigate.md` verbatim: the gate ladder, the tool-receipt safety contract, and the model-family diversity rule are load-bearing, not prose.

- [ ] **Step 7: Run the gate**

Run the gate command block. Expected: 1706 passed, ruff clean, ty clean.

Watch for one regression class specifically: any existing test that drives `findings-gate` and asserts on the exact set of files under `kb/`. The gate now writes one more file there.

- [ ] **Step 8: Commit GREEN**

```bash
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/investigate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): enforce the investigate saturation loop"
```

The commit body names REQ-24 and records Ruling 52's wave granularity and its cost.

---

## Group gate

After Task 4's GREEN commit, run the gate command block once more from `helpers/`:

```bash
uv run pytest -q          # expect 1706 passed
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Record the three outputs and the head commit in the ledger. A count other than 1706 is a real finding: reconcile it against the per-task table above before closing the group.

## Self-review record

- **Spec coverage.** REQ-04 is Task 1, REQ-11 is Task 2, REQ-25 is Task 3, REQ-24 is Task 4. Part E group 4 names exactly these four. No requirement in the group lacks a task.
- **Placeholder scan.** Every step carries the literal code or the literal deletion target. No step says "add validation", "handle edge cases", or "similar to Task N".
- **Type consistency.** `indicator_classes` returns `list[str]` in Task 3 Step 4 and is consumed as a list in Step 5. `route_summary` is a `dict` in Task 2 Step 4 and is read as a dict in Step 5 and in both Task 2 tests. `_investigate_is_saturated` returns `bool` and both Task 4 assertions compare against `True`/`False`.
- **Known non-monotonic suite count.** Task 1 deletes five tests. An executor that assumes growth will misread the gate.
