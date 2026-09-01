# sec-overlay Constraint Enforcers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every declared constraint in Group 3 an enforcer, so a rule the documentation states is a rule the code rejects.

**Architecture:** Four constraints declare a closed shape today and nothing checks it. `schema.py` ignores `additionalProperties`, so an undeclared finding key passes. `finding.schema.json` declares open types where the Python holds a closed vocabulary, so the two can drift. `evidence.py` treats an unrecognised receipt prefix the same as an honest LLM claim, so a typo silently loses its tier. `agents/trace.md` tells an agent to write `external-boundary`, a value the blocker taxonomy does not contain, and asks for an `open_questions` entry in prose that nothing verifies. Each task closes one gap with a mechanical check: a validator branch, a derivation test, a gate error, or a taxonomy entry.

**Tech Stack:** Python 3.11 (standard library only in `sec_overlay/`), pytest, ruff, ty, `uv` for every command. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** docs/superpowers/specs/2026-09-01-sec-overlay-defect-repairs-design.md (Section 5, Group 3)

## Global Constraints

- Requirement numbering starts at REQ-40. REQ-35 through REQ-39 are unused; the prior spec names a phantom REQ-35, so those five numbers stay retired.
- The test baseline at plugin 1.122.0 is 1766 passing tests. Every task adds tests; no task may reduce the count.
- Run `uv run ruff check sec_overlay/ bench/ tests/` and `uv run ty check` after the group, not after each step.
- One requirement per red/green pair. The red commit lands the failing test; the green commit lands the implementation.
- Carry the requirement id in both commit subjects of a pair.
- Stage explicit paths only. Never `git add -A`, never `git add .`, never `--no-verify`. Run `prek run` before each commit.
- Bump the plugin version in the same commit as any shipping-file change. Everything under `helpers/`, `agents/`, `references/`, `commands/`, and `skills/` is a shipping file, including tests and folder README files.
- Stage the touched folder's `README.md` plus `plugins/sec-overlay/CHANGELOG.md` in every commit. The `doc-update-guard` hook rejects a commit that changes a tracked file in a folder with a README and does not update that README.
- `helpers/tests/test_frozen_contract.py:30-31` pins the sha256 of `models.py` and `evidence.py`. Task 3 edits `evidence.py`, so Task 3 recomputes that digest in the same commit. Recompute with `python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>`. A separate Go port of `evidence.py` exists and needs a hand-sync on any edit.
- Do not merge and do not push. The branch is `docs/sec-overlay-defect-repairs-spec`.
- This plan starts at plugin version `2.1.12`, the version Plan 2 ends on. It ends at `2.2.0`.
- Plan 3 must run after Plan 1. Plan 1's REQ-42 removes `fact-checked` from `evidence.py`'s `VERIFICATION_VALUES` and from `finding.schema.json`'s `verification` enum, and deletes `factcheck.py`. Task 2's derivation test compares that frozenset against that enum, so it fails if Plan 1 has not landed.

## Pre-flight scan

Every `file:line` below was confirmed against HEAD `c3d4af3`, plugin version `1.122.0`. Version numbers in the task steps assume Plans 1 and 2 landed first.

### Corrections to the specification

| # | Spec text | What the source holds |
|---|-----------|----------------------|
| C-1 | REQ-49: "The schema declares it `false` today and the validator ignores it." | `references/finding.schema.json` holds no `additionalProperties` key at all. REQ-49 therefore has two halves: implement the keyword in `schema.py`, and declare `"additionalProperties": false` in the schema file. Two other schema files do declare it — `references/fix-disposition.schema.json:5` in boolean form and `references/scan-profile.schema.json:17` in schema form — but neither file is ever passed to `sec_overlay.schema.validate`. |
| C-2 | REQ-51 cites `references/prompt-constants.md:157-159`. | `:157` opens `## QUALIFIER_PROOF`. The receipt vocabulary lives at `:171-192`, under `## EVIDENCE_VOCABULARY`. Task 3 edits that block. |
| C-3 | REQ-52 cites `agents/trace.md:27-28` and `:34-39`. | The closed blocker taxonomy is inline in the step-3 "not reachable" bullet at `:32-35`. The external-fact `open_questions` branch is `:36-45`. The `external-boundary` instruction is `:47-51`. The verdict shape is `:52`. |
| C-4 | REQ-50: "Generate the `enum` ... from the Python frozensets." | Only two of the five sources are frozensets. `cls` comes from a function (`clsmap.canonical_classes()`, which parses `references/attack-classes.md` at run time), `completeness_tier` from a tuple (`fix_disposition.TIERS:11`), `reachability.blocker` from a tuple (`reachability.BLOCKERS:17`), and `judge_verdict` has no Python source at all — only `agents/judge.md:26-30` and a literal at `calibrate.py:242`. Task 2 creates the missing constant and drops `cls` (ruling R-4). |
| C-5 | REQ-51 acceptance: "A finding whose only source is `llm-claimed:` receives no mechanical tier." | That already holds. `evidence.py:39-50` returns `False` for any source starting `llm-claimed:` or `llm`, so `receipt_tier` returns `None`. The real gap is that an *unrecognised* prefix — a typo, an undeclared tool — is indistinguishable from an honest LLM claim. Task 3 targets that gap instead. |

### Rulings taken against plugin HEAD

