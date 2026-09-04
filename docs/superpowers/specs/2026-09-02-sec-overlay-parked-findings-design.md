# sec-overlay parked-findings repair — design

**Date:** 2026-09-02
**Status:** approved for planning
**Supersedes:** nothing. Extends `2026-09-01-sec-overlay-defect-repairs-design.md` (REQ-40 to REQ-61).

## Context

Five subagent-driven plans ran against `2026-09-01-sec-overlay-defect-repairs-design.md`. Each plan
parked findings that its own scope did not cover. The ledgers hold eleven such findings, each with a
ruling that names the file, the line, and the reason for the deferral. The ledgers live under
`.superpowers/sdd/`, which git ignores. This specification moves those eleven findings into a
tracked document and defines one correction for each.

The eleven findings and their ledger sources:

| Finding | Ledger | Line |
|---------|--------|------|
| F-4, F-5, F-6 | `2026-09-01-sec-overlay-constraint-enforcers/progress.md` | 213-221 |
| F-7 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 140 |
| F-8 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 163 |
| F-9 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 168 |
| F-10 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 232 |
| F-11 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 270 |
| F-12 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 304-312 |
| F-13 | `2026-09-01-sec-overlay-population-reconciliation/progress.md` | 314 |
| F-14 | `2026-09-01-sec-overlay-verify-precision-and-doc-generation/progress.md` | 177 |

No finding in this set produces a wrong audit result today. Each is a latent defect, a test that
cannot fail on drift, or a prose deviation. The value of the change is that a later edit cannot turn
a latent defect into a live one without a test catching it.

## Non-goals

- No new feature and no new pipeline phase.
- No change to any finding schema, enum, or published vocabulary.
- No change to what the harness reports to a user, except the two corrections REQ-67 and REQ-71
  state explicitly.
- No edit to `sec_overlay/models.py` or `sec_overlay/evidence.py`. See Global constraints.

## Global constraints

1. **`sec_overlay/models.py` and `sec_overlay/evidence.py` are byte-frozen.**
   `helpers/tests/test_frozen_contract.py` pins the sha256 of both files. Each file is a
   byte-identical mirror of a separate Go port. An edit to either requires a hand-applied identical
   Go change, a sign-off, and a re-pin. No requirement in this specification edits either file. This
   constraint decides the shape of REQ-62 and REQ-63.
2. **Every code change lands test-first.** Write the failing test, run it, confirm it fails for the
   stated reason, then write the fix.
3. **The helpers package is stdlib-only.** `pyproject.toml` declares zero runtime dependencies, and
   `test_helpers_declare_zero_runtime_dependencies` pins that. No requirement adds a dependency.
4. **Line length is 100 characters** (`ruff` configuration in `helpers/pyproject.toml`).
5. **Per-commit gate:** run `uv run pytest -q`, `uv run ruff check sec_overlay/ bench/ tests/`,
   `uv run ty check`, and `prek run` from `plugins/sec-overlay/skills/sec-overlay/helpers/`.
6. **Version bump.** Every commit in this change touches a shipping file. Bump the `version` field
   in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit. Every requirement here is
   a `fix`, a `refactor`, a `test`, or a `docs` commit, so every bump is a patch bump. Read
   `plugin.json` before each bump. Do not trust a version literal written in this document.
7. **Repository governance.** Branch per change. Conventional Commits. Stage explicit paths only.
   Never `git add -A`. Never `--no-verify`.
8. **Commit contents.** No `Co-Authored-By` trailer. Update the plugin `CHANGELOG.md` and the
   changed folder's `README.md` in the same commit.
9. **Do not merge and do not push.** The branch stays local until the user says otherwise.
10. **A stray git repository sits at `helpers/.git`.** Its working tree is permanently dirty. Run
   every git command with `git -C <repo-root>`. Do not read `helpers/.git` as branch state.

All paths below are relative to
`plugins/sec-overlay/skills/sec-overlay/helpers/` unless stated otherwise.

---

## Group A — declarations that cannot fail on drift

