# sec-overlay Verify Precision and Document Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the verify oracle name the reason a re-scan still fires, and generate every document's phase order from `PHASE_TABLE`.

**Architecture:** Two root causes share no code, so the plan runs them in the specification's order. RC-5 is a verify oracle that is imprecise: it matches a scanner hit to a finding by base filename, and it reports `not-fixed` whenever a post-patch hit exists, whatever the hit is. Its repair adds path-segment matching and two new non-condemning causes, each carrying the pre-hit and post-hit evidence in the finding's history. RC-3 is a documented contract that drifts from the code. Its repair adds one generator, `sec_overlay/phase_docs.py`, renders a marked block into the five documents that state the phase order, and extends the REQ-32 contract lint so a rename or a reorder fails a test.

**Tech Stack:** Python 3.11 (standard library only in `sec_overlay/`), pytest, ruff, ty, `uv` for every command. All commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** docs/superpowers/specs/2026-09-01-sec-overlay-defect-repairs-design.md (Section 5, Group 6 and Group 7)

## Global Constraints

- `sec_overlay/` imports the standard library only. No new dependency.
- `sec_overlay/models.py` and `sec_overlay/evidence.py` are byte-pinned by `tests/test_frozen_contract.py:30-31`. Do not edit either file in this plan. No task needs to.
- `Finding.verification` is a closed enum owned by `evidence.py`. A new verify cause is never a verification value; it maps through `_CAUSE_TO_VERIFICATION` to an existing one.
- One commit per red step and one commit per green step. The red commit must fail; the green commit must pass.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `version` in every commit. A test file under `helpers/tests/` is a shipping file, so a red commit bumps too.
- Derive the increment from the Conventional Commit type: `feat` bumps minor, every other type bumps patch.
- Stage explicit paths. Never `git add -A`. Never `--no-verify`.
- A commit that changes a file under `helpers/sec_overlay/` updates `helpers/sec_overlay/README.md` in the same commit. A commit that changes a file under `helpers/tests/` updates `helpers/tests/README.md` in the same commit.
- A commit that changes `skills/sec-overlay/CLAUDE.md` stages `skills/sec-overlay/README.md` in the same commit, because the `doc-update-guard` hook requires the immediate folder's README.
- A commit that invalidates a statement in `helpers/README.md` updates that statement in the same commit.
- Add one entry to `plugins/sec-overlay/CHANGELOG.md` per commit. The plan touches no repo-level file, so the root `CHANGELOG.md` gets no entry.
- Keep `skills/sec-overlay/CLAUDE.md` under 200 lines. It holds 214 lines at 1.122.0; Task 4 brings it under the cap.
- Run `prek run` before every commit.
- Do not merge and do not push. The branch is `docs/sec-overlay-defect-repairs-spec`.
- Do not edit a test this plan does not name. One test fake is widened on purpose; it is named in the pre-flight scan.
- The plugin version at the start of this plan is 2.5.2, the version Plan 4 ends on. The versions below are prospective. Read the real value from `plugin.json` before each bump.
- Task order is REQ-59 (Tasks 1 and 2), REQ-60 (Task 3), REQ-61 (Tasks 4 and 5). RC-5 runs before RC-3, per the specification's build order: generating documents from `PHASE_TABLE` is stable only after the table stops moving, and Plans 1 to 4 are the last edits to the table.

---

## Pre-flight scan

Every citation in Group 6 and Group 7 was opened at plugin 1.122.0, commit `db5be34`. The tables below record what differs from the specification.

### Corrections to the specification

| Requirement | Specification says | Plugin 1.122.0 holds |
|---|---|---|
| REQ-59 | Cites `verify.py:166-170`. | Lines 166-170 are the `Returns:` paragraph of `_file_has_hit`'s docstring. The defect is the compare at `verify.py:183`: `if os.path.basename(f.file) != file_basename: continue`. |
| REQ-59 | Cites `verify.py:287`. | The ponytail comment that names the aliasing risk sits at `verify.py:286-287`. The `pre = _check(...)` call it precedes is line 288. |
| REQ-60 | Cites `verify.py:248-301`. | `verify_patch` spans lines 250-303. Line 248 is blank. |
| REQ-61 | "`SKILL.md`; four folder READMEs". | Only three folder READMEs hold phase content: `skills/sec-overlay/README.md:101`, `agents/README.md:41`, `helpers/README.md:55`. `references/README.md` holds no phase order, index, or phase name and gets no block. The fourth document is `skills/sec-overlay/CLAUDE.md:54`, whose hand-numbered fence is the largest single source of F-2 drift. |
| REQ-61 | "a token absent from `PHASE_TABLE` or `DISPATCH_TOKENS`". | `SKILL.md` names four tokens `DISPATCH_TOKENS` does not hold: `{{PHASE}}`, `{{ROUND}}`, `{{REPO_ROOT}}`, `{{SCAN_SCOPE}}`. `DISPATCH_TOKENS` cannot absorb them, because `test_dispatch_tokens_are_a_single_source` at `tests/test_contract_lint.py:167` asserts `render_dispatch`'s substitute line equals the whole tuple, and `render_dispatch` supplies none of the four. Task 5 adds a second code-sourced constant instead. |
| Register D-B83-c | "the `not-fixed` cause is never recorded in history". | Already closed. `verify_findings` at `verify.py:384` appends `{"event": f"verify:cause:{cause}"}` for every cause. The register's line cites `:331` and `:333-339`; the code is at `:384-385`. |
| Register (Group 6 citations) | `verify.py:255`, `:260`, `:268-269`, `:270`, `:273`, `:320-322`. | All stale by the same drift. The live lines are `:283`, `:288`, `:296-297`, `:298`, `:301`, `:373-374`. |

### Rulings taken against plugin HEAD

1. **REQ-59's acceptance sentence is unachievable and is narrowed on the record.** The specification's criterion reads "A patch to `file-name-sanitize.ts` that clears a sink in `PackageSetup.ts` verifies." OSS semgrep taint analysis is intra-file. A sanitizer added in a different file leaves the sink line byte-identical, so the post-patch scan returns the identical hit and no re-scan oracle can return `verified-static`. The criterion becomes: **such a patch does not report `not-fixed`.** It reports a new, non-condemning cause instead. Task 2 lands that cause.

2. **The path compare is a segment-suffix match, not full equality.** `verify_patch`'s `target` may be the scan scope while `Finding.file` is repo-root-relative, and Plan 2 deletes `scanscope.rel_to_root`, so nothing remains to reconcile the two prefixes. A both-directions suffix match at a `/` boundary closes the aliasing defect — `a/util.py` no longer matches a finding citing `b/util.py` — and cannot regress on a prefix difference. Full equality would break every verify whose target is a subdirectory.

3. **Each backend reports paths in its own shape, so normalization precedes the compare.** semgrep prefixes the scan target (`sast.py:38` reads `r["path"]`, and `run_semgrep` appends `target` to the command at `sast.py:65`); CodeQL emits a SARIF URI already repo-relative, optionally prefixed by a resolved `uriBaseId` (`codeql.py:155-172`); osv-scanner emits `source.path`, usually absolute (`sca.py:51`). One pure-string helper strips the scan root's prefix. It touches no filesystem, so a CodeQL URI that does not exist relative to the process CWD passes through unchanged.

4. **`_check` keeps its five-positional semgrep call.** The docstring at `verify.py:194-199` pins it, and `tests/test_verify.py:126` monkeypatches a fake with exactly five positional parameters and no `**kwargs`. Task 1 renames the third parameter from `file_basename` to `file_path`, which is safe because every call and every fake is positional.

5. **REQ-60 compares evidence text, never line numbers.** A patch that inserts a line shifts every later line number, so a line-number comparison would call a genuinely unfixed finding "a different construction" on any insertion. `Finding.evidence` carries semgrep's matched source text (`sast.py:44` reads `extra["lines"]`), so disjoint pre-patch and post-patch evidence sets prove the rule matched a construction the patch introduced, and intersecting sets prove the original construction survives. The register's own example — `path.join` at pre-patch line 177 becoming `path.resolve` at post-patch line 180 — is exactly the insertion case.

