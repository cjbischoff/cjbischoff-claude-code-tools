# sec-overlay Parked Code Repairs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the nine parked code and test defects (REQ-62 to REQ-70) that the five completed sec-overlay plans left with rulings instead of fixes.

**Architecture:** Nine independent repairs inside the `sec_overlay` helpers package. Each repair is one test-first change to one module or one test file, followed by its own commit. No task depends on another task's output, so the order below only follows the spec's build order. Two byte-frozen modules (`models.py`, `evidence.py`) stay untouched, which forces three of the repairs to derive their values from those modules instead of restating them.

**Tech Stack:** Python 3.12 (stdlib only), `pytest`, `ruff`, `ty`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-02-sec-overlay-parked-findings-design.md`

## Global Constraints

- `sec_overlay/models.py` and `sec_overlay/evidence.py` are byte-frozen. `helpers/tests/test_frozen_contract.py` pins their sha256 because they mirror a Go port. No task in this plan edits either file.
- Every code change lands test-first: write the failing test, run it, see it fail, then change the code.
- The helpers package is stdlib-only. `helpers/pyproject.toml` declares `dependencies = []`. Add no dependency.
- Maximum line length is 100 characters (`[tool.ruff] line-length = 100`).
- Per-commit gate, run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:
  ```bash
  uv run pytest -q
  uv run ruff check sec_overlay/ bench/ tests/
  uv run ty check
  uv run python -m sec_overlay.phase_docs --check
  ```
  Then `prek run` from the repository root.
- Bump the plugin version once per commit. Read `plugins/sec-overlay/.claude-plugin/plugin.json`, then increment the patch component. Do not trust a version literal written here.
- Repository governance: work on a branch, never on `main`. Use Conventional Commits: `<type>(<scope>): <imperative summary under 50 chars>`. Stage explicit paths only. Never use `git add -A`, `git add .`, `git commit -a`, or `--no-verify`.
- Commit contents: add no `Co-Authored-By` trailer. Every commit updates `plugins/sec-overlay/CHANGELOG.md` and the `README.md` of every folder it touches. The pre-commit hook rejects a commit that omits either.
- Do not merge and do not push. The user withheld that permission.
- A stray second git repository sits at `plugins/sec-overlay/skills/sec-overlay/helpers/.git` with a permanently dirty working tree. Always run git with `git -C /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools`.
- Text written into a file follows ASD-STE100: no semicolons in prose, one instruction per sentence, sentences under 25 words. `sec_overlay/README.md` gets an STE100 lint pass in the companion plan, so every entry this plan appends must already be clean.

## Paths

Every path below is relative to the repository root.

- Helpers root: `plugins/sec-overlay/skills/sec-overlay/helpers/`
- Package: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/`
- Tests: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/`

For brevity the tasks write `helpers/` for the helpers root.

## Staging Sets

The pre-commit hook derives its requirements from the staged paths. Use one of these two sets.

**Test-only commit** (Tasks 1, 3, 9):

```
helpers/tests/<test file>.py
helpers/tests/README.md
plugins/sec-overlay/CHANGELOG.md
plugins/sec-overlay/.claude-plugin/plugin.json
```

**Code and test commit** (Tasks 2, 4, 5, 6, 7, 8):

```
helpers/sec_overlay/<module>.py
helpers/sec_overlay/README.md
helpers/tests/<test file>.py
helpers/tests/README.md
plugins/sec-overlay/CHANGELOG.md
plugins/sec-overlay/.claude-plugin/plugin.json
```

`plugins/sec-overlay/.claude-plugin/` holds no tracked `README.md`, so `plugin.json` adds no further requirement.

## Documentation Conventions

- `helpers/sec_overlay/README.md` — append a `### <title> (REQ-NN)` section at the end of the file.
- `helpers/tests/README.md` — append a `## YYYY-MM-DD — REQ-NN red: <description>` section at the end of the file. Use `2026-09-02`.
- `plugins/sec-overlay/CHANGELOG.md` — add a bullet under `## Unreleased`, inside `### Added`, `### Fixed`, `### Changed`, or `### Removed`. Wrap near 100 characters. Name the finding the entry closes.

---

### Task 1: REQ-62 — derive the receipt-tier enum bar

The contract lint test asserts that each closed vocabulary in code equals its counterpart enum in `references/finding.schema.json`. For `receipt_tier` it compares the schema against the literal `frozenset({1, 2})`, so a third tier added to `evidence.py` would pass unnoticed. Derive the set from the tier constants instead.

**Files:**
- Modify: `helpers/tests/test_contract_lint.py:24-29` (import block) and `helpers/tests/test_contract_lint.py:40-53` (`test_every_closed_vocabulary_matches_its_schema_enum`)
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.evidence.TIER1_RECEIPTS`, `sec_overlay.evidence.TIER2_RECEIPTS`, `sec_overlay.evidence.receipt_tier(source: str) -> int | None`. `receipt_tier` returns `None` for a source that is not a tool receipt, `1` for a Tier-1 prefix, and `2` otherwise.
- Produces: nothing. This is a test-only change.

- [ ] **Step 1: Confirm the derived value equals the current literal**

The change must not alter what the test asserts today. Run this from `helpers/`:

```bash
uv run python -c "
from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS, receipt_tier
print(sorted(frozenset(receipt_tier(f'{p}:x') for p in TIER1_RECEIPTS | TIER2_RECEIPTS)))
"
```

Expected: `[1, 2]`. If it prints anything else, stop and report — the premise is wrong.

- [ ] **Step 2: Prove the derivation is live**

A test-only change cannot have a red phase against frozen code, so demonstrate that the new expression tracks `evidence.py` while the literal does not. Run this from `helpers/`:

```bash
uv run python -c "
from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS
stub = {'sca': 3}
print('literal bar:', sorted({1, 2}))
print('derived bar with a stubbed tier-3 receipt:',
      sorted(frozenset(stub.get(p, 1 if p in TIER1_RECEIPTS else 2)
                       for p in TIER1_RECEIPTS | TIER2_RECEIPTS)))