Three tests or constants restate a value the code already holds. Each restatement can drift from the
code without any test failing. Each correction replaces the restatement with a reference to the real
producer.

### REQ-62 (F-4) — the contract lint derives the receipt-tier set from `receipt_tier`

**Current state.** `tests/test_contract_lint.py:48` pins the schema's `receipt_tier` enum against the
literal `frozenset({1, 2})`. Neither side of that comparison is a code constant, so a new tier or a
changed tier mapping passes the test.

**Constraint.** The obvious fix is a `RECEIPT_TIERS` constant in `evidence.py`. Global constraint 1
forbids that edit.

**Correction.** Derive the expected set from the function that assigns the tier. `receipt_tier` is
already public in `evidence.py` at line 70. `TIER1_RECEIPTS` and `TIER2_RECEIPTS` are already
imported at `tests/test_contract_lint.py:23-28`. Add `receipt_tier` to that import and replace the
literal with:

```python
("receipt_tier", frozenset(receipt_tier(f"{p}:x") for p in TIER1_RECEIPTS | TIER2_RECEIPTS)),
```

**Acceptance.** The test passes unchanged against the current schema. A new prefix that maps to a
tier the schema does not list fails the test. A prefix moved between `TIER1_RECEIPTS` and
`TIER2_RECEIPTS` does not fail the test, because the tier set is unchanged. That is correct: the
schema enum names the tier values, not the prefix-to-tier mapping.

### REQ-63 (F-5) — `_RULE_ORIGINS` holds only prefixes the harness writes

**Current state.** `sec_overlay/rule_gaps.py:19` declares six rule-origin prefixes:

```python
_RULE_ORIGINS = ("semgrep:", "codeql:", "sca:", "secrets:", "asvs:", "codeguard:")
```

Nothing in the harness writes an `asvs:` or a `codeguard:` evidence source. `rule_matcher.py:39-44`
maps a name pattern to an `asvs` list and a `codeguard` list, but both flow into the separate
`Finding.asvs_ids` and `Finding.codeguard_ids` fields, never into `Finding.evidence_sources`. Both
prefixes are dead. The defect is latent because `rule_gaps.py` only
reads. If a later change starts writing an `asvs:` source, that source becomes rule-originated
without a decision, and `record_rule_gaps` silently stops recording a real rule gap.

**Constraint.** The alternative fix is to add both prefixes to `evidence._MECHANICAL`. Global
constraint 1 forbids that edit. Dropping the dead prefixes is therefore the only available
correction, not a preference.

**Correction.** Two parts.

1. Reduce `_RULE_ORIGINS` to the four prefixes the harness writes:
   `("semgrep:", "codeql:", "sca:", "secrets:")`. Update the comment above it to say that every
   entry must be a mechanical receipt prefix.
2. Add a test that asserts the invariant, so the pair cannot diverge again. The test asserts that
   every entry in `_RULE_ORIGINS`, with its trailing colon removed, is a member of
   `evidence._MECHANICAL`.

**Acceptance.** `is_rule_originated` returns the same verdict for every finding the harness can
produce today, because no finding carries an `asvs:` or a `codeguard:` source. Adding a prefix to
`_RULE_ORIGINS` that `_MECHANICAL` does not hold fails the new test.

**Residual, stated.** The new test constrains `_RULE_ORIGINS` to a subset of `_MECHANICAL`. It does
not assert the reverse. `ripgrep:`, `ast-grep:`, `structural-index:`, `tree-sitter:`, and
`dependency-catalog:` are mechanical but are deliberately not rule origins, because they locate code
rather than detect a defect. That asymmetry is the module's stated design.

### REQ-64 (F-6) — the wiring guard iterates the real receipt constants

**Current state.** `tests/test_wiring.py:53-59` iterates a hardcoded six-prefix tuple:

```python
for prefix in ("secrets", "sca", "semgrep", "codeql", "ast-grep", "ripgrep"):
    assert prefix in _MECHANICAL
    assert is_tool_receipt(f"{prefix}:x") is True
```

