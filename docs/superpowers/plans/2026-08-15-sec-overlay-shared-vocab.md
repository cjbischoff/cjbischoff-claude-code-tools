# sec-overlay shared vocabularies (T2 parser/schema + T3 status/receipt) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every gate, filter, red-team bar, and self-score one shared reference parser and one shared status/receipt vocabulary, so the four issues rooted in each component reading its own narrower subset disappear.

**Architecture:** Add one module of shared constants and predicates (`evidence.py` extensions), derive a receipt-tier from each finding's evidence, and route the existing gates/filters/bars to read those shared definitions instead of their private subsets. The reference parser gains hint-stripping; the recon schema gains the two fields recon already writes; the receipt gate revokes tier-2-only confirmation. Agents stay external and the deterministic-vs-judgment boundary set by Plan A is preserved — the deterministic gate proves a reference *resolves*; meaning stays the opus adversary's job.

**Tech Stack:** Python 3.13, stdlib-only core, `pytest`, `ruff`, `ty`, run via `uv` from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md` (§4.2 T2, §4.3 T3, §5 data model, §6 testing)

## Global Constraints

- **Stdlib-only core.** No new runtime dependency. Dev deps stay `pytest`, `ruff`, `ty`.
- **TDD, security-fix order for the receipt gate.** Write the failing test first, confirm it fails on current code, then fix. The receipt-tier gate (Task 3) writes the attack/regression test (a Tier-2-only finding must not reach `confirmed`), confirms it fails, then fixes.
- **Run from** `plugins/sec-overlay/skills/sec-overlay/helpers/`. Commands: `uv run pytest -q`, `uv run ruff check sec_overlay/ tests/`, `uv run ruff format sec_overlay/ tests/`, `uv run ty check`.
- **Two documented env-only failures are expected and not yours to fix:** `test_bench.py::test_seed_corpus_is_valid` (gitignored corpus) and `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` (semgrep submodule). A green run means every OTHER test passes.
- **Line length 100.** Absolute imports only (`from sec_overlay.x import y`).
- **Governance, every commit:** branch already exists for this plan; Conventional Commits `<type>(sec-overlay): <summary under 50 chars>`; stage explicit paths only (never `git add -A`/`.`/`-a`, never `--no-verify`). A shipping-file change bumps `plugin.json` `version` in the same commit by commit type (fix/refactor/docs/test → patch, feat → minor, `!`/BREAKING CHANGE → major). Every commit adds a `plugins/sec-overlay/CHANGELOG.md` entry. For every folder you touch that holds a tracked `README.md` (`sec_overlay/README.md`, `agents/README.md`, `references/README.md`, and the folder READMEs), stage that README in the same commit — the prek hook rejects the commit and names the folder otherwise. `tests/` may or may not have a README; if the hook names it, stage it.
- **No Co-Authored-By trailer.**
- **Preserve verbatim** the load-bearing agent-prompt rules (model-family diversity, tool-receipt safety contract, count-invariant verdict tables, the `{{FP_FEEDBACK}}` token, and the "proof tuple"/anti-collapse strings `test_wiring.py` checks).

---

### Task 1: Shared vocabulary constants and predicates

**Files:**
- Modify: `sec_overlay/evidence.py` (add after `_MECHANICAL`, evidence.py:14-15)
- Modify: `sec_overlay/README.md` (note the new constants)
- Test: `tests/test_evidence.py` (create if absent; else append)

**Interfaces:**
- Consumes: nothing (foundation).
- Produces:
  - `TIER1_RECEIPTS: frozenset[str]` = `{"codeql", "semgrep", "sca", "secrets"}`
  - `TIER2_RECEIPTS: frozenset[str]` = `{"ripgrep", "structural-index", "ast-grep", "tree-sitter"}`
  - `SHIPPING_STATUSES: frozenset[str]` = `{"confirmed", "fixed", "needs-deployment-testing"}`
  - `RUNTIME_DISPOSITIONS: frozenset[str]` = `{"needs-runtime", "static-settled", "unassessed"}`
  - `def receipt_tier(source: str) -> int | None` — returns `1`, `2`, or `None` for a single evidence source string.
  - `def confirms_alone(sources: list[str]) -> bool` — True iff any source is a Tier-1 receipt.

**Ruling (recorded):** `tree-sitter` is placed in Tier 2. The spec §4.3 lists Tier 2 as "ripgrep, structural-index, ast-grep" and omits `tree-sitter`, but `tree-sitter` is a structural locator with the same proof strength as `ast-grep`. `TIER1_RECEIPTS | TIER2_RECEIPTS` must equal `_MECHANICAL` exactly, so `tree-sitter` cannot be dropped — a mechanical receipt in neither tier would be un-gradable. Cost if wrong: a `tree-sitter`-only finding routes to `needs-deployment-testing` instead of `confirmed`, which is the safe direction.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_evidence.py
from sec_overlay.evidence import (
    TIER1_RECEIPTS, TIER2_RECEIPTS, _MECHANICAL,
    SHIPPING_STATUSES, RUNTIME_DISPOSITIONS,
    receipt_tier, confirms_alone,
)


def test_tiers_partition_mechanical_exactly():
    assert TIER1_RECEIPTS | TIER2_RECEIPTS == _MECHANICAL
    assert TIER1_RECEIPTS.isdisjoint(TIER2_RECEIPTS)


def test_receipt_tier_grades_colon_forms():
    assert receipt_tier("codeql:dataflow") == 1
    assert receipt_tier("semgrep:rule-x") == 1
    assert receipt_tier("ripgrep") == 2
    assert receipt_tier("ast-grep:pattern") == 2
    assert receipt_tier("llm-claimed:codeql") is None
    assert receipt_tier("nonsense") is None


def test_confirms_alone_requires_tier1():
    assert confirms_alone(["codeql:dataflow"]) is True
    assert confirms_alone(["ripgrep", "structural-index"]) is False
    assert confirms_alone(["ripgrep", "semgrep:x"]) is True
    assert confirms_alone(["llm-claimed:codeql"]) is False


def test_shipping_and_disposition_sets():
    assert SHIPPING_STATUSES == {"confirmed", "fixed", "needs-deployment-testing"}
    assert RUNTIME_DISPOSITIONS == {"needs-runtime", "static-settled", "unassessed"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_evidence.py -q`