| # | Ruling | Why |
|---|--------|-----|
| R-1 | REQ-49 deletes three levers: `render_stale` (`agents/artifact-review.md:38`, `agents/README.md:170`), the `"re-render"` verdict value, and `forced_rerender` (`agents/artifact-review.md:47-48`). | `additionalProperties: false` makes the findings gate reject the key `artifact-review.md:38` instructs an agent to write; 9 of 338 finding files carried it in the measured run. The register's second option is removal, and the levers are unreachable: no helper reads the verdict value, and `phases.py:86` only checks that `kb/gates/artifact-review.json` exists. Same pattern as Plan 2's R-5. Classified `fix:`, patch bump. |
| R-2 | REQ-49's blast radius is bounded. | `sec_overlay.schema.validate` has exactly one production caller, `findings_gate.py:105`, and it only ever validates `finding.schema.json`. `Finding.to_dict()` emits no key the schema does not declare (verified: the difference set is empty; the schema is a superset, declaring nine prompt-written extras — `attacker`, `privilege`, `exact_request`, `exfil_channels`, `library_version`, `refutation`, `negative_results`, `baseline`, `reproduction`). Nested objects stay open unless Task 2 declares their properties. |
| R-3 | Implement only the boolean-`false` form. Document the schema form as unsupported. | The dict form at `scan-profile.schema.json:17` is unreachable from this validator, and reading a truthy dict as "allowed, unchecked" is exactly today's lenient behaviour, so it is not a trap. Testing `is False` keeps the branch to three lines. |
| R-4 | REQ-50 drops `cls` from the enum list. | `findings_gate.py:160-164` already rejects a non-canonical `cls` with a pointed error. A schema enum would be duplicate enforcement, and copying a Markdown-derived vocabulary into JSON creates a second source that needs regeneration on every attack-class edit. Dropping it removes the need for any generator script: the four remaining enums are small stable literals. |
| R-5 | REQ-50 does not edit `models.py`. It extends `helpers/tests/test_contract_lint.py` instead. | `models.py` is byte-pinned; editing it forces a digest recomputation for no functional gain. The acceptance criterion — a frozenset and its enum cannot drift — is met by the existing `test_every_closed_vocabulary_matches_its_schema_enum`, which already derives one from the other. Extending it is rung 2 of the ladder. |
| R-6 | `JUDGE_VERDICTS` lands in `calibrate.py`, not `evidence.py`. | `calibrate.py:242` is its only Python consumer. `evidence.py` is the more natural home for a closed vocabulary and holds the other three, but it is byte-pinned, and putting the constant there would force a second digest recomputation in Task 2 on top of Task 3's. Trade-off accepted: the closed vocabularies now live in two modules; the derivation test names both, so a reader following the test finds both. |
| R-7 | Nested item schemas declare `properties` and types but `require` nothing. | No runtime validator checks `models.OPEN_QUESTION_KEYS` or `models.AFFECTED_SITE_KEYS` against produced entries; only `test_contract_lint.py` reads those tuples. Requiring nested keys would reject real data on no evidence. `history` items require `event` alone — every `history.append` call site writes `event`, and the extras vary (`cls`, `reason`, `field`, `value`, `lockfile_only`, `error`, `judge_verdict`, `from`, `to`). |
| R-8 | REQ-51 adds `unknown_receipts(sources)` rather than raising from `receipt_tier`. | `confirms_alone` and `confidence_for` call `receipt_tier` on arbitrary strings, and `findings_gate.py:122` calls it inside a list comprehension. An exception there aborts the gate instead of reporting an error. A pure function returning the offenders lets the gate append a normal error string. |
| R-9 | REQ-52 keeps the `open_questions` instruction in `agents/trace.md` and adds the gate check beside it. | The spec says "check `open_questions` in the gate instead of requesting it in prose". Deleting the instruction leaves an agent unable to satisfy the new gate. What moves is the enforcement, not the instruction. |
| R-10 | REQ-52 is the `feat:` of the group and takes the minor bump. | It adds a value to a closed taxonomy that agents may now write, and a new gate rejection that can fail a run. |

### Drift rows

| Row | HEAD state | Action |
|-----|-----------|--------|
| `references/finding.schema.json:3` | `"type": "object",` with no `additionalProperties` sibling | Task 1 inserts `"additionalProperties": false,` after it |
| `helpers/tests/test_finding_schema.py:66-69` | `test_unknown_extra_key_is_not_flagged` asserts an extra key validates clean | Task 1 reverses it to assert the key is flagged, and renames it |
| `helpers/tests/test_schema.py:52-55` | `test_unknown_keys_not_in_properties_are_ignored` | Unchanged. Its inline schema declares no `additionalProperties`, so open remains correct behaviour |
| `helpers/tests/test_findings_gate.py:65` | `f.evidence_sources = ["llm-claimed:reasoning", "read:sanity"]` | Task 3 rewrites `read:sanity` to `llm-claimed:read-sanity`. It is the only source string in the tree that Task 3's closed set rejects, and the test's intent — no mechanical receipt — is preserved |
| `references/README.md:285-286` | "The schema declares no `additionalProperties`, so a finding written before this change still validates." | Task 1 rewrites the sentence |
| `helpers/sec_overlay/evidence.py:14-15`, `:28` | `_MECHANICAL` is a literal set; an `assert` checks it equals the union of the two tiers | Task 3 derives `_MECHANICAL` from the union and deletes the now-tautological assert |

### Adjacent findings this plan does not fix

| # | Finding | Why it is deferred |
|---|---------|--------------------|
| A-1 | D-B78-b: `phases.py:122-123` runs `validate` before `trace`, so `agents/validate.md:91`'s ban on an `external-boundary` finding reaching `confirmed` can never fire — the blocker is not yet set when validate reads the finding. | No requirement in Groups 3 through 7 covers phase ordering. Reordering the two phases changes the run's shape and belongs in its own change. |
| A-2 | D-B75-a's cross-field rule: `reachable: true` together with `blocker: "external-boundary"` is a contradiction, and 72 of 78 traced findings in the measured run held it. | REQ-52 asks only for the taxonomy entry and the `open_questions` check. Task 4 makes the prose unambiguous — `external-boundary` leaves `reachable` absent — but adds no gate clause for the contradiction. |
| A-3 | D-B76-a: phase-14 provenance is not recorded. | No requirement covers it. |
| A-4 | `findings_gate.py:105` calls `_load_finding_schema()` once per finding inside the loop, re-reading and re-parsing the JSON each time. | A performance defect, not a correctness one. Fixing it touches the loop Tasks 3 and 4 both edit, and a hoist is easy to get wrong while other edits are in flight. |

