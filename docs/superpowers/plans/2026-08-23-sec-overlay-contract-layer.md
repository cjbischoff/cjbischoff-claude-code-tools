# sec-overlay Contract Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five contract-layer requirements (REQ-02, REQ-18, REQ-07, REQ-10, REQ-32) so the finding schema, the code constants, `references/prompt-constants.md`, and the agent prompts state one contract, and a lint fails on any drift.

**Architecture:** Code owns each closed vocabulary as a module constant. `references/finding.schema.json` restates it as a JSON `enum`. `references/prompt-constants.md` restates it as prose for the agents. A new lint module reads the code constants and asserts the schema and the document agree. `Finding.from_dict` rejects an out-of-enum value at load, so a bad value cannot travel to a later phase.

**Tech Stack:** Python 3, standard library only. pytest for tests. `ruff` for lint, `ty` for types. No new dependency.

**Spec:** `docs/superpowers/specs/2026-08-23-sec-overlay-improvements-design.md`

## Global Constraints

- The plugin core is stdlib-only. Dev dependencies are `pytest`, `ruff`, and `ty` only. Do not add a dependency.
- Do not invent scope. Build only what the requirements document defines.
- One requirement per commit pair. Each pair is a red commit (the failing test) then a green commit (the change). Both subjects carry the requirement id.
- Never commit to `main`. The branch is `feat/sec-overlay-improvements`.
- Conventional Commits. Subject under 50 characters. Stage explicit paths only. Never `git add -A`, `git add .`, `git commit -a`, or `--no-verify`.
- No `Co-Authored-By` trailer.
- Run `prek run` before every commit.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `version` in the same commit as any shipping-file change. A breaking change bumps major, `feat` bumps minor, every other type bumps patch. Everything under `helpers/`, `agents/`, and `references/` is a shipping file, including a test file and a folder `README.md`.
- The prek hook requires the immediate folder's `README.md` staged in the same commit. `helpers/sec_overlay/` needs `helpers/README.md`. `helpers/tests/` needs `helpers/tests/README.md`. `references/` needs `references/README.md`. `agents/` needs `agents/README.md`.
- Add an entry to `plugins/sec-overlay/CHANGELOG.md` under `## Unreleased` in every green commit.
- Functions stay under 100 lines with cyclomatic complexity under 8 and at most five positional parameters. Public functions carry Google-style docstrings.
- Prose written to a file follows ASD-STE100. One instruction per sentence. Maximum 20 words for an instruction.
- Run the full suite (`uv run pytest -q` from `plugins/sec-overlay/skills/sec-overlay/helpers/`) after the last task in this plan. The baseline is 1619 passed.
- `rtk` rewrites shell commands. An `rg`, `fd`, or `find` call can return corrupted output. Use the `Read` tool for an existence check or exact-string evidence.

## Conflicts recorded before build

Three conflicts between the requirements document and the current code. Each has a resolution below. Do not resolve one a different way without saying so.

1. **REQ-32 lint property (c) cannot pass in this group.** Property (c) asserts every `{{TOKEN}}` in a prompt is in the substitution map. `driver.py:132-133` names only `{{TARGET}}`, `{{WORKSPACE}}`, and `{{SHA}}`; `:128` adds `{{ATTACK_CLASS}}`. Prompts also use `{{OVERLAY_ROOT}}`, `{{HELPERS_DIR}}`, and `{{FP_FEEDBACK}}`. Adding those three is REQ-08, which the Part E sequencing places in group 2. **Resolution:** Task 5 lands lint properties (a), (b), (d), (e), and (f) and exports `DISPATCH_TOKENS` from `driver.py`. Property (c) lands in REQ-08's commit in group 2, as the requirements document itself directs ("Test: covered by REQ-32 (N-5)"). Task 5 leaves a named gap, not a silent one.

2. **REQ-10's stated test is not implementable.** The requirements document says REQ-10's test is "covered by REQ-32 (required-block list matches the class-gate requirement)". No class gate requires `QUALIFIER_PROOF`. A search of `helpers/` for `QUALIFIER_PROOF` returns zero hits; the string appears only in `agents/architecture.md`, `agents/recon.md`, `agents/context-ingest.md`, `references/README.md`, and `references/prompt-constants.md`. **Resolution:** REQ-10 gets a direct test. Lint property (f) asserts that every prompt which imports `SEVERITY_PRECONDITION` also imports `QUALIFIER_PROOF`. `agents/threat-model.md` imports `SEVERITY_PRECONDITION` today, so the property fails red and REQ-10's one-line edit turns it green.