"
```

Expected: `literal bar: [1, 2]` and `derived bar with a stubbed tier-3 receipt: [1, 2, 3]`. Record both lines in the task report — they are the evidence that the assertion now moves with the code.

- [ ] **Step 3: Add `receipt_tier` to the import block**

Replace the `sec_overlay.evidence` import at `helpers/tests/test_contract_lint.py:24-29`:

```python
from sec_overlay.evidence import (
    RUNTIME_DISPOSITIONS,
    TIER1_RECEIPTS,
    TIER2_RECEIPTS,
    VERIFICATION_VALUES,
    receipt_tier,
)
```

- [ ] **Step 4: Derive the expected tier set**

In `test_every_closed_vocabulary_matches_its_schema_enum`, insert the hoisted local before the `for field, allowed in (` loop, and replace the `receipt_tier` tuple entry. The result:

```python
    props = json.loads(SCHEMA.read_text())["properties"]
    receipt_tiers = frozenset(receipt_tier(f"{p}:x") for p in TIER1_RECEIPTS | TIER2_RECEIPTS)
    for field, allowed in (
        ("verification", VERIFICATION_VALUES),
        ("runtime_disposition", RUNTIME_DISPOSITIONS),
        ("completeness_tier", frozenset(TIERS)),
        ("judge_verdict", JUDGE_VERDICTS),
        ("receipt_tier", receipt_tiers),
    ):
```

Keep the loop body unchanged. Hoist the local rather than inlining the expression inside the tuple — inlined, the line reaches 105 characters and fails the 100-character limit.

- [ ] **Step 5: Run the test**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_contract_lint.py -q
```

Expected: PASS.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean. `ruff` must report no `E501`.

- [ ] **Step 7: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-62 red: the receipt-tier bar was a literal

`test_every_closed_vocabulary_matches_its_schema_enum` compared the schema enum for
`receipt_tier` against the literal `frozenset({1, 2})`. A third tier added to
`evidence.py` would have satisfied the literal and the test would have stayed green.
The expected set now comes from `receipt_tier` applied to every prefix in
`TIER1_RECEIPTS | TIER2_RECEIPTS`, so the assertion follows the code.

`evidence.py` is byte-frozen, so no red run is possible. A stubbed tier-3 receipt shows
the derived set becomes `{1, 2, 3}` while the literal stays `{1, 2}`. Closes F-4.
```

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased` in `plugins/sec-overlay/CHANGELOG.md`, inside `### Changed` (create the subsection if it is absent):

```markdown
- Derive the `receipt_tier` contract-lint bar from `TIER1_RECEIPTS | TIER2_RECEIPTS` instead of a
  `frozenset({1, 2})` literal, so a new receipt tier cannot pass the schema check. Closes F-4.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component of `version`. Change nothing else in that file.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): derive the receipt-tier bar"
```

---

### Task 2: REQ-63 — drop the dead rule-origin prefixes

`_RULE_ORIGINS` lists `asvs:` and `codeguard:`, but no receipt ever carries either prefix. `is_rule_originated` therefore has two entries that can never match. Reduce the tuple to the four real mechanical prefixes and add a test that pins the property.

**Files:**
- Modify: `helpers/sec_overlay/rule_gaps.py:18-19`
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_phase1_extras.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.evidence._MECHANICAL` — the set of receipt prefixes without their colon, equal to `TIER1_RECEIPTS | TIER2_RECEIPTS`.
- Produces: `sec_overlay.rule_gaps._RULE_ORIGINS: tuple[str, ...]` — exactly `("semgrep:", "codeql:", "sca:", "secrets:")`. `is_rule_originated(f: Finding) -> bool` keeps its signature.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_phase1_extras.py`:

```python
def test_every_rule_origin_is_a_mechanical_receipt_prefix():
    """REQ-63: a prefix no receipt carries can never mark a finding rule-originated."""
    from sec_overlay.evidence import _MECHANICAL
    from sec_overlay.rule_gaps import _RULE_ORIGINS

    for origin in _RULE_ORIGINS:
        assert origin.endswith(":"), origin
        assert origin[:-1] in _MECHANICAL, origin
```

- [ ] **Step 2: Run it and see it fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_phase1_extras.py::test_every_rule_origin_is_a_mechanical_receipt_prefix -q
```

Expected: FAIL with `AssertionError: asvs:`.

- [ ] **Step 3: Reduce the tuple**

In `helpers/sec_overlay/rule_gaps.py`, replace lines 18-19:

```python
# Sources that mean "a detection RULE surfaced this" (vs agent navigation/claims).
# Every entry must be a receipt prefix in evidence._MECHANICAL. An `asvs:`/`codeguard:`
# identifier reaches a finding through its own field, never through an evidence source.
_RULE_ORIGINS = ("semgrep:", "codeql:", "sca:", "secrets:")
```

Leave `is_rule_originated` and its docstring unchanged.

- [ ] **Step 4: Run the test and see it pass**

```bash
uv run pytest tests/test_phase1_extras.py -q
```

Expected: PASS, including the existing `test_is_rule_originated`.

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 6: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### Rule origins are mechanical receipt prefixes (REQ-63)

`_RULE_ORIGINS` in `rule_gaps.py` decides whether a detection rule surfaced a finding, or
whether an agent found it by hunting. Every entry must be a receipt prefix that
`evidence._MECHANICAL` also holds. The tuple previously listed `asvs:` and `codeguard:`,
which no evidence source ever carries. Those two entries could never match, so they made the
rule-gap ledger read as broader than it was. The tuple now holds `semgrep:`, `codeql:`,
`sca:`, and `secrets:` only. A test in `tests/test_phase1_extras.py` pins the property.

The test constrains `_RULE_ORIGINS` to a subset of `_MECHANICAL`, not to an equal set.
`ripgrep:`, `ast-grep:`, `structural-index:`, `tree-sitter:`, and `dependency-catalog:` are
mechanical receipts that are navigation aids rather than detectors, so they stay out.
```

- [ ] **Step 7: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-63 red: two rule-origin prefixes could never match

`_RULE_ORIGINS` listed `asvs:` and `codeguard:`. Neither prefix appears in
`evidence._MECHANICAL`, so no evidence source could ever start with either one.
`test_every_rule_origin_is_a_mechanical_receipt_prefix` failed with `AssertionError: asvs:`
before the fix and passes after it. Closes F-5.
```

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Removed`:

```markdown
- Remove the `asvs:` and `codeguard:` entries from `_RULE_ORIGINS`. No evidence source
  carries either prefix, so both were unreachable. Closes F-5.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_gaps.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase1_extras.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): drop dead rule-origin prefixes"
```

---

### Task 3: REQ-64 — derive the backend receipt prefixes

`test_backend_receipt_prefixes_are_mechanical` hardcodes six prefixes and asserts `prefix in _MECHANICAL`. That assertion is a tautology: `is_tool_receipt` is defined by membership in `_MECHANICAL`, so the test restates its own premise. Iterate the tier sets instead, and assert the two properties that matter.

**Files:**
- Modify: `helpers/tests/test_wiring.py:10` (import) and `helpers/tests/test_wiring.py:53-59` (`test_backend_receipt_prefixes_are_mechanical`)
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.evidence.TIER1_RECEIPTS`, `sec_overlay.evidence.TIER2_RECEIPTS`, `sec_overlay.evidence.is_tool_receipt(source: str) -> bool`, `sec_overlay.evidence.receipt_tier(source: str) -> int | None`.
- Produces: nothing. This is a test-only change.

- [ ] **Step 1: Confirm `_MECHANICAL` has no other use in the file**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n '_MECHANICAL' tests/test_wiring.py
```

Expected: exactly two lines — the import at line 10 and the assertion at line 58. If a third line appears, keep `_MECHANICAL` in the import and report the extra use.

- [ ] **Step 2: Prove the widened loop is live**

Show that the derived loop rejects a prefix `evidence.py` does not declare. Run from `helpers/`:

```bash
uv run python -c "
from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS, is_tool_receipt, receipt_tier
declared = TIER1_RECEIPTS | TIER2_RECEIPTS
print('declared prefixes:', len(declared))
for prefix in sorted(declared | {'nosuch'}):
    print(prefix, is_tool_receipt(f'{prefix}:x'), receipt_tier(f'{prefix}:x'))
"
```

Expected: every declared prefix prints `True` with a tier of `1` or `2`, and `nosuch` prints `False None`. Record the `nosuch` line in the task report.

- [ ] **Step 3: Replace the import**

Replace `helpers/tests/test_wiring.py:10`:

```python
from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS, is_tool_receipt, receipt_tier
```

- [ ] **Step 4: Replace the test**

Replace `helpers/tests/test_wiring.py:53-59` in full:

```python
def test_backend_receipt_prefixes_are_mechanical():
    # Every receipt prefix the harness declares must pass the gate and carry a tier.
    # A prefix that fails either check would make its backend's confirmed findings
    # unrecordable. Deriving the list from the tier sets covers a newly added backend.
    for prefix in sorted(TIER1_RECEIPTS | TIER2_RECEIPTS):
        assert is_tool_receipt(f"{prefix}:x") is True
        assert receipt_tier(f"{prefix}:x") in (1, 2)
```

The `prefix in _MECHANICAL` assertion is gone on purpose. `is_tool_receipt` is defined by that membership, so the assertion could never fail.

- [ ] **Step 5: Run the test**

```bash
uv run pytest tests/test_wiring.py -q
```

Expected: PASS.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean. `ruff` must report no `F401` for a now-unused `_MECHANICAL` import.

- [ ] **Step 7: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-64 red: the receipt-prefix test restated its own premise

`test_backend_receipt_prefixes_are_mechanical` hardcoded six prefixes and asserted
`prefix in _MECHANICAL`. `is_tool_receipt` is defined by that same membership, so the
assertion could not fail, and the hardcoded list missed any newly declared prefix. The test
now iterates `TIER1_RECEIPTS | TIER2_RECEIPTS` and asserts the gate result and the tier.

A probe over `declared | {"nosuch"}` shows the loop rejects an undeclared prefix.

Residual gap: the test cannot catch a new backend whose prefix is never added to
`evidence.py`. No constant enumerates the backends — `prefilter.py` names the four inline.
Closes F-6.
```

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Derive `test_backend_receipt_prefixes_are_mechanical` from `TIER1_RECEIPTS | TIER2_RECEIPTS`
  and drop the tautological `_MECHANICAL` membership assertion. Closes F-6.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_wiring.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): derive backend receipt prefixes"
```

---

### Task 4: REQ-65 — copy the cluster representative

`collapse_clusters` mutates a caller's `Finding` when no member already carries `affected_sites`. It assigns onto `primary.affected_sites` in place, so the input list a caller still holds changes underneath it. Build a copy with `dataclasses.replace` instead.

**Files:**
- Modify: `helpers/sec_overlay/report.py:8` (import) and `helpers/sec_overlay/report.py:604-630` (`collapse_clusters`)
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_report.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.report._risk_sort_key(f: Finding) -> tuple[int, int, str]` at `report.py:52`. `Finding` is a plain dataclass with `field(default_factory=list)` defaults and no `__post_init__`, so `dataclasses.replace` is safe.
- Produces: `collapse_clusters(findings: list[Finding]) -> list[Finding]` keeps its signature and its return shape. It now never mutates an input element. Callers at `selfscore.py:68-69` and `report.py:716-717` need no change.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_report.py`. The file already imports `Finding`, `FindingStatus`, `Severity`, and `collapse_clusters`.

```python
def test_collapse_clusters_does_not_mutate_the_input_findings():
    """REQ-65: the synthesized representative is a copy, so the caller's list is untouched."""
    members = [
        Finding(
            id=f"F-{i}",
            rule_id="r",
            cls="authz",
            status=FindingStatus.CONFIRMED,
            severity=Severity.MEDIUM,
            file=f"route_{i}.py",
            line=i,
            message="missing owner check",
            cluster_id="cluster:F-1",
        )
        for i in (1, 2, 3)
    ]

    reps = collapse_clusters(members)

    assert len(reps) == 1
    assert len(reps[0].affected_sites) == 3
    assert all(m.affected_sites == [] for m in members)
    assert all(reps[0] is not m for m in members)
```

- [ ] **Step 2: Run it and see it fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_report.py::test_collapse_clusters_does_not_mutate_the_input_findings -q
```

Expected: FAIL on `assert all(m.affected_sites == [] for m in members)` — one member now carries three sites.

- [ ] **Step 3: Import `replace`**

Replace `helpers/sec_overlay/report.py:8`:

```python
from dataclasses import asdict, is_dataclass, replace
```

- [ ] **Step 4: Build the representative as a copy**

In `collapse_clusters`, replace the group loop body:

```python
    for members in groups.values():
        primary = next((m for m in members if m.affected_sites), None)
        if primary is None:
            primary = replace(
                min(members, key=_risk_sort_key),
                affected_sites=[{"id": m.id, "file": m.file, "line": m.line} for m in members],
            )
        reps.append(primary)
```

Add one sentence to the `collapse_clusters` docstring: `The input findings are never mutated — a synthesized representative is a copy.`

- [ ] **Step 5: Run the test and see it pass**

```bash
uv run pytest tests/test_report.py tests/test_cluster.py -q
```

Expected: PASS.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 7: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### collapse_clusters returns a copy (REQ-65)

`collapse_clusters` picks one representative per cluster. When no member already carries
`affected_sites`, it synthesizes the site list from the whole group. It used to assign that
list onto the lowest-risk member in place, so a caller's own `Finding` changed underneath
it. The function now builds the representative with `dataclasses.replace`.

`replace` makes a shallow copy. The copy shares the member's other mutable list fields with
the original. That is acceptable because every consumer of a representative renders it and
does not write to it. `selfscore.py` and `report.py` are the only two callers.
```

- [ ] **Step 8: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-65 red: collapse_clusters mutated its input

`collapse_clusters` assigned onto `primary.affected_sites` in place. A caller that kept its
own list saw one element change. `test_collapse_clusters_does_not_mutate_the_input_findings`
failed on `assert all(m.affected_sites == [] for m in members)` before the fix. The function
now returns a `dataclasses.replace` copy. Closes F-7.
```

- [ ] **Step 9: Add the changelog entry**

Add under `## Unreleased`, inside `### Fixed`:

```markdown
- Build the cluster representative in `collapse_clusters` with `dataclasses.replace` instead of
  assigning `affected_sites` onto a caller's `Finding` in place. Closes F-7.
```

- [ ] **Step 10: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 11: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): copy the cluster representative"
```

---

### Task 5: REQ-66 — drop the finding's own site from SARIF

`affected_sites` on a cluster representative includes the representative itself. `_related_locations` turns every site into a SARIF related location, so the primary location repeats as a related location on the same result. Skip the site whose `id` matches the finding's own id.

**Files:**
- Modify: `helpers/sec_overlay/sarif.py:75-99` (`_related_locations`)
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_sarif.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `Finding.id`, `Finding.affected_sites: list[dict]`. A site dict holds `id`, `file`, and `line`. `cluster.py:81` writes the list. `id` is optional in a hand-built site.
- Produces: `_related_locations(finding: Finding) -> list[dict]` keeps its signature. It now omits a site whose `id` equals `finding.id`. `report.py:279-287` renders the same list into the report's sites table and stays unchanged.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_sarif.py`. The file already defines `_f(sev)` at line 7, which returns a `Finding` with `id="F-0001"` and `file="app.py"`.