## File Structure

**Created:**
- `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py` — behaviour tests for REQ-49, REQ-51, and REQ-52: the validator branch, the removed levers, the unknown-receipt error, and the `external-boundary` gate clause.

**Modified:**
- `helpers/sec_overlay/schema.py` — the `additionalProperties` branch (REQ-49).
- `references/finding.schema.json` — `additionalProperties: false`, five enums, three item schemas (REQ-49, REQ-50, REQ-52).
- `agents/artifact-review.md` — the three deleted levers (REQ-49).
- `agents/README.md` — the Phase 6 row that repeats the `render_stale` lever (REQ-49).
- `references/README.md` — the rewritten `additionalProperties` sentence and the new enum record (REQ-49, REQ-50).
- `helpers/tests/test_finding_schema.py` — the reversed extra-key test (REQ-49).
- `helpers/sec_overlay/calibrate.py` — `JUDGE_VERDICTS` (REQ-50).
- `helpers/tests/test_contract_lint.py` — the extended derivation test and the new item-schema test (REQ-50).
- `helpers/sec_overlay/evidence.py` — derived `_MECHANICAL` and `unknown_receipts` (REQ-51). Byte-pinned.
- `helpers/tests/test_frozen_contract.py` — the recomputed `evidence.py` digest (REQ-51).
- `helpers/sec_overlay/findings_gate.py` — the unknown-receipt error and the `external-boundary` clause (REQ-51, REQ-52).
- `helpers/tests/test_findings_gate.py` — the `read:sanity` fixture (REQ-51).
- `references/prompt-constants.md` — the unknown-prefix rule in `## EVIDENCE_VOCABULARY` (REQ-51).
- `helpers/sec_overlay/reachability.py` — `external-boundary` in `BLOCKERS` (REQ-52).
- `agents/trace.md` — `external-boundary` in the step-3 taxonomy and the `reachable`-absent statement (REQ-52).
- Folder README files under `helpers/sec_overlay/`, `helpers/tests/`, `agents/`, and `references/`, plus `plugins/sec-overlay/CHANGELOG.md` and `plugins/sec-overlay/.claude-plugin/plugin.json`, in every commit that touches the matching folder.

---

## Task 1: REQ-49 — enforce `additionalProperties` and remove the three levers it invalidates

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/schema.py:60-67`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json:3`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/artifact-review.md:36-49`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/README.md:170`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/README.md:285-286`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_finding_schema.py:66-69`

**Interfaces:**
- Consumes: `sec_overlay.schema.validate(data: dict, schema: dict) -> list[str]`, unchanged signature.
- Produces: `validate` now appends `f"{path}.{key}: unknown field"` for every key absent from `properties` when the schema holds `additionalProperties: False`. Tasks 2 and 4 add properties to `finding.schema.json` and rely on this branch rejecting anything they do not declare.

- [ ] **Step 1: Write the failing validator tests**

Create `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`:

```python
"""Tests for the constraint enforcers of Group 3 (REQ-49 through REQ-52)."""

import json
from pathlib import Path

from sec_overlay.schema import validate

SKILL = Path(__file__).resolve().parents[2]
SCHEMA = SKILL / "references" / "finding.schema.json"
GOLDEN = SKILL / "helpers" / "fixtures" / "golden_raw_finding.json"


def test_additional_properties_false_rejects_an_unknown_key():
    """REQ-49: a closed object reports every key no property declares."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"a": {"type": "string"}},
    }
    errors = validate({"a": "x", "b": 1}, schema)
    assert any("b" in e and "unknown field" in e for e in errors)


def test_additional_properties_false_accepts_a_declared_key():
    """REQ-49: closing the object must not reject a declared key."""
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"a": {"type": "string"}},
    }
    assert validate({"a": "x"}, schema) == []


def test_additional_properties_dict_form_stays_permissive():
    """REQ-49: only the boolean-false form closes an object (ruling R-3)."""
    schema = {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "properties": {"a": {"type": "string"}},
    }
    assert validate({"a": "x", "b": 1}, schema) == []


def test_finding_schema_closes_the_object():
    """REQ-49: the finding schema declares itself closed."""
    assert json.loads(SCHEMA.read_text())["additionalProperties"] is False


def test_render_stale_is_rejected_by_the_finding_schema():
    """REQ-49: the key the deleted lever wrote no longer validates."""
    data = json.loads(GOLDEN.read_text())
    data["render_stale"] = True
    errors = validate(data, json.loads(SCHEMA.read_text()))
    assert any("render_stale" in e for e in errors)


def test_no_prompt_offers_a_render_stale_lever():
    """REQ-49: no agent prompt instructs an agent to write a rejected key."""
    for path in sorted((SKILL / "agents").glob("*.md")):
        assert "render_stale" not in path.read_text(), f"{path.name} still offers render_stale"


def test_artifact_review_verdict_vocabulary_drops_the_rerender_path():
    """REQ-49: the unreachable re-render verdict and its id list are gone."""
    text = (SKILL / "agents" / "artifact-review.md").read_text()
    assert '"verdict": "clean" | "downgrades"' in text
    assert "forced_rerender" not in text
```

- [ ] **Step 2: Reverse the test that asserts the old behaviour**

In `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_finding_schema.py`, replace lines 66-69:

```python
def test_unknown_extra_key_is_not_flagged():
    data = json.loads(GOLDEN_PATH.read_text())
    data["some_future_field"] = "value"
    assert validate(data, _schema()) == []
```

with:

```python
def test_unknown_extra_key_is_flagged():
    """REQ-49: the schema is closed, so an undeclared key is an error."""
    data = json.loads(GOLDEN_PATH.read_text())
    data["some_future_field"] = "value"
    assert any("some_future_field" in e for e in validate(data, _schema()))
```

