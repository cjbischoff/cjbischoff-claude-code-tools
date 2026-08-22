# Phase 3: Rule Matching & Review Modes - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 8 (2 new modules, 1 new rule_docs tree, 3 existing extended, 2 CLI/skill wiring)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `helpers/sec_overlay/rule_glob.py` (NEW) | utility (path matcher) | transform (path → resolved rule doc) | `helpers/sec_overlay/rule_matcher.py` (role: pattern-table matcher, different purpose — content regex not path glob) + `helpers/sec_overlay/exclusions.py` (role: layered config + glob, same shape) | role-match |
| `helpers/sec_overlay/reflection.py` (NEW) | service (subagent-dispatch validator) | event-driven (per-file LLM response → mechanical veto/retract) | `helpers/sec_overlay/phase_gate.py` (`run_phase_checks`/`build_gate_record`) | exact (same dispatch shape: deterministic pre-check → agent → apply verdict → ledger) |
| `rules/rule_docs/*.md` (NEW, 9 files + default) | config/data (LLM prompt payload) | file-I/O (read-only template content) | `references/prompt-constants.md` (existing prompt-payload blocks) | role-match |
| `rules/rule_docs/README.md` (NEW) | doc | — | any existing folder README under `references/` | role-match |
| `helpers/sec_overlay/cli.py` (MODIFY — `review` subparser + `run_review`) | controller (CLI) | request-response | itself, existing `review` subparser (lines 198-201) and `scan` subparser pattern (lines 174-186) | exact |
| `helpers/sec_overlay/phase_gate.py` (MODIFY — profile branch beside `review_position_gate`) | service (gate ladder) | transform (findings → kept/dropped) | itself, `review_position_gate` (lines 410-462) | exact |
| `helpers/sec_overlay/report.py` (MODIFY — `write_review_ledger` extension) | service (report/ledger writer) | file-I/O (atomic JSON write) | itself, `write_review_ledger` (lines 683-716) | exact |
| `helpers/sec_overlay/findings_gate.py` (MODIFY — general-defect disposition cases) | service (schema/receipt gate) | CRUD (validate + rewrite finding files) | itself, `validate_findings` (lines 33-96), esp. the `receipt_tier` stamping block (70-82) | exact |

## Pattern Assignments

### `helpers/sec_overlay/rule_glob.py` (utility, transform)

**Analogs:** `helpers/sec_overlay/exclusions.py` (layered-config shape) and
`helpers/sec_overlay/rule_matcher.py` (dataclass-result + no-LLM discipline).

**Imports pattern** (`exclusions.py` lines 1-14):
```python
from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field

from sec_overlay.models import Finding
from sec_overlay.workspace import Workspace
```
`rule_glob.py` needs the same shape but swap `fnmatch` for the new custom `**`-aware matcher
(D-01 forbids `PurePath.full_match`); no third import beyond stdlib (`json`, `pathlib`,
`dataclasses`) — REL-03 zero-dependency rule.

**Config-dataclass + loader pattern** (`exclusions.py` lines 17-49, `Exclusions` + `load_exclusions`):
```python
@dataclass
class Exclusions:
    rule_ids: set[str] = field(default_factory=set)
    paths: list[str] = field(default_factory=list)
    classes: set[str] = field(default_factory=set)


def load_exclusions(ws: Workspace) -> Exclusions:
    path = ws.kb / "exclusions.json"
    if not path.exists():
        return Exclusions()
    d = json.loads(path.read_text())
    return Exclusions(
        rule_ids=set(d.get("rule_ids", [])),
        paths=list(d.get("paths", [])),
        classes=set(d.get("classes", [])),
    )
```
Mirror this for a `RuleLayer` dataclass (`path_rules`, `default_rule`, `merge_system_rule`) loaded
from `.sec-overlay/rule.json` / `~/.sec-overlay/rule.json` / built-in — "absent file → empty/default
layer" is the same defensive-load idiom to reuse, not reinvent.

**Result/matched-or-not dataclass pattern** (`rule_matcher.py` lines 51-61):
```python
@dataclass
class MatchResult:
    asvs_ids: list[str] = field(default_factory=list)
    codeguard_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        return bool(self.asvs_ids or self.codeguard_ids)
```
Use the same `@dataclass` + derived-boolean-property idiom for `ResolvedRule` (path, layer,
`merge_system_rule`).

