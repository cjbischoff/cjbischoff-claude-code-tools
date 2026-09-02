# sec-overlay Package README STE Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `sec_overlay/README.md` so it passes the repository's ASD-STE100 structural lint with zero errors and zero warnings (REQ-71), guarded by a test that lands before the rewrite starts.

**Architecture:** One acceptance test, then one file rewritten in six ordered parts, one commit per part. The lint is additive over the file's text, so each part's error count subtracts from the whole-file count and the remaining count after each commit is a checkable number. The test is committed red and stays red until the last part lands. The spec authorises that departure from red-green-per-commit, because the file is too large for one commit.

**Tech Stack:** Markdown, `sec_overlay.ste_lint` (stdlib-only Python), `pytest`, `uv`.

**Spec:** `docs/superpowers/specs/2026-09-02-sec-overlay-parked-findings-design.md`

## Global Constraints

- Run `docs/superpowers/plans/2026-09-02-sec-overlay-parked-code-repairs.md` first. That plan appends nine sections to this same file. Starting here first would force a rebase of every part boundary.
- Prose only. Do not change a code fence, an identifier, a command, a path, a link, or a block of quoted tool output. Do not correct a fact. This requirement is a style pass and nothing else.
- Split, do not delete. Every fact in the file must survive the rewrite. A sentence over the word limit becomes two sentences, never one shorter sentence that drops a clause.
- The bar is `sec_overlay.ste_lint.lint_prose`. It is the only checkable criterion. `_SENTENCE_MAX` is 25 and `_PARA_MAX_SENTENCES` is 6. The ASD-STE100 standard states a 20-word limit for an instruction, but this file is descriptive prose and the linter is the gate. Do not hand-count words against 20.
- The three error classes are `semicolon in prose`, `sentence over 25 words`, and `paragraph over 6 sentences`. The two warning classes are `sequence buried in prose (use a list)` and `possible noun cluster over 3 words`. The acceptance test asserts both lists are empty, so do not introduce a warning while fixing an error.
- Headings are exempt from the lint. Adding a heading is always safe.
- Maximum line length is 100 characters for Python. Markdown prose in this file has no line-length gate, so follow the file's existing wrap.
- **The test suite is red from Task 2 until Task 8.** Exactly one test may fail — `test_package_readme_ste_lint_clean` — and its reported error count must strictly decrease at every commit. Any other failing test, or a count that does not fall, stops the task. No commit uses `--no-verify`; the repository's hooks do not run pytest, so a red suite still commits.
- Per-commit gate, run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:
  ```bash
  uv run pytest -q
  uv run ruff check sec_overlay/ bench/ tests/
  uv run ty check
  uv run python -m sec_overlay.phase_docs --check
  ```
  Then `prek run` from the repository root. The last three must be clean at every commit. `pytest` must be clean at Task 8, and may report the one known failure before it.
- Bump the plugin version once per commit. Read `plugins/sec-overlay/.claude-plugin/plugin.json`, then increment the patch component. Do not trust a version literal written here.
- Repository governance: work on a branch, never on `main`. Use Conventional Commits: `<type>(<scope>): <imperative summary under 50 chars>`. Stage explicit paths only. Never use `git add -A`, `git add .`, `git commit -a`, or `--no-verify`.
- Commit contents: add no `Co-Authored-By` trailer. Every commit updates `plugins/sec-overlay/CHANGELOG.md`.
- Do not merge and do not push. The user withheld that permission.
- A stray second git repository sits at `plugins/sec-overlay/skills/sec-overlay/helpers/.git` with a permanently dirty working tree. Always run git with `git -C /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools`.

## Paths

Every path below is relative to the repository root.