3. **REQ-32 lint property (b) exposes real drift in the document.** `references/prompt-constants.md:59` states "The harness caps `risk_score` by the precondition count deterministically". `calibrate.py:106-122` caps by precondition **weight**, not count: `w<1` gives 10, `1<=w<2` gives 8, `2<=w<3` gives 7, and `w>=3` gives 5. The document is wrong. **Resolution:** Task 5 exports the cap table from `calibrate.py` as `PRECONDITION_CAPS` and corrects `prompt-constants.md:59` to state the weight thresholds. The band guidance at `:55` is prompt policy with no code counterpart, so the lint does not check it. Leave `:55` alone.

## Design deviation from the requirements document

REQ-02 at requirements-document line 222-224 says: "Enforce at finding load in `models.py`, not only at the gate. No `jsonschema` dependency exists; do not add one. Hand-roll the enum check by reading the allowed values from the schema JSON, so the schema stays the single source. (Assumption, reversible.)"

This plan reverses that assumption. The allowed values live in `evidence.py` as code constants; the schema restates them; the Task 5 lint binds the two. Three reasons:

1. `evidence.py:23` already holds `RUNTIME_DISPOSITIONS` as a code constant. The schema is not the single source today, so the stated assumption does not describe the tree.
2. `models.py` imports only `dataclasses` and `enum`. Reading the schema JSON there adds file input/output to the frozen contract core and costs one read per finding load.
3. REQ-32 exists to bind code, schema, and document together. With the lint in place, a code constant and a schema enum cannot drift.

Trade-off accepted: a value now appears in three places instead of two. The lint is what makes that safe, so Task 5 is not optional.

## File Structure

| Path | Responsibility | Task |
|------|----------------|------|
| `helpers/sec_overlay/evidence.py` | Add `VERIFICATION_VALUES`. Sole owner of the closed evidence, status, and disposition vocabularies. | 1 |
| `references/finding.schema.json` | Add the `verification` and `runtime_disposition` enums. | 1 |
| `helpers/sec_overlay/models.py` | Reject an out-of-enum value in `from_dict`. Export the three nested-object shapes as constants. | 1, 2 |
| `references/prompt-constants.md` | Document `verification`. Add the `FINDING_SHAPES` block. Correct the precondition-cap claim. | 1, 2, 5 |
| `agents/investigate.md` | Import `FINDING_SHAPES`. | 2 |
| `agents/validate.md` | State the Tier-1 confirmation rule. | 3 |
| `agents/threat-model.md` | Import `QUALIFIER_PROOF`. | 4 |
| `helpers/sec_overlay/calibrate.py` | Export `PRECONDITION_CAPS` and read it in `_precondition_cap`. | 5 |
| `helpers/sec_overlay/driver.py` | Export `DISPATCH_TOKENS` and build the dispatch block from it. | 5 |
| `helpers/tests/test_models.py` | REQ-02 load-enforcement tests. | 1 |
| `helpers/tests/test_finding_schema.py` | REQ-02 schema-enum tests. | 1 |
| `helpers/tests/test_contract_lint.py` | NEW. The REQ-32 lint. Five properties in this plan; property (c) arrives with REQ-08. | 2, 3, 4, 5 |
| `helpers/tests/test_docs_invariants.py` | Extend the existing vocabulary test with `VERIFICATION_VALUES`. | 1 |

`helpers/tests/test_contracts.py` stays as it is. It checks that a prompt's JSON example validates against the model. The new module checks that a document, a schema, and a code constant agree. Two different jobs.

---

### Task 1: REQ-02 — closed enums for `verification` and `runtime_disposition`

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py:14-27`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py:160-169`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json:27,38`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md:174`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_models.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_finding_schema.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py:172-177`

**Interfaces:**
- Consumes: `evidence.RUNTIME_DISPOSITIONS` (exists at `evidence.py:23`).
- Produces: `evidence.VERIFICATION_VALUES: frozenset[str]`. `models.Finding.from_dict` raises `ValueError` on an out-of-enum `verification` or `runtime_disposition`. Task 5's lint reads both constants.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_models.py`:

```python
def test_from_dict_rejects_prose_verification():
    d = _minimal_finding_dict()
    d["verification"] = (
        "The fix was reviewed by hand and appears to address the reported issue."
    )
    with pytest.raises(ValueError, match="verification"):
        Finding.from_dict(d)


def test_from_dict_accepts_a_documented_verification_value():
    d = _minimal_finding_dict()
    d["verification"] = "static-only"
    assert Finding.from_dict(d).verification == "static-only"


def test_from_dict_accepts_a_null_verification():
    d = _minimal_finding_dict()
    d["verification"] = None
    assert Finding.from_dict(d).verification is None


def test_from_dict_rejects_an_unknown_runtime_disposition():
    d = _minimal_finding_dict()
    d["runtime_disposition"] = "neither"
    with pytest.raises(ValueError, match="runtime_disposition"):
        Finding.from_dict(d)
```