`_MECHANICAL` holds nine prefixes. `structural-index`, `tree-sitter`, and `dependency-catalog` are
never checked.

**Correction.** Import `TIER1_RECEIPTS` and `TIER2_RECEIPTS` in `tests/test_wiring.py` and iterate
their union. Drop the `prefix in _MECHANICAL` assertion, which becomes a tautology, and assert the
two behaviours instead:

```python
for prefix in TIER1_RECEIPTS | TIER2_RECEIPTS:
    assert is_tool_receipt(f"{prefix}:x") is True
    assert receipt_tier(f"{prefix}:x") in (1, 2)
```

**Acceptance.** All nine prefixes are checked. A prefix added to either constant is checked with no
test edit.

**Residual, stated.** This does not close the census-error class in the direction the finding's name
suggests. No constant names the set of backends `prefilter.py` can run, so a new backend that emits
a receipt prefix absent from `evidence.py` still passes. Closing that direction requires a new
backend-name constant, which is new surface and is out of scope here.

---

## Group B — mutation and duplicate output

### REQ-65 (F-7) — `collapse_clusters` does not mutate its input

**Current state.** `sec_overlay/report.py:604-630`. When no cluster member already carries
`affected_sites`, the function elects the highest-risk member and writes the synthesized site list
onto that member in place:

```python
primary = min(members, key=_risk_sort_key)
primary.affected_sites = [{"id": m.id, "file": m.file, "line": m.line} for m in members]
```

The `Finding` object belongs to the caller. `selfscore.build_self_score` calls `collapse_clusters`
twice over overlapping subsets of the same in-memory list (`selfscore.py:68-69`). The second call
therefore sees a list the first call wrote. The result is correct today, because the two calls
synthesize the same list and `build_self_score` returns counts without persisting the objects. The
defect is that a documented pure-looking reducer writes to its argument.

**Correction.** Build the representative as a copy. `Finding` is a plain `@dataclass` with no
`__post_init__` and no non-init field, so `dataclasses.replace` is safe. `report.py` already imports
from `dataclasses` at line 8. Add `replace` to that import and use:

```python
primary = replace(
    min(members, key=_risk_sort_key),
    affected_sites=[{"id": m.id, "file": m.file, "line": m.line} for m in members],
)
```

Update the docstring to say the input findings are never modified.

**Acceptance.** A test builds a two-member cluster whose members carry no `affected_sites`, calls
`collapse_clusters`, and asserts that every input `Finding` still has an empty `affected_sites` while
the returned representative carries both sites. The existing report and self-score tests pass
unchanged.

**Note on the copy.** `dataclasses.replace` is shallow. The returned representative shares list
objects such as `history` and `evidence_sources` with the original. That is acceptable, because
every consumer of the returned list renders rather than mutates.

### REQ-66 (F-10) — SARIF related locations exclude the finding's own site

**Current state.** `sec_overlay/cluster.py:81` builds `affected_sites` from every cluster member,
the elected primary included. `sec_overlay/sarif.py:75-99` `_related_locations` turns each site into
a SARIF `relatedLocations` entry. The SARIF result's own `locations` array already carries the
primary, so a real cluster reports the primary location twice.

**Where the correction belongs.** Not in `cluster.py`. `affected_sites` has two consumers. The report
renders it as the cluster's sites table (`report.py:279-287`), where the primary belongs, because a
reader needs the full member list. Only the SARIF path duplicates. Removing the primary from
`affected_sites` would fix SARIF and break the report.

**Correction.** In `_related_locations`, skip the site whose `id` equals the finding's own `id`. A
site with no `id` key is kept, as is a site whose `id` names a different finding. Update the
docstring to record the exclusion and its reason.

**Acceptance.** A test builds a finding whose `affected_sites` holds its own id plus two others, calls
`to_sarif`, and asserts `relatedLocations` holds exactly the two other sites. A test with an
`affected_sites` entry that carries no `id` asserts that entry survives.

---

## Group C — behaviour the earlier specification mandated