- Target file: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Test file: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py`

For brevity the tasks write `helpers/` for `plugins/sec-overlay/skills/sec-overlay/helpers/`.

## Staging Sets

**The test commit** (Task 2):

```
helpers/tests/test_docs_invariants.py
helpers/tests/README.md
plugins/sec-overlay/CHANGELOG.md
plugins/sec-overlay/.claude-plugin/plugin.json
```

**A rewrite commit** (Tasks 3 to 8):

```
helpers/sec_overlay/README.md
plugins/sec-overlay/CHANGELOG.md
plugins/sec-overlay/.claude-plugin/plugin.json
```

`helpers/sec_overlay/README.md` is the immediate folder's own `README.md`, so it satisfies the doc-update hook by itself. `plugins/sec-overlay/.claude-plugin/` holds only `plugin.json` and has no tracked `README.md`, so it adds no further requirement.

## Measuring the Lint

Three commands drive this plan. Save all three.

**The test as a meter.** From Task 2 onward this is the primary measurement, because it is the acceptance criterion itself:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

The failure prints the error list. Count its entries. That count is what must fall at every commit.

**Whole-file count**, for the breakdown by error class:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "
from pathlib import Path
from sec_overlay.ste_lint import lint_prose
errors, warnings = lint_prose(Path('sec_overlay/README.md').read_text())
print('errors', len(errors))
print('warnings', len(warnings))
for e in errors:
    print('E', e)
for w in warnings:
    print('W', w)
"
```

**One part's count**, given a 1-based inclusive line range:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "
import sys
from pathlib import Path
from sec_overlay.ste_lint import lint_prose
lo, hi = int(sys.argv[1]), int(sys.argv[2])
text = '\n'.join(Path('sec_overlay/README.md').read_text().splitlines()[lo - 1 : hi])
errors, warnings = lint_prose(text)
print('errors', len(errors), 'warnings', len(warnings))
" <LO> <HI>
```

The lint is additive over line ranges. Splitting the file into disjoint ranges and summing each range's error count reproduces the whole-file count. That property is what makes each part's target checkable, and Task 1 verifies it before any rewriting starts.

The error strings state the class of the problem. They may not carry a line number. Locate offenders directly instead:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md
```

Roughly 119 of the 125 baseline errors are semicolons, so this finds nearly all of them. A semicolon inside a code fence, an inline code span, or a command is not prose. Leave it alone, and confirm the lint agrees by re-measuring after each edit.

---

### Task 1: Measure the baseline and fix the part boundaries

The plan's per-part targets were computed against a 1810-line file with 125 errors. The companion code-repair plan appends nine sections to the same file before this plan starts, so the totals must be re-derived rather than assumed.

**Files:**
- Read only: `helpers/sec_overlay/README.md`
- Create: `<sdd workspace>/readme-ste-baseline.md`

**Interfaces:**
- Consumes: `sec_overlay.ste_lint.lint_prose(text: str) -> tuple[list[str], list[str]]`.
- Produces: a baseline file naming six line ranges and each range's error and warning count. Tasks 3 to 8 read their target from it.

- [ ] **Step 1: Take the whole-file count**

Run the whole-file command from the Measuring the Lint section. Record the error count, the warning count, and the count per error class.

Expected shape: most errors are `semicolon in prose`, a handful are `sentence over 25 words`, and warnings are 0. The reference measurement on the pre-append file was 125 errors and 0 warnings, of which 119 were semicolons and 6 were long sentences.

- [ ] **Step 2: Locate the six part boundaries**