Add the helper at the top of the same file, below the imports, if no equivalent exists. Read the file first; reuse an existing minimal-finding factory rather than adding a second one.

```python
def _minimal_finding_dict() -> dict:
    """Return the smallest dict ``Finding.from_dict`` accepts."""
    return {
        "id": "SSRF-0001",
        "rule_id": "r1",
        "cls": "ssrf",
        "status": "raw",
        "severity": "medium",
        "file": "app/main.py",
        "line": 10,
        "message": "unvalidated outbound request",
    }
```

Append to `helpers/tests/test_finding_schema.py`:

```python
def test_schema_pins_the_verification_enum():
    schema = json.loads(_SCHEMA_PATH.read_text())
    enum = schema["properties"]["verification"]["enum"]
    assert set(enum) == VERIFICATION_VALUES | {None}


def test_schema_pins_the_runtime_disposition_enum():
    schema = json.loads(_SCHEMA_PATH.read_text())
    enum = schema["properties"]["runtime_disposition"]["enum"]
    assert set(enum) == RUNTIME_DISPOSITIONS | {None}
```

Read `test_finding_schema.py` first and reuse its existing schema-path constant. If it names the path differently, use that name instead of `_SCHEMA_PATH`. Add the two constants to its imports:

```python
from sec_overlay.evidence import RUNTIME_DISPOSITIONS, VERIFICATION_VALUES
```

`json` is already imported there; check before adding it again.

- [ ] **Step 2: Run the tests to verify they fail**

Run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

```bash
uv run pytest tests/test_models.py -k verification -v
uv run pytest tests/test_finding_schema.py -k enum -v
```

Expected: the `test_models.py` cases fail because `from_dict` accepts any string. The `test_finding_schema.py` cases fail with `ImportError` on `VERIFICATION_VALUES` and then `KeyError: 'enum'`.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.107.4 in plugins/sec-overlay/.claude-plugin/plugin.json first
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_models.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_finding_schema.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): add failing REQ-02 enum tests"
```

- [ ] **Step 4: Add the code constant**

In `helpers/sec_overlay/evidence.py`, insert after the `RUNTIME_DISPOSITIONS` line at `:23` and before the partition assert at `:25`:

```python
VERIFICATION_VALUES = frozenset(
    {"verified-static", "static-only", "not-fixed", "verify-error"}
)
```

Do not touch `_MECHANICAL`, `TIER1_RECEIPTS`, or `TIER2_RECEIPTS`. The partition assert at `:25` couples those three; a change there breaks the import.

- [ ] **Step 5: Add the schema enums**

In `references/finding.schema.json`, replace line 27:

```json
    "verification": {
      "enum": ["verified-static", "static-only", "not-fixed", "verify-error", null]
    },
```

and replace line 38:

```json
    "runtime_disposition": {
      "enum": ["needs-runtime", "static-settled", "unassessed", null]
    },
```

Drop the `"type"` key on both. `schema.py:_validate_value` checks `type` first and returns early on a mismatch, so a `["string","null"]` type beside an enum containing `null` still works — but the enum alone is the narrower statement and needs no second rule.

- [ ] **Step 6: Enforce at load**

In `helpers/sec_overlay/models.py`, add the import beside the existing stdlib imports:

```python
from sec_overlay.evidence import RUNTIME_DISPOSITIONS, VERIFICATION_VALUES
```

`evidence.py` imports only `enum`, so this creates no cycle.

Add the module-level table above the `Finding` dataclass:

```python
_CLOSED_ENUMS: dict[str, frozenset[str]] = {
    "verification": VERIFICATION_VALUES,
    "runtime_disposition": RUNTIME_DISPOSITIONS,
}
```

Then in `Finding.from_dict`, after the unknown-key filter and before the status coercion:

```python
        for name, allowed in _CLOSED_ENUMS.items():
            value = d.get(name)
            if value is not None and value not in allowed:
                raise ValueError(
                    f"{name} {value!r} is not one of {sorted(allowed)} or null"
                )
```

Extend the `from_dict` docstring with a `Raises:` block naming `ValueError` for an out-of-enum value.

- [ ] **Step 7: Document `verification`**

In `references/prompt-constants.md`, add one bullet to the `EVIDENCE_VOCABULARY` block, directly after the `runtime_disposition` bullet at `:174-175`:

```markdown
- **`verification` (closed enum):** `verified-static`, `static-only`, `not-fixed`,
  `verify-error`. Any other value is rejected when a finding loads. Never write prose here.