```python
def test_related_locations_skip_the_findings_own_site():
    """REQ-66: the primary location must not repeat as a related location."""
    from sec_overlay.sarif import _related_locations

    f = _f(Severity.HIGH)
    f.affected_sites = [
        {"id": "F-0001", "file": "app.py", "line": 18},
        {"id": "F-0002", "file": "other.py", "line": 4},
        {"file": "nameless.py", "line": 9},
    ]

    uris = [loc["physicalLocation"]["artifactLocation"]["uri"] for loc in _related_locations(f)]
    assert uris == ["other.py", "nameless.py"]
```

If `Severity` is not already imported in `test_sarif.py`, add it to the existing `sec_overlay.models` import.

- [ ] **Step 2: Run it and see it fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_sarif.py::test_related_locations_skip_the_findings_own_site -q
```

Expected: FAIL — the list is `["app.py", "other.py", "nameless.py"]`.

- [ ] **Step 3: Skip the self site**

In `helpers/sec_overlay/sarif.py`, change the guard inside `_related_locations`:

```python
    out: list[dict] = []
    for site in finding.affected_sites or []:
        uri = site.get("file")
        if not uri or site.get("id") == finding.id:
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

Update the docstring's last sentence to read: `An entry missing ``file`` is skipped, and ``line`` defaults to 1. An entry whose ``id`` is the finding's own id is skipped, because SARIF already carries it as the primary location. An entry with no ``id`` is kept.`

- [ ] **Step 4: Run the test and see it pass**

```bash
uv run pytest tests/test_sarif.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 6: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### SARIF related locations exclude the primary site (REQ-66)