Expected: FAIL (ImportError — the new names do not exist).

- [ ] **Step 3: Add the constants and predicates**

In `sec_overlay/evidence.py`, immediately after the `_MECHANICAL` definition (evidence.py:14-15):

```python
TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
TIER2_RECEIPTS = frozenset({"ripgrep", "structural-index", "ast-grep", "tree-sitter"})
SHIPPING_STATUSES = frozenset({"confirmed", "fixed", "needs-deployment-testing"})
RUNTIME_DISPOSITIONS = frozenset({"needs-runtime", "static-settled", "unassessed"})

assert TIER1_RECEIPTS | TIER2_RECEIPTS == _MECHANICAL, "receipt tiers must partition _MECHANICAL"


def receipt_tier(source: str) -> int | None:
    """Return the receipt tier (1 or 2) of an evidence source, or None.

    Tier 1 sources confirm a finding alone (a dataflow path, a vulnerable
    version, a live secret). Tier 2 sources only locate code. An LLM-claimed
    or unknown source has no tier.

    Args:
        source: An evidence source string (e.g. ``codeql:dataflow``).

    Returns:
        ``1`` for a Tier-1 receipt, ``2`` for a Tier-2 receipt, ``None`` for
        an ``llm-claimed:*`` or non-mechanical source.
    """
    if not is_tool_receipt(source):
        return None
    head = source.split(":", 1)[0]
    if head in TIER1_RECEIPTS:
        return 1
    return 2


def confirms_alone(sources: list[str]) -> bool:
    """Return True iff at least one source is a Tier-1 receipt.

    Args:
        sources: Evidence source strings.

    Returns:
        True when a Tier-1 receipt is present — the only ground on which a
        finding may reach ``confirmed``/``fixed``.
    """
    return any(receipt_tier(s) == 1 for s in sources)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_evidence.py -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS, no lint/type errors.

- [ ] **Step 5: Commit**

Update `sec_overlay/README.md` with a one-line note that `evidence.py` now exports the tier/status vocabularies. Bump `plugin.json` patch. Add a CHANGELOG entry.

```bash
git add sec_overlay/evidence.py tests/test_evidence.py sec_overlay/README.md \
        ../../.claude-plugin/plugin.json ../../CHANGELOG.md
# paths are relative to helpers/; adjust plugin.json/CHANGELOG paths to the real
# plugins/sec-overlay/.claude-plugin/plugin.json and plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add shared receipt-tier and status vocab"
```

Note: `plugin.json` and `CHANGELOG.md` live at `plugins/sec-overlay/.claude-plugin/plugin.json` and `plugins/sec-overlay/CHANGELOG.md`. Use their real repo paths when staging. This task is `feat` → minor bump.

---

### Task 2: Add the derived `receipt_tier` field to `Finding`

**Files:**
- Modify: `sec_overlay/models.py` (Finding dataclass fields ~models.py:100-131; `to_dict` models.py:133; `from_dict` models.py:140)
- Modify: `references/finding.schema.json` (`properties`)
- Modify: `sec_overlay/README.md` and `references/README.md` (note the field)
- Test: `tests/test_models.py` (create if absent; else append)

**Interfaces:**
- Consumes: nothing at the type level (the value is stamped by Task 3's gate).
- Produces: `Finding.receipt_tier: int | None = None`, round-tripped by `to_dict`/`from_dict`, present in `finding.schema.json`.

**Note for the implementer:** `tests/test_contracts.py::test_investigate_finding_example_matches_model` asserts that example JSON blocks in `agents/investigate.md` carry no key outside `Finding.to_dict()`'s output. Adding a field to `to_dict()` is safe (examples simply omit it). Do NOT add `receipt_tier` to the schema `required` list — it is derived and optional.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from sec_overlay.models import Finding, FindingStatus, Severity


def _minimal(**kw) -> Finding:
    base = dict(id="F-1", rule_id="r", cls="injection",
                status=FindingStatus.RAW, severity=Severity.HIGH,
                file="a.py", line=3, message="m")
    base.update(kw)
    return Finding(**base)


def test_receipt_tier_defaults_none_and_round_trips():
    f = _minimal(receipt_tier=1)
    assert f.receipt_tier == 1
    d = f.to_dict()
    assert d["receipt_tier"] == 1
    assert Finding.from_dict(d).receipt_tier == 1


def test_receipt_tier_absent_from_dict_loads_none():
    f = _minimal()
    assert f.receipt_tier is None
    assert Finding.from_dict(f.to_dict()).receipt_tier is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -q`
Expected: FAIL (`TypeError: unexpected keyword argument 'receipt_tier'`).

- [ ] **Step 3: Add the field and schema property**

In `sec_overlay/models.py`, add to the `Finding` dataclass beside the other derived fields (near `completeness_tier`, models.py:122):

```python
    receipt_tier: int | None = None
```

Confirm `to_dict` (models.py:133) serializes all dataclass fields via `dataclasses.asdict` or an explicit dict — if explicit, add `"receipt_tier": self.receipt_tier`. Confirm `from_dict` (models.py:140) already tolerates unknown/optional keys (the Explore step confirmed it does); no change needed there if it filters to known fields.

In `references/finding.schema.json`, add to `properties`:

```json
    "receipt_tier": { "type": ["integer", "null"] }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py tests/test_contracts.py -q && uv run ty check`