Both requirements in this group change behaviour an earlier specification asked for. Each ruling in
the ledgers deferred the change on the ground that the earlier specification was binding at the
time. This specification is the later authority.

### REQ-67 (F-8) — an explicitly empty `preconditions` list renders as "none needed"

**Current state.** `sec_overlay/redteam.py:180-183`:

```python
f"- **Objective:** {rt.get('objective', f.message)}",
f"- **Preconditions / access:**\n{_bullets(rt.get('preconditions') or f.preconditions)}",
```

Line 181 uses a default argument, so it falls back only when the key is absent. Line 182 uses `or`,
so it falls back when the key is absent **and** when the key holds an empty list. A red-team payload
that states "no preconditions needed" by supplying `"preconditions": []` is overwritten by the
finding's own precondition list. The file is internally inconsistent: two adjacent lines apply
different absent-versus-empty rules.

**Correction.** Distinguish three cases.

| `runtime_test["preconditions"]` | Rendered |
|--------------------------------|----------|
| key absent | `_bullets(f.preconditions)` — unchanged |
| present and non-empty | `_bullets(<the list>)` — unchanged |
| present and empty | `  - _(none needed)_` |

The third row is a behaviour change. Rendering `_bullets([])` would print `_not specified_`, which
reads as "unknown" and is a second wrong message. `_(none needed)_` matches the idiom the payload
branch already uses at `redteam.py:171` (`_(none supplied)_`).

**Acceptance.** Three tests, one per row of the table above. The existing red-team rendering tests
pass unchanged, because none of them supplies an empty `preconditions` list.

### REQ-68 (F-12) — the truncated-title check tests an independent property

**Current state.** `sec_overlay/artifact_consistency.py:202-221`, clause (f). The check rebuilds the
expected cell with `report.triage_what` and compares it to the rendered cell. The renderer and the
expectation are the same function, so the clause cannot detect a defect in `triage_what`. It detects
only a hand-edited or stale report. Ruling P4-16 recorded that REQ-56 mandated this reuse, and
corrected the docstring's overclaim rather than the assertion.

**Correction.** Replace the comparison with a property that does not call `triage_what`.

`report._short_title` (`report.py:294-309`) documents the invariant: "Never cuts a word." Its output
is always a whitespace-normalised substring of its input, and `triage_what` only splits and clips the
message, so the rendered cell is always a substring of the whitespace-normalised
`finding.message`. The property to assert is therefore:

> For a cell ending in the ellipsis character, the cell with the ellipsis removed appears in the
> whitespace-normalised `finding.message`, and the character following that occurrence is a space or
> the end of the message.

**The one exception to encode.** `_short_title` has a fallback branch. When the first `limit`
characters hold no space, it cuts mid-word deliberately, because no word boundary exists. The check
must not fire on that legitimate output. Add the guard: flag a mid-word cut only when the cell itself
contains a space.

**Correction, stated as logic.**

1. Normalise `finding.message` whitespace with `" ".join(message.split())`.
2. Strip the trailing ellipsis from the cell to get `prefix`.
3. Find `prefix` in the normalised message. Absent means the report is stale — report an error.
4. Take the text that follows the occurrence. If it is non-empty, does not start with a space, and
   `prefix` contains a space, report a mid-word truncation error.

Rewrite the docstring: the clause now detects a real `triage_what` defect as well as a stale report.

**Acceptance.** Four tests. A correctly truncated cell passes. A hand-edited cell absent from the
message fails. A cell cut mid-word fails. A cell built from a single word longer than the limit
passes, exercising the fallback guard.

**Trade-off.** The new clause can fire on a report that is correct but whose findings file changed
after rendering. The old clause had the same exposure. The new clause also depends on `triage_what`
keeping the property that the cell is a substring of the message. If a future change makes
`triage_what` rewrite rather than clip the message, this clause becomes a false halt. That risk is
recorded, not mitigated: rewriting the cell would be a larger contract change and would need its own
decision.

---

## Group D — parser and test robustness

### REQ-69 (F-14) — `_patch_files` decodes a git-quoted path