- [ ] **Step 3: Run the new tests to verify they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_constraint_enforcer.py tests/test_finding_schema.py::test_unknown_extra_key_is_flagged -v
```

Expected: `test_additional_properties_false_rejects_an_unknown_key`, `test_finding_schema_closes_the_object`, `test_render_stale_is_rejected_by_the_finding_schema`, `test_no_prompt_offers_a_render_stale_lever`, `test_artifact_review_verdict_vocabulary_drops_the_rerender_path`, and `test_unknown_extra_key_is_flagged` all FAIL. `test_additional_properties_false_accepts_a_declared_key` and `test_additional_properties_dict_form_stays_permissive` PASS — they describe behaviour the lenient validator already has.

- [ ] **Step 4: Commit the red state**

Record the reversal and the new file in `helpers/tests/README.md` and in `plugins/sec-overlay/CHANGELOG.md` under `## Unreleased`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.13"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_finding_schema.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(schema): pin the REQ-49 closed-object contract"
```

- [ ] **Step 5: Implement the validator branch**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/schema.py`, replace `_validate_object_fields`:

```python
def _validate_object_fields(data: dict, schema: dict, path: str, errors: list[str]) -> None:
    for key in schema.get("required", []):
        if key not in data:
            errors.append(f"{path}.{key}: missing required field")
    properties = schema.get("properties", {})
    for key, prop_schema in properties.items():
        if key in data:
            _validate_value(data[key], prop_schema, f"{path}.{key}", errors)
    if schema.get("additionalProperties") is False:
        for key in data:
            if key not in properties:
                errors.append(f"{path}.{key}: unknown field")
```

Then extend the module docstring's keyword list at `:3-7` to name the new keyword and its one supported form:

```python
``additionalProperties`` is honoured only in its boolean-``false`` form, which closes
the object. The schema form (a subschema applied to undeclared keys) is not supported;
a truthy value leaves the object open and unchecked.
```

- [ ] **Step 6: Close the finding schema**

In `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json`, insert one line after `"type": "object",` on line 3:

```json
  "additionalProperties": false,
```

- [ ] **Step 7: Delete the three levers**

In `plugins/sec-overlay/skills/sec-overlay/agents/artifact-review.md`, replace the `## Output — the safety contract (§3.3)` opening list:

```markdown
Adversarial reasoning ALONE may:
- demote a claim's rendered severity (record `history` event `artifact-review:downgrade`
  with a `file:line` citation and one-line reason), or
- mark a finding `render_stale: true` to FORCE a re-render (the orchestrator re-runs
  `report`), or
- add an `open_questions` entry when a rendered claim needs a fact you cannot settle.
```

with:

```markdown
Adversarial reasoning ALONE may:
- demote a claim's rendered severity (record `history` event `artifact-review:downgrade`
  with a `file:line` citation and one-line reason), or
- add an `open_questions` entry when a rendered claim needs a fact you cannot settle.
```

Then replace the verdict shape:

```markdown
`{"verdict": "clean" | "re-render" | "downgrades", "notes": [...], "downgraded": [ids],
"forced_rerender": [ids]}`. Return a one-line summary. You do not write `report.md`.
```

with:

```markdown
`{"verdict": "clean" | "downgrades", "notes": [...], "downgraded": [ids]}`. Return a
one-line summary. You do not write `report.md`.
```

In `plugins/sec-overlay/skills/sec-overlay/agents/README.md:170`, replace the clause

```
reasoning alone may demote severity (with a `file:line` cite), mark a finding `render_stale: true` to force a re-render, or add an `open_questions` entry
```

with

```
reasoning alone may demote severity (with a `file:line` cite) or add an `open_questions` entry
```

- [ ] **Step 8: Rewrite the references sentence**

In `plugins/sec-overlay/skills/sec-overlay/references/README.md`, replace lines 285-286:

```
The schema declares no
`additionalProperties`, so a finding written before this change still validates.
```

with:

```
The schema sets `additionalProperties: false` (REQ-49), so a key no property declares is a
validation error at the findings gate, not silent overflow. Adding a prompt-written field
means declaring it here first.
```

- [ ] **Step 9: Run the full suite**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
```

Expected: every test passes. Watch for a failure in `tests/test_artifact_review.py` or `tests/test_phases.py` if either asserts the old verdict vocabulary; if one does, update the assertion to the two-value form in this step.

- [ ] **Step 10: Commit the green state**

Record the closed schema, the deleted levers, and the new validator keyword in `helpers/sec_overlay/README.md`, `references/README.md`, `agents/README.md`, `helpers/tests/README.md`, and `plugins/sec-overlay/CHANGELOG.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.14"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/schema.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/artifact-review.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(schema): close the finding object (REQ-49)"
```

---

## Task 2: REQ-50 — derive every schema enum and item shape from its code source

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py:29-30`, `:242`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json:33`, `:39`, `:58-64`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/README.md`

**Interfaces:**
- Consumes: `sec_overlay.evidence.VERIFICATION_VALUES`, `sec_overlay.evidence.RUNTIME_DISPOSITIONS`, `sec_overlay.fix_disposition.TIERS`, `sec_overlay.reachability.BLOCKERS`, `sec_overlay.models.OPEN_QUESTION_KEYS`, `sec_overlay.models.AFFECTED_SITE_KEYS`. The `additionalProperties: false` branch from Task 1.
- Produces: `sec_overlay.calibrate.JUDGE_VERDICTS: frozenset[str]` — the closed judge vocabulary, `{"uphold", "severity-inflated", "downgrade"}`. Task 4 adds `"external-boundary"` to `reachability.BLOCKERS` and to the `reachability.blocker` enum this task creates; the derivation test then holds both in step.