6. **Detail rides an out-parameter, not a changed return type.** `_file_has_hit` keeps `-> bool | None` and gains a keyword-only `detail: list[Finding] | None = None`. Changing the return type would break all six parametrized causes in `tests/test_verify_causes.py:60-75`, which stub `_file_has_hit` with booleans. When `detail` stays empty — every monkeypatched test — the new logic falls back to today's boolean comparison unchanged.

7. **The history `reason` key appears only when detail is non-empty.** `test_verify_findings_records_the_cause` at `tests/test_verify_causes.py:94` asserts exact dict equality on `{"event": f"verify:cause:{cause}"}`. A `reason` key added unconditionally fails that assertion. Adding it only on a real scan keeps the test green and still carries the pre-hit and post-hit lines the register asks for.

8. **`tests/test_verify.py:126` is widened, and it is the only test edit in Tasks 1 to 3.** Its fake reads `def fake_hit(target_dir, config, basename, cls, rules):`. Task 3 threads a keyword argument, so the fake gains `**kw`. The second fake at `tests/test_verify.py:198` already accepts `**kw` and needs no edit.

9. **The new cause vocabulary needs no schema or prompt edit.** `grep -rn "VERIFY_CAUSES\|verify:cause"` finds five consumers: `sec_overlay/verify.py`, `tests/test_verify_causes.py`, `tests/README.md:474,477`, and `sec_overlay/README.md:314,316`. No file under `references/` enumerates the causes, so `finding.schema.json` and `prompt-constants.md` stay untouched.

10. **REQ-61's generated block carries its own column list.** Each document's `<!-- BEGIN GENERATED: phase-table columns=... -->` marker states which columns and which `kind` filter it wants. One renderer therefore serves five documents with no per-document registry in the module, and no registry can drift from the documents it describes.

11. **The index column always counts positions in the full table.** A filtered view — `agents/README.md` holds agent phases only, `helpers/README.md` deterministic phases only — still states each phase's real place in the run. A per-view index would contradict the unfiltered views.

12. **The ordinal lint the specification implies is replaced by a note-key lint.** Scanning the documents for ordinal-prefixed list items is imprecise, and scanning for backticked phase names would flag hundreds of module names and field names. Instead, the two documents holding per-phase operator notes carry a `<!-- BEGIN PHASE NOTES -->` region whose items are keyed `- **<phase-name>** — …`. The lint asserts the key set covers every `PHASE_TABLE` name, holds nothing outside `PHASE_TABLE | NON_TABLE_STEPS`, and appears in table order. A rename fails the key-set assertion; a reorder fails the order assertion. That is precisely the specification's acceptance criterion.

13. **Tokens the operator substitutes get their own constant.** `phase_docs.ORCHESTRATOR_TOKENS` holds `REPO_ROOT` and `SCAN_SCOPE`, which `run.py:159-160` writes and `review_agent.py:179` also writes, plus `PHASE` and `ROUND`, which the operator supplies by hand per prompt. The document token lint checks `DISPATCH_TOKENS | ORCHESTRATOR_TOKENS`, so `DISPATCH_TOKENS` stays exactly what `render_dispatch` emits.

14. **The pipeline documents keep every operational sentence they hold today.** `SKILL.md`'s numbered list at `:191` holds per-phase instructions no table can carry — the CodeQL pack warning, the partial-scan rule, the `reconcile_plan` call sequence. Task 4 rekeys those items from ordinals to phase names and preserves each sentence. Nothing is summarized away.

### Drift the plan closes as a class

| Document | Drift at 1.122.0 |
|---|---|
| `skills/sec-overlay/CLAUDE.md:54-100` | A hand-numbered fence (`0`, `1`, `C1`, `T1`, `R0`, `2`, `2.5`, `3`, `3.5`, `4`, `4.5`, `0.5`, `5`…`15`) whose ordinals are out of order and whose entries predate the `prove`, `demote-noise`, `artifact-consistency`, and `judge` phases. |
| `skills/sec-overlay/SKILL.md:191-250` | A hand-numbered prose list (0, 1, C1, T1, 2..14, plus 7.5 and 13.5) that omits `recall-gate`, `judge`, `trace`, `selfscore`, `demote-noise`, `artifact-gate`, `artifact-review`, `artifact-consistency`, `prove`, and `postflight`, and that states `redteam` after `verify` rather than the order Plan 1 lands. |
| `skills/sec-overlay/README.md:101` | A mermaid graph plus prose, hand-maintained. |
| `skills/sec-overlay/agents/README.md:41` | Per-phase prompt rows, hand-maintained. |
| `skills/sec-overlay/helpers/README.md:55` | Deterministic-module rows, hand-maintained. |

### Adjacent findings recorded without a fix

1. `skills/sec-overlay/CLAUDE.md` holds 214 lines at 1.122.0, over the root `CLAUDE.md` 200-line cap. Task 4 replaces a 47-line fence with a 30-line table and brings the file under the cap as a side effect. If a later edit pushes it back over, that is a separate change.
2. `{{PHASE}}` and `{{ROUND}}` have no code producer at all. `agents/tune-config.md` and `agents/phase-adversary.md` name them, and only a human substitutes them. `ORCHESTRATOR_TOKENS` records that fact; it does not add a producer.
3. `sca.run_sca` reports `line=1` for every dependency finding (`sca.py:69`). REQ-60's evidence comparison is inert for the `sca` backend, because every SCA hit carries the package coordinate as evidence rather than a source construction. The plan does not special-case it; `not-fixed` stays the SCA verdict when the coordinate survives.
4. `_placeholder_version_bump` at `verify.py:225-249` is a narrow heuristic for one non-functional patch shape. REQ-60's new cause does not extend it, and a non-functional patch of any other shape still reads as `verified-static` when the coordinate disappears.

---

## File Structure

| File | Responsibility |
|---|---|
| `sec_overlay/verify.py` | Modified. Path-segment matching, a `detail` out-parameter, two new causes, and their `_CAUSE_TO_VERIFICATION` entries. |
| `sec_overlay/phase_docs.py` | New. Renders `PHASE_TABLE` into a marked markdown block, and holds `NON_TABLE_STEPS`, `ORCHESTRATOR_TOKENS`, `DOCUMENTS`, `NOTE_DOCUMENTS`, and `note_keys`. Its `--check`/`--write` CLI is the maintainer's regeneration lever. |
| `tests/test_verify_paths.py` | New. Pins the path-segment matcher and the two new causes. |
| `tests/test_phase_docs.py` | New. Pins that every document's generated block is current and that a rename makes it stale. |
| `tests/test_contract_lint.py` | Modified. Two note-key assertions and one document-token assertion. |
| `skills/sec-overlay/CLAUDE.md` | Modified. The hand-numbered fence becomes a generated block plus a phase-keyed operator-note region. |
| `skills/sec-overlay/SKILL.md` | Modified. Same shape; every operational sentence is preserved and rekeyed. |
| `skills/sec-overlay/README.md`, `agents/README.md`, `helpers/README.md` | Modified. Each gains a generated block with its own column list. |

---

## Task 1: REQ-59 — match the finding's path, not its base filename

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py:147-187`, `:286-288`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py` (new)

**Interfaces:**
- Consumes: nothing from an earlier task.
- Produces: `verify._rel_path(path: str, root: str) -> str` and `verify._path_matches(scanner_path: str, finding_path: str, root: str) -> bool`. Task 2 and Task 3 both call `_rel_path`. `_file_has_hit`'s third parameter is renamed `file_path` and now receives the finding's full path rather than its base filename.

- [ ] **Step 1: Write the failing test**

Create `tests/test_verify_paths.py`:

```python
"""REQ-59: the verify oracle matches a scanner hit by path, not by base filename."""

from __future__ import annotations

from sec_overlay import verify as V
from sec_overlay.evidence import Severity
from sec_overlay.models import Finding, FindingStatus


def _hit(path: str) -> Finding:
    return Finding(
        id="C-0001",
        rule_id="r.sqli",
        cls="sqli",
        status=FindingStatus.CANDIDATE,
        severity=Severity.HIGH,
        file=path,
        line=7,
        message="m",
    )


def test_rel_path_strips_the_scan_root():
    assert V._rel_path("/repo/src/app.py", "/repo") == "src/app.py"
    assert V._rel_path("src/app.py", "src") == "app.py"
    assert V._rel_path("src/app.py", "") == "src/app.py"


def test_rel_path_leaves_an_unprefixed_path_alone():
    assert V._rel_path("src/app.py", "/other") == "src/app.py"


def test_path_matches_accepts_the_same_file():
    assert V._path_matches("/repo/a/util.py", "a/util.py", "/repo")


def test_path_matches_accepts_a_repo_relative_finding_under_a_scoped_target():
    assert V._path_matches("/repo/src/a/util.py", "src/a/util.py", "/repo/src")


def test_path_matches_rejects_a_same_named_file_in_another_directory():
    assert not V._path_matches("/repo/b/util.py", "a/util.py", "/repo")


def test_file_has_hit_rejects_an_aliased_same_named_file(monkeypatch):
    monkeypatch.setattr(V, "run_semgrep", lambda t, c: [_hit("/repo/b/util.py")])
    assert V._file_has_hit("/repo", "cfg", "a/util.py", "sqli", set()) is False
    monkeypatch.setattr(V, "run_semgrep", lambda t, c: [_hit("/repo/a/util.py")])
    assert V._file_has_hit("/repo", "cfg", "a/util.py", "sqli", set()) is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_verify_paths.py -v`

Expected: FAIL. `test_rel_path_strips_the_scan_root` errors with `AttributeError: module 'sec_overlay.verify' has no attribute '_rel_path'`, and `test_file_has_hit_rejects_an_aliased_same_named_file` fails on its first assertion, because `os.path.basename("/repo/b/util.py") == os.path.basename("a/util.py")`.