A cluster representative's `affected_sites` list includes the representative itself, because
`cluster.py` builds the list from every member. `_related_locations` mapped each site to a
SARIF related location, so a SARIF consumer saw the primary location twice on one result.
The function now skips a site whose `id` equals the finding's own id.

A site with no `id` is kept. Only a site written by the clustering step carries an `id`, so
the check cannot silently drop a hand-built entry. The report's sites table in `report.py`
still lists every site, including the primary one.
```

- [ ] **Step 7: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-66 red: SARIF repeated the primary location

`_related_locations` mapped every entry of `affected_sites` to a related location. A cluster
representative appears in its own site list, so its primary location repeated as a related
location. `test_related_locations_skip_the_findings_own_site` asserted
`["other.py", "nameless.py"]` and saw `["app.py", "other.py", "nameless.py"]` before the fix.
Closes F-10.
```

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Fixed`:

```markdown
- Skip the finding's own site when building SARIF related locations, so a cluster
  representative no longer repeats its primary location. Closes F-10.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/sarif.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): drop the self site from SARIF"
```

---

### Task 6: REQ-67 — honour an empty preconditions list

The red-team directive renders preconditions as `rt.get('preconditions') or f.preconditions`. An author who states "no preconditions are needed" writes an empty list, and `or` then falls through to the finding's stale preconditions. Distinguish the three cases: the key is absent, the key holds a non-empty value, and the key holds an empty value.

**Files:**
- Modify: `helpers/sec_overlay/redteam.py:157-190` (`_directive_block`)
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_redteam.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.redteam._bullets(items) -> str` at `redteam.py:133`. It returns `_not specified_` for an empty or non-string, non-list input. `Finding.runtime_test: dict`, `Finding.preconditions: list[str]`.
- Produces: `_directive_block(f: Finding) -> str` keeps its signature. The `- **Preconditions / access:**` line now renders `  - _(none needed)_` when `runtime_test["preconditions"]` is present and empty.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_redteam.py`. The file already defines `_f(fid, ..., runtime_test=None, ...)` at line 19.

```python
def test_an_explicit_empty_preconditions_list_renders_none_needed():
    """REQ-67: an author who states "no preconditions" must not read as "unknown"."""
    from sec_overlay.redteam import _directive_block

    f = _f("F-1", runtime_test={"objective": "hit the endpoint", "preconditions": []})
    f.preconditions = ["a stale fallback nobody asked for"]

    out = _directive_block(f)

    assert "_(none needed)_" in out
    assert "stale fallback" not in out