Expected: PASS (contracts still green).

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(sec-overlay): add derived receipt_tier field to Finding"
```
`feat` → minor bump. Stage: `sec_overlay/models.py`, `references/finding.schema.json`, `tests/test_models.py`, `sec_overlay/README.md`, `references/README.md`, plugin.json, CHANGELOG.md.

---

### Task 3: Receipt-tier confirmation gate + runtime_disposition enum gate + honor gate errors

**Files:**
- Modify: `sec_overlay/findings_gate.py` (`validate_findings`, findings_gate.py:27-74)
- Modify: `sec_overlay/driver.py` (`_act_findings_gate`, driver.py:162-163)
- Modify: `sec_overlay/README.md`
- Test: `tests/test_findings_gate.py` (create if absent; else append), `tests/test_driver.py` (append)

**Interfaces:**
- Consumes: `confirms_alone`, `receipt_tier`, `RUNTIME_DISPOSITIONS` from Task 1; `Finding.receipt_tier` from Task 2; `PhaseHalt` from `sec_overlay.driver`.
- Produces: `validate_findings` stamps `f.receipt_tier` and enforces the tier-1 rule and the disposition enum; `_act_findings_gate` raises `PhaseHalt` when `validate_findings` returns any error.

**BREAKING (recorded ruling):** This revokes the current allowance (findings_gate.py:63 comment) that a `ripgrep:` receipt alone confirms a finding for SAST-unsupported languages. Under the tier model a Tier-2-only finding cannot reach `confirmed`/`fixed`; it must route to `needs-deployment-testing`. This changes a shipped finding's status semantics, so this commit is `fix(sec-overlay)!` with a `BREAKING CHANGE:` footer → **major bump**. Cost if the ruling is wrong: some real, ripgrep-grounded findings ship as `needs-deployment-testing` (a manual test directive) instead of `confirmed` — the accuracy-over-completeness trade the spec chose (§4.3 tradeoff).

**Bench note (verify before landing):** `helpers/bench/` locked positives must keep being *detected*. A locked positive that moves `confirmed → needs-deployment-testing` is still detected. The bench corpus is gitignored/local-only, so CI cannot run it — the implementer records this as a manual-verification item; if a bench assertion over-asserts on `confirmed` status for a ripgrep-only positive, that assertion is adjusted in a follow-on, not silently.

**Contract note:** `tests/test_contracts.py::test_investigate_example_passes_the_gate` loads the example findings from `agents/investigate.md` and asserts the gate returns no error. If any example is `confirmed`/`fixed` with only Tier-2 (e.g. `ripgrep`) receipts, it will now fail. The implementer must inspect those examples and, if one relies on tier-2-only confirmation, update the example finding in `agents/investigate.md` to carry a Tier-1 receipt or a non-shipping status — preserving the surrounding prose and the `{{FP_FEEDBACK}}`/proof-tuple strings verbatim. Stage `agents/investigate.md` and `agents/README.md` if edited.

- [ ] **Step 1: Write the failing tests (security-fix order)**

```python
# tests/test_findings_gate.py
import json
from pathlib import Path

from sec_overlay.findings_gate import validate_findings
from sec_overlay.workspace import Workspace


def _write(ws: Workspace, fid: str, **over) -> None:
    data = dict(id=fid, rule_id="r", cls="injection", status="confirmed",
                severity="high", file="a.py", line=3, message="m",
                dataflow=[], evidence_sources=["ripgrep"])
    data.update(over)
    (ws.findings_dir / f"{fid}.json").write_text(json.dumps(data))


def _ws(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path)
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "a.py").write_text("x = 1\ny = 2\nz = 3\n")
    return ws


def test_tier2_only_confirmed_is_rejected(tmp_path):
    ws = _ws(tmp_path)
    _write(ws, "F-1", evidence_sources=["ripgrep", "structural-index"])
    errors = validate_findings(ws)
    assert any("F-1" in e and "confirm" in e.lower() for e in errors)


def test_tier1_confirmed_passes(tmp_path):
    ws = _ws(tmp_path)
    _write(ws, "F-2", evidence_sources=["codeql:dataflow"])
    errors = validate_findings(ws)
    assert not any("F-2" in e for e in errors)


def test_out_of_vocab_disposition_rejected(tmp_path):
    ws = _ws(tmp_path)
    _write(ws, "F-3", evidence_sources=["codeql:dataflow"],
           runtime_disposition="neither")
    errors = validate_findings(ws)
    assert any("F-3" in e and "runtime_disposition" in e for e in errors)


def test_receipt_tier_is_stamped(tmp_path):
    ws = _ws(tmp_path)
    _write(ws, "F-4", evidence_sources=["codeql:dataflow"])
    validate_findings(ws)
    stamped = json.loads((ws.findings_dir / "F-4.json").read_text())
    assert stamped["receipt_tier"] == 1
```

```python
# tests/test_driver.py  (append)
import json
import pytest
from sec_overlay.driver import AuditContext, _act_findings_gate, PhaseHalt
from sec_overlay.workspace import Workspace


def test_findings_gate_action_halts_on_error(tmp_path):
    ws = Workspace(tmp_path)
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "a.py").write_text("x = 1\n")
    (ws.findings_dir / "F-1.json").write_text(json.dumps(dict(
        id="F-1", rule_id="r", cls="injection", status="confirmed",
        severity="high", file="a.py", line=1, message="m",
        dataflow=[], evidence_sources=["ripgrep"])))
    ctx = AuditContext(ws=ws, target=str(tmp_path), config="", sha="s")
    with pytest.raises(PhaseHalt):
        _act_findings_gate(ctx)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_findings_gate.py tests/test_driver.py::test_findings_gate_action_halts_on_error -q`
Expected: FAIL — current gate accepts a ripgrep-only confirmed finding, does not check the disposition enum, does not stamp `receipt_tier`, and `_act_findings_gate` never raises.

- [ ] **Step 3: Implement the gate changes**

In `sec_overlay/findings_gate.py`, replace the import (findings_gate.py:10) and the confirmed/fixed receipt block (findings_gate.py:64-72). New import line:

```python
from sec_overlay.evidence import confirms_alone, receipt_tier, RUNTIME_DISPOSITIONS
```

Inside the per-finding loop of `validate_findings`, stamp the tier and replace the receipt check:

```python
        tiers = [t for t in (receipt_tier(s) for s in f.evidence_sources) if t is not None]
        stamped_tier = min(tiers) if tiers else None  # 1 outranks 2
        if data.get("receipt_tier") != stamped_tier:
            data["receipt_tier"] = stamped_tier
            p.write_text(json.dumps(data))

        if f.status.value in ("confirmed", "fixed") and not confirms_alone(f.evidence_sources):
            errors.append(
                f"{f.id}: {f.status.value} finding has no Tier-1 tool receipt "
                f"(sources {f.evidence_sources or 'none'}) — a Tier-2-only match "
                f"(ripgrep/ast-grep/structural-index/tree-sitter) locates code but does "
                f"not prove reachability; route to needs-deployment-testing"
            )

        if f.runtime_disposition is not None and f.runtime_disposition not in RUNTIME_DISPOSITIONS:
            errors.append(
                f"{f.id}: runtime_disposition {f.runtime_disposition!r} is not one of "
                f"{sorted(RUNTIME_DISPOSITIONS)}"
            )