Find each anchor's current line number. The anchors are text, not line numbers, so they survive the companion plan's appends.

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'whether the run produced one\. `render_ndt`' sec_overlay/README.md
rg -n 'gained `synthesize_manifest\(product, members\) -> dict`' sec_overlay/README.md
rg -n 'see which layer a rule came from without running a review' sec_overlay/README.md
rg -n 'line for a scoped npm-style identifier' sec_overlay/README.md
rg -n 'renders eight optional elements on a finding page' sec_overlay/README.md
wc -l < sec_overlay/README.md
```

Each command must print exactly one line. If one prints zero lines or more than one, stop and report — the file drifted and the boundaries need re-choosing.

The six parts are then:

| Part | Range |
|------|-------|
| 1 | line 1 to (anchor 1 − 1) |
| 2 | anchor 1 to (anchor 2 − 1) |
| 3 | anchor 2 to (anchor 3 − 1) |
| 4 | anchor 3 to (anchor 4 − 1) |
| 5 | anchor 4 to (anchor 5 − 1) |
| 6 | anchor 5 to the last line |

Part 6 absorbs everything the companion plan appended.

- [ ] **Step 3: Count each part**

Run the one-part command once per range. Record all six error counts and all six warning counts.

- [ ] **Step 4: Check additivity**

The six error counts must sum to the whole-file error count from Step 1. The six warning counts must sum to the whole-file warning count.

If the sums do not match, the lint is not additive across a boundary — a boundary probably falls inside a paragraph. Move that boundary to the next blank line and re-count. Do not proceed with a mismatch: every later task's target depends on this property.

The reference measurement produced per-300-line counts of 25, 21, 19, 18, 19, and 23, which sum to 125.

- [ ] **Step 5: Write the baseline file**

Write `<sdd workspace>/readme-ste-baseline.md`. Use the workspace path this plan's runner prints. Content:

```markdown
# REQ-71 baseline

Measured before any rewriting.

Whole file: <E> errors, <W> warnings.
By class: semicolon in prose <n>, sentence over 25 words <n>, paragraph over 6 sentences <n>.

| Part | Range | Errors | Warnings | Remaining after this part |
|------|-------|--------|----------|---------------------------|
| 1 | <lo>-<hi> | <e1> | <w1> | <E - e1> |
| 2 | <lo>-<hi> | <e2> | <w2> | <E - e1 - e2> |
| 3 | <lo>-<hi> | <e3> | <w3> | <...> |
| 4 | <lo>-<hi> | <e4> | <w4> | <...> |
| 5 | <lo>-<hi> | <e5> | <w5> | <...> |
| 6 | <lo>-<hi> | <e6> | <w6> | 0 |

Additivity checked: the six error counts sum to <E>.
```

Report the `Remaining after this part` column in the task result. Tasks 3 to 8 each assert their own row.

This task makes no commit. It produces a measurement, and the workspace is git-ignored.

---

### Task 2: Add the acceptance test, red

The spec requires the test first: add it, confirm it fails at the baseline count, and commit it red. It is the durable guard, and having it before the rewrite makes every later commit's progress measurable by the acceptance criterion itself rather than by a side command.

**Files:**
- Modify: `helpers/tests/test_docs_invariants.py`
- Modify: `helpers/tests/README.md`
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `sec_overlay.ste_lint.lint_prose(text: str) -> tuple[list[str], list[str]]`.
- Produces: `_PKG_README: Path` — a new module-level constant in `tests/test_docs_invariants.py` — and `test_package_readme_ste_lint_clean`. Tasks 3 to 8 run that test as their meter.

- [ ] **Step 1: Add the path constant**

`tests/test_docs_invariants.py` already defines `_ASSURANCE` near line 288 as `Path(__file__).resolve().parents[2] / "ASSURANCE_CASE.md"`. It has no constant for the package README. Add one beside `_ASSURANCE`, following the same shape:

```python
_PKG_README = Path(__file__).resolve().parents[1] / "sec_overlay" / "README.md"
```

`parents[1]` is the helpers root. `parents[2]` is the skill root, which is why `_ASSURANCE` uses a different index.

- [ ] **Step 2: Verify the path resolves**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "
from pathlib import Path
p = Path('tests/test_docs_invariants.py').resolve().parents[1] / 'sec_overlay' / 'README.md'
print(p, p.exists())
"
```

Expected: the absolute path to `helpers/sec_overlay/README.md`, then `True`. If it prints `False`, the index is wrong. Fix it before writing the test.

- [ ] **Step 3: Add the test**