- [ ] **Step 3: Commit the red state**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.3"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(verify): pin path matching over base filename"
```

- [ ] **Step 4: Add the two helpers above `_file_has_hit`**

Insert immediately before `def _file_has_hit(` in `sec_overlay/verify.py`:

```python
def _rel_path(path: str, root: str) -> str:
    """Return ``path`` in POSIX form with ``root``'s prefix removed.

    Pure string work on purpose: a CodeQL SARIF URI is already repo-relative and
    does not exist relative to this process's CWD, so a ``realpath`` round-trip
    would corrupt it. semgrep prefixes the scan target, osv-scanner reports an
    absolute source path, and CodeQL reports neither.

    Args:
        path: A scanner-reported or finding-reported file path.
        root: The directory the scan ran against; may be empty.

    Returns:
        ``path`` relative to ``root`` when ``root`` prefixes it, else ``path``
        unchanged, always with ``/`` separators and no leading ``./``.
    """
    q = path.replace(os.sep, "/").removeprefix("./")
    r = root.replace(os.sep, "/").rstrip("/")
    return q[len(r) + 1 :] if r and q.startswith(r + "/") else q


def _path_matches(scanner_path: str, finding_path: str, root: str) -> bool:
    """Return True when two paths name the same file after normalization.

    Matches on a path-segment suffix in both directions rather than on equality.
    ``verify_patch``'s ``target`` may be the scan scope while the finding cites a
    repo-root-relative path, and no helper reconciles the two prefixes. A suffix
    match survives that difference and still separates ``a/util.py`` from
    ``b/util.py``, which a base-filename match could not.

    Args:
        scanner_path: The path the re-scan reported.
        finding_path: The path the finding cites.
        root: The directory the re-scan ran against.

    Returns:
        Whether both paths name one file.
    """
    a = _rel_path(scanner_path, root)
    b = _rel_path(finding_path, root)
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)
```

- [ ] **Step 5: Rewrite `_file_has_hit`'s parameter and matching loop**

In `sec_overlay/verify.py`, change the signature's third parameter and the docstring line that describes it:

```python
def _file_has_hit(
    target_dir: str, config: str, file_path: str, cls: str, rules: set[str],
    *, backend: str = "semgrep", language: str | None = None, db_dir: str | None = None,
) -> bool | None:
    """Return True if the finding's signal is present in ``file_path``.
```

In the same docstring, replace the `file_basename` argument line with:

```python
        file_path: The finding's own file path, matched by path segment (e.g.
            ``src/app.py``); a bare filename still matches as a one-segment suffix.
```

Replace the matching loop:

```python
    for f in findings:
        if not _path_matches(f.file, file_path, target_dir):
            continue
        if f.rule_id in rules if rules else f.cls == cls:
            return True
    return False
```

- [ ] **Step 6: Pass the finding's full path and retire the ponytail comment**

In `verify_patch`, replace lines 285-288:

```python
    basename = os.path.basename(file)
    backend = _pick_backend(evidence_sources)
    rules = _source_rules(f"{backend}:", evidence_sources)
    # ponytail: basename match is fine for distinct filenames; a repo with two
    # same-named files in different dirs could alias — revisit with full paths then.
    pre = _check(target, configs, basename, cls, rules, backend, language, db_dir)
```

with:

```python
    backend = _pick_backend(evidence_sources)
    rules = _source_rules(f"{backend}:", evidence_sources)
    pre = _check(target, configs, file, cls, rules, backend, language, db_dir)
```

Then replace the one remaining `basename` use, the post-patch call:

```python
            post = _check(str(repo), configs, file, cls, rules, backend, language, db_dir)
```

Rename `_check`'s third parameter to match, and update its docstring's first line:

```python
def _check(
    target: str, configs: list[str], file_path: str, cls: str, rules: set[str],
    backend: str, language: str | None, db_dir: str | None,
) -> bool | None:
```

Inside `_check`, both `_file_has_hit` calls now pass `file_path` in place of `basename`. The semgrep call keeps its five positional arguments.

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_verify_paths.py tests/test_verify.py tests/test_verify_causes.py -v`

Expected: PASS, all three files. `tests/test_verify.py`'s three `needs_semgrep` cases still pass: they call `verify_patch(str(FIXTURE), GOLDEN, CONFIG, "app.py", …)`, the fixture holds one `app.py`, and semgrep reports `<FIXTURE>/app.py`, which `_rel_path` reduces to `app.py`.

- [ ] **Step 8: Run the full suite and the linters**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`

Expected: PASS. The baseline is 1766 passing plus the tests Plans 1 to 4 added, plus the 6 from Step 1.

- [ ] **Step 9: Update `sec_overlay/README.md`**

In the `verify.py` entry, replace the sentence stating that a hit matches on base filename with:

> A scanner hit matches a finding when their paths share a suffix at a `/` boundary after `_rel_path` strips the scan root, so two same-named files in different directories no longer alias.

- [ ] **Step 10: Commit**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.4"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
git commit -m "fix(verify): match a hit by path, not base filename"
```

---

## Task 2: REQ-59 — a cause for a patch that touches no file the rule fires in

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py:22-33`, `:288-303`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py`

**Interfaces:**
- Consumes: `verify._rel_path` from Task 1.
- Produces: `verify._patch_files(patch_diff: str) -> set[str]`, and the cause string `"rule-no-target-file"` in `VERIFY_CAUSES`, mapped to `"static-only"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verify_paths.py`:

```python
_CROSS_FILE_DIFF = (
    "--- a/src/file-name-sanitize.ts\n"
    "+++ b/src/file-name-sanitize.ts\n"
    "@@ -1 +1,2 @@\n"
    "+export const sanitize = (s: string) => s.replace(/\\.\\./g, '');\n"
)


def test_patch_files_reads_the_post_image_paths():
    assert V._patch_files(_CROSS_FILE_DIFF) == {"src/file-name-sanitize.ts"}
    assert V._patch_files("--- a/app.py\n+++ b/app.py\n") == {"app.py"}
    assert V._patch_files("no diff here") == set()


def test_a_cross_file_fix_is_not_reported_as_not_fixed(monkeypatch):
    monkeypatch.setattr(V, "_file_has_hit", lambda *a, **k: True)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    out = V.verify_patch("/repo", _CROSS_FILE_DIFF, "cfg", "src/PackageSetup.ts", "path-traversal")
    assert out == "rule-no-target-file"


def test_the_new_cause_maps_to_a_legal_verification():
    assert "rule-no-target-file" in V.VERIFY_CAUSES
    assert V._CAUSE_TO_VERIFICATION["rule-no-target-file"] == "static-only"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_verify_paths.py -k "patch_files or cross_file or new_cause" -v`

Expected: FAIL. `test_patch_files_reads_the_post_image_paths` errors with `AttributeError: module 'sec_overlay.verify' has no attribute '_patch_files'`; `test_a_cross_file_fix_is_not_reported_as_not_fixed` fails with `assert 'not-fixed' == 'rule-no-target-file'`.

- [ ] **Step 3: Commit the red state**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.5.5"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(verify): pin the cross-file-fix cause"
```

- [ ] **Step 4: Add the cause to both vocabularies**

In `sec_overlay/verify.py`, extend the two constants:

```python
VERIFY_CAUSES = frozenset({
    "verified-static", "not-fixed", "patch-not-applied", "rule-no-match", "unconfirmed",
    "rule-no-target-file", "rule-no-discriminate",
})

_CAUSE_TO_VERIFICATION = {
    "verified-static": "verified-static",
    "not-fixed": "not-fixed",
    "patch-not-applied": "static-only",
    "rule-no-match": "static-only",
    "unconfirmed": "static-only",
    "rule-no-target-file": "static-only",
    "rule-no-discriminate": "static-only",
}
```

Both causes land here in one edit. Task 3 makes `rule-no-discriminate` reachable; until then `test_every_cause_maps_to_a_legal_verification` at `tests/test_verify_causes.py:79` keeps passing, because it only asserts the mapping's key set equals `VERIFY_CAUSES` and its values are legal.

- [ ] **Step 5: Add `_patch_files`**

Insert immediately after `_placeholder_version_bump` in `sec_overlay/verify.py`:

```python
def _patch_files(patch_diff: str) -> set[str]:
    """Return the post-image paths a unified diff writes to.

    Reads ``+++ b/<path>`` headers only. ``/dev/null`` (a deletion) contributes
    nothing, and a diff with no header at all yields an empty set, which the
    caller reads as "unknown" and skips the check.

    Args:
        patch_diff: The unified diff text.

    Returns:
        The set of POSIX paths the diff writes, with a ``b/`` prefix stripped.
    """
    files = set()
    for line in patch_diff.splitlines():
        if not line.startswith("+++ "):
            continue
        path = line[4:].split("\t", 1)[0].strip()
        if path == "/dev/null":
            continue
        files.add(_rel_path(path.removeprefix("b/"), ""))
    return files
```

- [ ] **Step 6: Return the cause between the pre-scan and the repo copy**

In `verify_patch`, insert directly after the `if not pre: return "rule-no-match"` block:

```python
    # A cross-file fix — a sanitizer added beside the sink — leaves the sink line
    # byte-identical, so OSS semgrep's intra-file taint reports the identical hit
    # after the patch. That is not evidence the patch failed (REQ-59).
    touched = _patch_files(patch_diff)
    if touched and not any(_path_matches(t, file, target) for t in touched):
        return "rule-no-target-file"
```

The guard on `touched` being non-empty keeps every existing test green: `tests/test_verify_causes.py`'s `_DIFF` is `"--- a/app.py\n+++ b/app.py\n"`, which yields `{"app.py"}` and matches its `file="app.py"`, and `tests/test_verify.py:133` passes the literal `"diff"`, which yields the empty set.

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/test_verify_paths.py tests/test_verify.py tests/test_verify_causes.py -v`

Expected: PASS, all three files.

- [ ] **Step 8: Run the full suite and the linters**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`

Expected: PASS.

- [ ] **Step 9: Update `sec_overlay/README.md`**

In the `verify.py` entry, add to the cause list:

> `rule-no-target-file` — the patch writes no file the finding's rule fires in, so a re-scan cannot observe the fix. Maps to `static-only`, never to `not-fixed`.

- [ ] **Step 10: Commit**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.6.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
git commit -m "feat(verify): add the rule-no-target-file cause"
```

---

## Task 3: REQ-60 — `rule-no-discriminate` from a pre/post evidence comparison

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py:68`, `:147-190`, `:190-213`, `:288-303`, `:328-397`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify.py:126`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py`

**Interfaces:**
- Consumes: `verify._path_matches` from Task 1; the `"rule-no-discriminate"` cause already in `VERIFY_CAUSES` from Task 2.
- Produces: `_file_has_hit(..., *, detail: list[Finding] | None = None)` and `_check(..., *, detail: list[Finding] | None = None)`. `verify_patch` gains no new parameter. `verify_findings` writes a `reason` key into the `verify:cause:` history entry when, and only when, the scan produced detail.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_verify_paths.py`:

```python
_INSERTING_DIFF = (
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1,2 +1,5 @@\n"
    "+import os\n"
    "+import posixpath\n"
    "+\n"
    "-p = path.join(base, name)\n"
    "+p = path.resolve(base, name)\n"
)


def _evidence_hit(path: str, line: int, text: str) -> Finding:
    f = _hit(path)
    f.line = line
    f.evidence = text
    return f


def test_a_rule_that_matches_both_constructions_reports_no_discriminate(monkeypatch):
    pre = _evidence_hit("app.py", 177, "p = path.join(base, name)")
    post = _evidence_hit("app.py", 180, "p = path.resolve(base, name)")
    seen = {"n": 0}

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        seen["n"] += 1
        if detail is not None:
            detail.append(pre if seen["n"] == 1 else post)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    out = V.verify_patch("/repo", _INSERTING_DIFF, "cfg", "app.py", "path-traversal")
    assert out == "rule-no-discriminate"


def test_a_surviving_construction_still_reports_not_fixed(monkeypatch):
    same = _evidence_hit("app.py", 177, "p = path.join(base, name)")

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        if detail is not None:
            detail.append(same)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    out = V.verify_patch("/repo", _INSERTING_DIFF, "cfg", "app.py", "path-traversal")
    assert out == "not-fixed"


def test_the_history_reason_names_both_lines(monkeypatch, tmp_path):
    from sec_overlay.workspace import Workspace, write_findings

    pre = _evidence_hit("app.py", 177, "p = path.join(base, name)")
    post = _evidence_hit("app.py", 180, "p = path.resolve(base, name)")
    seen = {"n": 0}

    def fake_hit(target_dir, config, file_path, cls, rules, *, detail=None, **kw):
        seen["n"] += 1
        if detail is not None:
            detail.append(pre if seen["n"] == 1 else post)
        return True

    monkeypatch.setattr(V, "_file_has_hit", fake_hit)
    monkeypatch.setattr(V, "apply_patch", lambda d, p, **k: True)
    ws = Workspace(root=tmp_path / "ws")
    ws.ensure()
    f = _hit("app.py")
    f.status = FindingStatus.CONFIRMED
    f.patch_diff = _INSERTING_DIFF
    write_findings(ws, [f])
    V.verify_findings(ws, "/repo", "cfg")
    entry = next(
        h for h in V.read_findings(ws)[0].history
        if h.get("event") == "verify:cause:rule-no-discriminate"
    )
    assert entry["reason"] == "pre line 177, post line 180"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_verify_paths.py -k "discriminate or surviving or history_reason" -v`

Expected: FAIL. `test_a_rule_that_matches_both_constructions_reports_no_discriminate` fails with `assert 'not-fixed' == 'rule-no-discriminate'`, and `test_the_history_reason_names_both_lines` raises `StopIteration`.

- [ ] **Step 3: Commit the red state**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.6.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify_paths.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(verify): pin rule-no-discriminate on evidence text"
```

- [ ] **Step 4: Import `Finding` and thread `detail` through `_file_has_hit`**

In `sec_overlay/verify.py`, change the models import at line 68:

```python
from sec_overlay.models import Finding, FindingStatus
```

Add the keyword-only parameter and its docstring entry to `_file_has_hit`:

```python
def _file_has_hit(
    target_dir: str, config: str, file_path: str, cls: str, rules: set[str],
    *, backend: str = "semgrep", language: str | None = None, db_dir: str | None = None,
    detail: list[Finding] | None = None,
) -> bool | None:
```

```python
        detail: When given, every matching scanner finding is appended, so the
            caller can compare pre-patch and post-patch matches rather than only
            their presence. A monkeypatched stub that ignores it leaves it empty,
            and the caller falls back to the boolean comparison.
```

Extend the matching loop to record before returning:

```python
    matched = False
    for f in findings:
        if not _path_matches(f.file, file_path, target_dir):
            continue
        if f.rule_id in rules if rules else f.cls == cls:
            matched = True
            if detail is None:
                return True
            detail.append(f)
    return matched
```

- [ ] **Step 5: Thread `detail` through `_check`**

```python
def _check(
    target: str, configs: list[str], file_path: str, cls: str, rules: set[str],
    backend: str, language: str | None, db_dir: str | None,
    *, detail: list[Finding] | None = None,
) -> bool | None:
    """Call ``_file_has_hit`` once per config, OR-combining the tri-state result.

    ``semgrep`` uses the original 5-positional-arg call (kept exact for
    backward compatibility with existing monkeypatches of ``_file_has_hit``);
    ``codeql``/``sca`` ignore ``configs`` entirely and run once, so a
    multi-ruleset plan never re-runs a database build per ruleset. ``detail``
    rides as a keyword so a 5-positional monkeypatch still binds.
    """
    if backend != "semgrep":
        return _file_has_hit(
            target, configs[0], file_path, cls, rules,
            backend=backend, language=language, db_dir=db_dir, detail=detail,
        )
    saw_none = False
    for config in configs:
        hit = _file_has_hit(target, config, file_path, cls, rules, detail=detail)
        if hit:
            return True
        if hit is None:
            saw_none = True
    return None if saw_none else False
```

The semgrep branch keeps five positional arguments; `detail=` is the only addition and it is a keyword.

- [ ] **Step 6: Compare the two evidence sets in `verify_patch`**

Replace the two `_check` calls and the post-patch verdict. The pre-scan:

```python
    pre_detail: list[Finding] = []
    pre = _check(
        target, configs, file, cls, rules, backend, language, db_dir, detail=pre_detail
    )
    if not pre:
        return "rule-no-match"
```

The post-scan and verdict, inside the `try:` block:

```python
            post_detail: list[Finding] = []
            post = _check(
                str(repo), configs, file, cls, rules, backend, language, db_dir,
                detail=post_detail,
            )
            if post is None:
                return "unconfirmed"
            if not post:
                return "verified-static"
            return _post_verdict(pre_detail, post_detail)
```

Add the helper immediately above `verify_patch`:

```python
def _post_verdict(pre: list[Finding], post: list[Finding]) -> str:
    """Return ``not-fixed`` or ``rule-no-discriminate`` for a surviving hit.

    Compares matched source text, never line numbers: a patch that inserts a
    line shifts every later line, so a line comparison would call a genuinely
    unfixed finding a new construction. Disjoint evidence sets mean the rule
    fires on something the patch introduced — the rule does not separate the
    vulnerable construction from the safe one (REQ-60). Overlapping sets mean the
    original construction survives.

    Args:
        pre: Findings the pre-patch scan matched; empty when a stub supplied none.
        post: Findings the post-patch scan matched; empty on the same condition.

    Returns:
        ``"rule-no-discriminate"`` when both sets are non-empty and share no
        evidence text, else ``"not-fixed"``.
    """
    if not pre or not post:
        return "not-fixed"
    before = {f.evidence.strip() for f in pre if f.evidence}
    after = {f.evidence.strip() for f in post if f.evidence}
    if before and after and not (before & after):
        return "rule-no-discriminate"
    return "not-fixed"
```

`verify_patch` returns a plain string, so the pre-hit and post-hit lines cannot ride on the return value. Step 7 recovers them in `verify_findings`, which owns the history write.

- [ ] **Step 7: Carry the lines into the history entry**

`verify_findings` calls `verify_patch` per finding and appends the cause at `verify.py:384`. Give the module a per-call detail record and read it back. Add above `_post_verdict`:

```python
# The lines the last ``verify_patch`` call matched, pre-patch and post-patch. The
# cause is a plain string, so the numbers the register asks for cannot ride on the
# return value; ``verify_findings`` reads them here immediately after the call.
_LAST_LINES: dict[str, int] = {}
```

Set it in `_post_verdict`, immediately after the two set comprehensions:

```python
    _LAST_LINES.clear()
    _LAST_LINES.update({"pre": pre[0].line, "post": post[0].line})
```

Clear it at the top of `verify_patch`, so a stale record from a prior finding cannot leak:

```python
    _LAST_LINES.clear()
```

In `verify_findings`, replace the history append at line 384:

```python
        entry: dict[str, object] = {"event": f"verify:cause:{cause}"}
        if _LAST_LINES:
            entry["reason"] = f"pre line {_LAST_LINES['pre']}, post line {_LAST_LINES['post']}"
        f.history.append(entry)
```

`_LAST_LINES` is only ever populated when both detail lists are non-empty, which no monkeypatched stub produces, so `test_verify_findings_records_the_cause` at `tests/test_verify_causes.py:94` still sees the exact dict `{"event": f"verify:cause:{cause}"}`.

- [ ] **Step 8: Widen the one narrow test fake**

In `tests/test_verify.py:126`, change:

```python
    def fake_hit(target_dir, config, basename, cls, rules):
```

to:

```python
    def fake_hit(target_dir, config, file_path, cls, rules, **kw):
```

That is the only test edit in this task. The fake at `tests/test_verify.py:198` already accepts `**kw`.

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/test_verify_paths.py tests/test_verify.py tests/test_verify_causes.py -v`

Expected: PASS, all three files, including the three `needs_semgrep` cases, which now run the real scanner with a populated `detail` list.

- [ ] **Step 10: Run the full suite and the linters**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`

Expected: PASS.

- [ ] **Step 11: Update `sec_overlay/README.md` and `tests/README.md`**

In `sec_overlay/README.md`, add to the cause list:

> `rule-no-discriminate` — the rule fires after the patch on source text the pre-patch scan never matched, so its sink list covers both the vulnerable and the safe construction. Maps to `static-only`. The finding's history entry names the pre-patch and post-patch lines.

In `tests/README.md`, add a `test_verify_paths.py` row stating that it pins the path matcher, the `rule-no-target-file` cause, the `rule-no-discriminate` cause, and the history reason.

- [ ] **Step 12: Commit**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.7.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_verify.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "feat(verify): add the rule-no-discriminate cause"
```

---

## Task 4: REQ-61 — generate every document's phase order from `PHASE_TABLE`

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_docs.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md:54-100`
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md:191-250`
- Modify: `plugins/sec-overlay/skills/sec-overlay/README.md:101`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/README.md:41`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/README.md:55`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_docs.py` (new)

**Interfaces:**
- Consumes: nothing from Tasks 1 to 3.
- Produces: `phase_docs.render_phase_table(columns: tuple[str, ...], kind: str | None = None) -> str`, `phase_docs.regenerate(text: str) -> str`, `phase_docs.DOCUMENTS: tuple[Path, ...]`, `phase_docs.NOTE_DOCUMENTS: tuple[Path, ...]`, `phase_docs.NON_TABLE_STEPS: tuple[str, ...]`, `phase_docs.ORCHESTRATOR_TOKENS: tuple[str, ...]`, `phase_docs.note_keys(text: str) -> list[str]`, and `phase_docs.main(argv: list[str] | None = None) -> int`. Task 5 calls `note_keys`, `NOTE_DOCUMENTS`, `NON_TABLE_STEPS`, and `ORCHESTRATOR_TOKENS`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_phase_docs.py`:

```python
"""REQ-61: every document states the phase order the code holds."""

from __future__ import annotations

from dataclasses import replace

from sec_overlay import phase_docs
from sec_overlay.phase_docs import DOCUMENTS, regenerate, render_phase_table
from sec_overlay.phases import PHASE_TABLE


def test_every_document_carries_a_generated_block():
    for doc in DOCUMENTS:
        assert "<!-- BEGIN GENERATED: phase-table" in doc.read_text(), doc.name


def test_every_generated_block_is_current():
    for doc in DOCUMENTS:
        text = doc.read_text()
        assert regenerate(text) == text, f"{doc.name} phase-table block is stale"


def test_the_table_states_every_phase_in_order():
    out = render_phase_table(("index", "phase"))
    rows = [ln for ln in out.splitlines()[2:] if ln.startswith("|")]
    assert len(rows) == len(PHASE_TABLE)
    for i, (row, phase) in enumerate(zip(rows, PHASE_TABLE, strict=True), start=1):
        assert row.startswith(f"| {i} | `{phase.name}` |")


def test_a_kind_filter_keeps_the_full_table_index():
    out = render_phase_table(("index", "phase"), kind="agent")
    rows = [ln for ln in out.splitlines()[2:] if ln.startswith("|")]
    agents = [(i, p) for i, p in enumerate(PHASE_TABLE, start=1) if p.kind == "agent"]
    assert len(rows) == len(agents)
    assert rows[0].startswith(f"| {agents[0][0]} | `{agents[0][1].name}` |")


def test_renaming_a_phase_makes_a_block_stale(monkeypatch):
    renamed = tuple(
        replace(p, name="renamed-phase") if p.name == "dedupe" else p for p in PHASE_TABLE
    )
    monkeypatch.setattr(phase_docs, "PHASE_TABLE", renamed)
    for doc in DOCUMENTS:
        text = doc.read_text()
        if "`dedupe`" in text:
            assert regenerate(text) != text, doc.name


def test_check_mode_passes_and_reports_nothing(capsys):
    assert phase_docs.main(["--check"]) == 0
    assert capsys.readouterr().out == ""
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_phase_docs.py -v`

Expected: FAIL. Every test errors at collection with `ModuleNotFoundError: No module named 'sec_overlay.phase_docs'`.

- [ ] **Step 3: Commit the red state**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.7.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_docs.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(phase-docs): pin the generated phase-order block"
```

- [ ] **Step 4: Write the generator**

Create `sec_overlay/phase_docs.py`:

```python
"""Render the phase order from ``PHASE_TABLE`` into the documents that state it.

