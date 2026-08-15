# sec-overlay Coverage + Accuracy (T4/T5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the T4 coverage-table and T5 accuracy/provenance defects so every audit phase's output is checked against a derived route-to-control table, every gap is logged (never dropped), and every shipping finding carries a resolvable anchor.

**Architecture:** Add one deterministic route-to-control table (`route_control.py`) derived from recon's scan-profile plus the structural index; check recon/architecture/threat-model output against it and record gaps with `reason`+`next_step`. Add a resolver-backed citation check to `findings_gate` (reuses `phase_gate.resolve_ref`). Fix the remaining accuracy leaks in place: prefilter sidecar skip, same-line dedupe, CodeQL receipt regression, red-team payload reachability, and a class-extension alias map with graceful fallback. Verify the already-wired items (reconcile-on-rewrite, unrouted-triage, fingerprint-keyed feedback, artifact-written findings) with regression tests.

**Tech Stack:** Python 3.13, stdlib-only core (dev deps: `pytest`, `ruff`, `ty`); `uv run` from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md` (§4.4 T4, §4.5 T5, §8 traceability). Plan C = issues 016, 027, 029, 031, 036, 037, 049 (T4) and 004, 005, 017, 018, 019, 020, 023, 032, 033, 042, 056 (T5).

## Global Constraints

- **Branch:** all work on `feat/sec-overlay-coverage-accuracy`; never commit to `main` (blocked by ruleset).
- **Commits:** Conventional Commits, `<type>(sec-overlay): <summary under 50 chars>`; stage explicit paths only — never `git add -A`/`.`/`-a`; never `--no-verify`; no `Co-Authored-By` trailer.
- **Version bump (same commit as a shipping-file change):** shipping files = `plugin.json`, `SKILL.md`, everything under `skills/`, `agents/`, `helpers/`, `references/`, incl. their folder `README.md`. Increment by CC type: `feat`→minor, `fix`/`refactor`/`docs`/`style`/`test`/`chore`→patch, `!`/`BREAKING`→major. Edit `plugins/sec-overlay/.claude-plugin/plugin.json`. A plugin `CLAUDE.md` edit alone does **not** bump.
- **Changelog (every commit):** update `plugins/sec-overlay/CHANGELOG.md`.
- **Docs track code (same commit, prek-enforced):** any changed file whose folder has a tracked `README.md` must stage that `README.md`. Editing under `agents/` → stage `agents/README.md`; under `helpers/sec_overlay/` → stage `helpers/README.md`; under `references/` → stage `references/README.md`.
- **TDD, security-fix order:** failing test first (an attack/regression case that fails on current code), then the minimum fix, confirm pass.
- **Stdlib-only core:** no new runtime dependency without explicit user sign-off.
- **Preserve invariants:** model-family diversity (sonnet producer / opus adversary), the tool-receipt safety contract (adversarial reasoning demotes but never deletes a receipt-backed finding), and count-invariant verdict tables in `agents/*.md` — keep verbatim.
- **Env-only test failures — do NOT "fix":** `test_bench.py::test_seed_corpus_is_valid`, `test_citations.py::test_all_mapped_ids_exist_in_seed`, `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` (missing submodule/seed on a clean checkout).
- **Keep contract/wiring tests green:** `tests/test_contracts.py`, `tests/test_wiring.py`.

## Rulings carried into this plan (from the code map + user decisions)

- **Class extensions (ISSUE-037/049):** use a class→file **alias map**; a coarse file (`injection.md`) counts as coverage for its aliased keys (`sqli`/`cmdi`/`xss`). Log a gap only for truly uncovered keys. Authoring the missing extension files is a spec §9 follow-on, out of scope here. (User decision.)
- **Route→control table (ISSUE-027/029/036):** derive from recon's existing `entrypoints` + `attack_surface_evidence` + the structural index. Do **not** populate `kind="control"` graph nodes (dormant today; that is a larger substrate change deferred to a follow-on). (User decision.)
- **Anchor rejection (ISSUE-018/019/023):** reject a citation that does not resolve; treat `line: 1` as a placeholder **only when it does not resolve**. A genuine, resolvable line-1 finding survives. (User decision.)
- **ISSUE-023** control findings are already written by code (`context.control_findings`, `context.py:233`); the only remaining gap is their `line`-defaults-to-1 anchor (`_split_where`, `context.py:223`), covered by the Task 2 anchor check.
- **ISSUE-020/031/033/017** are already wired in landed code (`reconcile_plan` at `driver.py:280`, `unrouted_candidate_classes` at `driver.py:139/284`, fingerprint-keyed `fp_feedback.py:41`, driver output-artifact precondition at `driver.py:239-250`). Task 10 pins them with regression tests; new code only if a test proves an item unwired.
- **ISSUE-004** CodeQL already attaches `codeql:<rule_id>` receipts at construction (`codeql.py`); the low receipt count is environmental (pack/config). Task 8 is a regression test plus a config-path assertion, not a behavioural rewrite.
- **ISSUE-012** (coverage-ledger `reason`/`next_step` **gate**) stays in Plan D; Plan C only makes the route/coverage gap entries **carry** `reason`+`next_step` so Plan D's gate has real data.

---

### Task 1: Context doc-coverage provenance (ISSUE-016)

Record documents discovered vs documents read, and warn when the read ratio is low. `discover_context_files(repo_root, scan_scope)` already enumerates candidate docs (`context.py:106`); `Context.provenance` already carries `docs_read`/`prior_scans_read`/`sha` (`context.py:81`).

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/context.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_context.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugins/sec-overlay/.claude-plugin/plugin.json`; `plugins/sec-overlay/CHANGELOG.md`

**Interfaces:**
- Consumes: `Context.provenance: dict` (`context.py:81`); `discover_context_files(repo_root, scan_scope=".") -> list[str]` (`context.py:106`).
- Produces: `doc_coverage(provenance: dict, *, low_ratio: float = 0.25) -> dict` returning `{"discovered": int, "read": int, "ratio": float, "warning": str | None}`. `warning` is a non-empty string when `discovered > 0 and read/discovered < low_ratio`, else `None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context.py
from sec_overlay.context import doc_coverage


def test_doc_coverage_warns_when_few_docs_read():
    prov = {"docs_discovered": ["a", "b", "c", "d"], "docs_read": ["a"]}
    cov = doc_coverage(prov)
    assert cov["discovered"] == 4
    assert cov["read"] == 1
    assert cov["ratio"] == 0.25
    assert cov["warning"] is None  # 0.25 is not < 0.25


def test_doc_coverage_warns_below_ratio():
    prov = {"docs_discovered": ["a", "b", "c", "d", "e"], "docs_read": ["a"]}
    cov = doc_coverage(prov)
    assert cov["ratio"] == 0.2
    assert cov["warning"] and "1" in cov["warning"] and "5" in cov["warning"]


def test_doc_coverage_no_docs_no_warning():
    cov = doc_coverage({"docs_discovered": [], "docs_read": []})
    assert cov == {"discovered": 0, "read": 0, "ratio": 0.0, "warning": None}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/test_context.py -k doc_coverage -v`
Expected: FAIL — `ImportError: cannot import name 'doc_coverage'`.

- [ ] **Step 3: Write minimal implementation**

```python
# context.py — add near the other provenance helpers
def doc_coverage(provenance: dict, *, low_ratio: float = 0.25) -> dict:
    """Compare documents discovered vs read and flag a low read ratio.

    Args:
        provenance: A ``Context.provenance`` dict; reads ``docs_discovered``
            and ``docs_read`` (each a list; missing keys count as empty).
        low_ratio: Warn when ``read / discovered`` is strictly below this.

    Returns:
        ``{"discovered": int, "read": int, "ratio": float, "warning": str | None}``.
        ``warning`` is ``None`` when nothing was discovered or the ratio is
        at or above ``low_ratio``.

    Example:
        >>> doc_coverage({"docs_discovered": ["a", "b"], "docs_read": ["a"]})["ratio"]
        0.5
    """
    discovered = len(provenance.get("docs_discovered", []) or [])
    read = len(provenance.get("docs_read", []) or [])
    ratio = (read / discovered) if discovered else 0.0
    warning = None
    if discovered and ratio < low_ratio:
        warning = f"low doc coverage: read {read} of {discovered} discovered documents"
    return {"discovered": discovered, "read": read, "ratio": ratio, "warning": warning}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/sec-overlay/skills/sec-overlay/helpers && uv run pytest tests/test_context.py -k doc_coverage -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Wire `docs_discovered` at ingestion**

In the code path that builds `Context.provenance` (search `context.py` for where `docs_read` is assigned into `provenance`), also set `provenance["docs_discovered"] = discover_context_files(repo_root, scan_scope)`. If that assignment lives in a caller (e.g. the C1 orchestration), set it there and leave `doc_coverage` reading whatever the producer records. Do not change the `context-ingest.md` prompt in this task — the count is computed from `discover_context_files`, not from the agent.

- [ ] **Step 6: Lint, type-check, commit**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run ruff check sec_overlay/context.py tests/test_context.py && uv run ty check
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/context.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_context.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): record doc-coverage provenance"
```

---

### Task 2: Resolver-backed citation/anchor check (ISSUE-018, ISSUE-019, ISSUE-023)

Reject a finding whose citation does not resolve against the target source; reject a `line: 1` anchor **only when it does not resolve**. Control findings (`context.control_findings`) inherit the check because they flow through the same gate. Reuse `phase_gate.resolve_ref(root, ref) -> tuple[bool, str | None]` (`phase_gate.py:98`).

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py` (`_act_findings_gate`, `driver.py:162`)
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `resolve_ref(root, ref) -> tuple[bool, str | None]` (`phase_gate.py:98`); `Workspace` findings via the same loader `validate_findings` uses; `AuditContext.target: str` (`driver.py:49`).
- Produces: `validate_citations(ws: Workspace, root: str | Path, *, statuses: set[str] | None = None) -> list[str]`. Returns one error string per shipping finding whose `file:line` does not resolve. `statuses` defaults to `evidence.SHIPPING_STATUSES`. Signature note: `validate_findings(ws)` (`findings_gate.py:27`) is unchanged; the citation check is separate because it needs `root`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_findings_gate.py
from pathlib import Path

from sec_overlay.findings_gate import validate_citations
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace
from sec_overlay.findings_io import write_findings  # existing finding writer


def _ws(tmp_path) -> Workspace:
    return Workspace(tmp_path / "ws")


def _shipping(fid: str, file: str, line: int) -> Finding:
    return Finding(
        id=fid, rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
        severity=Severity.MEDIUM, file=file, line=line, message="m",
        evidence_sources=["semgrep:r"],
    )


def test_unresolved_citation_rejected(tmp_path):
    root = tmp_path / "target"
    (root).mkdir()
    (root / "app.py").write_text("import os\nx = 1\n")
    ws = _ws(tmp_path)
    write_findings(ws, [_shipping("F-1", "app.py", 999)])  # line 999 does not exist
    errs = validate_citations(ws, root)
    assert any("F-1" in e for e in errs)


def test_resolvable_line_one_survives(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    (root / "app.py").write_text("import os\n")  # line 1 is real code
    ws = _ws(tmp_path)
    write_findings(ws, [_shipping("F-2", "app.py", 1)])
    assert validate_citations(ws, root) == []


def test_placeholder_line_one_unresolved_rejected(tmp_path):
    root = tmp_path / "target"
    root.mkdir()  # no app.py at all → line 1 does not resolve
    ws = _ws(tmp_path)
    write_findings(ws, [_shipping("F-3", "app.py", 1)])
    assert any("F-3" in e for e in validate_citations(ws, root))


def test_candidate_not_gated(tmp_path):
    root = tmp_path / "target"
    root.mkdir()
    ws = _ws(tmp_path)
    f = _shipping("F-4", "missing.py", 1)
    f.status = FindingStatus.CANDIDATE
    write_findings(ws, [f])
    assert validate_citations(ws, root) == []  # only shipping statuses gated
```

*(If `write_findings`/`Workspace` import paths differ, use the same imports `tests/test_findings_gate.py` already uses — do not invent new ones.)*

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_findings_gate.py -k citation -v`
Expected: FAIL — `ImportError: cannot import name 'validate_citations'`.

- [ ] **Step 3: Write minimal implementation**

```python
# findings_gate.py — add
from pathlib import Path

from sec_overlay.evidence import SHIPPING_STATUSES
from sec_overlay.phase_gate import resolve_ref


def validate_citations(ws, root, *, statuses=None):
    """Reject shipping findings whose ``file:line`` does not resolve in ``root``.

    A ``line: 1`` anchor is rejected only when the reference does not resolve,
    so a genuine top-of-file finding survives while a placeholder anchor on a
    missing/short file does not.

    Args:
        ws: The audit workspace.
        root: Target source root the citations point into.
        statuses: Finding statuses to gate; defaults to ``SHIPPING_STATUSES``.

    Returns:
        One error string per finding whose citation does not resolve.
    """
    from sec_overlay.findings_io import read_findings

    gated = statuses if statuses is not None else SHIPPING_STATUSES
    errors: list[str] = []
    for f in read_findings(ws):
        if f.status.value not in gated:
            continue
        ok, _ = resolve_ref(root, f"{f.file}:{f.line}")
        if not ok:
            errors.append(f"{f.id}: citation {f.file}:{f.line} does not resolve")
    return errors
```

*(Use whatever finding reader `validate_findings` already uses in this module — match it; `read_findings` above is illustrative.)*

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_findings_gate.py -k citation -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Wire into the driver gate**

In `driver.py` `_act_findings_gate` (`driver.py:162`), after the existing `validate_findings(ctx.ws)` call, also run `validate_citations(ctx.ws, ctx.target)` and fold its errors into the same `PhaseHalt` message. Import `validate_citations` alongside `validate_findings`.

```python
def _act_findings_gate(ctx: AuditContext) -> None:
    errors = validate_findings(ctx.ws)
    errors += validate_citations(ctx.ws, ctx.target)
    if errors:
        raise PhaseHalt(
            f"findings-gate rejected {len(errors)} finding(s): " + "; ".join(errors)
        )
```

- [ ] **Step 6: Regression test — control findings inherit the check**

```python
# tests/test_findings_gate.py — add
from sec_overlay.context import Context, ContextItem, control_findings


def test_control_finding_placeholder_anchor_rejected(tmp_path):
    root = tmp_path / "target"
    root.mkdir()  # no doc-cited file exists → bare-path anchor resolves to line 1, unresolved
    ws = _ws(tmp_path)
    ctx = Context(items=[ContextItem(
        kind="claimed_control", text="auth required", cls="authz",
        where="docs/SECURITY.md", verify_status="MISSING")])
    cf = control_findings(ctx)
    for f in cf:
        f.status = FindingStatus.CONFIRMED  # force shipping status to exercise the gate
    write_findings(ws, cf)
    assert validate_citations(ws, root)  # non-empty: the placeholder anchor is rejected
```

*(Match `Context`/`ContextItem` constructor kwargs to their real definitions in `context.py`; adjust field names if they differ.)*

Run: `cd .../helpers && uv run pytest tests/test_findings_gate.py -v` → PASS.

- [ ] **Step 7: Lint, type-check, commit**

```bash
git add .../findings_gate.py .../driver.py .../tests/test_findings_gate.py \
        .../helpers/README.md plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): reject unresolved finding citations"
```

---

### Task 3: Route-to-control table + phase-output checks (ISSUE-027, ISSUE-029, ISSUE-036)

Derive one route-to-control table from recon's `scan-profile.json` and the structural index; check each phase's output against it. A missing route, control, or entrypoint is a **logged gap** carrying `reason` and `next_step`, never dropped.

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_control.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `ScanProfile` from `kb/scan-profile.json` — fields `entrypoints`, `attack_surface`, `attack_surface_evidence` (recon output; confirm exact field names against `references/schemas/scan-profile*.json` and `recon.md`). `Workspace` for `kb/` paths.
- Produces:
  - `build_route_control_table(ws: Workspace) -> dict` → `{"routes": [{"route": str, "entrypoint": str, "evidence": str}], "controls": [str], "entrypoints": [str]}`.
  - `check_recon_routes(table, profile) -> list[dict]`
  - `check_architecture_controls(table, architecture_md: str) -> list[dict]`
  - `check_threat_entrypoints(table, threat_model_md: str) -> list[dict]`
  - Each check returns gap dicts `{"id": str, "disposition": "needs_follow_up", "reason": str, "next_step": str}` — the shape the coverage ledger's `needs_follow_up` surfaces will consume (Plan D gates on `reason`/`next_step`; here they are recorded).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_route_control.py
from sec_overlay.route_control import (
    check_architecture_controls,
    check_threat_entrypoints,
)


def test_architecture_gap_when_control_unreported():
    table = {"routes": [], "controls": ["auth", "rate-limit", "csrf"], "entrypoints": []}
    arch = "# Architecture\nThe app enforces auth on all routes.\n"  # mentions only auth
    gaps = check_architecture_controls(table, arch)
    ids = {g["id"] for g in gaps}
    assert "rate-limit" in ids and "csrf" in ids and "auth" not in ids
    for g in gaps:
        assert g["disposition"] == "needs_follow_up"
        assert g["reason"] and g["next_step"]


def test_threat_gap_when_entrypoint_dropped():
    table = {"routes": [], "controls": [], "entrypoints": ["POST /login", "GET /admin"]}
    tm = "Attackers target POST /login.\n"  # /admin dropped
    gaps = check_threat_entrypoints(table, tm)
    assert [g["id"] for g in gaps] == ["GET /admin"]


def test_no_gap_when_all_present():
    table = {"routes": [], "controls": ["auth"], "entrypoints": ["GET /"]}
    assert check_architecture_controls(table, "auth is enforced") == []
    assert check_threat_entrypoints(table, "GET / is the entrypoint") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_route_control.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# route_control.py
"""Derive one route-to-control table from recon output and check each phase against it.

A missing route, control, or entrypoint is a logged gap (never dropped), carrying
``reason`` and ``next_step`` so a follow-on gate (Plan D) can enforce it.
"""

from __future__ import annotations

import json

from sec_overlay.workspace import Workspace


def build_route_control_table(ws: Workspace) -> dict:
    """Build the route-to-control table from ``kb/scan-profile.json``.

    Args:
        ws: The audit workspace holding ``kb/scan-profile.json``.

    Returns:
        ``{"routes": [...], "controls": [...], "entrypoints": [...]}``. Empty
        lists when the profile is absent or a field is missing.
    """
    path = ws.kb_dir / "scan-profile.json"
    if not path.exists():
        return {"routes": [], "controls": [], "entrypoints": []}
    prof = json.loads(path.read_text())
    entrypoints = [str(e) for e in prof.get("entrypoints", [])]
    surface = prof.get("attack_surface", []) or []
    controls = sorted({str(c) for c in prof.get("controls", surface)})
    routes = [{"route": str(e), "entrypoint": str(e), "evidence": ""} for e in entrypoints]
    return {"routes": routes, "controls": controls, "entrypoints": entrypoints}


def _gap(item: str, kind: str) -> dict:
    return {
        "id": item,
        "disposition": "needs_follow_up",
        "reason": f"{kind} {item!r} in the route-to-control table is not reported downstream",
        "next_step": f"report {item!r} in the {kind} section or record why it is out of scope",
    }


def check_recon_routes(table: dict, profile: dict) -> list[dict]:
    """Gap for any table route the recon profile does not summarise."""
    summarised = {str(r) for r in profile.get("route_summary", [])}
    return [_gap(r["route"], "route") for r in table.get("routes", [])
            if r["route"] not in summarised]


def check_architecture_controls(table: dict, architecture_md: str) -> list[dict]:
    """Gap for any table control the architecture markdown does not mention."""
    text = architecture_md.lower()
    return [_gap(c, "control") for c in table.get("controls", []) if c.lower() not in text]


def check_threat_entrypoints(table: dict, threat_model_md: str) -> list[dict]:
    """Gap for any table entrypoint the threat model drops."""
    text = threat_model_md.lower()
    return [_gap(e, "entrypoint") for e in table.get("entrypoints", [])
            if e.lower() not in text]
```

*(Confirm `prof.get("controls", ...)` and `entrypoints`/`attack_surface` key names against the real scan-profile schema before finalizing; adjust to the landed field names.)*

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_route_control.py -v` → PASS.

- [ ] **Step 5: Record gaps to the coverage ledger**

Add a helper `record_route_gaps(ws, gaps: list[dict]) -> None` that appends the gap dicts into `kb/coverage-ledger.json`'s surfaces (reuse `coverage_ledger` read/write; keep the `{id, disposition}` shape plus `reason`/`next_step`). Add one test that a recorded gap round-trips with `reason` and `next_step` intact. This is the driver's hook for the checks; the main agent calls the three `check_*` functions after recon/architecture/threat-model and passes the union to `record_route_gaps`.

- [ ] **Step 6: Lint, type-check, commit**

```bash
git add .../route_control.py .../tests/test_route_control.py \
        .../helpers/README.md plugin.json CHANGELOG.md
git commit -m "feat(sec-overlay): derive route-to-control table"
```

---

### Task 4: Phase prompts summarise the table (ISSUE-027, ISSUE-029, ISSUE-036)

Make the three producer prompts emit what the Task 3 checks look for: recon summarises its route table, architecture reports **all** controls, threat-model retains **every** entrypoint. Preserve each prompt's hard rules verbatim.

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/recon.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/architecture.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/threat-model.md`
- Docs: `plugins/sec-overlay/skills/sec-overlay/agents/README.md`; `plugin.json`; `CHANGELOG.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py`

**Interfaces:**
- Consumes: the Task 3 check functions' expectations (`route_summary` field in scan-profile; controls named in `architecture.md`; entrypoints named in `THREAT_MODEL.md`).
- Produces: prompt text only — no Python signature.

- [ ] **Step 1: Write the failing contract assertion**

```python
# tests/test_contracts.py — add
from pathlib import Path

_AGENTS = Path(__file__).resolve().parents[2] / "agents"


def test_recon_prompt_requires_route_summary():
    assert "route" in (_AGENTS / "recon.md").read_text().lower()


def test_architecture_prompt_requires_all_controls():
    txt = (_AGENTS / "architecture.md").read_text().lower()
    assert "all controls" in txt or "every control" in txt


def test_threat_model_retains_every_entrypoint():
    txt = (_AGENTS / "threat-model.md").read_text().lower()
    assert "every entrypoint" in txt or "each entrypoint" in txt
```

*(Confirm the `agents/` path relative to `tests/` matches how `test_contracts.py` already locates prompt files; reuse its existing path constant if present.)*

- [ ] **Step 2: Run to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_contracts.py -k "route_summary or all_controls or every_entrypoint" -v`
Expected: FAIL on the assertions whose phrasing is absent.

- [ ] **Step 3: Edit the prompts (minimal, additive)**

- `recon.md`: add one instruction to emit a `route_summary` list summarising the external route table it already inventories from `entrypoints`/`attack_surface_evidence`.
- `architecture.md`: add a controls-enumeration instruction — report **all controls** the route-to-control table holds (auth, authz, rate-limit, csrf, input-validation, output-encoding, etc.), not a single example.
- `threat-model.md`: add an instruction to keep **every entrypoint** its input described, one line each, before prioritising.

Do not alter the anti-manipulation blocks, trust envelope, model-tier lines, or any count-invariant table. One added paragraph per file.

- [ ] **Step 4: Run to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_contracts.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .../agents/recon.md .../agents/architecture.md .../agents/threat-model.md \
        .../agents/README.md .../tests/test_contracts.py plugin.json CHANGELOG.md
git commit -m "feat(sec-overlay): prompts summarise route table"
```

---

### Task 5: Class-extension alias map + gap logging (ISSUE-037, ISSUE-049)

Investigate and patch already degrade to the base prompt when `agents/classes/<cls>.md` is absent ("if it exists", `investigate.md:15`). Add a deterministic presence check with an **alias map** (coarse files count) so no class is silently unhandled, and log a gap for each uncovered canonical key.

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/class_ext.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_class_ext.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: canonical class keys from `references/attack-classes.md` (18 keys; `deps` is SCA-handled, not an investigation class → excluded); existing files in `agents/classes/` (authn, authz, business-logic, config, context-bleed, crypto, excessive-agency, injection, prompt-injection, resource, ssrf).
- Produces: `class_extension_status(classes: list[str], classes_dir: str | Path) -> dict` → `{"present": {cls: filename}, "gaps": [gap dict]}`, gap dict as in Task 3 (`{"id", "disposition":"needs_follow_up", "reason", "next_step"}`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_class_ext.py
from sec_overlay.class_ext import class_extension_status


def test_alias_maps_coarse_file(tmp_path):
    (tmp_path / "injection.md").write_text("injection family")
    st = class_extension_status(["sqli", "cmdi", "xss"], tmp_path)
    assert st["present"] == {"sqli": "injection.md", "cmdi": "injection.md", "xss": "injection.md"}
    assert st["gaps"] == []


def test_direct_file_counts(tmp_path):
    (tmp_path / "ssrf.md").write_text("ssrf")
    st = class_extension_status(["ssrf"], tmp_path)
    assert st["present"] == {"ssrf": "ssrf.md"}


def test_uncovered_key_logs_gap(tmp_path):
    st = class_extension_status(["xxe"], tmp_path)  # no xxe.md, no alias
    assert st["present"] == {}
    assert len(st["gaps"]) == 1
    g = st["gaps"][0]
    assert g["id"] == "xxe" and g["disposition"] == "needs_follow_up"
    assert g["reason"] and g["next_step"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_class_ext.py -v` → FAIL (module missing).

- [ ] **Step 3: Write minimal implementation**

```python
# class_ext.py
"""Check class-extension coverage; a coarse file counts for its aliased keys.

Investigate/patch fall back to the base prompt for an uncovered class; this
records the gap so coverage is never silently lost. Authoring the missing
files is a spec-9 follow-on.
"""

from __future__ import annotations

from pathlib import Path

# canonical key -> the coarse extension file that covers it (user-approved alias map)
_ALIASES: dict[str, str] = {"sqli": "injection", "cmdi": "injection", "xss": "injection"}


def class_extension_status(classes, classes_dir) -> dict:
    """Report which classes have an extension file and which are gaps.

    Args:
        classes: Attack-class keys dispatched this run.
        classes_dir: ``agents/classes`` directory.

    Returns:
        ``{"present": {cls: filename}, "gaps": [gap dict]}``. A class is present
        if ``<cls>.md`` exists or its alias file exists.
    """
    root = Path(classes_dir)
    present: dict[str, str] = {}
    gaps: list[dict] = []
    for cls in classes:
        stem = _ALIASES.get(cls, cls)
        fname = f"{stem}.md"
        if (root / fname).exists():
            present[cls] = fname
        else:
            gaps.append({
                "id": cls,
                "disposition": "needs_follow_up",
                "reason": f"no class-extension file for {cls!r}; investigate/patch use the base prompt",
                "next_step": f"author agents/classes/{cls}.md (spec §9 follow-on)",
            })
    return {"present": present, "gaps": gaps}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_class_ext.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .../class_ext.py .../tests/test_class_ext.py .../helpers/README.md \
        plugin.json CHANGELOG.md
git commit -m "feat(sec-overlay): log class-extension coverage gaps"
```

---

### Task 6: Prefilter skips its own sidecar directory (ISSUE-032)

`run_semgrep` uses `--no-git-ignore` (`sast.py`), so it scans the gitignored `.sec-overlay/` sidecar and can raise findings on the audit's own output. Exclude the sidecar directory from the scan.

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sast.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sast.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `run_semgrep(target, config, *, runner=subprocess.run)` (`sast.py:49`).
- Produces: module-level `_SKIP_DIRS: tuple[str, ...] = (".sec-overlay", ".git", ".venv", "node_modules")`; `run_semgrep` command includes one `--exclude <dir>` per entry. Signature unchanged.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sast.py
import json

from sec_overlay.sast import run_semgrep, _SKIP_DIRS


def test_semgrep_excludes_sidecar():
    captured = {}

    def fake_runner(cmd, **kw):
        captured["cmd"] = cmd
        class R:
            stdout = json.dumps({"results": []})
        return R()

    run_semgrep("/repo", "rules.yaml", runner=fake_runner)
    cmd = captured["cmd"]
    for d in _SKIP_DIRS:
        i = cmd.index(d)
        assert cmd[i - 1] == "--exclude"
    assert ".sec-overlay" in _SKIP_DIRS
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_sast.py -k exclude -v`
Expected: FAIL — `ImportError: cannot import name '_SKIP_DIRS'`.

- [ ] **Step 3: Write minimal implementation**

```python
# sast.py — add near the top-level constants
_SKIP_DIRS: tuple[str, ...] = (".sec-overlay", ".git", ".venv", "node_modules")

# in run_semgrep, replace the cmd line:
def run_semgrep(target: str, config: str, *, runner=subprocess.run) -> list[Finding]:
    cmd = ["semgrep", "--config", config, "--json", "--no-git-ignore"]
    for d in _SKIP_DIRS:
        cmd += ["--exclude", d]
    cmd.append(target)
    completed = runner(cmd, capture_output=True, text=True, check=False)
    return parse_semgrep_json(json.loads(completed.stdout))
```

Keep the docstring; only the command construction changes.

- [ ] **Step 4: Run to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_sast.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .../sast.py .../tests/test_sast.py .../helpers/README.md plugin.json CHANGELOG.md
git commit -m "fix(sec-overlay): exclude sidecar dir from semgrep"
```

---

### Task 7: Same-line dedupe + fold recurrence status set (ISSUE-042, ISSUE-005)

Two active findings sharing `(file, line, cls)` with empty `dataflow` currently escape dedupe (the cross-class pass at `dedupe.py:78` only fires when `dataflow` is non-empty). Add a same-line collapse keyed on the structured fingerprint. Fold `correlate/edges.py:89` `_RECURRENCE_STATUSES` into the shared `evidence.SHIPPING_STATUSES` so the status set is defined once.

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dedupe.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/correlate/edges.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dedupe.py`; `tests/test_correlate_edges.py` (or the existing edges test file)
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `evidence.SHIPPING_STATUSES` (`evidence.py:19`); `dedupe_findings(ws) -> int` (`dedupe.py:18`); `fingerprint(finding, anchor=None) -> str` (`fingerprint.py:17`).
- Produces: `dedupe_findings` marks same-`(file,line,cls)` active duplicates even with empty dataflow (existing first pass already keys on `(file, line, cls, dataflow-or-message)` — verify it covers this; if `message` differs, add a fingerprint-keyed pass). `edges.py` imports `SHIPPING_STATUSES` instead of the local literal.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dedupe.py
from sec_overlay.dedupe import dedupe_findings
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace
from sec_overlay.findings_io import write_findings, read_findings


def _f(fid, msg):
    return Finding(id=fid, rule_id="r", cls="authz", status=FindingStatus.RAW,
                   severity=Severity.MEDIUM, file="a.py", line=10, message=msg,
                   dataflow=[])


def test_same_line_same_class_dedupes_without_dataflow(tmp_path):
    ws = Workspace(tmp_path / "ws")
    write_findings(ws, [_f("F-1", "one wording"), _f("F-2", "different wording")])
    dedupe_findings(ws)
    statuses = {f.id: f.status for f in read_findings(ws)}
    assert FindingStatus.DUPLICATE in statuses.values()
```

```python
# tests/test_correlate_edges.py
from sec_overlay.correlate import edges
from sec_overlay.evidence import SHIPPING_STATUSES


def test_recurrence_uses_shared_shipping_set():
    assert edges._RECURRENCE_STATUSES == SHIPPING_STATUSES
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd .../helpers && uv run pytest tests/test_dedupe.py tests/test_correlate_edges.py -v`
Expected: FAIL — the same-line case leaks (both stay RAW) and `_RECURRENCE_STATUSES` is a separate literal.

- [ ] **Step 3: Implement**

`edges.py`: replace `_RECURRENCE_STATUSES = {"confirmed", "needs-deployment-testing", "fixed"}` with `from sec_overlay.evidence import SHIPPING_STATUSES` and use `SHIPPING_STATUSES` at the two call sites (`edges.py:92, 104`). Keep an alias `_RECURRENCE_STATUSES = SHIPPING_STATUSES` only if other code imports the old name; otherwise delete it and update references.

`dedupe.py`: the first grouping pass keys on `(f.file, f.line, f.cls, tuple(f.dataflow) or f.message)`. When two findings differ only in `message` and have empty `dataflow`, they land in different groups and leak. Change the same-line key to drop `message` when `dataflow` is empty, keying on `(f.file, f.line, f.cls)` — a same-file/line/class active pair is one fact regardless of wording.

```python
# dedupe.py — same-line pass key
key = (f.file, f.line, f.cls) if not f.dataflow else (f.file, f.line, f.cls, tuple(f.dataflow))
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd .../helpers && uv run pytest tests/test_dedupe.py tests/test_correlate_edges.py -v` → PASS. Then `uv run pytest tests/test_dedupe.py -v` in full to confirm no cross-class regression.

- [ ] **Step 5: Commit**

```bash
git add .../dedupe.py .../correlate/edges.py .../tests/test_dedupe.py \
        .../tests/test_correlate_edges.py .../helpers/README.md plugin.json CHANGELOG.md
git commit -m "fix(sec-overlay): collapse same-line duplicate findings"
```

---

### Task 8: CodeQL receipt regression (ISSUE-004)

CodeQL already attaches `codeql:<rule_id>` receipts at finding construction (`codeql.py`). The low receipt count in the observed run was environmental (pack/config path). Pin the receipt behaviour with a regression test and assert the run-config path is correct; do not rewrite the parser.

**Files:**
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_codeql.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` (note the regression); `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `parse_codeql_sarif(payload, *, source_root=None) -> list[Finding]` (`codeql.py:124`); `evidence.is_tool_receipt` / the `_MECHANICAL` whitelist.

- [ ] **Step 1: Write the failing/º pinning test**

```python
# tests/test_codeql.py — add
from sec_overlay.codeql import parse_codeql_sarif
from sec_overlay.evidence import Evidence  # or the receipt-check helper the module exposes


def test_every_codeql_finding_carries_receipt():
    payload = {
        "runs": [{
            "results": [{
                "ruleId": "py/sql-injection",
                "message": {"text": "sqli"},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": "app.py"},
                    "region": {"startLine": 5}}}],
            }],
            "tool": {"driver": {"rules": [{"id": "py/sql-injection"}]}},
        }]
    }
    findings = parse_codeql_sarif(payload)
    assert findings, "parser produced no findings"
    for f in findings:
        assert any(s.startswith("codeql:") for s in f.evidence_sources)
```

*(Adjust the payload shape and the receipt-check import to the real `parse_codeql_sarif` signature and the module's actual receipt helper — read `codeql.py` and an existing `test_codeql.py` case first, and mirror them.)*

- [ ] **Step 2: Run to verify current behaviour**

Run: `cd .../helpers && uv run pytest tests/test_codeql.py -k receipt -v`
Expected: PASS if the receipt is already attached (confirms no regression). If it FAILS, the receipt is not attached on this path — fix `parse_codeql_sarif` to append `f"codeql:{rule_id}"` to `evidence_sources`, then re-run.

- [ ] **Step 3: Assert the config path (preflight tie-in)**

Add a one-line note in `helpers/README.md` that a missing CodeQL pack drops that language's dataflow (already surfaced by `preflight`); no code change unless Step 2 failed. Ruling if Step 2 passes: ISSUE-004 is environmental — the regression test is the deliverable.

- [ ] **Step 4: Commit**

```bash
git add .../tests/test_codeql.py .../helpers/README.md plugin.json CHANGELOG.md
git commit -m "test(sec-overlay): pin codeql receipt attachment"
```

---

### Task 9: Red-team payload reachability pre-check (ISSUE-056)

The red-team producer must trace a payload source→sink through the target's own input validation before shipping it as a live test; an un-traceable payload is marked an unrunnable precondition, not a live directive. Add the deterministic pre-check to `redteam.py` and the tracing instruction to `redteam.md`.

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/redteam.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugins/sec-overlay/skills/sec-overlay/agents/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `discriminate(findings, min_risk=7) -> dict` (`redteam.py:64`); `wants_runtime(f) -> bool` (`redteam.py:39`); `Finding.reachability` / `runtime_disposition` fields (`models.py`).
- Produces: `payload_runnable(f: Finding) -> bool` — `True` only when the finding carries a traced source→sink reachability (a Tier-1 dataflow receipt or a non-empty `reachability` marking it reachable). `discriminate` routes a finding with `payload_runnable(f) is False` into an `"unrunnable"` bucket (precondition), not the live-test bucket.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_redteam.py — add
from sec_overlay.redteam import discriminate, payload_runnable
from sec_overlay.models import Finding, FindingStatus, Severity


def _f(fid, *, dataflow, reach):
    return Finding(id=fid, rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=Severity.HIGH, file="a.py", line=1, message="m",
                   risk_score=8, dataflow=dataflow, reachability=reach,
                   evidence_sources=["codeql:dataflow"] if dataflow else ["ripgrep:x"])


def test_untraceable_payload_is_unrunnable():
    f = _f("F-1", dataflow=[], reach="")
    assert payload_runnable(f) is False


def test_traced_payload_is_runnable():
    f = _f("F-2", dataflow=["src", "sink"], reach="reachable")
    assert payload_runnable(f) is True


def test_discriminate_buckets_unrunnable_separately():
    out = discriminate([_f("F-1", dataflow=[], reach="")], min_risk=7)
    assert "unrunnable" in out
    assert any(x.id == "F-1" for x in out["unrunnable"])
```

*(Match `discriminate`'s real return shape — read `redteam.py:64-190` and mirror its existing bucket keys; add `"unrunnable"` alongside them.)*

- [ ] **Step 2: Run to verify it fails**

Run: `cd .../helpers && uv run pytest tests/test_redteam.py -k "runnable or unrunnable" -v` → FAIL (function/bucket missing).

- [ ] **Step 3: Implement**

```python
# redteam.py — add
def payload_runnable(f) -> bool:
    """True when a payload can be traced source->sink for a live test.

    A finding with a dataflow receipt or an explicit reachable marker is
    runnable; otherwise it is an unrunnable precondition (needs runtime), not
    a live directive.
    """
    has_dataflow = bool(getattr(f, "dataflow", None))
    reach = (getattr(f, "reachability", "") or "").lower()
    return has_dataflow or reach in {"reachable", "static-settled"}
```

In `discriminate`, before placing an above-bar finding into the live-test bucket, route `payload_runnable(f) is False` into a new `out["unrunnable"]` list. Keep every existing bucket and count invariant intact.

`redteam.md`: add one instruction — trace each payload source→sink through the target's own input validation; a payload you cannot trace is an unrunnable precondition, not a live test. Preserve the producer→adversary rule and the safety contract verbatim.

- [ ] **Step 4: Run to verify it passes**

Run: `cd .../helpers && uv run pytest tests/test_redteam.py -v` → PASS.

- [ ] **Step 5: Commit**

```bash
git add .../redteam.py .../agents/redteam.md .../tests/test_redteam.py \
        .../helpers/README.md .../agents/README.md plugin.json CHANGELOG.md
git commit -m "feat(sec-overlay): gate red-team payloads on reachability"
```

---

### Task 10: Regression pins for already-wired items (ISSUE-017, ISSUE-020, ISSUE-031, ISSUE-033)

Four spec items are already implemented in landed code. Pin them with regression tests in `test_wiring.py`; write new code only if a test proves an item unwired.

**Files:**
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_wiring.py`
- Docs: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md`; `plugin.json`; `CHANGELOG.md`

**Interfaces:**
- Consumes: `reconcile_plan(ws, agents_to_spawn) -> list[str]` (`partition.py:93`, wired `driver.py:280`); `unrouted_candidate_classes(ws, agents_to_spawn) -> dict[str, int]` (`partition.py:29`, wired `driver.py:139/284`); `render_fp_feedback(ws, *, cap=50) -> str` keyed on `f.fingerprint` (`fp_feedback.py:41`); the driver output-artifact precondition (`driver.py:239-250`, `run_deterministic_phase` `driver.py:85`).

- [ ] **Step 1: Write the regression tests**

```python
# tests/test_wiring.py — add
import inspect

from sec_overlay import driver, fp_feedback


def test_reconcile_runs_in_driver():  # ISSUE-020 (reconcile after context rewrite)
    src = inspect.getsource(driver)
    assert "reconcile_plan(" in src


def test_unrouted_triage_wired():  # ISSUE-031
    src = inspect.getsource(driver)
    assert "unrouted_candidate_classes(" in src or "unrouted_triage_dispatch(" in src


def test_fp_feedback_keys_on_fingerprint():  # ISSUE-033 (survives workspace rename)
    src = inspect.getsource(fp_feedback.render_fp_feedback)
    assert "fingerprint" in src


def test_missing_output_halts_phase():  # ISSUE-017 (finding cannot live only in chat)
    src = inspect.getsource(driver.run_deterministic_phase)
    assert "did not produce" in src  # PhaseHalt on absent output artifact
```

- [ ] **Step 2: Run**

Run: `cd .../helpers && uv run pytest tests/test_wiring.py -v`
Expected: PASS (all four are already wired). If any FAILS, that item is genuinely unwired — stop, wire the minimal call in `driver.py` per the referenced landed function, add the code to the same commit, and re-run.

- [ ] **Step 3: Add a fingerprint-rename behavioural test (ISSUE-033)**

```python
# tests/test_fp_feedback.py — add (or the existing fp-feedback test file)
def test_feedback_survives_workspace_rename(tmp_path):
    from sec_overlay.workspace import Workspace
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.findings_io import write_findings
    from sec_overlay.fp_feedback import render_fp_feedback

    def rej(fid):
        return Finding(id=fid, rule_id="r", cls="authz", status=FindingStatus.REJECTED,
                       severity=Severity.LOW, file="a.py", line=1, message="m",
                       fingerprint="fp-123")

    ws_a = Workspace(tmp_path / "name-a")
    write_findings(ws_a, [rej("R-1")])
    out_a = render_fp_feedback(ws_a)
    # same finding, different workspace dir name, same fingerprint → same feedback body
    ws_b = Workspace(tmp_path / "renamed-b")
    write_findings(ws_b, [rej("R-1")])
    assert render_fp_feedback(ws_b) == out_a
```

- [ ] **Step 4: Run and commit**

Run: `cd .../helpers && uv run pytest tests/test_wiring.py tests/test_fp_feedback.py -v` → PASS.

```bash
git add .../tests/test_wiring.py .../tests/test_fp_feedback.py .../helpers/README.md \
        plugin.json CHANGELOG.md
git commit -m "test(sec-overlay): pin wired coverage/accuracy items"
```

---

## Self-Review

**Spec coverage (§4.4 T4, §4.5 T5 — 18 issues):**

| Issue | Task | Notes |
|---|---|---|
| 016 | 1 | doc-coverage provenance + warning |
| 027 | 3, 4 | route table + recon route_summary |
| 029 | 3, 4 | all-controls check + prompt |
| 036 | 3, 4 | entrypoint retention check + prompt |
| 031 | 10 | already wired — regression pin |
| 037 | 5 | class-extension alias map + gap log |
| 049 | 5 | reaches patch via same status helper |
| 004 | 8 | receipt regression (environmental) |
| 005 | 7 | same-line dedupe |
| 042 | 7 | structured-fingerprint dedupe + shared status set |
| 017 | 10 | driver output-artifact precondition — pin |
| 018 | 2 | citation resolution |
| 019 | 2 | anchor (line:1-when-unresolved) |
| 020 | 10 | reconcile wired — pin |
| 023 | 2 | control findings inherit anchor check |
| 032 | 6 | prefilter sidecar skip |
| 033 | 10 | fingerprint-keyed feedback — pin + rename test |
| 056 | 9 | payload reachability pre-check |

All 18 mapped.

**Placeholder scan:** every code step carries runnable code/tests. Three spots are flagged "confirm against landed shape before finalizing" — scan-profile field names (Task 3), `parse_codeql_sarif` payload shape (Task 8), and `discriminate` bucket keys (Task 9) — because the implementer must mirror the real signature rather than a guessed one; the surrounding logic is fully specified. These are read-then-mirror instructions, not TBDs.

**Type consistency:** gap dicts use the same shape (`{id, disposition:"needs_follow_up", reason, next_step}`) in Tasks 3 and 5. `SHIPPING_STATUSES` is the single status set consumed by Tasks 2 and 7. `validate_citations(ws, root, *, statuses=None)` is defined in Task 2 and wired in the same task.

**Scope check:** ISSUE-012 (coverage-ledger reason/next_step **gate**) and ISSUE-021 (docs_read count accuracy) are Plan D per §8 — excluded here; Plan C only produces the gap data they will gate. Control graph-node population and authoring the 11 class-extension files are follow-ons per the recorded rulings.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-15-sec-overlay-coverage-accuracy.md`. Two execution options:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, spec + quality review between tasks, broad review at the end.
2. **Inline Execution** — tasks run in this session with checkpoints.