Append to `helpers/tests/test_docs_invariants.py`:

```python
def test_package_readme_ste_lint_clean():
    """REQ-71 acceptance: the package README passes the STE structural lint."""
    from sec_overlay.ste_lint import lint_prose

    errors, warnings = lint_prose(_PKG_README.read_text())
    assert errors == [], errors
    assert warnings == [], warnings
```

The test asserts both lists. The model test in this same file, `test_assurance_case_ste_lint_clean` near line 323, discards warnings with `errors, _ = lint_prose(...)`. The spec requires both for this file, and the baseline warning count is zero, so asserting both costs nothing and catches a regression the model test would miss.

- [ ] **Step 4: Confirm the test fails at the baseline count**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: FAIL on `assert errors == []`, with an error list whose length equals the whole-file count from Task 1 Step 1. Record that number — it is the meter's starting value.

If the length does not match Task 1's count, the constant points at the wrong file. Fix it before committing.

- [ ] **Step 5: Confirm nothing else broke**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three commands are clean. A second failure means the new constant or import broke an existing test — fix it before committing.

- [ ] **Step 6: Append the tests README entry**

Add at the end of `helpers/tests/README.md`:

```markdown
## 2026-09-02 — REQ-71 red: the package README is STE-linted

`sec_overlay/README.md` held semicolon-joined clauses and over-long sentences throughout, and
nothing checked it. `test_package_readme_ste_lint_clean` now asserts `lint_prose` returns no
error and no warning for the file.

The test is committed red on purpose. The file is too large to rewrite in one commit, so the
rewrite lands in six parts and the test stays red until the last part. The spec authorises the
departure from red-green-per-commit. Each rewrite commit must reduce the reported error count,
and no other test may fail during that window.

The test asserts errors and warnings, while the model test `test_assurance_case_ste_lint_clean`
asserts errors only. The README's baseline warning count is zero, so asserting both is free and
catches a buried sequence or a noun cluster the model test would let through. Closes F-9 and F-11.
```

- [ ] **Step 7: Add the changelog entry**

Add under `## Unreleased` in `plugins/sec-overlay/CHANGELOG.md`, inside `### Added` (create the subsection if it is absent):

```markdown
- Add `test_package_readme_ste_lint_clean`, which asserts the `sec_overlay` package README passes
  `ste_lint` with no error and no warning. The test is committed failing: the rewrite that satisfies
  it lands in the six commits that follow. Part of REQ-71.
```

- [ ] **Step 8: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 9: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin the README STE lint"
```

---

### Task 3: Rewrite part 1

Part 1 runs from line 1 to the line before anchor 1. Line 1 is the file's only heading until roughly line 1387, so part 1 is heading-free prose. Add headings while rewriting it.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 1's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 1. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: part 1 at 0 errors and 0 warnings. The meter drops to row 1's `Remaining after this part`.

- [ ] **Step 1: Read the baseline row**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 1's range, its error count, and the remaining count this task must reach.

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO> && $1 <= <HI>'
```

Then run the one-part lint command on part 1's range to see the error classes. A semicolon that `rg` finds inside a code fence or an inline code span is not one of them — the linter strips code before it lints.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.

   Before: `The gate reads the receipt; a finding without one never reaches the report.`

   After: `The gate reads the receipt. A finding without one never reaches the report.`

2. **A sentence over 25 words splits at its natural join.** Split at a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.

   Before: `The prefilter drops a finding whose rule the catalog does not know, because an unknown rule cannot carry a class, and a finding with no class cannot be scored or clustered.`

   After: `The prefilter drops a finding whose rule the catalog does not know. An unknown rule cannot carry a class, and a finding with no class cannot be scored or clustered.`

3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Re-measure part 1**

Run the one-part command on part 1's range.

Expected: `errors 0 warnings 0`. If a warning appeared that the baseline did not have, the rewrite introduced a buried sequence or a noun cluster. Fix it now — the acceptance test asserts warnings are empty too.