```

- [ ] **Step 2: Run it and see it fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_redteam.py::test_an_explicit_empty_preconditions_list_renders_none_needed -q
```

Expected: FAIL — the directive renders `a stale fallback nobody asked for`.

- [ ] **Step 3: Compute the block before rendering**

In `_directive_block`, add these four lines immediately after the `payload_md = ...` assignment and before the `lines = [` literal:

```python
    if "preconditions" in rt:
        precond_md = _bullets(rt["preconditions"]) if rt["preconditions"] else "  - _(none needed)_"
    else:
        precond_md = _bullets(f.preconditions)
```

Then replace the preconditions entry in the `lines +=` block:

```python
        f"- **Preconditions / access:**\n{precond_md}",
```

The `_(none needed)_` wording matches the `_(none supplied)_` idiom that `payload_md` already uses for an absent payload list.

- [ ] **Step 4: Run the tests and see them pass**

```bash
uv run pytest tests/test_redteam.py -q
```

Expected: PASS, including the existing `test_directive_falls_back_to_the_finding_preconditions`, which covers the absent-key case.

- [ ] **Step 5: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 6: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### An empty preconditions list means none are needed (REQ-67)

`_directive_block` in `redteam.py` renders three cases for a runtime test's preconditions:

1. The `preconditions` key is absent. The directive falls back to `Finding.preconditions`.
2. The key holds a non-empty value. The directive renders that value.
3. The key holds an empty value. The directive renders `_(none needed)_`.

Case 3 used to fall through to case 1, because the code read
`rt.get('preconditions') or f.preconditions`. An author who deliberately stated that a test
needs no preconditions saw the finding's stale list instead. The distinct wording tells a
reader that the author answered the question, and did not leave it open.
```

- [ ] **Step 7: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-67 red: an empty preconditions list fell through

`_directive_block` used `rt.get('preconditions') or f.preconditions`, which cannot tell an
absent key from an explicit empty list. A runtime test that stated "no preconditions" rendered
the finding's stale preconditions instead.
`test_an_explicit_empty_preconditions_list_renders_none_needed` failed on
`assert "stale fallback" not in out` before the fix. Closes F-8.
```

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Fixed`:

```markdown
- Render `_(none needed)_` when a runtime test declares an empty `preconditions` list, instead of
  falling back to the finding's own preconditions. Closes F-8.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/redteam.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_redteam.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): honour empty preconditions"