```

- [ ] **Step 8: Extend the existing vocabulary test**

In `helpers/tests/test_docs_invariants.py`, add `VERIFICATION_VALUES` to the import line beside `RUNTIME_DISPOSITIONS`, then change line 176:

```python
    for value in (
        TIER1_RECEIPTS | TIER2_RECEIPTS | SHIPPING_STATUSES | RUNTIME_DISPOSITIONS
        | VERIFICATION_VALUES
    ):
```

- [ ] **Step 9: Run the tests to verify they pass**

```bash
uv run pytest tests/test_models.py tests/test_finding_schema.py tests/test_docs_invariants.py -q
```

Expected: PASS.

- [ ] **Step 10: Run the full suite**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ tests/
uv run ty check
```

Expected: 1619 or more passed, zero failed, zero warnings.

A fixture that sets an out-of-enum `verification` now fails at load. That is the point of the change, not a regression to work around. Correct the fixture value to the documented enum. Do not weaken the check. If a fixture holds a prose `verification` deliberately, as a rejection example, move it into a test that asserts the rejection.

- [ ] **Step 11: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.108.0; add a CHANGELOG entry under ## Unreleased
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): REQ-02 close finding contract enums"
```

---

### Task 2: REQ-18 — publish the nested finding shapes

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py` (add the shape constants)
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` (new `FINDING_SHAPES` block)
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/investigate.md:8-13`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py` (NEW)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `models.RUNTIME_TEST_KEYS`, `models.OPEN_QUESTION_KEYS`, `models.AFFECTED_SITE_KEYS`, each a `tuple[str, ...]`. Task 5 reuses the same lint module.

The source of truth is the `Finding` docstring. `runtime_test` at `models.py:74-75` names `objective`, `preconditions`, `payloads`, `expected_signal`, and `telemetry`. `open_questions` at `:87-93` names `question`, `why_it_matters`, and `who_to_ask_or_check`. `affected_sites` at `:96-97` names `id`, `file`, and `line`. The requirements document cites `models.py:79-98`; that cite drifted, and the spec's cite-verification record already holds the correction.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_contract_lint.py`:

```python
"""REQ-32 contract lint: code, schema, and prompt-constants must state one contract.

Each test reads a code constant and asserts the document or the schema agrees.
A failure here is drift, not a flaky test. Fix the document, not the assertion.
"""

from __future__ import annotations

from pathlib import Path

from sec_overlay.models import AFFECTED_SITE_KEYS, OPEN_QUESTION_KEYS, RUNTIME_TEST_KEYS

SKILL = Path(__file__).resolve().parents[2]
CONSTS = SKILL / "references" / "prompt-constants.md"
AGENTS = SKILL / "agents"


def _block(name: str) -> str:
    """Return the body of a single ``## NAME`` block in prompt-constants.md."""
    text = CONSTS.read_text()
    marker = f"## {name}"
    assert marker in text, f"{name} block missing from prompt-constants.md"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def test_published_finding_shapes_match_the_model():
    block = _block("FINDING_SHAPES")
    for field, keys in (
        ("runtime_test", RUNTIME_TEST_KEYS),
        ("open_questions", OPEN_QUESTION_KEYS),
        ("affected_sites", AFFECTED_SITE_KEYS),
    ):
        assert field in block, f"{field} shape not published"
        for key in keys:
            assert f"`{key}`" in block, f"{field}.{key} missing from FINDING_SHAPES"


def test_investigate_prompt_imports_the_published_shapes():
    text = (AGENTS / "investigate.md").read_text()
    assert "FINDING_SHAPES" in text, "investigate.md does not import FINDING_SHAPES"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_contract_lint.py -v
```

Expected: FAIL at collection with `ImportError: cannot import name 'AFFECTED_SITE_KEYS'`.

- [ ] **Step 3: Commit the red test**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.108.1
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): add failing REQ-18 shape lint"
```

- [ ] **Step 4: Export the shape constants**

In `helpers/sec_overlay/models.py`, add above the `Finding` dataclass, beside `_CLOSED_ENUMS`:

```python
RUNTIME_TEST_KEYS = (
    "objective",
    "preconditions",
    "payloads",
    "expected_signal",
    "telemetry",
)
OPEN_QUESTION_KEYS = ("question", "why_it_matters", "who_to_ask_or_check")
AFFECTED_SITE_KEYS = ("id", "file", "line")
```

These are the published shapes. The `Finding` docstring already names the same keys; the constants make them readable by the lint.

- [ ] **Step 5: Publish the shapes**

In `references/prompt-constants.md`, add a new block. Place it directly after the `FIELD_OWNERSHIP` block, which ends at `:141`, and before `## QUALIFIER_PROOF`:

```markdown
## FINDING_SHAPES

Three `Finding` fields hold nested objects. Use exactly these keys. A different key
is dropped when the finding loads.

- **`runtime_test`** — one object, or null. Keys: `objective`, `preconditions`,
  `payloads`, `expected_signal`, `telemetry`. The red-team phase owns this field.
- **`open_questions`** — a list of objects. Keys per object: `question`,
  `why_it_matters`, `who_to_ask_or_check`. Trace and red-team own this field.
- **`affected_sites`** — a list of objects, on a cluster primary only. Keys per
  object: `id`, `file`, `line`. The cluster pass owns this field.
```

- [ ] **Step 6: Import the block from the producer prompt**

In `agents/investigate.md`, extend the `## Imports` list at `:8-11`. Replace:

```markdown
Include the ANTI_MANIPULATION, EXCLUSION_RULES, SEVERITY_GUIDANCE,
SEVERITY_PRECONDITION, SHAPE_HUNTING, EXHAUSTIVENESS, TOOL_TRUST,
OUTPUT_WRITE_FALLBACK, and FIELD_OWNERSHIP blocks from
```

with:

```markdown
Include the ANTI_MANIPULATION, EXCLUSION_RULES, SEVERITY_GUIDANCE,
SEVERITY_PRECONDITION, SHAPE_HUNTING, EXHAUSTIVENESS, TOOL_TRUST,
OUTPUT_WRITE_FALLBACK, FIELD_OWNERSHIP, and FINDING_SHAPES blocks from
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contract_lint.py tests/test_contracts.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.0; add a CHANGELOG entry
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/models.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/investigate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): REQ-18 publish finding shapes"
```

---

### Task 3: REQ-07 — align the validate prompt to the gate

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/validate.md:80-84`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`

**Interfaces:**
- Consumes: `evidence.TIER1_RECEIPTS` and `evidence.TIER2_RECEIPTS` (exist at `evidence.py:20-21`).
- Produces: nothing new.

The gate rule is at `findings_gate.py:139`: `if f.status.value in ("confirmed", "fixed") and not confirms_alone(f.evidence_sources)`. `confirms_alone` accepts a Tier-1 receipt only. `validate.md:82-83` today tells the agent to record `ast-grep:`, `structural-index:`, or `ripgrep:` entries, "not just `llm-claimed:`". All three are Tier-2, so the prompt implies a Tier-2 receipt confirms. It does not.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_contract_lint.py`:

```python
def test_validate_prompt_states_the_tier1_confirmation_rule():
    text = (AGENTS / "validate.md").read_text()
    for receipt in sorted(TIER1_RECEIPTS):
        assert receipt in text, f"validate.md never names the Tier-1 receipt {receipt}"
    assert "Tier-1" in text, "validate.md does not name the Tier-1 requirement"
    assert "needs-deployment-testing" in text, (
        "validate.md does not route a Tier-2-only finding to needs-deployment-testing"
    )


def test_validate_prompt_does_not_imply_tier2_confirms():
    """A Tier-2 receipt must never appear as sufficient for ``confirmed``."""
    text = (AGENTS / "validate.md").read_text()
    confirmed = text.split("**Confirmed**", 1)[1].split("- **Rejected**", 1)[0]
    assert "Tier-1" in confirmed, "the Confirmed verdict does not require a Tier-1 receipt"
```

Add `TIER1_RECEIPTS` to the module's import line:

```python
from sec_overlay.evidence import TIER1_RECEIPTS
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_contract_lint.py -k validate -v
```

Expected: FAIL. `validate.md` contains no `Tier-1` string today.

- [ ] **Step 3: Commit the red test**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.1
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): add failing REQ-07 gate-match lint"
```

- [ ] **Step 4: Edit the prompt**

In `agents/validate.md`, replace lines 80-84:

```markdown
   - **Confirmed** (you tried and could not refute it; the source→sink path
     holds, at confidence 8–10 per the anchor above): set `status: "confirmed"`,
     record `evidence_sources` (the tool receipts you personally confirmed —
     `ast-grep:`/`structural-index:`/`ripgrep:` entries, not just `llm-claimed:`),
     propose a `cvss_vector`, append `history` `{"event": "validate:confirmed"}`.
```

with:

```markdown
   - **Confirmed** (you tried and could not refute it; the source→sink path
     holds, at confidence 8–10 per the anchor above): set `status: "confirmed"`,
     record `evidence_sources` (the tool receipts you personally confirmed).
     `confirmed` requires at least one Tier-1 receipt — `codeql:`, `semgrep:`,
     `sca:`, or `secrets:`. A finding whose only receipts are Tier-2
     (`ast-grep:`, `structural-index:`, `ripgrep:`, `tree-sitter:`,
     `dependency-catalog:`) is real but unproven from source: set
     `status: "needs-deployment-testing"`, not `confirmed`. An `llm-claimed:`
     entry corroborates and never confirms. Propose a `cvss_vector`, append
     `history` `{"event": "validate:confirmed"}`.
```

Leave lines 85-88 as they are. The `external-boundary` rule and the dataflow-correction rule are separate and still hold.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contract_lint.py tests/test_contracts.py tests/test_findings_gate.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.2; add a CHANGELOG entry
prek run
git add plugins/sec-overlay/skills/sec-overlay/agents/validate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(sec-overlay): REQ-07 match validate to the gate"
```

---

### Task 4: REQ-10 — import `QUALIFIER_PROOF` into the threat-model prompt

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/threat-model.md:8`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`

**Interfaces:**
- Consumes: the `_block` helper and the `AGENTS` path from Task 2.
- Produces: nothing new.

This is lint property (f). See Conflict 2 above for why the requirements document's stated test is not implementable and what replaces it.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_contract_lint.py`:

```python
def _imports_line(prompt: Path) -> str:
    """Return the ``## Imports`` section of an agent prompt, or an empty string."""
    text = prompt.read_text()
    if "## Imports" not in text:
        return ""
    return text.split("## Imports", 1)[1].split("\n## ", 1)[0]


def test_every_severity_prompt_also_imports_qualifier_proof():
    """A prompt that grades severity writes blanket qualifiers, so it needs the rule."""
    offenders = []
    for prompt in sorted(AGENTS.glob("*.md")):
        if prompt.name == "README.md":
            continue
        imports = _imports_line(prompt)
        if "SEVERITY_PRECONDITION" in imports and "QUALIFIER_PROOF" not in imports:
            offenders.append(prompt.name)
    assert not offenders, f"prompts import SEVERITY_PRECONDITION without QUALIFIER_PROOF: {offenders}"
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_contract_lint.py -k qualifier -v
```

Expected: FAIL, listing at least `threat-model.md`.

If the failure lists prompts other than `threat-model.md`, stop and report the list. REQ-10 names only `threat-model.md`. Adding the block to another prompt is scope this plan does not authorize.

- [ ] **Step 3: Commit the red test**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.3
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): add failing REQ-10 qualifier lint"
```

- [ ] **Step 4: Edit the prompt**

In `agents/threat-model.md`, replace line 8:

```markdown
Include FIELD_OWNERSHIP, OUTPUT_WRITE_FALLBACK, and STE_PROSE from
```

with:

```markdown
Include FIELD_OWNERSHIP, QUALIFIER_PROOF, OUTPUT_WRITE_FALLBACK, and STE_PROSE from
```

`threat-model.md:8` does not name `SEVERITY_PRECONDITION` in the visible import list. Read the whole `## Imports` section before editing. If `SEVERITY_PRECONDITION` is absent from that section, the Step 2 failure came from a different prompt — stop and report, because REQ-10 then has no red state and the lint property needs a different predicate.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contract_lint.py tests/test_docs_invariants.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.4; add a CHANGELOG entry
prek run
git add plugins/sec-overlay/skills/sec-overlay/agents/threat-model.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(sec-overlay): REQ-10 add QUALIFIER_PROOF to TM"
```

---

### Task 5: REQ-32 — finish the contract lint

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py:106-122`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py:126-137`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md:59`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`

**Interfaces:**
- Consumes: `_block`, `AGENTS`, and `CONSTS` from Task 2.
- Produces: `calibrate.PRECONDITION_CAPS: tuple[tuple[float, int], ...]`, `calibrate.PRECONDITION_CAP_FLOOR: int`, and `driver.DISPATCH_TOKENS: tuple[str, ...]`. REQ-08 in group 2 reads `DISPATCH_TOKENS` for lint property (c).

Properties (a) and (e) already landed: (a) as the extended `test_evidence_vocabulary_block_lists_all_values` in Task 1 plus the two schema-enum tests, and (e) as Task 3's two validate tests. Property (d) landed as Task 2. Property (f) landed as Task 4. This task lands (b) and the schema-versus-code binding for every closed vocabulary, and it exports `DISPATCH_TOKENS` so REQ-08 has something to assert against.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_contract_lint.py`:

```python
def test_precondition_cap_thresholds_are_published():
    """The document must state the cap table the harness actually applies."""
    block = _block("SEVERITY_PRECONDITION")
    for _threshold, cap in PRECONDITION_CAPS:
        assert str(cap) in block, f"cap {cap} missing from SEVERITY_PRECONDITION"
    assert str(PRECONDITION_CAP_FLOOR) in block, "cap floor missing"
    assert "weight" in block.lower(), "the block still describes a count, not a weight"


def test_precondition_cap_reads_the_published_table():
    """_precondition_cap must derive from PRECONDITION_CAPS, not a second copy."""
    assert _precondition_cap([]) == PRECONDITION_CAPS[0][1]
    # one strong precondition weighs 1.0, so it lands in the second band
    assert _precondition_cap(["non-default config"]) == PRECONDITION_CAPS[1][1]


def test_every_closed_vocabulary_matches_its_schema_enum():
    """Each code constant with a schema counterpart must equal that enum."""
    schema = json.loads(SCHEMA.read_text())
    props = schema["properties"]
    for field, allowed in (
        ("verification", VERIFICATION_VALUES),
        ("runtime_disposition", RUNTIME_DISPOSITIONS),
    ):
        assert set(props[field]["enum"]) == allowed | {None}, f"{field} drifted"


def test_dispatch_tokens_are_a_single_source():
    """render_dispatch must build its substitute line from DISPATCH_TOKENS."""
    for token in DISPATCH_TOKENS:
        assert re.fullmatch(r"[A-Z0-9_]+", token), f"{token} is not a token name"
    assert "TARGET" in DISPATCH_TOKENS
    assert "WORKSPACE" in DISPATCH_TOKENS
    assert "SHA" in DISPATCH_TOKENS
    assert "ATTACK_CLASS" in DISPATCH_TOKENS
```

Extend the module imports. `re` and `json` are new here; Task 2 left them out so the module stayed clean of an unused import.

```python
import json
import re

from sec_overlay.calibrate import (
    PRECONDITION_CAPS,
    PRECONDITION_CAP_FLOOR,
    _precondition_cap,
)
from sec_overlay.driver import DISPATCH_TOKENS
from sec_overlay.evidence import RUNTIME_DISPOSITIONS, TIER1_RECEIPTS, VERIFICATION_VALUES
```

and add the schema path beside `CONSTS`:

```python
SCHEMA = SKILL / "references" / "finding.schema.json"
```

Record the deferred property in the module docstring so the gap is named, not silent. Replace the docstring's closing line with:

```python
"""REQ-32 contract lint: code, schema, and prompt-constants must state one contract.

Each test reads a code constant and asserts the document or the schema agrees.
A failure here is drift, not a flaky test. Fix the document, not the assertion.

Property (c) of REQ-32 — every ``{{TOKEN}}`` in a prompt is in the dispatch
substitution map — lands with REQ-08, which adds the three unmapped tokens.
``DISPATCH_TOKENS`` below is the constant that test will read.
"""
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_contract_lint.py -v
```

Expected: FAIL at collection with `ImportError: cannot import name 'PRECONDITION_CAPS' from 'sec_overlay.calibrate'`.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.109.5
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): add failing REQ-32 lint properties"
```

- [ ] **Step 4: Export the cap table**

In `helpers/sec_overlay/calibrate.py`, add above `_precondition_weight` at `:91`:

```python
# The risk_score ceiling by precondition WEIGHT, not count. Published in
# prompt-constants.md SEVERITY_PRECONDITION; the contract lint binds the two.
PRECONDITION_CAPS: tuple[tuple[float, int], ...] = ((1.0, 10), (2.0, 8), (3.0, 7))
PRECONDITION_CAP_FLOOR = 5
```

Then replace the body of `_precondition_cap` at `:106-122`:

```python
def _precondition_cap(preconditions: list[str]) -> int:
    """Risk ceiling from precondition DIFFICULTY (weight), not count.

    Args:
        preconditions: The finding's precondition strings.

    Returns:
        The first cap in ``PRECONDITION_CAPS`` whose threshold the summed
        weight falls below, or ``PRECONDITION_CAP_FLOOR`` when no cap matches.
    """
    w = _precondition_weight(preconditions)
    for threshold, cap in PRECONDITION_CAPS:
        if w < threshold:
            return cap
    return PRECONDITION_CAP_FLOOR