- [ ] **Step 5: Read the meter**

```bash
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: still FAIL, with an error list whose length equals row 1's `Remaining after this part`. A different number means the edit reached outside part 1's range. Find and revert the stray edit.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff --stat -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

The second command must print nothing. A changed fence line means a code block moved, which this plan forbids.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three are clean.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased` in `plugins/sec-overlay/CHANGELOG.md`, inside `### Changed` (create the subsection if it is absent):

```markdown
- Rewrite the first part of the `sec_overlay` package README to ASD-STE100. Prose only — no code,
  identifier, path, or fact changed. Part 1 of 6 for REQ-71.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 1 to STE"
```

---

### Task 4: Rewrite part 2

Part 2 runs from anchor 1 to the line before anchor 2. Anchor 1 is the line holding `` whether the run produced one. `render_ndt` ``.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 2's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 2. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: part 2 at 0 errors and 0 warnings. The meter drops to row 2's `Remaining after this part`.

- [ ] **Step 1: Read the baseline row and re-locate the anchors**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 2's error count and the remaining count this task must reach.

Part 1's rewrite may have changed part 1's line count, which shifts every later boundary. Re-locate the range before using it:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'whether the run produced one\. `render_ndt`' sec_overlay/README.md
rg -n 'gained `synthesize_manifest\(product, members\) -> dict`' sec_overlay/README.md
```

Use the current line numbers. The baseline's error count and remaining count stay valid — only the range shifts.

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO> && $1 <= <HI>'
```

Then run the one-part lint command on part 2's range.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.
2. **A sentence over 25 words splits at its natural join** — a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.
3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Re-measure part 2**

Run the one-part command on part 2's current range. Expected: `errors 0 warnings 0`. Fix any warning the baseline did not have.

- [ ] **Step 5: Read the meter**

```bash
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: still FAIL, with an error list whose length equals row 2's `Remaining after this part`. A different number means the edit reached outside part 2's range.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

Must print nothing.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three are clean.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Rewrite the second part of the `sec_overlay` package README to ASD-STE100. Prose only — no code,
  identifier, path, or fact changed. Part 2 of 6 for REQ-71.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 2 to STE"
```

---

### Task 5: Rewrite part 3

Part 3 runs from anchor 2 to the line before anchor 3. Anchor 2 is the line holding `` gained `synthesize_manifest(product, members) -> dict` ``.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 3's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 3. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: part 3 at 0 errors and 0 warnings. The meter drops to row 3's `Remaining after this part`.

- [ ] **Step 1: Read the baseline row and re-locate the anchors**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 3's error count and remaining count. Then re-locate the range, because earlier parts shifted it:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'gained `synthesize_manifest\(product, members\) -> dict`' sec_overlay/README.md
rg -n 'see which layer a rule came from without running a review' sec_overlay/README.md
```

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO> && $1 <= <HI>'
```

Then run the one-part lint command on part 3's range.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.
2. **A sentence over 25 words splits at its natural join** — a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.
3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Re-measure part 3**

Run the one-part command on part 3's current range. Expected: `errors 0 warnings 0`. Fix any warning the baseline did not have.

- [ ] **Step 5: Read the meter**

```bash
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: still FAIL, with an error list whose length equals row 3's `Remaining after this part`.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

Must print nothing.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three are clean.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Rewrite the third part of the `sec_overlay` package README to ASD-STE100. Prose only — no code,
  identifier, path, or fact changed. Part 3 of 6 for REQ-71.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 3 to STE"
```

---

### Task 6: Rewrite part 4

Part 4 runs from anchor 3 to the line before anchor 4. Anchor 3 is the line holding `see which layer a rule came from without running a review`.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 4's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 4. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: part 4 at 0 errors and 0 warnings. The meter drops to row 4's `Remaining after this part`.