**Current state.** `sec_overlay/verify.py:326-347`. The function reads `+++ b/<path>` headers as
plain text:

```python
path = line[4:].split("\t", 1)[0].strip()
if path == "/dev/null":
    continue
files.add(_rel_path(path.removeprefix("b/"), ""))
```

Git wraps a path in double quotes and applies C-style escaping when the path holds a double quote, a
backslash, or a non-ASCII byte with `core.quotePath` enabled. The parsed entry then keeps the quote
marks and the escapes, and `_path_matches` fails to match the real file. The failure direction is
safe: a real fix reads as unconfirmed, never as verified. A path holding a plain space is not quoted
by git and parses correctly today.

**Correction.** Decode the quoting before stripping the `b/` prefix. The quote wraps the whole
`b/<path>` token, so the order matters. Add a private helper:

```python
def _unquote_path(path: str) -> str:
    """Decode git's C-style quoting on a diff path (see ``core.quotePath``)."""
    if len(path) < 2 or not (path.startswith('"') and path.endswith('"')):
        return path
    try:
        body = path[1:-1].encode("utf-8").decode("unicode_escape")
        return body.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return path[1:-1]
```

Git emits only ASCII inside the quotes, so `decode("unicode_escape")` maps each escape to one
codepoint at or below 255, and `encode("latin-1")` recovers the original bytes. The `except` branch
preserves the current fail-safe direction for anything the decoder cannot handle.

**Acceptance.** Four tests. An unquoted path parses as today. A path quoted for an embedded double
quote decodes. A path quoted for a non-ASCII byte, written as three-digit octal escapes, decodes to
the real name. A path with a plain space still parses. One end-to-end test asserts that a patch
touching a quoted path now reaches `_path_matches` with the real name.

### REQ-70 (F-13) — the concurrency test measures concurrency

**Current state.** `tests/test_cli.py:501-528`
`test_review_fetches_files_concurrently_bounded_by_max_git_procs` sleeps 0.05 seconds per fake fetch
and asserts `elapsed < len(paths) * sleep_seconds`. The test passes on an idle machine and fails
under load. It measures wall-clock, not the property it names.

**Correction.** Replace the timing assertion with a direct measurement of peak concurrency. Keep a
lock-guarded in-flight counter inside the fake `runner`. Increment on entry to the fetch branch,
record the maximum, sleep, then decrement. Assert the recorded maximum is greater than 1. Keep the
sleep, which is what lets the workers overlap. Delete the `start`, `elapsed`, and `time.monotonic`
lines. Update the docstring to state the new claim.

**Acceptance.** The test passes under `pytest -q` and under `pytest -n` style load. Setting
`max_git_procs=1` makes the peak equal 1, which fails the assertion. Confirm that inversion during
implementation, then revert it.

**Trade-off.** The new assertion proves the pool overlaps at least two fetches. It does not prove the
pool is bounded by `max_git_procs`. The adjacent test at `tests/test_cli.py:495` already pins the
`max_git_procs` value that reaches the pool, so the bound is covered elsewhere.

---

## Group E — the package README

### REQ-71 (F-9, F-11) — `sec_overlay/README.md` passes the STE structural lint

**Current state.** `sec_overlay/README.md` is 1810 lines. Lines 1 to 18 are a real package
introduction. Lines 19 to about 1386 are one heading-free block of appended change descriptions.
Lines 1387 to 1810 carry per-requirement headings. Two separate reviewers raised the prose style as
an informational finding, and both rulings deferred a rewrite as its own change.

**Measured baseline.** The repository ships its own deterministic linter for the checkable subset of
ASD-STE100 at `sec_overlay/ste_lint.py`. Run against the README today it reports:

```
125 errors: 119 "semicolon in prose", 6 "sentence over 25 words"
0 warnings
```

**Resolved ambiguity — which word limit applies.** The two ledger entries cite STE100's 20-word
instruction limit. `ste_lint._SENTENCE_MAX` is 25, the description limit. The README is descriptive
prose, not a procedure, so 25 is the correct limit. The repository's own linter is the acceptance
bar, because it is the only bar a test can check. Do not hand-count words against 20.