```

Keep the existing `duplicate_of` check and the empty-file/line/dataflow checks. Delete the old `is_tool_receipt`-based confirmed/fixed block (findings_gate.py:64-72) — `confirms_alone` replaces it (a Tier-1 receipt is necessarily a tool receipt, so no finding loses a check).

In `sec_overlay/driver.py`, change `_act_findings_gate` (driver.py:162-163):

```python
def _act_findings_gate(ctx: AuditContext) -> None:
    errors = validate_findings(ctx.ws)  # records its own stage too
    if errors:
        raise PhaseHalt(
            f"findings-gate rejected {len(errors)} finding(s): " + "; ".join(errors)
        )
```

- [ ] **Step 4: Run the full suite to verify green**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS except the two documented env-only failures. If `test_contracts.py::test_investigate_example_passes_the_gate` fails, fix the offending example in `agents/investigate.md` per the Contract note above, then re-run.

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(sec-overlay)!: gate tier-2-only findings off confirmed"
```
Body must include a `BREAKING CHANGE:` footer describing the status-semantics change. `!` → **major bump**. Stage: `sec_overlay/findings_gate.py`, `sec_overlay/driver.py`, both test files, `sec_overlay/README.md`, (`agents/investigate.md` + `agents/README.md` if edited), plugin.json, CHANGELOG.md.

---

### Task 4: Self-score and fact-check read the shipping-status set

**Files:**
- Modify: `sec_overlay/selfscore.py` (`_REPORTED` selfscore.py:17; `build_self_score` selfscore.py:20-45)
- Modify: `agents/factcheck.md` (the "ONE already-confirmed finding" instruction)
- Modify: `sec_overlay/README.md` and `agents/README.md`
- Test: `tests/test_selfscore.py` (create if absent; else append)

**Interfaces:**
- Consumes: `SHIPPING_STATUSES` from Task 1.
- Produces: `build_self_score` returns a `"shipping"` count over `SHIPPING_STATUSES`; existing keys (`reported`, `confirmed`, `needs_runtime`, `rejected`) are retained.

**Ruling (recorded):** `_REPORTED = {CONFIRMED, FIXED}` stays as the narrow "reported" count for backward continuity, and a new `"shipping"` key counts the full `SHIPPING_STATUSES` set. Adding rather than redefining avoids breaking any downstream reader of `reported`. Cost if wrong: one redundant count key; harmless.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_selfscore.py
import json
from pathlib import Path

from sec_overlay.selfscore import build_self_score
from sec_overlay.workspace import Workspace


def _f(ws, fid, status):
    (ws.findings_dir / f"{fid}.json").write_text(json.dumps(dict(
        id=fid, rule_id="r", cls="c", status=status, severity="low",
        file="a.py", line=1, message="m", dataflow=[])))