- [ ] **Step 1: Read the baseline row and re-locate the anchors**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 4's error count and remaining count. Then re-locate the range:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'see which layer a rule came from without running a review' sec_overlay/README.md
rg -n 'line for a scoped npm-style identifier' sec_overlay/README.md
```

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO> && $1 <= <HI>'
```

Then run the one-part lint command on part 4's range.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.
2. **A sentence over 25 words splits at its natural join** — a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.
3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Re-measure part 4**

Run the one-part command on part 4's current range. Expected: `errors 0 warnings 0`. Fix any warning the baseline did not have.

- [ ] **Step 5: Read the meter**

```bash
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: still FAIL, with an error list whose length equals row 4's `Remaining after this part`.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

Must print nothing.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three are clean.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Rewrite the fourth part of the `sec_overlay` package README to ASD-STE100. Prose only — no code,
  identifier, path, or fact changed. Part 4 of 6 for REQ-71.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 4 to STE"
```

---

### Task 7: Rewrite part 5

Part 5 runs from anchor 4 to the line before anchor 5. Anchor 4 is the line holding `line for a scoped npm-style identifier`.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 5's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 5. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: part 5 at 0 errors and 0 warnings. The meter drops to row 5's `Remaining after this part`.

- [ ] **Step 1: Read the baseline row and re-locate the anchors**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 5's error count and remaining count. Then re-locate the range:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'line for a scoped npm-style identifier' sec_overlay/README.md
rg -n 'renders eight optional elements on a finding page' sec_overlay/README.md
```

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO> && $1 <= <HI>'
```

Then run the one-part lint command on part 5's range.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.
2. **A sentence over 25 words splits at its natural join** — a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.
3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Re-measure part 5**

Run the one-part command on part 5's current range. Expected: `errors 0 warnings 0`. Fix any warning the baseline did not have.

- [ ] **Step 5: Read the meter**

```bash
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: still FAIL, with an error list whose length equals row 5's `Remaining after this part`.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

Must print nothing.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: `pytest` reports exactly one failure, `test_package_readme_ste_lint_clean`. The other three are clean.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Rewrite the fifth part of the `sec_overlay` package README to ASD-STE100. Prose only — no code,
  identifier, path, or fact changed. Part 5 of 6 for REQ-71.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 5 to STE"
```

---

### Task 8: Rewrite part 6 and turn the test green

Part 6 runs from anchor 5 to the last line of the file. Anchor 5 is the line holding `renders eight optional elements on a finding page`. This part also holds every section the companion code-repair plan appended, so re-measure rather than assume its count.

This task closes the red window opened in Task 2. The suite must be fully green before its commit.