**Correction.** Rewrite the prose so `ste_lint.lint_prose` reports zero errors and zero warnings.
Three rules bound the rewrite.

1. **Prose only.** Do not change any code fence, identifier, command, file path, link target, or
   quoted output. Do not change a factual claim. If a sentence is wrong, record it and leave it. A
   factual correction is a separate change with its own verification.
2. **Split, do not delete.** Every semicolon becomes a sentence boundary. Every over-long sentence
   becomes two. The rewrite may reorganise and may add headings, but it must not drop a stated fact.
3. **Add headings to the heading-free block.** Lines 19 to about 1386 hold no heading. Group the
   entries under headings so a reader can navigate. Headings are exempt from the lint.

**Acceptance.** A new test in `tests/test_docs_invariants.py`, modelled on
`test_assurance_case_ste_lint_clean` at line 323:

```python
def test_package_readme_ste_lint_clean():
    """REQ-71 acceptance: the package README passes the STE structural lint."""
    from sec_overlay.ste_lint import lint_prose

    errors, warnings = lint_prose(_PKG_README.read_text())
    assert errors == [], errors
    assert warnings == [], warnings
```

`_PKG_README` resolves to `helpers/sec_overlay/README.md`. The test is the durable guard: a later
appended paragraph that reintroduces a semicolon fails it.

**Sequencing.** Add the test first and confirm it fails with 125 errors. Then rewrite in sections,
committing each section. The test stays red until the final section lands. That is a deliberate
departure from the usual red-green-per-commit rhythm, because the file is too large for one commit.
Each intermediate commit must reduce the error count, and the plan must state the expected count
after each one.

**Value, stated honestly.** This requirement buys style consistency and a guard against future
drift. It fixes no defect and changes no behaviour. It is the largest piece of the change by edit
volume.

---

## Requirement-to-finding map

| Requirement | Finding | File | Kind |
|-------------|---------|------|------|
| REQ-62 | F-4 | `tests/test_contract_lint.py:48` | test |
| REQ-63 | F-5 | `sec_overlay/rule_gaps.py:19` | fix |
| REQ-64 | F-6 | `tests/test_wiring.py:53-59` | test |
| REQ-65 | F-7 | `sec_overlay/report.py:604-630` | refactor |
| REQ-66 | F-10 | `sec_overlay/sarif.py:75-99` | fix |
| REQ-67 | F-8 | `sec_overlay/redteam.py:182` | fix |
| REQ-68 | F-12 | `sec_overlay/artifact_consistency.py:202-221` | fix |
| REQ-69 | F-14 | `sec_overlay/verify.py:326-347` | fix |
| REQ-70 | F-13 | `tests/test_cli.py:501-528` | test |
| REQ-71 | F-9, F-11 | `sec_overlay/README.md` | docs |

## Build order

The ten requirements are independent. No requirement consumes an interface another produces. Two
ordering preferences apply.

1. Run REQ-62, REQ-63, and REQ-64 first. They are the smallest, and each is confined to one or two
   files.
2. Run REQ-71 last. It is the largest by edit volume and touches no code.

## Risk

| Risk | Requirement | Mitigation |
|------|-------------|------------|
| A dropped rule-origin prefix silences a rule gap the harness does record | REQ-63 | Verified by search that nothing writes `asvs:` or `codeguard:` into `evidence_sources`. The new lint fails if a later change adds a prefix outside `_MECHANICAL`. |
| The new truncated-title clause becomes a false halt | REQ-68 | The fallback-branch guard covers the one legitimate mid-word cut. Recorded as an accepted residual above. |
| A shallow `dataclasses.replace` copy shares mutable lists | REQ-65 | Every consumer of the returned list renders rather than mutates. Stated in the requirement. |
| The README rewrite silently drops a fact | REQ-71 | Prose-only rule. Section-by-section commits keep each diff reviewable. |