```

---

### Task 7: REQ-68 — check title cuts against the message

`_check_truncated_titles` compares a truncated triage title against `triage_what(finding)`. It builds the expected cell with the same helper that produced the cell, so the check cannot catch a bug inside that helper. Replace it with a property the renderer does not define: a truncated title must be a prefix of its finding's message, and the cut must fall on a word boundary.

**Files:**
- Modify: `helpers/sec_overlay/artifact_consistency.py:202-221` (`_check_truncated_titles`)
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_artifact_consistency.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.artifact_consistency._triage_rows(report_md: str) -> list[list[str]]` at lines 54-64, `sec_overlay.workspace.read_findings(ws) -> list[Finding]`, `Finding.id`, `Finding.message`. `report.triage_what(f) -> str` stays imported for the tests, not for the check.
- Produces: `_check_truncated_titles(ws: Workspace, report_md: str) -> list[str]` keeps its signature. It emits `is not a prefix of its message` for a stale or hand-edited cell, and `is truncated mid-word` for a bad cut.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_artifact_consistency.py`. Add `triage_what` to the existing `sec_overlay.report` import first:

```python
from sec_overlay.report import triage_what, write_report
```

Then add the test:

```python
def test_gate_flags_a_hand_edited_truncated_title(tmp_path):
    """REQ-68: a truncated cell that is not a prefix of its message is a stale report."""
    ws = _ws(tmp_path)
    write_findings(ws, [_ndt(message="owner check may be advisory")])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", "something nobody rendered…", "see redteam-plan gaps")
    )

    errors = run_artifact_consistency(ws)

    assert any("not a prefix" in e for e in errors), errors
```

- [ ] **Step 2: Run it and see it fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_artifact_consistency.py::test_gate_flags_a_hand_edited_truncated_title -q
```

Expected: FAIL. The old check emits `is truncated mid-word`, so no error holds `not a prefix`. This is the behavioural difference: the old check cannot tell a stale report from a bad cut.

- [ ] **Step 3: Add the two regression tests**

Append both to `helpers/tests/test_artifact_consistency.py`:

```python
def test_gate_accepts_a_title_truncated_at_a_word_boundary(tmp_path):
    """REQ-68: the renderer's own word-boundary cut is not a contradiction."""
    ws = _ws(tmp_path)
    long_message = "the owner check is advisory " * 4
    write_findings(ws, [_ndt(message=long_message)])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD
        + _triage("N-1", triage_what(_ndt(message=long_message)), "see redteam-plan gaps")
    )

    assert not any("N-1" in e for e in run_artifact_consistency(ws))


def test_gate_accepts_a_single_long_word_cut_mid_word(tmp_path):
    """REQ-68: _short_title's no-space fallback cuts inside the only word — allowed."""
    ws = _ws(tmp_path)
    word = "A" * 90
    write_findings(ws, [_ndt(message=word)])
    _selfscore(ws, {"confirmed": 0, "needs_runtime": 1})
    ws.report_path.write_text(
        _REPORT_HEAD + _triage("N-1", word[:72] + "…", "see redteam-plan gaps")
    )

    assert not any("N-1" in e for e in run_artifact_consistency(ws))
```

- [ ] **Step 4: Replace the check**

Replace `_check_truncated_titles` in `helpers/sec_overlay/artifact_consistency.py` in full:

```python
def _check_truncated_titles(ws: Workspace, report_md: str) -> list[str]:
    """Check (f): a truncated triage title must cut its message at a word boundary.

    Compares the cell against the finding's own message, not against
    ``triage_what``'s output. The old comparison built the expected cell with the
    same helper that produced it, so it could not catch a bug inside that helper.
    A prefix absent from the message means a stale or hand-edited report.
    """
    by_id = {f.id: f for f in read_findings(ws)}
    errors: list[str] = []
    for row in _triage_rows(report_md):
        what = row[2] if len(row) > 2 else ""
        finding = by_id.get(row[0])
        if not what.endswith("…") or finding is None:
            continue
        message = " ".join((finding.message or "").split())
        prefix = what[:-1]
        at = message.find(prefix)
        if at < 0:
            errors.append(
                f"artifact-consistency: triage title for {row[0]} is not a prefix of its "
                f"message: {what!r}"
            )
            continue
        rest = message[at + len(prefix) :]
        if rest and not rest.startswith(" ") and " " in prefix:
            errors.append(
                f"artifact-consistency: triage title for {row[0]} is truncated mid-word: {what!r}"
            )
    return errors
```

The `" " in prefix` condition is deliberate. `_short_title` at `report.py:294` cuts a single long word without a boundary to cut on, so a prefix with no space cannot be a mid-word defect.

- [ ] **Step 5: Run the tests and see them pass**

```bash
uv run pytest tests/test_artifact_consistency.py -q
```

Expected: PASS, including the existing `test_gate_flags_a_title_truncated_mid_word` at line 165. That test uses the message `owner check may be advisory` and the cell `owner check may be advi…`, so the new check finds the prefix at position 0, sees `sory` after it, and reports the mid-word error.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 7: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### The truncated-title gate checks a word boundary (REQ-68)

Check (f) of the artifact-consistency gate used to rebuild the expected triage cell with
`triage_what` and compare it against the cell in the report. The gate therefore asserted that
a helper agrees with itself. It could detect a hand-edited or stale report, and nothing else.

The check now tests a property the renderer does not define. It normalises the finding's
message, strips the trailing ellipsis from the cell, and locates the remaining prefix in the
message. An absent prefix is a stale or hand-edited report. A prefix followed immediately by a
non-space character is a mid-word cut, unless the prefix holds no space at all — `_short_title`
cuts a single long word with no boundary available.

Residual gap: `find` returns the first match. A prefix that also appears earlier in the message
at a position where the next character is not a space could report a false mid-word cut. No
message in the current corpus has that shape.
```

- [ ] **Step 8: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-68 red: the truncated-title check was tautological

`_check_truncated_titles` built its expected cell with `triage_what`, the same helper that
produced the cell under test. The comparison could not fail on a renderer bug, and it reported
`is truncated mid-word` for a hand-edited cell that was not a cut at all.

`test_gate_flags_a_hand_edited_truncated_title` asserts `not a prefix` and failed before the
fix. Two further tests guard the accepted cases: a correct word-boundary cut and a single long
word with no boundary. `test_gate_flags_a_title_truncated_mid_word` still passes. Closes F-12.
```