Every document that states the order carries a marked block::

    <!-- BEGIN GENERATED: phase-table columns=index,phase,kind -->
    | # | Phase | Kind |
    ...
    <!-- END GENERATED: phase-table -->

The marker's own ``columns`` and optional ``kind`` attributes select what that
block holds, so one renderer serves every document and no per-document column
registry can drift from the document it describes.

``python -m sec_overlay.phase_docs --check`` fails when a block is stale;
``--write`` rewrites every stale block. The contract lint calls the same code, so
a phase rename or reorder fails a test until the documents regenerate.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from pathlib import Path

from sec_overlay.phases import PathOf, PHASE_TABLE, PhaseSpec
from sec_overlay.workspace import Workspace

# Steps the orchestrator runs that PHASE_TABLE does not own: they either precede
# the driver (preflight, begin-pass) or are dispatched by the skill outside the
# table (context-ingest, the tier-1 substrate build, the optional tune loop, the
# cluster pass). The operator-note lint accepts these keys beside phase names.
NON_TABLE_STEPS: tuple[str, ...] = (
    "preflight",
    "begin-pass",
    "context-ingest",
    "tier1-substrate",
    "tune",
    "cluster",
)

# Tokens a document may name that ``render_dispatch`` does not emit. ``run.py``
# writes REPO_ROOT and SCAN_SCOPE (``run.py:159-160``), ``review_agent`` writes
# REPO_ROOT, and PHASE and ROUND are supplied by hand per prompt. Keeping these
# out of ``DISPATCH_TOKENS`` keeps that tuple exactly what the driver substitutes.
ORCHESTRATOR_TOKENS: tuple[str, ...] = ("REPO_ROOT", "SCAN_SCOPE", "PHASE", "ROUND")