def test_shipping_counts_full_set(tmp_path):
    ws = Workspace(tmp_path)
    ws.findings_dir.mkdir(parents=True, exist_ok=True)
    _f(ws, "F-1", "confirmed")
    _f(ws, "F-2", "fixed")
    _f(ws, "F-3", "needs-deployment-testing")
    _f(ws, "F-4", "rejected")
    score = build_self_score(ws)
    assert score["shipping"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_selfscore.py::test_shipping_counts_full_set -q`
Expected: FAIL (`KeyError: 'shipping'`).

- [ ] **Step 3: Add the shipping count**

In `sec_overlay/selfscore.py`, import the set and add the count inside `build_self_score` (selfscore.py:36-41):

```python
from sec_overlay.evidence import SHIPPING_STATUSES
```

```python
        "shipping": sum(1 for f in findings if f.status.value in SHIPPING_STATUSES),
```

In `agents/factcheck.md`, change the target-selection instruction from "ONE already-confirmed finding" to "ONE shipping-status finding (`confirmed`, `fixed`, or `needs-deployment-testing`)", preserving every other rule in the prompt verbatim.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_selfscore.py tests/test_contracts.py tests/test_wiring.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(sec-overlay): selfscore/factcheck read shipping-status set"
```
`fix` → patch bump. Stage: `sec_overlay/selfscore.py`, `agents/factcheck.md`, `tests/test_selfscore.py`, `sec_overlay/README.md`, `agents/README.md`, plugin.json, CHANGELOG.md.

---

### Task 5: Red-team coverage-first bar

**Files:**
- Modify: `sec_overlay/redteam.py` (`_above_bar`, redteam.py:44-56)
- Modify: `tests/test_redteam.py` (the `prime-manual-test` test, test_redteam.py:29)
- Modify: `sec_overlay/README.md`
- Test: `tests/test_redteam.py` (append)

**Interfaces:**
- Consumes: `is_tool_receipt` (already imported redteam.py:20).
- Produces: `_above_bar(f, min_risk)` no longer withholds a test directive for a missing receipt; the dead `redteam:prime-manual-test` branch is removed.

**Ruling (recorded):** The `has_receipt` conjunct is dropped from the severity fast-path so a high/critical finding above the risk floor becomes a directive regardless of receipt (a missing receipt sorts it later, per Task's sort, but never withholds the test that would settle it — spec §4.3). The `redteam:prime-manual-test` branch is dead (no producer writes that history event — confirmed by the Explore step) and is deleted along with its unit test that manually injects the event. Cost if wrong: the plan grows by a few directives (the spec's intended ~11 → ~21 growth), which is the coverage-first goal.

- [ ] **Step 1: Write the failing test and update the dead-branch test**

```python
# tests/test_redteam.py  (append)
from sec_overlay.redteam import _above_bar
from sec_overlay.models import Finding, FindingStatus, Severity


def _f(**kw) -> Finding:
    base = dict(id="F", rule_id="r", cls="c", status=FindingStatus.NEEDS_DEPLOYMENT_TESTING,
                severity=Severity.HIGH, file="a.py", line=1, message="m",
                evidence_sources=[])
    base.update(kw)
    return Finding(**base)


def test_high_severity_without_receipt_is_above_bar():
    # No receipt, but high severity + above floor must still yield a directive.
    assert _above_bar(_f(severity=Severity.HIGH, risk_score=8), min_risk=7) is True


def test_below_floor_without_receipt_is_below_bar():
    assert _above_bar(_f(severity=Severity.LOW, risk_score=2), min_risk=7) is False
```

Delete the existing `prime-manual-test` test at `tests/test_redteam.py:29` (the one that injects `{"event": "redteam:prime-manual-test"}` into history).

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `uv run pytest tests/test_redteam.py -q`
Expected: `test_high_severity_without_receipt_is_above_bar` FAILS on current code (the `has_receipt` conjunct gates the severity fast-path off).

- [ ] **Step 3: Rewrite `_above_bar`**

In `sec_overlay/redteam.py`, replace `_above_bar` (redteam.py:44-56):

```python
def _above_bar(f: Finding, min_risk: int) -> bool:
    """Return True if a finding earns a full manual test directive.

    Coverage-first: a high/critical finding above the risk floor earns a
    directive regardless of receipt strength — a missing receipt sorts the
    directive later, it never withholds the test that would settle the
    finding.

    Args:
        f: The finding under consideration.
        min_risk: The risk-score floor (default from ``DEFAULT_MIN_RISK``).

    Returns:
        True when the finding is above the bar.
    """
    if f.severity in _ACTIONABLE_SEVERITIES:
        return True
    return (f.risk_score or 0) >= min_risk
```

Remove the now-unused `has_receipt` local and the `prime-manual-test` branch. If `is_tool_receipt` is now unused in the module, remove its import (redteam.py:20); if other functions still use it (redteam.py:51,142 — check `receipts = [...]` at redteam.py:142 which renders receipts in the directive), keep the import.

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_redteam.py -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS, no unused-import warning.

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(sec-overlay): coverage-first red-team bar, drop dead branch"
```
`fix` → patch bump. Stage: `sec_overlay/redteam.py`, `tests/test_redteam.py`, `sec_overlay/README.md`, plugin.json, CHANGELOG.md.

---

### Task 6: Reference parser strips a trailing human hint

**Files:**
- Modify: `sec_overlay/phase_gate.py` (`_parse_ref`, phase_gate.py:22-41)
- Modify: `sec_overlay/README.md`
- Test: `tests/test_phase_gate.py` (create if absent; else append)

**Interfaces:**
- Consumes: nothing.
- Produces: `_parse_ref(ref) -> tuple[str, int | None]` accepts `path:line[-range] <trailing hint>` and returns `(path, line)`, stripping the hint. The `(path, None)` behavior for a truly unparseable ref is unchanged.

**Ruling (recorded):** ISSUE-024/028 — today `_parse_ref` does `rsplit(":", 1)` and requires the whole tail to be a digit or `N-M` range, so `foo.py:42 in the handler` fails to resolve. The fix reads the leading `path:line[-range]` with a regex and treats any trailing text as an optional hint. A bare `path` with no colon-line still returns `(path, None)`; a colon with non-numeric first tail token (e.g. a Windows-style `C:\x`) still returns `(ref, None)` since there is no line to anchor. Cost if wrong: a citation with an unusual shape resolves to a slightly different path — caught by `ref_resolves` returning False, the safe direction.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phase_gate.py
from sec_overlay.phase_gate import _parse_ref


def test_plain_path_and_line():
    assert _parse_ref("sec/foo.py:42") == ("sec/foo.py", 42)


def test_range_anchors_on_start():
    assert _parse_ref("sec/foo.py:42-51") == ("sec/foo.py", 42)


def test_trailing_hint_is_stripped():
    assert _parse_ref("sec/foo.py:42 in the request handler") == ("sec/foo.py", 42)
    assert _parse_ref("sec/foo.py:42-51 (the taint sink)") == ("sec/foo.py", 42)


def test_bare_path_returns_none_line():
    assert _parse_ref("sec/foo.py") == ("sec/foo.py", None)


def test_unparseable_line_returns_none():
    assert _parse_ref("sec/foo.py:not-a-line") == ("sec/foo.py:not-a-line", None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_phase_gate.py -q`
Expected: `test_trailing_hint_is_stripped` FAILS (current code returns `("sec/foo.py:42 in the request handler", None)` etc.).

- [ ] **Step 3: Rewrite `_parse_ref` with a leading-anchor regex**

In `sec_overlay/phase_gate.py`, replace the body of `_parse_ref` (phase_gate.py:31-41). Add a module-level compiled pattern near the other regex (`_MD_CITATION`) or above the function:

```python
_REF_ANCHOR = re.compile(r"^(?P<path>.+?):(?P<start>\d+)(?:-\d+)?(?:\s.*)?$")
```

New body:

```python
    ref = (ref or "").strip()
    m = _REF_ANCHOR.match(ref)
    if m:
        return m.group("path"), int(m.group("start"))
    if ":" not in ref:
        return ref, None
    return ref, None
```

Keep the docstring, updating it to note that a trailing human hint after the line/range is stripped. `re` is already imported (phase_gate.py:17).

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_phase_gate.py -q && uv run pytest tests/test_redteam.py -q`
Expected: PASS (redteam consumes phase_gate helpers indirectly — confirm no regression).

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(sec-overlay): strip trailing hint in citation ref parser"
```
`fix` → patch bump. Stage: `sec_overlay/phase_gate.py`, `tests/test_phase_gate.py`, `sec_overlay/README.md`, plugin.json, CHANGELOG.md.

---

### Task 7: Recon scan-profile schema gains the two fields recon writes

**Files:**
- Modify: `references/scan-profile.schema.json` (`properties`; consider `required`)
- Modify: `sec_overlay/profile.py` (`_REQUIRED`, profile.py:69, if it drives `validate_profile`)
- Modify: `references/README.md`
- Test: `tests/test_profile.py` (create if absent; else append)

**Interfaces:**
- Consumes: nothing.
- Produces: `scan-profile.schema.json` `properties` includes `attack_surface_evidence` and `subsystems`; `attack_surface_evidence` is added to the schema so the phase gate can rely on it being present.

**Ruling (recorded):** ISSUE-025 — recon (`agents/recon.md`) writes `attack_surface_evidence` and `subsystems` (both real `ScanProfile` fields, profile.py) but neither appears in `scan-profile.schema.json`. Add both to `properties`. Add `attack_surface_evidence` to `required` (Task 8's gate depends on it); leave `subsystems` optional (a repo may have one subsystem and omit the partition). Cost if wrong: a recon profile missing `attack_surface_evidence` fails schema validation — the correct signal, since Task 8 needs it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_profile.py
import json
from pathlib import Path

_SCHEMA = (Path(__file__).resolve().parents[1] / "references" / "scan-profile.schema.json")


def test_schema_declares_evidence_and_subsystems():
    schema = json.loads(_SCHEMA.read_text())
    props = schema["properties"]
    assert "attack_surface_evidence" in props
    assert "subsystems" in props
    assert "attack_surface_evidence" in schema["required"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_profile.py::test_schema_declares_evidence_and_subsystems -q`
Expected: FAIL (keys absent).

- [ ] **Step 3: Add the properties**

In `references/scan-profile.schema.json`, add to `properties`:

```json
    "attack_surface_evidence": {
      "type": "object",
      "additionalProperties": { "type": "array", "items": { "type": "string" } }
    },
    "subsystems": {
      "type": "array",
      "items": { "type": "object" }
    }
```

Add `"attack_surface_evidence"` to the `required` array. If `sec_overlay/profile.py`'s `_REQUIRED` (profile.py:69) is the list `validate_profile` enforces and it should match, add `"attack_surface_evidence"` there too; do not add `subsystems` to `_REQUIRED`.

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_profile.py tests/test_wiring.py tests/test_contracts.py -q`
Expected: PASS. If a fixture profile elsewhere now fails schema validation for lacking `attack_surface_evidence`, add the key to that fixture (an empty object is valid).

- [ ] **Step 5: Commit**

```bash
git commit -m "fix(sec-overlay): add recon evidence/subsystems to profile schema"
```
`fix` → patch bump. Stage: `references/scan-profile.schema.json`, (`sec_overlay/profile.py` if edited), `tests/test_profile.py`, `references/README.md`, (`sec_overlay/README.md` if profile.py edited), plugin.json, CHANGELOG.md.

---

### Task 8: Recon gate requires a non-comment reference to establish an attack surface

**Files:**
- Modify: `sec_overlay/phase_gate.py` (add `attack_surface_gate`)
- Modify: `sec_overlay/README.md`
- Test: `tests/test_phase_gate.py` (append)

**Interfaces:**
- Consumes: `is_comment_line`, `resolve_ref` (phase_gate.py, same module); `ScanProfile.attack_surface`, `ScanProfile.attack_surface_evidence` (profile.py).
- Produces: `def attack_surface_gate(profile, target_root: str | Path) -> list[str]` — returns an error string per attack-surface key whose evidence refs are absent or resolve only to comment lines.

**Ruling (recorded):** ISSUE-026 — an attack surface must rest on a non-comment code reference. A comment (`// auth is enforced elsewhere`) is a claim about code, not proof it executes. The gate rejects an `attack_surface` key when it has no evidence ref, or when every resolving ref is a comment line. A ref that fails to resolve is also not acceptable evidence. This is a dedicated deterministic check, kept out of the generic `run_phase_checks` so architecture/context claims that legitimately cite a comment are not over-rejected. Cost if wrong: recon must cite a code line (not a comment) for each surface — the intended bar.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_phase_gate.py  (append)
from sec_overlay.phase_gate import attack_surface_gate
from sec_overlay.profile import ScanProfile


def _repo(tmp_path):
    (tmp_path / "h.py").write_text("def handler(req):\n    # entry point here\n    return run(req)\n")
    return tmp_path


def test_surface_backed_by_code_line_passes(tmp_path):
    repo = _repo(tmp_path)
    prof = ScanProfile(attack_surface=["http"],
                       attack_surface_evidence={"http": ["h.py:3"]})
    assert attack_surface_gate(prof, repo) == []


def test_surface_backed_only_by_comment_is_rejected(tmp_path):
    repo = _repo(tmp_path)
    prof = ScanProfile(attack_surface=["http"],
                       attack_surface_evidence={"http": ["h.py:2"]})
    errors = attack_surface_gate(prof, repo)
    assert any("http" in e and "comment" in e.lower() for e in errors)


def test_surface_with_no_evidence_is_rejected(tmp_path):
    repo = _repo(tmp_path)
    prof = ScanProfile(attack_surface=["http"], attack_surface_evidence={})
    errors = attack_surface_gate(prof, repo)
    assert any("http" in e for e in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_phase_gate.py -k attack_surface -q`
Expected: FAIL (`attack_surface_gate` does not exist).

- [ ] **Step 3: Implement `attack_surface_gate`**

In `sec_overlay/phase_gate.py`, add:

```python
def attack_surface_gate(profile, target_root: str | Path) -> list[str]:
    """Reject an attack-surface key not backed by a non-comment code reference.

    A comment line is a claim about code, not proof the surface executes; a
    ref that does not resolve is not evidence either. Each ``attack_surface``
    key must have at least one evidence ref that resolves to a non-comment
    line.

    Args:
        profile: A :class:`sec_overlay.profile.ScanProfile`.
        target_root: The scanned repo root.

    Returns:
        One error string per unbacked attack-surface key; empty if all pass.
    """
    evidence = getattr(profile, "attack_surface_evidence", {}) or {}
    errors: list[str] = []
    for key in getattr(profile, "attack_surface", []) or []:
        refs = evidence.get(key, []) or []
        code_backed = False
        for ref in refs:
            resolved, _ = resolve_ref(target_root, ref)
            if resolved and is_comment_line(target_root, ref) is False:
                code_backed = True
                break
        if not code_backed:
            errors.append(
                f"attack_surface {key!r} has no non-comment code reference "
                f"(evidence {refs or 'none'}) — a comment or unresolved ref does "
                f"not prove the surface executes"
            )
    return errors
```

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_phase_gate.py -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(sec-overlay): recon gate requires code-backed attack surface"
```
`feat` → minor bump. Stage: `sec_overlay/phase_gate.py`, `tests/test_phase_gate.py`, `sec_overlay/README.md`, plugin.json, CHANGELOG.md.

---

### Task 9: `render_prompt` render-check utility

**Files:**
- Create: `sec_overlay/prompts.py`
- Modify: `sec_overlay/README.md`
- Modify: `skills/sec-overlay/CLAUDE.md` (operating manual §2 — instruct the orchestrator to render through it)
- Test: `tests/test_prompts.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `def render_prompt(template: str, subs: dict[str, str]) -> str` — substitutes `{{KEY}}` tokens and raises `ValueError` naming every unfilled `{{TOKEN}}` that remains.

**Ruling (recorded):** ISSUE-040 — there is no code-level prompt renderer today; token substitution is done by the orchestrator by hand, which is where the patch prompt lost its class token (ISSUE-050, Plan A). This adds the render primitive with a loud failure on any leftover `{{token}}`, and the operating manual (`skills/sec-overlay/CLAUDE.md` §2) is updated to instruct rendering every agent dispatch through it. The utility is pure and independently tested; its caller is the human/orchestrator per the documented flow. Cost if wrong: the utility is under-used until the orchestrator adopts it — it never produces a wrong result, only an unused guard, so the risk is limited to token substitution staying manual.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prompts.py
import pytest
from sec_overlay.prompts import render_prompt


def test_fills_all_tokens():
    out = render_prompt("scan {{TARGET}} at {{SHA}}", {"TARGET": "/r", "SHA": "abc"})
    assert out == "scan /r at abc"


def test_unfilled_token_raises_and_names_it():
    with pytest.raises(ValueError) as exc:
        render_prompt("scan {{TARGET}} class {{ATTACK_CLASS}}", {"TARGET": "/r"})
    assert "ATTACK_CLASS" in str(exc.value)


def test_extra_subs_are_ignored():
    assert render_prompt("hi {{A}}", {"A": "x", "B": "y"}) == "hi x"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_prompts.py -q`
Expected: FAIL (module does not exist).

- [ ] **Step 3: Implement `render_prompt`**

Create `sec_overlay/prompts.py`:

```python
"""Prompt rendering with a loud failure on any unfilled ``{{token}}``.

Token substitution for agent dispatch was done by hand, which is how the
patch prompt once lost its class token. ``render_prompt`` substitutes every
``{{KEY}}`` and refuses to return a template that still carries an unfilled
token — a missing substitution fails loudly instead of shipping a literal
``{{ATTACK_CLASS}}`` to a model.
"""

from __future__ import annotations

import re

_TOKEN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def render_prompt(template: str, subs: dict[str, str]) -> str:
    """Substitute ``{{KEY}}`` tokens in ``template`` from ``subs``.

    Args:
        template: Prompt text with ``{{TOKEN}}`` placeholders.
        subs: Mapping of token name (without braces) to its value. Extra keys
            are ignored.

    Returns:
        The template with every provided token substituted.

    Raises:
        ValueError: One or more ``{{TOKEN}}`` placeholders had no substitution.

    Example:
        >>> render_prompt("scan {{T}}", {"T": "/repo"})
        'scan /repo'
    """
    rendered = _TOKEN.sub(lambda m: subs.get(m.group(1), m.group(0)), template)
    leftover = sorted(set(_TOKEN.findall(rendered)))
    if leftover:
        raise ValueError(f"unfilled prompt token(s): {', '.join(leftover)}")
    return rendered
```

In `skills/sec-overlay/CLAUDE.md` §2 ("How to run an audit"), add one line to the agent-dispatch description: the orchestrator renders each agent prompt through `sec_overlay.prompts.render_prompt` so an unfilled `{{token}}` fails before the model runs.

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_prompts.py -q && uv run ruff check sec_overlay/ tests/ && uv run ty check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(sec-overlay): add render_prompt token-completeness check"
```
`feat` → minor bump. Stage: `sec_overlay/prompts.py`, `tests/test_prompts.py`, `sec_overlay/README.md`, `skills/sec-overlay/CLAUDE.md`, plugin.json, CHANGELOG.md. Note: `skills/sec-overlay/CLAUDE.md` is not a shipping file, but `sec_overlay/prompts.py` is — the bump is driven by the module.

---

### Task 10: Evidence vocabulary as a prompt-constants block + drift test

**Files:**
- Modify: `references/prompt-constants.md` (add a 13th block `## EVIDENCE_VOCABULARY`)
- Modify: `references/README.md` (the block list — it enumerates the blocks)
- Test: `tests/test_docs_invariants.py` (append a drift test binding the block to the code constants)

**Interfaces:**
- Consumes: `TIER1_RECEIPTS`, `TIER2_RECEIPTS`, `SHIPPING_STATUSES`, `RUNTIME_DISPOSITIONS` from Task 1.
- Produces: a named `## EVIDENCE_VOCABULARY` block agents reference by name (the existing pattern — blocks are referenced in prose, not programmatically injected), plus a test asserting the block text lists exactly the code's tier/status/disposition values so the closed vocabulary cannot drift from the constants.

**Ruling (recorded):** ISSUE-046 — the receipt-tier and shipping-status vocabulary was a closed set the agent had to guess. There is no programmatic block-injection mechanism (confirmed by the Explore step); blocks are referenced by name in agent prose. The minimal, pattern-matching fix adds one `## EVIDENCE_VOCABULARY` block to `references/prompt-constants.md` and a drift test binding it to the code constants — introducing a first templating engine is out of scope for this plan. ISSUE-035 (the semantic gap stays split — deterministic gate proves *resolves*, opus adversary judges *meaning*) is a no-code decision recorded here for coverage; no implementation. Cost if wrong: agents read the vocabulary from prose rather than an injected block — the same delivery every other constant uses.

- [ ] **Step 1: Write the failing drift test**

```python
# tests/test_docs_invariants.py  (append)
from pathlib import Path
from sec_overlay.evidence import (
    TIER1_RECEIPTS, TIER2_RECEIPTS, SHIPPING_STATUSES, RUNTIME_DISPOSITIONS,
)

_PC = Path(__file__).resolve().parents[1] / "references" / "prompt-constants.md"


def test_evidence_vocabulary_block_lists_all_values():
    text = _PC.read_text()
    assert "## EVIDENCE_VOCABULARY" in text
    block = text.split("## EVIDENCE_VOCABULARY", 1)[1].split("\n## ", 1)[0]
    for value in (TIER1_RECEIPTS | TIER2_RECEIPTS | SHIPPING_STATUSES | RUNTIME_DISPOSITIONS):
        assert value in block, f"{value} missing from EVIDENCE_VOCABULARY block"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_docs_invariants.py::test_evidence_vocabulary_block_lists_all_values -q`
Expected: FAIL (block absent).

- [ ] **Step 3: Add the block**

Append to `references/prompt-constants.md` (after `## QUALIFIER_PROOF`):

```markdown
## EVIDENCE_VOCABULARY

The evidence, status, and disposition vocabularies are closed sets. Use only these values.

- **Tier-1 receipts (confirm a finding alone):** `codeql`, `semgrep`, `sca`, `secrets`.
  Each is proof-complete for its shape (a dataflow path, a vulnerable version, a live secret).
- **Tier-2 receipts (corroborate only, never confirm):** `ripgrep`, `structural-index`,
  `ast-grep`, `tree-sitter`. These locate code; they do not prove reachability. A finding
  whose only receipts are Tier-2 cannot reach `confirmed` — route it to
  `needs-deployment-testing`.
- **Shipping statuses (a reader acts on these):** `confirmed`, `fixed`,
  `needs-deployment-testing`.
- **`runtime_disposition` (closed enum):** `needs-runtime`, `static-settled`, `unassessed`.
  Any other value (e.g. `neither`) is rejected at the findings gate.
```

Update `references/README.md`'s enumeration of the prompt-constants blocks to list `EVIDENCE_VOCABULARY` (the count moves from 12 to 13).

- [ ] **Step 4: Run tests to verify green**

Run: `uv run pytest tests/test_docs_invariants.py tests/test_contracts.py tests/test_wiring.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "docs(sec-overlay): add EVIDENCE_VOCABULARY prompt-constants block"
```
`docs` → patch bump (a `references/` file is a shipping file). Stage: `references/prompt-constants.md`, `references/README.md`, `tests/test_docs_invariants.py`, plugin.json, CHANGELOG.md.

---

## Self-Review

**Spec coverage (§4.2 T2, §4.3 T3):**

| Issue | Theme | Task |
|---|---|---|
| 024 ref parser | T2 | Task 6 |
| 025 recon schema field | T2 | Task 7 |
| 026 non-comment reference | T2 | Task 8 |
| 028 ref parser hint | T2 | Task 6 |
| 035 semantic gap split (no-code) | T2 | Task 10 (recorded, no impl) |
| 040 render check | T2 | Task 9 |
| 041 schema at gate → dedupe | T2 | Task 3 (driver halts on gate errors) |
| 046 vocabulary in prompts | T2 | Task 10 |
| 003 receipt tiers | T3 | Tasks 1, 2, 3 |
| 048 gate reads shipping set | T3 | Task 3 |
| 054 coverage-first bar | T3 | Task 5 |
| 055 disposition enum | T3 | Tasks 1, 3 |
| 057 factcheck shipping set | T3 | Task 4 |

All 13 Plan B issues mapped. ISSUE-041's real gap (the driver ignored the gate's errors — driver.py:162) is fixed in Task 3; the schema check itself already runs at findings_gate.py:47, and Plan A placed the gate before dedupe.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N" — every code and test step carries real content.

**Type consistency:** `receipt_tier` is `int | None` in Task 1 (`receipt_tier(source)` return), Task 2 (`Finding.receipt_tier` field), and Task 3 (the stamped value, `min(tiers)`). `confirms_alone(list[str]) -> bool` consumed consistently in Task 3. `SHIPPING_STATUSES`/`RUNTIME_DISPOSITIONS` are `frozenset[str]` produced in Task 1 and consumed by `.value in <set>` string membership in Tasks 3 and 4. `render_prompt(str, dict[str,str]) -> str` self-consistent in Task 9. `attack_surface_gate(profile, root) -> list[str]` self-consistent in Task 8.

**Ordering:** Task 1 (constants) precedes every consumer. Task 2 (field) precedes Task 3 (stamp). Tasks 6–10 are independent of 1–5 and of each other, so their order is free.