**Files:**
- Modify: `helpers/sec_overlay/README.md` (part 6's range from the baseline file)
- Modify: `plugins/sec-overlay/CHANGELOG.md`
- Modify: `plugins/sec-overlay/.claude-plugin/plugin.json`

**Interfaces:**
- Consumes: `<sdd workspace>/readme-ste-baseline.md`, row 6. `test_package_readme_ste_lint_clean` from Task 2.
- Produces: the whole file at 0 errors and 0 warnings, which is REQ-71's acceptance condition, and a green test suite.

- [ ] **Step 1: Read the baseline row and re-locate the anchor**

Read `<sdd workspace>/readme-ste-baseline.md`. Note part 6's error count. Then re-locate the range start:

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n 'renders eight optional elements on a finding page' sec_overlay/README.md
wc -l < sec_overlay/README.md
```

- [ ] **Step 2: List the offenders inside the range**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
rg -n ';' sec_overlay/README.md | awk -F: '$1 >= <LO>'
```

Then run the one-part lint command on part 6's range.

- [ ] **Step 3: Rewrite the prose**

Apply these three transforms and nothing else.

1. **A semicolon joining two independent clauses becomes a period.** Capitalise the second clause. Where the second clause depends on the first, add the connective the semicolon implied.
2. **A sentence over 25 words splits at its natural join** — a conjunction, a relative pronoun, or a comma that separates two complete thoughts. Keep every clause.
3. **A paragraph over 6 sentences splits at a topic change,** and gets an `##` or `###` heading if the new paragraph opens a subject the file returns to.

Do not touch a code fence, an inline code span, an identifier, a path, a command, a link, or a block of quoted output. Do not correct a fact. Do not shorten by dropping a clause.

- [ ] **Step 4: Turn the meter green**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_docs_invariants.py::test_package_readme_ste_lint_clean -q
```

Expected: PASS. This is the requirement's acceptance condition. A remaining error means an earlier part regressed or part 6 is incomplete. Run the whole-file command to see which errors survive, and fix them before committing.

- [ ] **Step 5: Prove the assertion is live**

The test passed for the first time in Step 4, so its assertions have never been observed to fire against a clean file. Prove they can.

Append a single line holding a semicolon to `helpers/sec_overlay/README.md` — for example `The gate reads the receipt; a finding without one never reaches the report.` — then run the test again.

Expected: FAIL with `assert errors == []` and a `semicolon in prose` entry. Remove the added line, run the test once more, and confirm it passes. Record the failure line in the task report.

- [ ] **Step 6: Confirm no code changed**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git diff -- plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md | rg '^[-+].*```'
```

Must print nothing.

- [ ] **Step 7: Run the full gate**

```bash
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m sec_overlay.phase_docs --check
```

Expected: all four clean, with no failing test. The red window is closed.

- [ ] **Step 8: Add the changelog entry**

Add under `## Unreleased`, inside `### Changed`:

```markdown
- Rewrite the last part of the `sec_overlay` package README to ASD-STE100. The whole file now passes
  `ste_lint` with no error and no warning, so `test_package_readme_ste_lint_clean` passes. Part 6 of
  6 for REQ-71. Closes F-9 and F-11.
```

- [ ] **Step 9: Bump the patch version**

Read `plugins/sec-overlay/.claude-plugin/plugin.json` and increment the patch component.

- [ ] **Step 10: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "docs(sec-overlay): rewrite README part 6 to STE"
```

---

## Requirement Coverage

| Requirement | Finding | Task |
|-------------|---------|------|
| REQ-71 | F-9, F-11 | Tasks 1 to 8 |

REQ-62 to REQ-70 are the companion plan at `docs/superpowers/plans/2026-09-02-sec-overlay-parked-code-repairs.md`. Run it first.

## Reference Measurement

Taken on the file at 1810 lines, before the companion plan's appends. Task 1 re-derives every number. These values are the sanity check, not the target.

- Whole file: 125 errors, 0 warnings. 119 `semicolon in prose`, 6 `sentence over 25 words`, 0 `paragraph over 6 sentences`.
- Errors per 100-line block, in order from line 1: 5, 10, 10, 10, 5, 6, 5, 7, 7, 5, 6, 7, 6, 7, 6, 10, 5, 6, and 2 for the final 10 lines. These sum to 125, which is what proved the lint additive over line ranges.
- Errors per 300-line part: 25, 21, 19, 18, 19, 23. Remaining after each part: 100, 79, 60, 42, 23, 0.
- Structure: line 1 is the only heading until line 1387. Lines 19 to 1386 are one heading-free prose block. Nineteen dated `##` and `###` sections then run from line 1387 to line 1810.

## Deviations from the Spec

1. The spec presents REQ-71 as a single requirement. This plan splits the rewrite into six commits, because a rewrite of roughly 1800 lines of prose in one commit is not reviewable and gives no intermediate checkpoint. The spec asks for exactly this: "rewrite in sections, committing each section", with "the expected count after each one" stated in the plan.
2. The spec's baseline is a literal 125 errors. This plan measures it instead, in Task 1, because the companion code-repair plan appends nine sections to the same file first. The literal survives as the Reference Measurement, used as a sanity check.