- [ ] **Step 1: Write the failing derivation tests**

In `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`, extend the imports with

```python
from sec_overlay.calibrate import JUDGE_VERDICTS
from sec_overlay.fix_disposition import TIERS
from sec_overlay.models import AFFECTED_SITE_KEYS, OPEN_QUESTION_KEYS
from sec_overlay.reachability import BLOCKERS
```

and replace `test_every_closed_vocabulary_matches_its_schema_enum` with:

```python
def test_every_closed_vocabulary_matches_its_schema_enum():
    """Each code constant with a schema counterpart must equal that enum (REQ-50)."""
    props = json.loads(SCHEMA.read_text())["properties"]
    for field, allowed in (
        ("verification", VERIFICATION_VALUES),
        ("runtime_disposition", RUNTIME_DISPOSITIONS),
        ("completeness_tier", frozenset(TIERS)),
        ("judge_verdict", JUDGE_VERDICTS),
        ("receipt_tier", frozenset({1, 2})),
    ):
        assert "enum" in props[field], f"{field} has no schema enum"
        assert set(props[field]["enum"]) == allowed | {None}, f"{field} drifted"
    blocker = props["reachability"]["properties"]["blocker"]
    assert set(blocker["enum"]) == frozenset(BLOCKERS) | {None}, "reachability.blocker drifted"


def test_nested_item_schemas_declare_their_published_keys():
    """``open_questions``, ``affected_sites``, and ``history`` items are typed (REQ-50)."""
    props = json.loads(SCHEMA.read_text())["properties"]
    for field, keys in (
        ("open_questions", OPEN_QUESTION_KEYS),
        ("affected_sites", AFFECTED_SITE_KEYS),
    ):
        item = props[field]["items"]
        assert set(item["properties"]) == set(keys), f"{field} item schema drifted"
        assert "required" not in item, f"{field} items must require nothing (ruling R-7)"
    history = props["history"]["items"]
    assert history["required"] == ["event"], "history items must require event"
    assert set(history["properties"]) == {"event"}, "history item schema drifted"
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_contract_lint.py -k "closed_vocabulary or nested_item" -v
```

Expected: both FAIL. The first fails at import with `ImportError: cannot import name 'JUDGE_VERDICTS'`; after Step 3 defines it, it fails on `completeness_tier has no schema enum`.

- [ ] **Step 3: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.15"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(contract): pin the REQ-50 enum derivation"
```

- [ ] **Step 4: Publish the judge vocabulary**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py`, add the constant beside `_EXTERNAL_CAP` at `:29`:

```python
JUDGE_VERDICTS = frozenset({"uphold", "severity-inflated", "downgrade"})
_DOWNGRADE_VERDICTS = frozenset({"severity-inflated", "downgrade"})
```

Then replace the literal at `:242`:

```python
        if f.judge_verdict in ("severity-inflated", "downgrade"):
```

with:

```python
        if f.judge_verdict in _DOWNGRADE_VERDICTS:
```

- [ ] **Step 5: Declare the enums and item schemas**

In `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json`, replace line 33:

```json
    "history": {"type": "array", "items": {"type": "object"}},
```

with:

```json
    "history": {"type": "array", "items": {
      "type": "object",
      "required": ["event"],
      "properties": {"event": {"type": "string"}}
    }},
```

Replace line 39:

```json
    "completeness_tier": {"type": ["string", "null"]},
```

with:

```json
    "completeness_tier": {
      "type": ["string", "null"],
      "enum": ["FULL", "MITIGATION", "WORKAROUND", null]
    },
```

Replace lines 58-59:

```json
    "reachability": {"type": ["object", "null"]},
    "judge_verdict": {"type": ["string", "null"]},
```

with:

```json
    "reachability": {
      "type": ["object", "null"],
      "properties": {
        "reachable": {"type": "boolean"},
        "blocker": {
          "type": ["string", "null"],
          "enum": ["sanitizer", "auth_check", "input_validation", "dead_code",
                   "feature_flag", "other", null]
        },
        "chain": {"type": "array", "items": {"type": "string"}}
      }
    },
    "judge_verdict": {
      "type": ["string", "null"],
      "enum": ["uphold", "severity-inflated", "downgrade", null]
    },
```

Replace line 61:

```json
    "open_questions": {"type": "array", "items": {"type": "object"}},
```

with:

```json
    "open_questions": {"type": "array", "items": {
      "type": "object",
      "properties": {
        "question": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "who_to_ask_or_check": {"type": "string"}
      }
    }},
```

Replace line 63:

```json
    "affected_sites": {"type": "array", "items": {"type": "object"}},
```

with:

```json
    "affected_sites": {"type": "array", "items": {
      "type": "object",
      "properties": {
        "id": {"type": "string"},
        "file": {"type": "string"},
        "line": {"type": "integer"}
      }
    }},
```

Replace line 64:

```json
    "receipt_tier": {"type": ["integer", "null"]},
```

with:

```json
    "receipt_tier": {"type": ["integer", "null"], "enum": [1, 2, null]},
```

Do not add an enum for `cls` (ruling R-4). Do not add `additionalProperties: false` to any nested item schema: `history` extras vary by event kind, and `reachability` carries `chain` alongside future fields.

- [ ] **Step 6: Run the suite**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
```

Expected: every test passes. `tests/test_finding_schema.py::test_schema_accepts_cluster_fields` passes an `affected_sites` entry of `{"id": "F-2", "file": "b.py", "line": 5}`, which the new item schema declares in full.

- [ ] **Step 7: Commit the green state**

Add a `references/README.md` paragraph naming each new enum and its Python source, so a maintainer editing `TIERS`, `BLOCKERS`, or `JUDGE_VERDICTS` knows the schema follows. Record the change in `helpers/sec_overlay/README.md` and `plugins/sec-overlay/CHANGELOG.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.16"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(schema): derive every finding enum from code (REQ-50)"
```

---

## Task 3: REQ-51 — make the receipt frozensets the single source and reject an unknown prefix

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py:14-28`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py:12-17`, `:126`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md:171-192`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_frozen_contract.py:30-31`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py:65`