- [ ] **Step 9: Add the changelog entry**

Add under `## Unreleased`, inside `### Fixed`:

```markdown
- Check a truncated triage title against its finding's message and a word boundary, instead of
  against the renderer's own output. The old comparison could not fail. Closes F-12.
```

- [ ] **Step 10: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 11: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_artifact_consistency.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): check title cuts on word bounds"
```

---

### Task 8: REQ-69 — decode a quoted diff path

Git wraps a diff path in double quotes and escapes its bytes when the path holds a non-ASCII byte, a space, or a control character. `_patch_files` reads the raw field, so a quoted path enters the set with its quotes and escapes intact. The path then never matches the target file, and the patch-scope check silently passes a patch that touched the wrong file. Decode the quoting first.

**Files:**
- Modify: `helpers/sec_overlay/verify.py:326-347` (`_patch_files`, plus a new helper above it)
- Modify: `helpers/sec_overlay/README.md`
- Modify: `helpers/tests/test_verify_paths.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.verify._rel_path(path: str, root: str) -> str`.
- Produces: `sec_overlay.verify._unquote_path(path: str) -> str` — new module-private helper. `_patch_files(patch_diff: str) -> set[str]` keeps its signature and now returns decoded paths. The caller at `verify.py:452-453` needs no change.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_verify_paths.py`. The file already binds `from sec_overlay import verify as V`.

```python
def test_unquote_path_decodes_an_octal_escaped_utf8_path():
    """REQ-69: git escapes each non-ASCII byte in octal inside a quoted path."""
    assert V._unquote_path('"src/caf\\303\\251.py"') == "src/café.py"


def test_unquote_path_leaves_an_unquoted_path_alone():
    assert V._unquote_path("src/app.py") == "src/app.py"


def test_unquote_path_keeps_a_quoted_path_with_a_space():
    assert V._unquote_path('"src/my file.py"') == "src/my file.py"


def test_unquote_path_falls_back_to_stripping_the_quotes():
    """A body that does not decode still loses its quotes, so the path stays usable."""
    assert V._unquote_path('"src/bad\\"') == "src/bad\\"


def test_patch_files_reads_a_quoted_post_image_path():
    diff = '--- a/src/caf\\303\\251.py\n+++ "b/src/caf\\303\\251.py"\n'
    assert V._patch_files(diff) == {"src/café.py"}
```

- [ ] **Step 2: Run them and see them fail**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_verify_paths.py -q
```

Expected: the four `_unquote_path` tests fail with `AttributeError: module 'sec_overlay.verify' has no attribute '_unquote_path'`. `test_patch_files_reads_a_quoted_post_image_path` fails because the set holds the raw quoted path.

- [ ] **Step 3: Add the helper**

Insert immediately above `_patch_files` in `helpers/sec_overlay/verify.py`:

```python
def _unquote_path(path: str) -> str:
    """Decode git's C-style quoting on a diff path (see ``core.quotePath``).

    Git wraps a path in double quotes and escapes its bytes when the path holds a
    non-ASCII byte, a space, or a control character. Each byte becomes an octal
    escape, so the quoted form is pure ASCII.

    Args:
        path: One path field from a diff header, quotes included if git added them.

    Returns:
        The decoded path. An unquoted path comes back unchanged. A quoted body that
        does not decode comes back with its quotes stripped and nothing else changed.
    """
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    try:
        body = path[1:-1].encode("utf-8").decode("unicode_escape")
        return body.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return path[1:-1]
```

The two-step decode is required. `unicode_escape` turns each octal escape into one code point below U+0100. Re-encoding through `latin-1` recovers the original byte string, and decoding that as UTF-8 recovers the character.

- [ ] **Step 4: Call the helper**

In `_patch_files`, change the path extraction line:

```python
        path = _unquote_path(line[4:].split("\t", 1)[0].strip())
        if path == "/dev/null":
            continue
        files.add(_rel_path(path.removeprefix("b/"), ""))
```

Unquote before `removeprefix("b/")`. Git's quotes wrap the whole `b/<path>` field, so stripping the prefix first would leave a stray leading quote.

- [ ] **Step 5: Run the tests and see them pass**

```bash
uv run pytest tests/test_verify_paths.py -q
```

Expected: PASS, including the existing `test_patch_files_reads_the_post_image_paths` at line 66.

- [ ] **Step 6: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean.

- [ ] **Step 7: Append the package README entry**

Add at the end of `helpers/sec_overlay/README.md`:

```markdown
### Quoted diff paths are decoded (REQ-69)

`_patch_files` collects the post-image path of every file a patch touches. `verify.py` then
checks that the patch stayed inside the finding's file. Git quotes a diff path when the path
holds a non-ASCII byte, a space, or a control character, and escapes each byte in octal. The
raw field therefore never matched the target file, and the scope check passed a patch that
touched a different file.

`_unquote_path` decodes the quoting in two steps. `unicode_escape` turns each octal escape
into a code point below U+0100, and a re-encode through `latin-1` recovers the original bytes
for a UTF-8 decode. A body that does not decode keeps its bytes and loses only its quotes, so
the path stays usable and the check stays conservative.

Unquoting happens before the `b/` prefix is stripped, because git's quotes wrap the whole
field.
```

- [ ] **Step 8: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-69 red: a quoted diff path never matched

`_patch_files` read the raw `+++` field. A path git had quoted and octal-escaped entered the
set with its quotes and escapes intact, so `_path_matches` never matched it and the
patch-scope check passed a patch that touched the wrong file.

Four tests pin `_unquote_path` — an octal-escaped UTF-8 path, an unquoted path, a quoted path
holding a space, and a body that does not decode. A fifth test runs a quoted path through
`_patch_files`. All five failed before the fix. Closes F-14.
```