SKILL_ROOT = Path(__file__).resolve().parents[2]

DOCUMENTS: tuple[Path, ...] = (
    SKILL_ROOT / "CLAUDE.md",
    SKILL_ROOT / "SKILL.md",
    SKILL_ROOT / "README.md",
    SKILL_ROOT / "agents" / "README.md",
    SKILL_ROOT / "helpers" / "README.md",
)

# The two documents that also hold per-phase operator notes.
NOTE_DOCUMENTS: tuple[Path, ...] = (SKILL_ROOT / "CLAUDE.md", SKILL_ROOT / "SKILL.md")

_BEGIN = re.compile(r"^<!-- BEGIN GENERATED: phase-table(?P<attrs>[^>]*)-->$", re.MULTILINE)
_END = "<!-- END GENERATED: phase-table -->"

_NOTES_BEGIN = "<!-- BEGIN PHASE NOTES -->"
_NOTES_END = "<!-- END PHASE NOTES -->"
_NOTE_KEY = re.compile(r"^ *[-*] +\*\*(?P<key>[a-z0-9][a-z0-9_.-]*)\*\* +—", re.MULTILINE)

_HEADINGS = {
    "index": "#",
    "phase": "Phase",
    "kind": "Kind",
    "prompt": "Prompt",
    "reads": "Reads",
    "writes": "Writes",
}

# A path-only workspace: every PathOf in the table derives from ``ws.root``, so a
# literal root renders each declared artifact as a workspace-relative path with no
# filesystem access and no absolute path leaking into a document.
_WS = Workspace(root="workspace")


def _artifacts(getters: Sequence[PathOf]) -> str:
    """Render one phase's declared artifact paths, workspace-relative."""
    if not getters:
        return "—"
    return "<br>".join(f"`{g(_WS).relative_to(_WS.root).as_posix()}`" for g in getters)


def _cell(phase: PhaseSpec, index: int, column: str) -> str:
    """Render one table cell.

    Args:
        phase: The phase the row describes.
        index: The phase's 1-based position in the full ``PHASE_TABLE``.
        column: One key of ``_HEADINGS``.

    Returns:
        The cell's markdown text.

    Raises:
        ValueError: ``column`` is not a known column name.
    """
    if column == "index":
        return str(index)
    if column == "phase":
        return f"`{phase.name}`"
    if column == "kind":
        return phase.kind
    if column == "prompt":
        return f"`agents/{phase.prompt}`" if phase.prompt else "—"
    if column == "reads":
        return _artifacts(phase.inputs)
    if column == "writes":
        return _artifacts(phase.outputs)
    raise ValueError(f"unknown phase-table column: {column}")


def render_phase_table(columns: tuple[str, ...], kind: str | None = None) -> str:
    """Return the markdown table for ``columns``, optionally one ``kind`` only.

    The index column always counts positions in the full ``PHASE_TABLE``, so a
    filtered view still states each phase's real place in the run.

    Args:
        columns: Column keys, in render order; each must be a ``_HEADINGS`` key.
        kind: ``"agent"`` or ``"deterministic"`` to filter rows; ``None`` for all.

    Returns:
        The table as markdown, with no trailing newline.
    """
    rows = [(i, p) for i, p in enumerate(PHASE_TABLE, start=1) if kind is None or p.kind == kind]
    head = "| " + " | ".join(_HEADINGS[c] for c in columns) + " |"
    rule = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(_cell(p, i, c) for c in columns) + " |" for i, p in rows]
    return "\n".join([head, rule, *body])


def _attrs(raw: str) -> tuple[tuple[str, ...], str | None]:
    """Parse a marker's ``columns=`` and optional ``kind=`` attributes.

    Args:
        raw: The marker text between ``phase-table`` and ``-->``.

    Returns:
        The column keys and the kind filter, or ``None`` for no filter.

    Raises:
        ValueError: The marker declares no columns.
    """
    found = dict(re.findall(r"(\w+)=([\w,\-]+)", raw))
    if "columns" not in found:
        raise ValueError("phase-table marker declares no columns=")
    return tuple(found["columns"].split(",")), found.get("kind")


def regenerate(text: str) -> str:
    """Return ``text`` with every phase-table block replaced by fresh output.

    Blocks are rewritten last-first, so an earlier match's offsets stay valid.

    Args:
        text: A document's full text.

    Returns:
        The same text with each block regenerated.

    Raises:
        ValueError: A block has no end marker, or its marker declares no columns.
    """
    out = text
    for m in reversed(list(_BEGIN.finditer(text))):
        start = m.end()
        stop = out.find(_END, start)
        if stop < 0:
            raise ValueError("phase-table block has no END marker")
        columns, kind = _attrs(m.group("attrs"))
        out = out[:start] + "\n" + render_phase_table(columns, kind) + "\n" + out[stop:]
    return out


