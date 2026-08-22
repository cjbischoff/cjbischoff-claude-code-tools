---
phase: 04-scale-resume-diff-output
reviewed: 2026-08-20T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - plugins/sec-overlay/.claude-plugin/plugin.json
  - plugins/sec-overlay/CHANGELOG.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_bundle.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_comments.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_coverage.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_tracer.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
  - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_sarif.py
  - plugins/sec-overlay/skills/sec-overlay/README.md
  - plugins/sec-overlay/skills/sec-overlay/SKILL.md
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-08-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed the 04-04 gap-closure changes to `sec-overlay`'s diff-scoped `review` CLI path, with
particular attention to the three areas the task called out: manifest sealing before comment
writes in `cli.py`, the `--model` CLI flag wiring, and the unit-fetch timeout bound.

All three flagged areas are correctly implemented and are backed by direct, targeted tests:

- **Manifest sealing before comment writes** (`cli.py:554-561`): for any run with at least one
  reviewable file, `manifest.seal()` runs before `write_review_comments(...)`, so the embedded
  `coverage_manifest` in `review_comments.json` matches the on-disk `coverage_manifest.json`'s
  seal value for both `complete` and `partial` outcomes — proven by
  `test_review_comments_embedded_manifest_seal_matches_on_disk_after_complete_run` and
  `test_review_comments_embedded_manifest_seal_is_partial_after_partial_run` in `test_cli.py`.
  A real gap remains in the *zero-reviewable-files* branch, which never calls `.seal()` at all
  (see WR-01 below) — it is a distinct, adjacent bug the flagged fix did not need to touch, but
  it undermines the same OUT-01 contract for one input shape.
- **`--model` CLI flag wiring** (`cli.py:572-728`): correctly parsed, forwarded to `run_review`,
  and enforced by the resume-identity gate (`check_resume_identity`). Confirmed correct and
  comprehensively tested — no finding.
- **Unit-fetch timeout bound** (`cli.py:417-442`): the bounded `ThreadPoolExecutor` is sized
  correctly, `shutdown(wait=False)` avoids blocking the caller past `--timeout` on an abandoned
  worker, and the process-level `timeout=` binding on the shared `subprocess.run` partial
  (`cli.py:329-335`) reaches every git call the review path makes. Confirmed correct and
  comprehensively tested — no finding.

Beyond the three flagged areas, this review found one real, untested behavioral gap in the
zero-reviewable-files branch of `run_review` (WR-01) and one untested false-positive risk in
`bundle.py`'s locale-sibling grouping heuristic (WR-02). Neither is a crash, a security issue, or
a correctness failure for the common case (a diff with at least one reviewable file, or two files
that are genuinely locale/config siblings); both are contract/robustness gaps worth closing.

## Warnings

### WR-01: Zero-reviewable-files run never persists a coverage manifest, contradicting its own docstring

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:310-319, 556-558`

**Issue:** `run_review`'s docstring claims:

```
Returns:
    0 when the coverage manifest seals ``complete`` (including a diff with no
    reviewable files) or ``prepare=True`` completed, ...
```

but the code for that exact case never calls `.seal()`:

```python
if not selection.reviewable:
    write_review_comments(ws, comments, manifest.to_dict())
    return 0
```

This is deliberate — `CoverageManifest.seal()` raises `CoverageTransitionError` on an empty
manifest (`review_coverage.py:146-147`), so calling it here would crash a legitimately successful
run. But avoiding the raise leaves two real gaps instead of the docstring's claimed
`"complete"` seal:

1. `CoverageManifest.__init__` sets `self._seal: str | None = None`
   (`review_coverage.py:80`) and nothing in this branch ever changes it, so
   `manifest.to_dict()["seal"]` — the value embedded in `review_comments.json`'s
   `coverage_manifest` field — is `null`, not the string `"complete"` a downstream consumer
   checking the documented contract would expect.
2. `CoverageManifest._persist()` is only called from `add()`, `_transition()`
   (`start`/`finish`/`fail`), and `seal()` (`review_coverage.py:102, 125, 152`). None of those run
   when `selection.reviewable` is empty, so `coverage_manifest.json` is never written to disk at
   all for this run — despite the run returning exit code 0 (success). A subsequent invocation
   against the same target then finds `manifest_path.exists()` is `False`
   (`cli.py:343`), so the SCALE-03 resume-identity gate silently does not activate on the next
   call; that next call is treated as fresh rather than a resume. In this specific case the
   omission is low-impact (there is nothing to resume when zero files were reviewed), but it is
   still a departure from the "coverage manifest reflects what happened" invariant the rest of
   the module upholds everywhere else.

`test_review_zero_reviewable_files_returns_exit_0_with_no_unfinished_line` only asserts `rc == 0`
and that `"unfinished"` is absent from stdout — it does not assert on the embedded/on-disk seal
value or on `coverage_manifest.json`'s existence, so this gap is untested as well as
undocumented-accurately.

**Fix:** Either (a) correct the docstring to state the embedded/on-disk seal is `null` (or absent
entirely) for a diff with no reviewable files, while still returning 0, or (b) make the zero-file
case genuinely seal `"complete"` by special-casing it, e.g.:

```python
if not selection.reviewable:
    manifest._seal = "complete"  # vacuously complete: no files needed review
    manifest._persist()
    write_review_comments(ws, comments, manifest.to_dict())
    return 0