**Interfaces:**
- Consumes: `sec_overlay.evidence.TIER1_RECEIPTS`, `sec_overlay.evidence.TIER2_RECEIPTS`.
- Produces: `sec_overlay.evidence.unknown_receipts(sources: list[str]) -> list[str]` — the sources that name a receipt prefix outside `TIER1_RECEIPTS | TIER2_RECEIPTS` and are not `llm`-namespaced, in input order. `findings_gate.validate_findings` appends one error per returned source.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`:

```python
def test_mechanical_set_is_derived_from_the_two_tiers():
    """REQ-51: the tiers are the single source; no literal can drift from them."""
    from sec_overlay import evidence

    assert evidence._MECHANICAL == evidence.TIER1_RECEIPTS | evidence.TIER2_RECEIPTS


def test_unknown_receipts_reports_an_undeclared_prefix():
    """REQ-51: a typo or an undeclared tool is an error, not a silent tier drop."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["semgrp:a.py:1"]) == ["semgrp:a.py:1"]


def test_unknown_receipts_passes_a_declared_prefix():
    """REQ-51: both tiers stay clean."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["semgrep:a.py:1", "ripgrep:b.py:2"]) == []


def test_unknown_receipts_passes_an_llm_claim():
    """REQ-51: an llm-namespaced source claims no receipt, so it is not an offender."""
    from sec_overlay.evidence import unknown_receipts

    assert unknown_receipts(["llm-claimed:reasoning", "llm-corroborated"]) == []


def test_gate_rejects_a_finding_with_an_undeclared_receipt_prefix(tmp_path):
    """REQ-51: the gate reports the offender instead of dropping its tier."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.models import Finding, FindingStatus, Severity
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = Finding(id="F-0002", rule_id="r", cls="sqli", status=FindingStatus.RAW,
                severity=Severity.HIGH, file="app.py", line=18, message="m",
                dataflow=["a -> b"], evidence="e")
    f.evidence_sources = ["semgrp:app.py:18"]
    write_findings(ws, [f])
    errors = validate_findings(ws)
    assert any("semgrp:app.py:18" in e and "closed set" in e for e in errors)
```

- [ ] **Step 2: Fix the one fixture the closed set rejects**

In `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py:65`, replace

```python
    f.evidence_sources = ["llm-claimed:reasoning", "read:sanity"]  # no mechanical receipt
```

with

```python
    f.evidence_sources = ["llm-claimed:reasoning", "llm-claimed:read-sanity"]  # no receipt
```

`read:sanity` is the only source string in the tree that Task 3's closed set rejects. The test's intent — a confirmed finding with no mechanical receipt — is unchanged.

- [ ] **Step 3: Run the new tests to verify they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_constraint_enforcer.py -k "mechanical or unknown_receipts or undeclared_receipt" -v
```

Expected: `test_mechanical_set_is_derived_from_the_two_tiers` PASSES — the current literal happens to equal the union, which is what the deleted assert proves. The four others FAIL with `ImportError: cannot import name 'unknown_receipts'` or a missing gate error.

- [ ] **Step 4: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.17"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(evidence): pin the REQ-51 receipt-prefix contract"
```

- [ ] **Step 5: Derive the mechanical set and add `unknown_receipts`**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py`, delete the literal at `:14-15` and move the derivation below the two tiers. The block that today reads

```python
_MECHANICAL = {"semgrep", "codeql", "ast-grep", "tree-sitter", "ripgrep",
               "structural-index", "secrets", "sca", "dependency-catalog"}

TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
```

becomes

```python
TIER1_RECEIPTS = frozenset({"codeql", "semgrep", "sca", "secrets"})
```

and the assert at `:28`

```python
assert TIER1_RECEIPTS | TIER2_RECEIPTS == _MECHANICAL, "receipt tiers must partition _MECHANICAL"
```

becomes

```python
_MECHANICAL = TIER1_RECEIPTS | TIER2_RECEIPTS
```

Keep every other line, including the Tier-2 comment and the three other vocabularies, in place. Then add the new function after `receipt_tier`:

```python
def unknown_receipts(sources: list[str]) -> list[str]:
    """Return the sources that claim a receipt prefix outside the closed set.

    An ``llm``-namespaced source claims no receipt and never appears here. Every
    other source names a tool, so a prefix in neither receipt tier is a contract
    violation — a typo or an undeclared tool — not a source with no tier. Callers
    report the result; this function raises nothing, because ``receipt_tier`` runs
    inside comprehensions that an exception would abort.

    Args:
        sources: Evidence source strings, each ``<prefix>:<detail>`` or a bare prefix.

    Returns:
        The offending sources, in input order. Empty when every source is declared.

    Example:
        >>> unknown_receipts(["semgrp:a.py:1", "llm-claimed:reasoning"])
        ['semgrp:a.py:1']
    """
    return [
        s
        for s in sources
        if not s.startswith(("llm-claimed:", "llm")) and s.split(":", 1)[0] not in _MECHANICAL
    ]
```

- [ ] **Step 6: Report the offender at the gate**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py`, add `unknown_receipts` to the `from sec_overlay.evidence import (...)` block at `:12-17`, keeping alphabetical order:

```python
from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    SHIPPING_STATUSES,
    confirms_alone,
    receipt_tier,
    unknown_receipts,
)
```

Then insert the clause immediately after the receipt-tier stamp block, which ends at `:126` with `p.write_text(json.dumps(data))`:

```python
        for source in unknown_receipts(f.evidence_sources):
            errors.append(
                f"{f.id}: evidence source {source!r} names a receipt prefix outside the "
                f"closed set (see references/prompt-constants.md, EVIDENCE_VOCABULARY); "
                f"use a declared receipt or namespace the claim llm-claimed:"
            )
```

- [ ] **Step 7: Publish the rule**

In `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md`, append one bullet to the `## EVIDENCE_VOCABULARY` block, after the `verification` bullet:

```markdown
- A source whose prefix is in neither receipt tier, and which is not `llm-claimed:` or
  `llm-corroborated`, is rejected at the findings gate. There is no third category: name a
  declared receipt, or namespace the claim `llm-claimed:`.
```

- [ ] **Step 8: Recompute the frozen-contract digest**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
python3 -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" sec_overlay/evidence.py
```

Write the printed digest into `tests/test_frozen_contract.py:30-31`, replacing the `evidence.py` value only. Leave the `models.py` pin untouched — no task in this plan edits `models.py` (ruling R-5). A separate Go port of `evidence.py` exists; hand-sync `unknown_receipts` and the derived `_MECHANICAL` into it, or record the divergence in `helpers/sec_overlay/README.md` if the port is out of scope for this branch.

- [ ] **Step 9: Run the suite**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
```

Expected: every test passes. A failure naming a source string other than `read:sanity` means a fixture the census missed; namespace it `llm-claimed:` and note it in the commit body.

- [ ] **Step 10: Commit the green state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.18"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_frozen_contract.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(evidence): reject an undeclared receipt prefix (REQ-51)"
```

---

## Task 4: REQ-52 — admit `external-boundary` to the taxonomy and enforce its open question

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reachability.py:17`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` (before `record_stage`)
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json` (`reachability.blocker` enum)
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/trace.md:32-35`, `:47-51`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`

**Interfaces:**
- Consumes: `sec_overlay.reachability.BLOCKERS`, `sec_overlay.models.OPEN_QUESTION_KEYS`, and Task 2's `reachability.blocker` enum, which this task extends by one value.
- Produces: no new public symbol. `findings_gate.validate_findings` gains one error string: an `external-boundary` finding with no well-formed `open_questions` entry.

- [ ] **Step 1: Write the failing tests**

Append to `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py`:

```python
def _external_boundary_finding():
    from sec_overlay.models import Finding, FindingStatus, Severity

    f = Finding(id="F-0002", rule_id="r", cls="sqli", status=FindingStatus.RAW,
                severity=Severity.HIGH, file="app.py", line=18, message="m",
                dataflow=["a -> b"], evidence="e")
    f.reachability = {"blocker": "external-boundary", "chain": ["app.py:18"]}
    return f


def test_external_boundary_is_in_the_blocker_taxonomy():
    """REQ-52: the value agents are told to write is a declared blocker."""
    from sec_overlay.reachability import BLOCKERS

    assert "external-boundary" in BLOCKERS


def test_blocker_of_no_longer_coerces_external_boundary():
    """REQ-52: an undeclared value was silently rewritten to 'other'."""
    from sec_overlay.reachability import blocker_of

    f = _external_boundary_finding()
    f.reachability["reachable"] = False
    assert blocker_of(f) == "external-boundary"


def test_trace_prompt_declares_external_boundary_in_the_taxonomy():
    """REQ-52: the prose taxonomy and the code taxonomy agree."""
    text = (SKILL / "agents" / "trace.md").read_text()
    assert "`external-boundary`" in text.split("3. Decide reachability:")[1].split("4. Write")[0]


def test_gate_rejects_external_boundary_without_an_open_question(tmp_path):
    """REQ-52: the prose asked for the entry; the gate now requires it."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_external_boundary_finding()])
    errors = validate_findings(ws)
    assert any("external-boundary" in e and "open_questions" in e for e in errors)