- [ ] **Step 9: Add the changelog entry**

Add under `## Unreleased`, inside `### Fixed`:

```markdown
- Decode git's C-style quoting on a diff path before the patch-scope check, so a path holding a
  non-ASCII byte or a space no longer bypasses the check. Closes F-14.
```

- [ ] **Step 10: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 11: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): decode quoted diff paths"
```

---

### Task 9: REQ-70 — assert fetch overlap, not elapsed time

`test_review_fetches_files_concurrently_bounded_by_max_git_procs` asserts `elapsed < len(paths) * sleep_seconds`. A wall-clock bound turns a loaded machine into a test failure, and it proves concurrency only indirectly. Count the concurrent fetches inside the fake runner and assert the observed peak.

**Files:**
- Modify: `helpers/tests/test_cli.py:501-528`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.cli.run_review(base, head, root, *, runner, max_git_procs)`, and `_FakeResult(stdout="", returncode=0)` at `tests/test_cli.py:114`.
- Produces: nothing. This is a test-only change.

- [ ] **Step 1: Replace the test**

Replace `helpers/tests/test_cli.py:501-528` in full:

```python
def test_review_fetches_files_concurrently_bounded_by_max_git_procs(tmp_path):
    """REQ-70: a pool runs more than one per-file fetch at once. A serial loop cannot.

    Asserts the observed peak of concurrent fetches, not elapsed time. A wall-clock
    bound turns a loaded machine into a test failure and only proves overlap
    indirectly.
    """
    import threading
    import time

    from sec_overlay import cli

    paths = ["a.py", "b.py", "c.py"]
    sleep_seconds = 0.05
    lock = threading.Lock()
    state = {"live": 0, "peak": 0}

    def runner(cmd, capture_output, text, check):
        if cmd[1] == "rev-parse":
            return _FakeResult(f"sha-{cmd[-1]}\n")
        if cmd[1] == "diff" and "--name-status" in cmd:
            return _FakeResult("".join(f"M\t{p}\n" for p in paths))
        if cmd[1] == "diff" and ("--unified=3" in cmd or "--unified=0" in cmd):
            with lock:
                state["live"] += 1
                state["peak"] = max(state["peak"], state["live"])
            time.sleep(sleep_seconds)
            with lock:
                state["live"] -= 1
            path = cmd[-1]
            return _FakeResult(f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n")
        return _FakeResult("")

    rc = cli.run_review(
        "main", "develop", str(tmp_path), runner=runner, max_git_procs=len(paths)
    )

    assert rc == 0
    assert state["peak"] > 1, state
```

The sleep stays. Without it, each fetch returns before the next one starts, and the peak would be 1 even with a working pool.

- [ ] **Step 2: Run the test**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_cli.py::test_review_fetches_files_concurrently_bounded_by_max_git_procs -q
```

Expected: PASS with a peak above 1.

- [ ] **Step 3: Prove the assertion is live**

Temporarily change `max_git_procs=len(paths)` to `max_git_procs=1` and run the test again.

Expected: FAIL with `assert state["peak"] > 1` and `{'live': 0, 'peak': 1}`. Record the failure line in the task report, then restore `max_git_procs=len(paths)` and confirm the test passes again.

- [ ] **Step 4: Run the full gate**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean. `ruff` must report no unused import for the removed `time.monotonic` use — `time` is still used by the sleep.

- [ ] **Step 5: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-70 red: the concurrency test asserted wall-clock time

`test_review_fetches_files_concurrently_bounded_by_max_git_procs` asserted
`elapsed < len(paths) * sleep_seconds`. A loaded machine could fail the test with correct
code, and the bound proved overlap only indirectly. The fake runner now counts its own
concurrent calls under a lock and the test asserts the peak is above 1.

Setting `max_git_procs=1` drops the peak to 1 and fails the assertion, which is the proof the
assertion is live.

Trade-off: the test no longer covers the value of the bound. `test_review_default_bounds_are_8_600_and_16`
at line 475 already asserts `{"concurrency": 8, "timeout": 600, "max_git_procs": 16}`, so the
bound stays pinned elsewhere. Closes F-13.
```

- [ ] **Step 6: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Assert the observed peak of concurrent git fetches in the review concurrency test, instead of
  a wall-clock bound that a loaded machine could fail. Closes F-13.
```

- [ ] **Step 7: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 8: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): assert fetch overlap not time"
```

---

## Requirement Coverage

| Requirement | Finding | Task |
|-------------|---------|------|
| REQ-62 | F-4 | Task 1 |
| REQ-63 | F-5 | Task 2 |
| REQ-64 | F-6 | Task 3 |
| REQ-65 | F-7 | Task 4 |
| REQ-66 | F-10 | Task 5 |
| REQ-67 | F-8 | Task 6 |
| REQ-68 | F-12 | Task 7 |
| REQ-69 | F-14 | Task 8 |
| REQ-70 | F-13 | Task 9 |

REQ-71 (F-9 and F-11) is the companion plan at `docs/superpowers/plans/2026-09-02-sec-overlay-readme-ste-rewrite.md`. Run this plan first. It appends nine sections to `helpers/sec_overlay/README.md`, and the companion plan re-measures that file's lint baseline before it starts.

## Deviations from the Spec

Two corrections to the spec's literal text, carried here on purpose:

1. REQ-62. The spec shows the derived frozenset inlined inside the tuple entry. At the 12-space indent that line reaches 105 characters and fails the 100-character limit. Task 1 hoists a `receipt_tiers` local instead. The value is identical.
2. Every `helpers/sec_overlay/README.md` entry in this plan is written to pass the STE100 structural lint — no semicolons, sentences under 25 words. The companion plan makes that file lint-clean, so an entry added here must not add a new error.