```

Option (b) is preferable — it keeps the manifest file's existence and the embedded seal value
consistent with every other return path, and it lets a resumed run against the same target still
be recognized as a resume. Add a test asserting `coverage_manifest.json` exists and its `seal`
field is `"complete"` after a zero-reviewable-files run, whichever fix is chosen.

### WR-02: Locale-sibling bundling heuristic can group unrelated source files

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/bundle.py:30, 65-66`

**Issue:** `_group_key` groups two files into one `ReviewUnit` as locale siblings whenever they
sit in the same directory and share a stem matching `_LOCALE_STEM`:

```python
_LOCALE_STEM = re.compile(r"^[a-z]{2}(-[A-Z]{2})?$")
...
if dot and _LOCALE_STEM.match(stem):
    return f"{directory}::locale::{ext}"
```

This regex matches any two-letter (optionally region-qualified) filename stem, regardless of
extension — it is not restricted to locale-data extensions (`.json`, `.yaml`, `.po`, `.arb`,
etc.). `group_bundles` only ever receives `selection.reviewable`, i.e. files that already passed
`file_select`'s `ALLOWED_EXTENSIONS` filter, which includes ordinary source extensions
(`.py`, `.js`, `.go`, ...). A plausible pair such as `id.py` and `ok.py` (or `to.js` and `db.js`)
in the same directory would be grouped into one `ReviewUnit` purely by heuristic coincidence, even
though they are unrelated source files, not locale siblings. The practical consequence (per
SCALE-01/SCALE-02) is that the two files then share one review pass's membership, one
`--timeout` budget, and one shared failure/timeout blast radius — an unrelated file's slow git
fetch can now mark another unrelated file `failed` too.

`test_bundle.py` exercises the genuine locale-sibling case (e.g. `en.json`/`fr.json`) and a
locale-siblings-*across-directories* negative case, but has no test for two same-stem,
non-locale-extension source files in the same directory, so this false-positive path is
untested.

**Fix:** Scope `_LOCALE_STEM` matching to a small allowlist of locale-data extensions, e.g.:

```python
_LOCALE_EXTENSIONS = frozenset({"json", "yaml", "yml", "po", "arb", "properties", "xliff"})
...
if dot and ext in _LOCALE_EXTENSIONS and _LOCALE_STEM.match(stem):
    return f"{directory}::locale::{ext}"
```

Add a regression test asserting `id.py` and `ok.py` in the same directory land in two separate
units.

## Info

### IN-01: Fetch-map lookup relies on an unstated cross-function invariant

**File:** `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py:443-444`

**Issue:**

```python
for record in selection.reviewable:
    fetched = fetch_by_path[record.path]
```

This direct dict-index access (no `.get()` fallback) only avoids a `KeyError` because
`group_bundles` is total over `selection.reviewable` (every path appears in exactly one unit,
proven by `test_bundle.py::test_group_bundles_every_path_appears_in_exactly_one_unit`) and the
fetch loop immediately above populates `fetch_by_path` for every member of every unit in `units`,
where `units = group_bundles(selection.reviewable)` (`cli.py:400`). The invariant holds today and
is well-tested, but nothing at this call site documents *why* the direct index is safe — a future
change to `units` construction (e.g. filtering `units` after computing `selection.reviewable`)
could silently reintroduce a `KeyError` here with no local signal of what broke the contract.

**Fix:** A one-line comment at `cli.py:443` noting the invariant (`# safe: group_bundles is total
over selection.reviewable, see bundle.py`) would make the coupling visible to the next editor
without changing behavior.

---

_Reviewed: 2026-08-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