**Partition-by-rule pattern** (`exclusions.py` lines 52-74, `apply_exclusions`):
```python
def apply_exclusions(findings, ex):
    kept, dropped = [], []
    for f in findings:
        excluded = (
            f.rule_id in ex.rule_ids
            or f.cls in ex.classes
            or any(fnmatch.fnmatch(f.file, pat) for pat in ex.paths)
        )
        (dropped if excluded else kept).append(f)
    return kept, dropped
```
This is the shape of Pattern 2 in RESEARCH.md (whole-layer `--exclude`/`FileFilter` selection) —
`rule_glob.py`'s exclude-resolution function should follow this exact "first matching predicate
wins" loop structure, kept structurally SEPARATE from the per-path fallthrough resolver (Pattern
1) per the RESEARCH.md anti-pattern warning — do not let one function do both jobs.

**Case-normalization note:** neither analog lower-cases before matching (`exclusions.py` uses
`fnmatch.fnmatch` on raw case); `rule_glob.py` must add explicit `.lower()` on both path and
pattern per D-04 — this is new behavior, not present in the analog, call it out in the plan.

---

### `helpers/sec_overlay/reflection.py` (service, event-driven)

**Analog:** `helpers/sec_overlay/phase_gate.py` (`run_phase_checks`, `build_gate_record`,
`write_gate_record`, `review_position_gate`).

**Deterministic pre-check → per-claim decision pattern** (`phase_gate.py` lines 165-218, structure
only — read `run_phase_checks`/`GateDecision` directly when implementing; the shape to copy is: a
`@dataclass` decision type, a function taking a list of claims + target root, returning one
decision per claim, REJECT-without-agent on hard failure).

**Ledger-write pattern** (`phase_gate.py` lines 373-379):
```python
def write_gate_record(ws, phase: str, record: dict) -> Path:
    """Persist a gate record to ``kb/gates/<phase>.json`` and return the path."""
    d = ws.kb / "gates"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{phase}.json"
    p.write_text(json.dumps(record, indent=2))
    return p
```
`reflection.py` should follow this same "ensure dir, write one JSON file per unit-of-work" idiom
for its own artifact (or, per D-14, extend `review_ledger.json` via `report.write_review_ledger`
instead of inventing a third file — see below).