def test_gate_rejects_an_incomplete_open_question(tmp_path):
    """REQ-52: an entry missing who to ask settles nothing."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = _external_boundary_finding()
    f.open_questions = [{"question": "does policy X apply?", "why_it_matters": "gates the sink"}]
    write_findings(ws, [f])
    errors = validate_findings(ws)
    assert any("external-boundary" in e and "open_questions" in e for e in errors)


def test_gate_accepts_external_boundary_with_a_full_open_question(tmp_path):
    """REQ-52: a complete entry passes."""
    from sec_overlay.findings_gate import validate_findings
    from sec_overlay.workspace import Workspace, write_findings

    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    f = _external_boundary_finding()
    f.open_questions = [{
        "question": "does @lume/account-portal-core check ownership?",
        "why_it_matters": "it is the only control between the route and the sink",
        "who_to_ask_or_check": "ask the platform team or read the published package",
    }]
    write_findings(ws, [f])
    assert validate_findings(ws) == []
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_constraint_enforcer.py -k "external_boundary or blocker_of or trace_prompt" -v
```

Expected: `test_external_boundary_is_in_the_blocker_taxonomy`, `test_blocker_of_no_longer_coerces_external_boundary`, `test_trace_prompt_declares_external_boundary_in_the_taxonomy`, `test_gate_rejects_external_boundary_without_an_open_question`, and `test_gate_rejects_an_incomplete_open_question` FAIL. `test_gate_accepts_external_boundary_with_a_full_open_question` PASSES — the gate has no clause yet, so nothing rejects it.

- [ ] **Step 3: Commit the red state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.1.19"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_constraint_enforcer.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "test(trace): pin the REQ-52 external-boundary contract"
```

- [ ] **Step 4: Admit the value to the taxonomy**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reachability.py:17`, replace

```python
BLOCKERS = ("sanitizer", "auth_check", "input_validation", "dead_code", "feature_flag", "other")
```

with

```python
BLOCKERS = ("sanitizer", "auth_check", "input_validation", "dead_code", "feature_flag",
            "external-boundary", "other")
```

In `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json`, extend the `reachability.blocker` enum Task 2 created so the derivation test stays green:

```json
        "blocker": {
          "type": ["string", "null"],
          "enum": ["sanitizer", "auth_check", "input_validation", "dead_code",
                   "feature_flag", "external-boundary", "other", null]
        },
```

- [ ] **Step 5: Add the gate clause**

In `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py`, extend the models import to

```python
from sec_overlay.models import Finding, OPEN_QUESTION_KEYS
```

and insert the clause immediately before `record_stage(ws, "findings-gate")`, after the shipping-impact check:

```python
        if (f.reachability or {}).get("blocker") == "external-boundary" and not any(
            isinstance(q, dict) and all(str(q.get(k, "")).strip() for k in OPEN_QUESTION_KEYS)
            for q in f.open_questions
        ):
            errors.append(
                f"{f.id}: reachability.blocker is 'external-boundary' but the finding "
                f"carries no complete open_questions entry (keys "
                f"{list(OPEN_QUESTION_KEYS)}); name the person, team, or system that can "
                f"settle the external fact"
            )
```

- [ ] **Step 6: State the value in the prompt taxonomy**

In `plugins/sec-overlay/skills/sec-overlay/agents/trace.md`, replace the closed list in the step-3 "not reachable" bullet:

```markdown
     MUST cite the specific `file:line` blocker and classify it: `sanitizer` | `auth_check` |
     `input_validation` | `dead_code` | `feature_flag` | `other`. An INCOMPLETE sanitizer is NOT
     a blocker — only a control effective on every path counts.
```

with

```markdown
     MUST cite the specific `file:line` blocker and classify it: `sanitizer` | `auth_check` |
     `input_validation` | `dead_code` | `feature_flag` | `external-boundary` | `other`. An
     INCOMPLETE sanitizer is NOT a blocker — only a control effective on every path counts.
     `external-boundary` is the one blocker that does not assert `reachable: false`; see below.
```

Then extend the `external-boundary` paragraph at `:47-51`. Replace

```markdown
     When a sink resolves into a dependency whose source is not in the ingested set
     (check `kb/scan-scope.json`), set `reachability.blocker = "external-boundary"` and
     record the package name in `preconditions` (e.g. "ownership check in
     @lume/account-portal-core"). Do not mark the finding reachable or confirmed from
     source you cannot read.
```

with

```markdown
     When a sink resolves into a dependency whose source is not in the ingested set
     (check `kb/scan-scope.json`), set `reachability.blocker = "external-boundary"`, leave
     `reachable` absent, and record the package name in `preconditions` (e.g. "ownership
     check in @lume/account-portal-core"). Do not mark the finding reachable or confirmed
     from source you cannot read. The findings gate rejects an `external-boundary` finding
     that carries no complete `open_questions` entry, so add the entry described above in
     the same pass.
```

- [ ] **Step 7: Run the suite and the linters**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Expected: every test passes, ruff reports no finding, ty reports no error. If an existing reachability test asserts that `blocker_of` returns `"other"` for `external-boundary`, that test encoded the defect — update it to expect `"external-boundary"` and say so in the commit body.

- [ ] **Step 8: Commit the green state**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.2.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reachability.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/trace.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(trace): enforce the external-boundary question (REQ-52)"
```

---

## Self-review

**1. Specification coverage.** Group 3 holds four requirements and every one has a task. REQ-49 is Task 1, in two halves because the spec's premise is wrong (C-1): the validator branch plus the schema declaration, with the three levers the closure invalidates removed under ruling R-1. REQ-50 is Task 2, minus `cls` (R-4) and without a `models.py` edit (R-5); the "generate from the frozensets" wording is satisfied by derivation in the test rather than by a generator script, because four of the five sources are literals small enough to read (C-4). REQ-51 is Task 3; its stated acceptance criterion already passes (C-5), so the task enforces the gap behind it — an unrecognised prefix — through `unknown_receipts` (R-8). REQ-52 is Task 4, in three parts: the taxonomy entry, the prose statement, and the gate clause, keeping the prose instruction the spec's wording could be read as deleting (R-9). Four requirements, four red/green pairs, eight commits, 2.1.12 to 2.2.0.

**2. Placeholder scan.** No step says TBD, TODO, "add error handling", or "similar to Task N". Every code step holds the literal text to write, including the full docstring for `unknown_receipts` and the exact JSON replacement for each of the seven schema lines Task 2 touches. Two steps name a conditional edit rather than a fixed one — Task 1 Step 9 and Task 4 Step 7, each covering a test that may encode the old behaviour — and both name the expected assertion and the file to look in, so neither is a blank to fill.

**3. Type consistency.** `unknown_receipts(sources: list[str]) -> list[str]` is declared once in Task 3's Interfaces block and called with that signature in Task 3 Step 6. `JUDGE_VERDICTS` is a `frozenset[str]` produced in Task 2 Step 4 and consumed in Task 2 Step 1's derivation test with `allowed | {None}`, which requires a set on the left. `BLOCKERS` stays a tuple in Task 4 Step 4, and the test wraps it in `frozenset(...)` before the set comparison. `OPEN_QUESTION_KEYS` is a tuple of three strings; Task 4 Step 5 iterates it and formats it with `list(...)` for the error text. `reachability` is `dict | None` throughout, so both readers use `(f.reachability or {})`.

**4. Ordering.** Task 1 must run first: Tasks 2 and 4 add properties to `finding.schema.json` whose enforcement depends on the `additionalProperties` branch, and Task 1's lever removal must land before the closed schema starts rejecting `render_stale` in a real run. Task 2 must precede Task 4, because Task 4 extends the `reachability.blocker` enum Task 2 creates; running Task 4 first leaves the derivation test comparing against an absent enum. Task 3 is independent of Tasks 2 and 4 but is placed third so the single `evidence.py` digest recomputation sits in one commit. The whole plan runs after Plan 1, whose REQ-42 removes the `fact-checked` value that Task 2's `verification` derivation compares (Global Constraints, final bullet).