def note_keys(text: str) -> list[str]:
    """Return the phase keys of a document's operator-note list, in order.

    Args:
        text: A document's full text, holding one phase-notes region.

    Returns:
        The bolded key of each ``- **<key>** — …`` item, in document order.

    Raises:
        ValueError: The document has no phase-notes region.
    """
    if _NOTES_BEGIN not in text or _NOTES_END not in text:
        raise ValueError("document has no phase-notes region")
    body = text.split(_NOTES_BEGIN, 1)[1].split(_NOTES_END, 1)[0]
    return [m.group("key") for m in _NOTE_KEY.finditer(body)]


def main(argv: list[str] | None = None) -> int:
    """Check or rewrite every generated phase-table block.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        1 when ``--check`` found a stale block, else 0.
    """
    ap = argparse.ArgumentParser(description="Generate phase-order document blocks.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail when a block is stale")
    mode.add_argument("--write", action="store_true", help="rewrite every stale block")
    args = ap.parse_args(argv)
    stale = []
    for doc in DOCUMENTS:
        text = doc.read_text()
        fresh = regenerate(text)
        if fresh == text:
            continue
        stale.append(doc)
        if args.write:
            doc.write_text(fresh)
    for doc in stale:
        print(f"{'rewrote' if args.write else 'stale'}: {doc}")
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Insert the marked block into each of the three folder READMEs**

In `skills/sec-overlay/README.md`, directly under the `## The pipeline` prose at line 104, insert:

```markdown
<!-- BEGIN GENERATED: phase-table columns=index,phase,kind -->
<!-- END GENERATED: phase-table -->
```

In `agents/README.md`, directly under the `## The pipeline, as prompts` heading at line 41, insert:

```markdown
<!-- BEGIN GENERATED: phase-table columns=index,phase,prompt kind=agent -->
<!-- END GENERATED: phase-table -->
```

In `helpers/README.md`, directly under the `## The pipeline these modules implement` heading at line 55, insert:

```markdown
<!-- BEGIN GENERATED: phase-table columns=index,phase,reads,writes kind=deterministic -->
<!-- END GENERATED: phase-table -->
```

Leave the hand-written prose, the mermaid graph, and the per-module rows in place. The block states the order; the prose states what each part means.

- [ ] **Step 6: Replace `CLAUDE.md`'s hand-numbered fence**

In `skills/sec-overlay/CLAUDE.md`, delete the fenced block at lines 54-100 in full, keeping the `### Phase order (one pass)` heading and the `Legend:` line above it. In its place put:

```markdown
<!-- BEGIN GENERATED: phase-table columns=index,phase,kind,prompt,reads,writes -->
<!-- END GENERATED: phase-table -->

### Operator notes per phase

<!-- BEGIN PHASE NOTES -->
<!-- END PHASE NOTES -->
```

Then move every operational sentence out of the deleted fence into the notes region, keyed by phase name in the order the table states, one item per phase. Every phase in the table gets an item; a phase whose note is only its command gets that command. Keep the ordinal-free form exactly:

```markdown
- **preflight** — `python -m sec_overlay.preflight`; run any printed install or vendor command before scanning. Not in `PHASE_TABLE`; the operator runs it.
- **begin-pass** — `sec_overlay.state.begin_pass(ws, sha)` pins the SHA and increments only after a prior pass recorded a stage. Not in `PHASE_TABLE`.
- **context-ingest** — `agents/context-ingest.md` (sonnet), then `agents/context-adversary.md` (opus); repo documents are UNTRUSTED. Not in `PHASE_TABLE`.
- **tier1-substrate** — `python -m sec_overlay.graph build --target <T> --workspace <WS> --sha <sha>`; LLM-free structural index plus regex call edges. Not in `PHASE_TABLE`.
- **tune** — `agents/tune-config.md`, optional, ratcheted rule and exclusion loop, at most 3 rounds. Not in `PHASE_TABLE`.
- **cluster** — `python -m sec_overlay.cluster --workspace <WS>` groups 3 or more same-class, same-sink `raw` findings into one systemic cluster. Not in `PHASE_TABLE`.
- **route-census** — code-derived route inventory; reads the target's source, never recon's output, so a route recon never names still appears as a gap.
- **recon** — `agents/recon.md` (sonnet); validate the profile with `load_profile`. Phase gate: `agents/phase-adversary.md` (opus).
```

Continue that list through every remaining phase the generated table names, in table order, carrying the sentences the fence held for each. Where the fence held no sentence for a phase, write its command or its prompt name. When `--write` has run, the notes region and the table sit side by side and neither restates the other's ordinals.

- [ ] **Step 7: Replace `SKILL.md`'s hand-numbered list**

In `skills/sec-overlay/SKILL.md`, keep every paragraph from `## Running a full audit` down to the sentence ending `keep that fallback in the agent's instructions.` unchanged. Then replace the numbered list that follows (items `0.` through `14.`, including `7.5` and `13.5`) with:

```markdown
<!-- BEGIN GENERATED: phase-table columns=index,phase,kind,prompt -->
<!-- END GENERATED: phase-table -->

<!-- BEGIN PHASE NOTES -->
<!-- END PHASE NOTES -->
```

Move each numbered item's text into the notes region verbatim, keyed by phase name, in table order. Change nothing inside an item except its leading ordinal and label. For example, item `0.` becomes:

```markdown
- **preflight** — `python -m sec_overlay.preflight`; run any printed install/vendor commands before scanning (missing backends are skipped + logged). The report lists which **CodeQL query packs** are installed — the `codeql` binary being present does NOT mean the per-language packs exist, and a missing pack silently drops all of that language's dataflow coverage. If a language you will scan is not listed, run `codeql pack download codeql/<lang>-queries` first. CodeQL runs only on a trusted config (`codeql_config_trusted`); unsupported or untrusted configs are skipped and logged in the prefilter `failed` list.
```

Every phase the table names needs an item, so the ten phases the old list omitted — `recall-gate`, `judge`, `trace`, `demote-noise`, `selfscore`, `artifact-gate`, `artifact-review`, `artifact-consistency`, `prove`, `postflight` — gain one each. Write each from the phase's own module docstring or prompt front matter; do not invent behavior. Do not renumber, do not reorder, and drop no sentence from an existing item.

- [ ] **Step 8: Generate every block**

Run: `uv run python -m sec_overlay.phase_docs --write`

Expected output: five `rewrote:` lines, one per document.

- [ ] **Step 9: Run the tests**

Run: `uv run pytest tests/test_phase_docs.py -v`

Expected: PASS, six tests.

- [ ] **Step 10: Check the `CLAUDE.md` line cap**

Run: `wc -l ../CLAUDE.md`

Expected: under 200. The file holds 214 lines at 1.122.0; the 47-line fence becomes a 30-line table. If the notes region pushes it back over 200, move the longest notes into `SKILL.md`, which has no cap, and leave a pointer.

- [ ] **Step 11: Run the full suite and the linters**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`

Expected: PASS.

- [ ] **Step 12: Update `sec_overlay/README.md` and `helpers/README.md`**

Add a `phase_docs.py` row to `sec_overlay/README.md`'s module table: renders `PHASE_TABLE` into the five documents that state the phase order, with `--check` and `--write` modes and the note-key parser the contract lint uses.

In `helpers/README.md`, add to the maintainer commands: `uv run python -m sec_overlay.phase_docs --write` after any change to `PHASE_TABLE`, and `--check` to see whether a document is stale without editing it.

- [ ] **Step 13: Commit**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.8.0"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_docs.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/README.md \
        plugins/sec-overlay/skills/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md
git commit -m "feat(phase-docs): generate the phase order from the table"
```

---

## Task 5: REQ-61 — extend the contract lint to phase names and document tokens

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md`

**Interfaces:**
- Consumes: `phase_docs.note_keys`, `phase_docs.NOTE_DOCUMENTS`, `phase_docs.DOCUMENTS`, `phase_docs.NON_TABLE_STEPS`, and `phase_docs.ORCHESTRATOR_TOKENS` from Task 4; `driver.DISPATCH_TOKENS`, already imported at `tests/test_contract_lint.py:18`.
- Produces: nothing a later task consumes. This is the last task in the plan.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_contract_lint.py`:

```python
def test_operator_notes_name_every_phase_and_nothing_else():
    """Every PHASE_TABLE phase has an operator note; no note names a stranger."""
    from sec_overlay.phase_docs import NON_TABLE_STEPS, NOTE_DOCUMENTS, note_keys
    from sec_overlay.phases import PHASE_TABLE

    phases = {p.name for p in PHASE_TABLE}
    known = phases | set(NON_TABLE_STEPS)
    for doc in NOTE_DOCUMENTS:
        keys = set(note_keys(doc.read_text()))
        assert keys <= known, f"{doc.name} names steps absent from the table: {keys - known}"
        assert keys >= phases, f"{doc.name} omits phases: {phases - keys}"


def test_operator_notes_follow_the_table_order():
    """A reorder in PHASE_TABLE must fail until the notes follow it."""
    from sec_overlay.phase_docs import NOTE_DOCUMENTS, note_keys
    from sec_overlay.phases import PHASE_TABLE

    order = [p.name for p in PHASE_TABLE]
    for doc in NOTE_DOCUMENTS:
        keys = [k for k in note_keys(doc.read_text()) if k in order]
        assert keys == sorted(keys, key=order.index), f"{doc.name} is out of table order"


def test_pipeline_documents_name_only_substitutable_tokens():
    """Every {{TOKEN}} in a pipeline document has a substituter."""
    from sec_overlay.phase_docs import DOCUMENTS, NOTE_DOCUMENTS, ORCHESTRATOR_TOKENS

    known = set(DISPATCH_TOKENS) | set(ORCHESTRATOR_TOKENS)
    for doc in dict.fromkeys((*DOCUMENTS, *NOTE_DOCUMENTS)):
        found = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", doc.read_text()))
        assert found <= known, f"{doc.name} names tokens nothing substitutes: {found - known}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_contract_lint.py -k "operator_notes or substitutable_tokens" -v`

Expected: FAIL on all three. Task 4's notes regions exist, so `note_keys` returns keys, but the phase-name coverage and the table order are unverified until now, and no test has ever checked a document's tokens. If all three pass immediately, the notes were written completely in Task 4 — record that and continue; the tests still guard the next rename.

- [ ] **Step 3: Commit the red state**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.8.1"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(contract-lint): pin phase notes and document tokens"
```

- [ ] **Step 4: Fix every document the lint rejects**

Read the failure output and repair the documents, never the assertions:

- A missing phase key: add its operator note, in table order.
- A key the table does not hold: either the phase was renamed — rename the note key — or the step is not in the table, and its name belongs in `phase_docs.NON_TABLE_STEPS`.
- An out-of-order key: move the note, do not reorder `PHASE_TABLE`.
- A token nothing substitutes: check `run.py:159-160` and `review_agent.py:179` for a producer. A token with a producer belongs in `ORCHESTRATOR_TOKENS`; a token with none is a documentation error, and the sentence naming it must stop presenting it as substitutable.

The four tokens `SKILL.md` names at 1.122.0 — `{{PHASE}}`, `{{ROUND}}`, `{{REPO_ROOT}}`, `{{SCAN_SCOPE}}` — are already in `ORCHESTRATOR_TOKENS` from Task 4, so they pass. Do not add any of them to `DISPATCH_TOKENS`: `test_dispatch_tokens_are_a_single_source` asserts that tuple equals `render_dispatch`'s substitute line, and `render_dispatch` supplies none of the four.

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/test_contract_lint.py tests/test_phase_docs.py -v`

Expected: PASS, both files.

- [ ] **Step 6: Verify a rename fails the lint**

Change `PhaseSpec("dedupe", …)` to `PhaseSpec("dedupe-x", …)` in `sec_overlay/phases.py`, run the two test files, confirm both `test_every_generated_block_is_current` and `test_operator_notes_name_every_phase_and_nothing_else` fail, then revert the edit with `git checkout -- sec_overlay/phases.py`.

Run: `uv run pytest tests/test_contract_lint.py tests/test_phase_docs.py -q`

Expected while renamed: at least 2 failures. Expected after the revert: PASS.

- [ ] **Step 7: Run the full suite and the linters**

Run: `uv run pytest -q && uv run ruff check sec_overlay/ bench/ tests/ && uv run ty check`

Expected: PASS.

- [ ] **Step 8: Update `tests/README.md`**

In the `test_contract_lint.py` row, add that it now also asserts every `PHASE_TABLE` phase has an operator note in `CLAUDE.md` and `SKILL.md`, that the notes follow table order, and that every `{{TOKEN}}` in a pipeline document is in `DISPATCH_TOKENS` or `ORCHESTRATOR_TOKENS`.

- [ ] **Step 9: Commit**

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("plugins/sec-overlay/.claude-plugin/plugin.json")
d = json.loads(p.read_text())
d["version"] = "2.8.2"
p.write_text(json.dumps(d, indent=2) + "\n")
PY
prek run
git add plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contract_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
git commit -m "test(contract-lint): fail on a phase or token a document invents"
```

---

## Self-review

**1. Specification coverage.** Group 6 holds two requirements and Group 7 holds one. REQ-59 splits across Task 1 (path-segment matching, replacing the base-filename compare at `verify.py:183`, and retiring the ponytail comment at `:286-287`) and Task 2 (the `rule-no-target-file` cause for a patch that writes no file the rule fires in). REQ-60 is Task 3 (`rule-no-discriminate` from a pre/post evidence-text comparison, plus the pre-hit and post-hit lines in the finding's history). REQ-61 splits across Task 4 (the `phase_docs.py` generator and the five documents) and Task 5 (the note-key and document-token lint). One specification sentence is not delivered as written and is recorded as ruling 1: REQ-59's "a patch to `file-name-sanitize.ts` that clears a sink in `PackageSetup.ts` verifies" is unachievable against intra-file semgrep taint, and the criterion becomes "does not report `not-fixed`". One specification phrase is corrected: REQ-61's "four folder READMEs" is three folder READMEs plus `skills/sec-overlay/CLAUDE.md`, because `references/README.md` holds no phase content. No requirement is left without a task.

**2. Placeholder scan.** Every code step holds runnable code. Every test step holds the assertions it claims. Two steps delegate content rather than showing it in full: Task 4 Step 6 and Step 7 move existing document sentences into a notes region, and the instruction is to carry each sentence unchanged, with one worked example each. That is a transcription instruction, not a placeholder — the source text is in the file being edited, and reproducing 60 lines of it here would let the plan drift from the document. Task 5 Step 4 lists the four repair cases by name with the decision rule for each, rather than naming a specific document, because which document fails depends on how completely Task 4's transcription ran.

**3. Type consistency.** `_rel_path(path: str, root: str) -> str` and `_path_matches(scanner_path: str, finding_path: str, root: str) -> bool` are defined in Task 1 and called under those names in Tasks 2 and 3. `_patch_files(patch_diff: str) -> set[str]` is defined and called in Task 2. `detail: list[Finding] | None` is keyword-only on both `_file_has_hit` and `_check` in Task 3, and `Finding` is imported in the same step. `_post_verdict(pre, post) -> str` and `_LAST_LINES: dict[str, int]` are defined and used in Task 3 only. In Task 4, `render_phase_table(columns, kind)`, `regenerate(text)`, `note_keys(text)`, `DOCUMENTS`, `NOTE_DOCUMENTS`, `NON_TABLE_STEPS`, `ORCHESTRATOR_TOKENS`, and `main(argv)` are defined once and consumed under exactly those names in Task 5. The renamed parameter is `file_path` in both `_file_has_hit` and `_check`, and the widened fake at `tests/test_verify.py:126` uses the same name.

**4. Ordering.** Tasks 1 to 3 run before Tasks 4 and 5, per the specification's build order: RC-3 runs last because generating documents from `PHASE_TABLE` is stable only once the table stops moving, and Plans 1 to 4 hold the last table edits. Inside RC-5, Task 1's `_rel_path` is a prerequisite for Task 2's `_patch_files` and Task 3's detail comparison, and Task 2 lands both new cause strings so Task 3 changes no vocabulary. Inside RC-3, Task 4 must create `phase_docs.py` and both notes regions before Task 5's lint can import them. Version numbers walk 2.5.3, 2.5.4, 2.5.5, 2.6.0, 2.6.1, 2.7.0, 2.7.1, 2.8.0, 2.8.1, 2.8.2 across the ten commits, and every one is prospective: read `plugin.json` before each bump.