**Never-mutate, always-copy pattern for position/finding changes** (`phase_gate.py` lines 396-407,
`_with_position`):
```python
def _with_position(finding, path: str, line: int):
    """Return `finding` at path/line, copying rather than mutating the input.

    A relocated finding is kept at its resolved position, not its claimed one — the input
    object is never touched, so calling the gate twice on the same findings is idempotent.
    """
    if finding.file == path and finding.line == line:
        return finding
    moved = copy.copy(finding)
    moved.file = path
    moved.line = line
    return moved
```
`reflection.py`'s retraction application must follow the same non-mutating idiom: never mutate a
`Finding` in place when applying a retraction/downgrade — copy first, exactly as `_with_position`
does, so the filter is idempotent and callable-twice-safe (mirrors D-13's phase-adversary reuse).

**Dataclass-with-frozen-invariant-in-`__post_init__`** (`positioning.py` `PositionResult`, lines
28-76 — see full excerpt already in context): reuse this idiom for any new `ReflectionVerdict` or
retraction-record dataclass — validate the decision enum and cross-field invariants
(e.g. a retraction record must always carry `reason == "reflection-retracted"`) in `__post_init__`,
raising `ValueError` on violation, exactly as `PositionResult` does for `needs-position-review`/
`relocated`/`exact`.

**Protected-subject veto (D-16) — mechanical-recheck-never-trust-LLM pattern**: `evidence.py`'s
`confirms_alone`/`receipt_tier` (lines 59-91) is the canonical example of "the code decides, not
the LLM's claim" — `receipt_tier` never trusts a source string's self-reported tier without
checking it against `TIER1_RECEIPTS`/`TIER2_RECEIPTS` frozensets. Model `reflection.py`'s
protected-subject check the same way: a fixed frozenset of protected classes, checked in Python
against the finding's own `cls`/tags field, independent of whatever the LLM response claims it
verified.

---

### `rules/rule_docs/*.md` (config/data, file-I/O)

**Analog:** `references/prompt-constants.md` — terse imperative block format (verified lines 19-34
above: `EXCLUSION_RULES`, `SEVERITY_GUIDANCE`). Per-language rule docs should match this same
terse-checklist voice (D-05) — bullet lists of exclusions/classes, NOT prose paragraphs. Port OCR
content verbatim where it exists; do not run an STE100 pass over these files (D-05 is explicit).

---

### `helpers/sec_overlay/cli.py` (`review` subparser + `run_review`)

**Analog:** itself — existing `review` subparser (lines 198-201) and the `scan` subparser's
richer optional-flag pattern (lines 174-186) for how to add `--rule`/`--exclude`/`--profile`.

**Existing subparser to extend:**
```python
review = sub.add_parser("review", help="Run a diff-scoped review pass (tracer path).")
review.add_argument("--base", required=True)
review.add_argument("--head", default="HEAD")
review.add_argument("--root", default=".")
```
Add `--profile` (choices `security`/`general`, default `security`), `--rule` (repeatable or single
override path), `--exclude` (repeatable glob) following the `scan` subparser's optional-arg style
(`scan.add_argument("--sha", default=None)` etc., lines 180-185).

**Integration point already flagged by RESEARCH.md** (`cli.py` lines 91-160, `run_review`):
```python
_kept, dropped, declines = review_position_gate([], hunks_by_path)
write_report(ws, dropped=dropped, position_reviews=declines)
```
The `[]` hardcoded empty finding list is the wiring point this phase must fill (per-file rule-doc
resolution → LLM review call → reflection filter → `review_position_gate` → profile branch). Read
this function's full docstring (lines 92-112) before touching it — it documents the exit-code
contract (0/2/3) that must not regress.

---

### `helpers/sec_overlay/phase_gate.py` (profile branch)

**Analog:** itself, `review_position_gate` (lines 410-462) — the exact composition point RESEARCH.md
names. The profile branch (gates A-E vs. A/B-bypass-by-class-allowlist) composes AFTER this
function's `kept`/`dropped`/`declines` split, per the architecture diagram in RESEARCH.md. Follow
the same `(kept, dropped, declines)`-tuple return convention for the new profile-branch function
rather than inventing a different return shape.

**Reason-enum-as-frozenset pattern** (lines 382-383):
```python
OUTSIDE_DIFF_REASON = "outside-diff"
DROP_REASONS: frozenset[str] = frozenset({OUTSIDE_DIFF_REASON})
```
Use the same frozenset-of-literal-reason-strings idiom for the general-defect-class allowlist
(NPE, thread-safety, resource-leak, error-swallowing, injection) named in D-09.

---

### `helpers/sec_overlay/report.py` (`write_review_ledger` extension)

**Analog:** itself (lines 683-716, full function already read):
```python
def write_review_ledger(ws: Workspace, *, position_reviews: list[PositionResult], dropped: list) -> Path:
    ledger = {
        "position_reviews": [...],
        "dropped": [asdict(d) if is_dataclass(d) else d for d in dropped],
    }
    path = ws.artifacts / "review_ledger.json"
    _atomic_write(path, json.dumps(ledger, indent=2))
    return path
```
D-14/D-15 (reflection retractions + fail-open markers) should be added as new keys in this SAME
dict (`"reflection_retractions"`, `"reflection_skipped"` — exact names are Claude's Discretion),
using the identical `asdict(d) if is_dataclass(d) else d` conversion idiom, NOT a new artifact
file or a new writer function. Keep the single-`_atomic_write`-call convention.

**Always-render-explicit-zero-case pattern** (cited in RESEARCH.md, `report.py` lines 625-626,
668-669 — not re-read this session, trust the RESEARCH.md verbatim quote):
```python
if not dropped: return f"{DROPPED_FINDINGS_HEADING}\n\nNo finding was dropped.\n"
if not results: return f"{POSITION_REVIEW_HEADING}\n\nNo finding required position review.\n"
```
Reflection's Markdown section (in `write_report`, not just the JSON ledger) must follow this same
"render explicitly even when the list is empty" convention — never omit a section for the
zero-case.

---

### `helpers/sec_overlay/findings_gate.py` (general-defect disposition)

**Analog:** itself, `validate_findings` (lines 33-96), specifically the receipt-tier stamping
block:
```python
tiers = [t for t in (receipt_tier(s) for s in f.evidence_sources) if t is not None]
stamped_tier = min(tiers) if tiers else None  # 1 outranks 2
if data.get("receipt_tier") != stamped_tier:
    data["receipt_tier"] = stamped_tier
    p.write_text(json.dumps(data))

if f.status.value in ("confirmed", "fixed") and not confirms_alone(f.evidence_sources):
    errors.append(
        f"{f.id}: {f.status.value} finding has no Tier-1 tool receipt "
        f"(sources {f.evidence_sources or 'none'}) — a Tier-2-only match ... "
        f"does not prove reachability; route to needs-deployment-testing"
    )
```
D-12's disposition logic (static-checkable general-defect classes without a Tier-1 receipt ship as
the new `unconfirmed` field; runtime-dependent classes ship `needs-deployment-testing`) should be
added as a new check in this same function, following the identical "compute from
`evidence_sources`, error/annotate if the finding's status doesn't match" idiom — and per D-11/
RESEARCH.md Pitfall 5, the new `unconfirmed` value must land as a NEW field (e.g. on the
review-mode payload dataclass or ledger), never as a `data["status"]` value, since
`FindingStatus` in `models.py` is frozen and has no such member.

## Shared Patterns

### Frozen-contract discipline (D-11)
**Source:** `positioning.py` module docstring (already in context) — "Returns the phase's own
result type rather than a `models.FindingStatus` member — `models.py` is the frozen milestone
contract and has no review-position member."
**Apply to:** `rule_glob.py`'s `ResolvedRule`, `reflection.py`'s verdict/retraction types, and the
general-profile `unconfirmed`/defect-class field — all must be new dataclasses in new modules,
never edits to `models.py`/`evidence.py`.

### Never-silent ledger discipline (D-14/D-15)
**Source:** `report.py:683-716` `write_review_ledger` + the always-render-zero-case idiom cited
above.
**Apply to:** reflection retractions, fail-open (`reflection-skipped`) markers, and any new
drop/decline reason — every one gets a ledger entry and an explicit-zero-case report section,
matching the existing `dropped`/`position_reviews` pattern exactly.

### Mechanical-receipt-is-the-only-confirmer discipline
**Source:** `evidence.py` `confirms_alone`/`receipt_tier` (lines 59-91) + `findings_gate.py` lines
76-82.
**Apply to:** `reflection.py`'s protected-subject veto enforcement (D-16) and the general
profile's gate-bypass allowlist (D-09) — both must be checked in Python code against a fixed
frozenset, never trusted from LLM output text alone.

### Dataclass-with-`__post_init__`-invariant discipline
**Source:** `positioning.py` `PositionResult` (lines 28-76).
**Apply to:** any new result/verdict type in `rule_glob.py` or `reflection.py` that has
decision-dependent field requirements (e.g. a retraction record must carry a reason; a
`needs-position-review`-style decline must not carry a resolved line).

## No Analog Found

None — every file in this phase has a strong existing analog; the closest to "no analog" is the
`rule_docs/*.md` content itself (ported from OCR, an external source, not this codebase), but its
FORMAT analog (`prompt-constants.md`) is present and verified.

## Metadata

**Analog search scope:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/`,
`plugins/sec-overlay/skills/sec-overlay/references/`, `plugins/sec-overlay/skills/sec-overlay/SKILL.md`
**Files scanned:** `rule_matcher.py`, `profile.py`, `exclusions.py`, `cli.py`, `findings_gate.py`,
`evidence.py`, `positioning.py`, `phase_gate.py` (partial, resolution/ledger functions),
`report.py` (partial, `write_review_ledger`), `prompt-constants.md` (partial), `SKILL.md`
(phase-adversary section), `pyproject.toml` (`requires-python` line)
**Pattern extraction date:** 2026-08-18