```

The behaviour is identical to the four-branch version. `w<1` gives 10, `1<=w<2` gives 8, `2<=w<3` gives 7, and `w>=3` gives 5. Complexity drops from four branches to one loop.

- [ ] **Step 5: Correct the published claim**

In `references/prompt-constants.md`, replace lines 58-60:

```markdown
This stops "SQL injection, therefore critical" anchoring: go through the evidence first,
label last. The harness caps `risk_score` by the precondition count deterministically and
flags any claimed severity that sits well above the derived score as inflation.
```

with:

```markdown
This stops "SQL injection, therefore critical" anchoring: go through the evidence first,
label last. The harness then caps `risk_score` by precondition WEIGHT, not count. A free
precondition weighs 0, a weak one 0.5, and a strong one 1.0. Summed weight below 1 caps at
10, below 2 caps at 8, below 3 caps at 7, and 3 or more caps at 5. The harness flags any
claimed severity that sits well above the derived score as inflation.
```

Leave line 55 as it is. The band guidance is prompt policy and has no code counterpart.

- [ ] **Step 6: Export the dispatch tokens**

In `helpers/sec_overlay/driver.py`, add above `render_dispatch` at `:104`:

```python
# Tokens render_dispatch tells the orchestrator to substitute. A prompt using a
# token absent from this tuple ships a literal {{TOKEN}} to the model; the
# contract lint checks the two agree (REQ-08 closes the current three gaps).
DISPATCH_TOKENS: tuple[str, ...] = ("TARGET", "WORKSPACE", "SHA", "ATTACK_CLASS")
```

Then build the substitute line from it. Replace `render_dispatch`'s body at `:125-137`:

```python
    outputs = ", ".join(str(p(ctx.ws)) for p in phase.outputs) or "(none)"
    values = {"TARGET": ctx.target, "WORKSPACE": str(ctx.ws.root), "SHA": ctx.sha}
    if classes:
        values["ATTACK_CLASS"] = ",".join(classes)
    pairs = [f"{{{{{name}}}}}={values[name]}" for name in DISPATCH_TOKENS if name in values]
    block = (
        f"NEXT AGENT PHASE: {phase.name}\n"
        f"  prompt: agents/{phase.prompt}\n"
        f"  substitute: {' '.join(pairs)}\n"
        f"  required outputs before advancing: {outputs}"
    )
    return safe_for_prompt(block)
```

This changes one thing a test may pin: the class token moves from its own line onto the substitute line. Run `tests/test_driver.py` and read any failure before editing it. If a test asserts the newline before `{{ATTACK_CLASS}}`, that assertion pins a format detail, not behaviour — update the expected string. If a test asserts an ordering or a value, the refactor is wrong; revert and keep the `class_line` form with `DISPATCH_TOKENS` used only by the lint.

- [ ] **Step 7: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contract_lint.py tests/test_calibrate.py tests/test_driver.py -q
```

Expected: PASS.

- [ ] **Step 8: Run the full suite and the group gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ tests/
uv run ty check
```

Expected: 1619 or more passed, zero failed, zero warnings. This is the Part E group-1 verification gate. Do not proceed to group 2 until it is green.

- [ ] **Step 9: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# bump version to 1.110.0; add a CHANGELOG entry
prek run
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/calibrate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): REQ-32 add the contract lint"
```

---

## Definition of done for this plan

1. `evidence.VERIFICATION_VALUES` exists and `references/finding.schema.json` carries both enums.
2. `Finding.from_dict` raises `ValueError` on an out-of-enum `verification` or `runtime_disposition`.
3. `references/prompt-constants.md` documents `verification`, publishes the three nested shapes, and states the weight-based precondition caps.
4. `agents/investigate.md` imports `FINDING_SHAPES`. `agents/validate.md` states the Tier-1 confirmation rule. `agents/threat-model.md` imports `QUALIFIER_PROOF`.
5. `helpers/tests/test_contract_lint.py` holds REQ-32 properties (a), (b), (d), (e), and (f). Its docstring names property (c) as REQ-08's work.
6. `uv run pytest -q` passes with no fewer than the 1619 baseline tests. `ruff` and `ty` report nothing.
7. Ten commits on `feat/sec-overlay-improvements`, five red and five green, each naming its requirement id. The plugin version reads 1.110.0.

## What this plan does not do

- REQ-08 (the three unmapped prompt tokens) and lint property (c). Group 2.
- REQ-09 (canonical class-key validation). It lands after REQ-32 per the build addendum, at the head of group 2.
- Any change to `class_ext.py`. Its fall-back-and-record behaviour stays.
- The `class_extension_status` dead-code defect. Recorded as deferred in the spec; do not fix it here.
