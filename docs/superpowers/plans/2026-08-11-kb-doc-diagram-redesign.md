# KB Doc/Diagram Redesign Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port upstream `sec-harness`'s "KB doc/diagram redesign" feature series into the local `sec-overlay` plugin, name-normalized, without overwriting the local `render_util` / object-`expected_signal` divergence.

**Architecture:** Semantic feature port, not a git cherry-pick — apply each upstream change to the renamed local files. Helper changes follow TDD (port the upstream test first, confirm red, then port the implementation). Prompt/doc changes are prose edits. Six logical commits on one branch, each leaving the `helpers/` suite green and updating governance docs.

**Tech Stack:** Python 3.13 (`sec_overlay` package, `pytest`), Markdown agent prompts, JSON Schema.

## Global Constraints

- Branch: `feat/kb-doc-diagram-redesign` (already checked out).
- Path base for all skill files: `plugins/sec-overlay/skills/sec-overlay/` (written `$B/` below).
- Python identifier namespace is `sec_overlay` (NOT `sec_harness`); kebab names are `sec-overlay`. Every ported snippet below is already name-normalized.
- Preserve local-only divergence: `helpers/sec_overlay/render_util.py` and object-form `expected_signal`. Do not remove or overwrite `render_util` imports/usage.
- Conventional Commits; summary under 50 chars; body wrapped at 72.
- Every commit updates root `README.md` + `CHANGELOG.md` (Common Changelog) AND the affected folder's `README.md`, in the same commit. Hooks enforce this — a commit missing them is rejected.
- Do NOT bump the plugin `version` field.
- No `Co-Authored-By` trailer in commit messages.
- Run tests from `$B/helpers/`: `uv run pytest -q` (or `pytest -q` if the env is already active). Fix all failures before committing.
- Merge to `main` only after user approval; delete the branch after merge.

## Merge-sensitive files (local render_util work coexists — keep both regions)

`$B/SKILL.md`, `$B/agents/README.md`, `$B/agents/redteam.md`, `$B/helpers/README.md`, `$B/references/README.md`, `$B/references/finding.schema.json`, `$B/helpers/sec_overlay/redteam.py`. In each, the upstream edit region and the local `render_util` region are disjoint. Apply the upstream edit without touching the local lines.

---

### Task 1: prompt-constants — DIAGRAM_STYLE, FIELD_OWNERSHIP, QUALIFIER_PROOF

**Files:**
- Modify: `$B/references/prompt-constants.md` (append after the `OUTPUT_WRITE_FALLBACK` block)
- Modify: `$B/references/README.md` (block table + count, merge-sensitive)
- Modify: root `README.md`, `CHANGELOG.md`, `$B/references/README.md`

**Interfaces:**
- Produces: three named prompt blocks (`DIAGRAM_STYLE`, `FIELD_OWNERSHIP`, `QUALIFIER_PROOF`) that Task 6's prompt edits import by name via `{{HARNESS_ROOT}}/references/prompt-constants.md`. (Local token note: confirm whether the local tree uses `{{HARNESS_ROOT}}` or a renamed token by grepping an existing block; match the existing local token verbatim.)

This task is prose only — no test cycle.

- [ ] **Step 1: Confirm the local import-path token**

Run: `rg -n 'HARNESS_ROOT|OVERLAY_ROOT' $B/references/prompt-constants.md | head`
Note which token the existing blocks use; use that same token in Task 6 references. (The block bodies below carry no token, so they are unaffected.)

- [ ] **Step 2: Append the three blocks to `prompt-constants.md`**

Append verbatim after the last existing block (`## OUTPUT_WRITE_FALLBACK`):

```markdown

## DIAGRAM_STYLE
When a phase's Output section asks for a mermaid diagram, follow these rules:
- One diagram, one job. If a view needs more entities than the cap below, add a
  SECOND diagram in sequence — never shrink labels or cram more in to avoid a
  second diagram. Give each diagram a one-line caption stating its job.
- HARD CAP: 10 entities (nodes + subgraphs combined) per diagram. Count before
  you finalize; if over, split.
- Short node IDs and labels. Put detail in a legend line below the diagram or
  in an edge label — never inside a node.
- Diagrams are a navigational/summary layer, never a citation. Every `file:line`
  claim still lives in the surrounding prose; a diagram node never carries a
  citation a reader would need to trust without the prose backing it.
- Use ` ```mermaid ` fenced code blocks so the diagram renders in any standard
  Markdown viewer.

## FIELD_OWNERSHIP
Every `Finding` field belongs to exactly one phase (see each agent's own
"Output" section for the fields it owns). Only populate the fields YOUR
phase's Output section names. If you read a finding and a field outside your
remit (`reachability`, `runtime_disposition`, `runtime_test`, `open_questions`,
`risk_score`, `patch_diff`, `verification`) already has a non-null value, leave
it exactly as it is — do not overwrite it, even if you believe you could do it
better. That field's owning phase will set or correct it. Writing outside your
remit has repeatedly produced lower-quality values that a downstream phase then
has to detect and redo.

## QUALIFIER_PROOF
A blanket security qualifier — "mitigated", "allowlisted", "sanitized",
"single chokepoint", "authorized by X", "handled elsewhere" — is a claim about
EVERY code path, not the first one you checked. Before writing one:
1. Enumerate every call site / code path that could plausibly bypass or differ
   from the one you checked (use `callers`/ast-grep, not a single grep hit).
2. Confirm the qualifier holds on ALL of them, citing each.
3. If you cannot check all paths, do NOT use the blanket qualifier — state
   exactly which specific path(s) you verified instead (e.g. "validated on the
   Cognito path; the corp/Azure path was not checked for this control").
A qualifier that turns out to cover only one of several paths is the single
most common error this harness's adversarial review layer has caught — avoid
manufacturing work for the adversary that a wider check up front would prevent.
```

- [ ] **Step 3: Update `references/README.md` (merge-sensitive — keep local lines)**

Change the mermaid node count from `(9 verbatim blocks)` to `(12 verbatim blocks)`, and the section header/prose from "9 blocks"/"Nine named blocks" to "12 blocks"/"Twelve named blocks". Replace the stale note. Add these three rows to the block table (after the `OUTPUT_WRITE_FALLBACK` row):

```markdown
| `DIAGRAM_STYLE` | When emitting a mermaid diagram, enforce the 10-entity hard cap per diagram, one diagram per job. Short node IDs with detail in legend/edges. Diagrams are navigational; `file:line` claims live in prose, not diagram nodes. |
| `FIELD_OWNERSHIP` | Each `Finding` field is owned by exactly one phase. Only populate your phase's Output fields; never overwrite downstream phase fields (e.g. `risk_score`, `patch_diff`). |
| `QUALIFIER_PROOF` | A blanket security claim ("mitigated", "sanitized", "handled elsewhere") is a claim about *every* code path. Enumerate all reachable paths and confirm the qualifier on each, or state which specific paths you verified. |
```

Replace the old stale-count note with:

```markdown
> **Note:** the table above is authoritative. If you add or remove a block, update the count
> in the Mermaid diagram, the section header, and this table.
```

(Do not touch any local `render_util`-related lines in this README.)

- [ ] **Step 4: Update governance docs and commit**

Root `README.md`: add a one-line inventory note if the references block set is inventoried (optional — only if a matching row exists). `CHANGELOG.md`: add under `### Added`: "Add the DIAGRAM_STYLE, FIELD_OWNERSHIP, and QUALIFIER_PROOF prompt-constants blocks."

```bash
git add $B/references/prompt-constants.md $B/references/README.md README.md CHANGELOG.md
git commit -m "feat(sec-overlay): add diagram/ownership/qualifier prompt blocks"
```
Expected: hook passes (references/README.md is the affected folder README; root README + CHANGELOG staged).

---

### Task 2: open_questions field on Finding

**Files:**
- Modify: `$B/helpers/sec_overlay/models.py` (add field + docstring)
- Modify: `$B/references/finding.schema.json` (add optional type, merge-sensitive)
- Test: `$B/helpers/tests/test_models.py`
- Modify: root `README.md`, `CHANGELOG.md`, `$B/helpers/README.md`

**Interfaces:**
- Produces: `Finding.open_questions: list[dict]` (default `[]`), item shape `{"question": str, "why_it_matters": str, "who_to_ask_or_check": str}`. Consumed by Task 6's `redteam.py` `_question_block`.

- [ ] **Step 1: Write the failing tests**

Append to `$B/helpers/tests/test_models.py`:

```python
def test_open_questions_field_roundtrips_and_defaults_empty():
    f = Finding(
        id="F-0099", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH, file="a.go", line=1, message="m",
    )
    assert f.open_questions == []

    f.open_questions = [{
        "question": "Is there an Azure AD group-membership check enforced "
                     "anywhere outside this repo for the /mcp user path?",
        "why_it_matters": "AUTHZ-0001 assumes no such check exists anywhere; "
                           "if one exists outside the repo, severity is overstated.",
        "who_to_ask_or_check": "identity/security-platform team; check Conditional "
                                "Access policies in the Azure AD tenant admin console.",
    }]
    d = f.to_dict()
    assert d["open_questions"][0]["question"].startswith("Is there an Azure AD")
    round_tripped = Finding.from_dict(d)
    assert round_tripped.open_questions == f.open_questions


def test_open_questions_backcompat_missing_key_defaults_empty():
    # A finding written before this field existed loads with an empty list, not a crash.
    old = Finding(
        id="F-0001", rule_id="r", cls="sqli", status=FindingStatus.RAW,
        severity=Severity.MEDIUM, file="a.py", line=1, message="m",
    ).to_dict()
    del old["open_questions"]
    assert Finding.from_dict(old).open_questions == []
```

- [ ] **Step 2: Run to verify red**

Run: `cd $B/helpers && uv run pytest tests/test_models.py -q -k open_questions`
Expected: FAIL (`AttributeError`/`TypeError` — `open_questions` not a field yet).

- [ ] **Step 3: Add the field and docstring to `models.py`**

In the `Finding` dataclass docstring `Attributes:` block, after the `runtime_dependent:` entry, add:

```python
        open_questions: Human-answerable unknowns a live-exploit test can't settle —
            org policy, external config, an affected-version range — each
            ``{"question": str, "why_it_matters": str, "who_to_ask_or_check": str}``.
            Populated by trace (external-fact verify-errors) and redteam (when the
            static/runtime discrimination surfaces a question, not a payload). Unrelated
            to ``coverage_ledger``'s same-named ``open_questions`` list, which is a
            differently-shaped surface-coverage concept, not per-finding questions.
```

In the field list, immediately after `runtime_dependent: bool = False`, add:

```python
    open_questions: list[dict] = field(default_factory=list)
```

(`field` is already imported in `models.py` — confirm; if not, this is the same `dataclasses.field` used by other defaults.)

- [ ] **Step 4: Add the schema property (merge-sensitive — keep the local `expected_signal` addition)**

In `$B/references/finding.schema.json`, in the properties object, change the `runtime_dependent` line to carry a trailing comma and add the new property after it:

```json
    "runtime_dependent": {"type": "boolean"},
    "open_questions": {"type": "array", "items": {"type": "object"}}
```

Do not remove or reorder the local `expected_signal`/`runtime_test` schema lines.

- [ ] **Step 5: Run to verify green**

Run: `cd $B/helpers && uv run pytest tests/test_models.py -q`
Expected: PASS. Then run the full suite: `uv run pytest -q` — expected: no new failures.

- [ ] **Step 6: Update docs and commit**

`$B/helpers/README.md`: in the `models.py` row, append (merge-sensitive, keep existing text):

```markdown
Recent: `open_questions` field added (list of dicts with `question`, `why_it_matters`, `who_to_ask_or_check` keys; defaults to []) — unrelated to `coverage_ledger.py`'s same-named, differently-shaped `open_questions` list.
```

`CHANGELOG.md` `### Added`: "Add the `open_questions` field to `Finding` and the finding schema." Update root `README.md` status line if warranted.

```bash
git add $B/helpers/sec_overlay/models.py $B/references/finding.schema.json \
        $B/helpers/tests/test_models.py $B/helpers/README.md README.md CHANGELOG.md
git commit -m "feat(sec-overlay): add open_questions to Finding"
```

---

### Task 3: phase-gate comment-line flagging

**Files:**
- Modify: `$B/helpers/sec_overlay/phase_gate.py` (new constants, `is_comment_line`, wire into `run_phase_checks`)
- Test: `$B/helpers/tests/test_phase_gate.py`
- Modify: root `README.md`, `CHANGELOG.md`, `$B/helpers/README.md`

**Interfaces:**
- Produces: `is_comment_line(root: str | Path, ref: str) -> bool | None`. `run_phase_checks` appends a gate note (not a reject) when a resolved ref lands on a comment.

- [ ] **Step 1: Write the failing tests**

Add `is_comment_line` to the existing `from sec_overlay.phase_gate import (...)` block in `$B/helpers/tests/test_phase_gate.py`, then append:

```python
def test_is_comment_line_detects_common_comment_markers(tmp_path):
    root = tmp_path
    (root / "a.go").write_text("package x\n// this is a comment\nfunc F() {}\n")
    (root / "a.py").write_text("x = 1\n# a comment\ny = 2\n")
    (root / "a.md").write_text("<!-- a comment -->\ntext\n")
    assert is_comment_line(root, "a.go:2") is True
    assert is_comment_line(root, "a.go:3") is False
    assert is_comment_line(root, "a.py:2") is True
    assert is_comment_line(root, "a.py:1") is False
    assert is_comment_line(root, "a.md:1") is True


def test_is_comment_line_none_when_ref_does_not_resolve(tmp_path):
    assert is_comment_line(tmp_path, "missing.go:1") is None
    assert is_comment_line(tmp_path, "missing.go") is None  # no line number at all


def test_run_phase_checks_notes_comment_only_citation(tmp_path):
    (tmp_path / "internal").mkdir()
    (tmp_path / "internal" / "auth.go").write_text(
        "package auth\n// this control is enforced elsewhere\nfunc Check() bool { return true }\n"
    )
    claims = [{"id": "c1", "text": "control is PRESENT", "refs": ["internal/auth.go:2"]}]
    decisions = run_phase_checks(claims, tmp_path)
    assert decisions[0].status == "to-adversary"  # still forwarded, not silently rejected
    assert any("comment" in n.lower() for n in decisions[0].notes)
```

- [ ] **Step 2: Run to verify red**

Run: `cd $B/helpers && uv run pytest tests/test_phase_gate.py -q -k "comment"`
Expected: FAIL (`ImportError: cannot import name 'is_comment_line'`).

- [ ] **Step 3: Add the constants and `is_comment_line`**

In `$B/helpers/sec_overlay/phase_gate.py`, after `_line_in_range` (before `resolve_ref`), add:

```python
_COMMENT_PREFIXES = ("//", "#", "*", "/*", "--", "<!--", ";", "%")
# In prose files `#` is a heading and `*` a bullet, so the code-comment prefixes would flag
# nearly every cited line. Only the HTML comment form is a real comment there.
# ponytail: `#`/`*` still over-flag in code (Go pointer deref, doc-comment continuation) —
# the cost is one extra adversary note, not a verdict change, so no per-language parser.
_PROSE_SUFFIXES = (".md", ".markdown", ".rst", ".txt")
_PROSE_COMMENT_PREFIXES = ("<!--",)


def is_comment_line(root: str | Path, ref: str) -> bool | None:
    """True if ``ref``'s cited line is a comment, not executing code.

    A citation resolving to a comment (e.g. ``// this control is enforced
    elsewhere``) is not evidence the control actually executes — only that
    someone wrote a claim about it. This is a cheap, language-agnostic
    heuristic (leading-symbol match after stripping whitespace); it does not
    replace the adversary's own judgment, it flags the citation for extra
    scrutiny via a gate note.

    Args:
        root: Target repo root.
        ref: A ``file:line`` reference (a bare path with no line returns
            ``None`` — there's no single line to classify).

    Returns:
        ``True``/``False`` if the ref resolves to a concrete line, ``None``
        if the ref doesn't resolve to a file or carries no line number.
    """
    path, line = _parse_ref(ref)
    if not path or line is None:
        return None
    fp = Path(root) / path
    if not fp.is_file():
        return None
    try:
        lines = fp.read_text(errors="replace").splitlines()
    except OSError:
        return None
    if not (1 <= line <= len(lines)):
        return None
    stripped = lines[line - 1].strip()
    prefixes = (_PROSE_COMMENT_PREFIXES if path.lower().endswith(_PROSE_SUFFIXES)
                else _COMMENT_PREFIXES)
    return stripped.startswith(prefixes)
```

(Confirm `_parse_ref` exists locally — it is used by `is_comment_line`. Grep: `rg -n "_parse_ref" $B/helpers/sec_overlay/phase_gate.py`.)

- [ ] **Step 4: Wire into `run_phase_checks`**

In `run_phase_checks`, the per-ref loop currently reads:

```python
            if not resolved:
                reasons.append(f"ref does not resolve: {ref!r}" + (f" ({note})" if note else ""))
                reject = True
            elif note:
                notes.append(note)
```

Replace with:

```python
            if not resolved:
                reasons.append(f"ref does not resolve: {ref!r}" + (f" ({note})" if note else ""))
                reject = True
                continue
            # Independent checks: a basename-fallback ref is exactly the sloppy citation
            # most likely to also land on a comment, so both notes can fire.
            if note:
                notes.append(note)
            if is_comment_line(target_root, ref):
                notes.append(f"cited line is a comment, not executing code: {ref!r} — "
                              "do not treat as proof a control executes")
```

(Confirm the loop variable for the repo root is `target_root`; match the local signature.)

- [ ] **Step 5: Run to verify green**

Run: `cd $B/helpers && uv run pytest tests/test_phase_gate.py -q` then `uv run pytest -q`.
Expected: PASS, no new failures.

- [ ] **Step 6: Update docs and commit**

`$B/helpers/README.md` `phase_gate.py` row: append (keep existing text):

```markdown
Detects comment-only citations via `is_comment_line()` and appends a gate note flagging them for extra scrutiny (prose files — `.md`/`.rst`/`.txt` — are skipped, since every Markdown heading would otherwise read as a comment); the comment check and the basename-fallback note are independent, so a sloppy citation can raise both.
```

`CHANGELOG.md` `### Added`: "Flag comment-only `file:line` citations in the phase gate as a scrutiny note."

```bash
git add $B/helpers/sec_overlay/phase_gate.py $B/helpers/tests/test_phase_gate.py \
        $B/helpers/README.md README.md CHANGELOG.md
git commit -m "feat(sec-overlay): flag comment-only citations in phase gate"
```

---

### Task 4: verify — placeholder-version FP fix + validate-fix conflict guard

**Files:**
- Modify: `$B/helpers/sec_overlay/verify.py` (`import re`, `_PLACEHOLDER_VERSION_RE`, `_placeholder_version_bump`, `verify_patch` short-circuit, `verify_findings` conflict guard)
- Test: `$B/helpers/tests/test_verify.py`
- Modify: root `README.md`, `CHANGELOG.md`, `$B/helpers/README.md`

**Interfaces:**
- Produces: `_placeholder_version_bump(patch_diff: str) -> bool`. `verify_patch` returns `"not-fixed"` for a placeholder deps bump. `verify_findings` appends a `verify:conflict` history event and does not promote when a `validate-fix:*` (non-`fixed`) verdict conflicts with a `verified-static` re-scan.

**Invariant:** a `CONFIRMED` finding is promoted to `FIXED` only if the deterministic re-scan says `verified-static` AND no prior `validate-fix:*` event other than `validate-fix:fixed` exists; otherwise its status/verification are left untouched and a single (idempotent) `verify:conflict` event is recorded.

- [ ] **Step 1: Write the failing tests**

Append to `$B/helpers/tests/test_verify.py` (confirm the module already imports `Workspace`, `Finding`, `FindingStatus`, `Severity`, `write_findings`, `read_findings`, `verify_findings`, `verify_patch`; the upstream test relies on all of them):

```python
def test_deps_finding_with_placeholder_version_stays_not_fixed(tmp_path):
    # A patch_diff that bumps go.mod to a literal placeholder (not a real version)
    # must never be credited as fixed, even if the OSV/SCA re-scan no longer flags
    # the old (now-missing) version string.
    (tmp_path / "go.mod").write_text(
        "module x\n\nrequire golang.org/x/crypto v0.51.0\n"
    )
    patch = (
        "--- a/go.mod\n+++ b/go.mod\n@@ -1,3 +1,3 @@\n"
        " module x\n \n-require golang.org/x/crypto v0.51.0\n"
        "+require golang.org/x/crypto vX.Y.Z\n"
    )
    result = verify_patch(str(tmp_path), patch, "rules/smoke.yaml", "go.mod", "deps",
                           evidence_sources=["sca:osv:GHSA-5cgq-3rg8-m6cv"])
    assert result == "not-fixed"


def test_deps_finding_with_real_version_bump_can_verify(tmp_path, monkeypatch):
    # A real semver bump is allowed to proceed to the normal SCA re-scan check
    # (this test stubs the re-scan to report the old signal is gone, since we're
    # only testing that a REAL version string doesn't get short-circuited to
    # not-fixed the way a placeholder does).
    (tmp_path / "go.mod").write_text(
        "module x\n\nrequire golang.org/x/crypto v0.51.0\n"
    )
    patch = (
        "--- a/go.mod\n+++ b/go.mod\n@@ -1,3 +1,3 @@\n"
        " module x\n \n-require golang.org/x/crypto v0.51.0\n"
        "+require golang.org/x/crypto v0.52.0\n"
    )

    state = {"pre": True}

    def fake_hit(target, config, basename, cls, rules, **kw):
        # first call = pre-patch (signal present), second = post-patch (gone)
        was_pre = state["pre"]
        state["pre"] = False
        return was_pre

    monkeypatch.setattr("sec_overlay.verify._file_has_hit", fake_hit)
    result = verify_patch(str(tmp_path), patch, "rules/smoke.yaml", "go.mod", "deps",
                           evidence_sources=["sca:osv:GHSA-5cgq-3rg8-m6cv"])
    assert result == "verified-static"


def test_verify_findings_does_not_override_validate_fix_not_fixed_verdict(tmp_path):
    ws = Workspace(tmp_path)
    ws.ensure()
    f = Finding(
        id="F-0001", rule_id="r", cls="deps", status=FindingStatus.CONFIRMED,
        severity=Severity.CRITICAL, file="go.mod", line=1, message="m",
        patch_diff="--- a/go.mod\n+++ b/go.mod\n@@ -1 +1 @@\n-x\n+y\n",
        evidence_sources=["sca:osv:GHSA-test"],
        history=[{"event": "validate-fix:not_fixed", "reason": "placeholder version"}],
    )
    write_findings(ws, [f])

    def always_verified(*a, **kw):
        return "verified-static"

    fixed_count = verify_findings(ws, str(tmp_path), "rules/smoke.yaml", verifier=always_verified)
    assert fixed_count == 0
    reloaded = read_findings(ws)[0]
    assert reloaded.status is FindingStatus.CONFIRMED  # NOT promoted to fixed
    assert any(h.get("event") == "verify:conflict" for h in reloaded.history)
```

If any of the referenced imports are absent from the local test module, add them to the existing import lines (match the local module paths, e.g. `from sec_overlay.workspace import Workspace`).

- [ ] **Step 2: Run to verify red**

Run: `cd $B/helpers && uv run pytest tests/test_verify.py -q -k "placeholder or override_validate_fix"`
Expected: FAIL (placeholder bump currently proceeds; `verify_findings` currently promotes).

- [ ] **Step 3: Add `import re` and the placeholder helper**

In `$B/helpers/sec_overlay/verify.py`, add `import re` to the stdlib import group (after `import os`). After `_check` (before `verify_patch`), add:

```python
# Case-sensitive on purpose: the placeholder convention is uppercase ``X.Y.Z``. Matching
# case-insensitively flags real lowercase strings (e.g. a module path containing ``x.y.z``).
_PLACEHOLDER_VERSION_RE = re.compile(r"\bv?[XYZ]\.[XYZ]\.[XYZ]\b")


def _placeholder_version_bump(patch_diff: str) -> bool:
    """True if an added diff line contains an obviously non-functional version
    placeholder (e.g. ``vX.Y.Z``) instead of a real version number.

    A patch that bumps a dependency to a literal template string will never
    build; crediting it as "fixed" because the old vulnerable version string
    is no longer text-matched by the SCA re-scan is a false clean. This is a
    narrow, deliberately conservative heuristic — it only catches the
    X/Y/Z-placeholder shape, not every possible non-functional diff.

    Args:
        patch_diff: The unified diff text.

    Returns:
        True if any added line (``+`` prefix, not ``+++``) matches the
        placeholder-version pattern.
    """
    for line in patch_diff.splitlines():
        if (
            line.startswith("+")
            and not line.startswith("+++")
            and _PLACEHOLDER_VERSION_RE.search(line)
        ):
            return True
    return False
```

- [ ] **Step 4: Short-circuit `verify_patch`**

At the very top of `verify_patch`'s body (before `basename = os.path.basename(file)`), add:

```python
    # Cheap string check first: a placeholder-version deps bump can never be a real fix, so
    # short-circuit before the pre-scan, the repo copy, and the patch apply.
    if cls == "deps" and _placeholder_version_bump(patch_diff):
        return "not-fixed"
```

- [ ] **Step 5: Add the `verify_findings` conflict guard**

In `verify_findings`, inside the `for f in findings:` loop, after the `if f.status is not FindingStatus.CONFIRMED or not f.patch_diff: continue` guard and before the `result = verifier(...)` call, add:

```python
        last_validate_fix = next(
            (h for h in reversed(f.history) if str(h.get("event", "")).startswith("validate-fix:")),
            None,
        )
        # Deliberately broad: ANY validate-fix verdict other than ``validate-fix:fixed``
        # blocks promotion — including ``validate-fix:unverifiable``. An unverifiable fix is
        # a verify-error, and a verify-error must never be laundered into a clean verdict.
        validate_fix_said_not_fixed = (
            last_validate_fix is not None
            and last_validate_fix.get("event") != "validate-fix:fixed"
        )
```

Then, immediately after the `result = verifier(...)` assignment and before `f.verification = result`, add:

```python
        if result == "verified-static" and validate_fix_said_not_fixed:
            # Idempotent: re-running verify on the same finding must not pile up duplicates.
            if f.history and f.history[-1].get("event") == "verify:conflict":
                continue
            f.history.append({
                "event": "verify:conflict",
                "reason": ("deterministic re-scan found the signal gone, but validate-fix "
                           f"explicitly said {last_validate_fix.get('event')!r} — leaving "
                           "status/verification as validate-fix left them for human review"),
            })
            changed = True
            continue
```

(Confirm the local `verify_findings` uses a `changed` flag and a `verifier` parameter — match the local names. Grep: `rg -n "def verify_findings" $B/helpers/sec_overlay/verify.py`.)

- [ ] **Step 6: Run to verify green**

Run: `cd $B/helpers && uv run pytest tests/test_verify.py -q` then `uv run pytest -q`.
Expected: PASS, no new failures.

- [ ] **Step 7: Update docs and commit**

`$B/helpers/README.md` `verify.py` row: replace with the merged description (keep any local `render_util`-unrelated text; this row is about verify, not render_util):

```markdown
| `verify.py` | Apply a `patch_diff` to a **temp copy**, re-scan, confirm the finding is gone. Never touches the real target. A `deps`-class patch that only bumps to an obviously non-functional placeholder version (e.g. `vX.Y.Z`) is rejected as `not-fixed` before the re-scan even runs (`_placeholder_version_bump`) — an SCA re-scan can't tell "real fix" from "text that no longer matches the old version string." `verify_findings` also never silently overwrites an explicit `validate-fix:not_fixed`-family verdict on a `CONFIRMED` finding: if the deterministic re-scan disagrees (says `verified-static`), it appends a `verify:conflict` history event (once — a re-run does not duplicate it) and leaves status/verification untouched for human review, instead of promoting to `FIXED`. The guard is deliberately broad: **any** `validate-fix:*` event other than `validate-fix:fixed` blocks promotion, `validate-fix:unverifiable` included — a verify-error is never laundered into a clean verdict. CLI-callable. |
```

`CHANGELOG.md` `### Fixed`: "Reject placeholder-version deps bumps and stop `verify_findings` from overriding a `validate-fix` not-fixed verdict."

```bash
git add $B/helpers/sec_overlay/verify.py $B/helpers/tests/test_verify.py \
        $B/helpers/README.md README.md CHANGELOG.md
git commit -m "fix(sec-overlay): guard placeholder bumps and validate-fix conflicts"
```

---

### Task 5: context — deployment_config kind + diagram slot

**Files:**
- Modify: `$B/helpers/sec_overlay/context.py` (`KINDS`, `_DEPLOYMENT_CONFIG_GLOBS`, `ContextItem.deployed_in`, `Context.diagram`, `to_dict`/`from_dict`, `discover_context_files`, `render_markdown`)
- Test: `$B/helpers/tests/test_context.py`
- Modify: root `README.md`, `CHANGELOG.md`, `$B/helpers/README.md`

**Interfaces:**
- Produces: `"deployment_config"` kind; `ContextItem.deployed_in: str`; `Context.diagram: str`. `render_markdown` emits a "## Claimed-control status diagram" section when `diagram` is set, and a "Deployment config" section for that kind.

**Invariant:** `to_dict`/`from_dict` round-trip `diagram` and `deployed_in`; `render_markdown` omits the diagram section entirely when `diagram == ""`.

- [ ] **Step 1: Write the failing tests**

Append to `$B/helpers/tests/test_context.py` (confirm it already imports `Context`, `ContextItem`, `discover_context_files`, `render_markdown`, `save`, `load`, `Workspace`, and a local `_ctx()` helper — the upstream test uses all of them):

```python
def test_discover_finds_iac_deployment_files(tmp_path):
    (tmp_path / "Pulumi.prd.yaml").write_text("config: {}\n")
    (tmp_path / "terraform.tfvars").write_text("x = 1\n")
    (tmp_path / "helm").mkdir()
    (tmp_path / "helm" / "values-prod.yaml").write_text("x: 1\n")
    (tmp_path / "k8s").mkdir()
    (tmp_path / "k8s" / "deployment.yaml").write_text("x: 1\n")
    (tmp_path / "docker-compose.prod.yaml").write_text("x: 1\n")
    (tmp_path / "serverless.yml").write_text("x: 1\n")
    found = discover_context_files(tmp_path)
    assert "Pulumi.prd.yaml" in found
    assert "terraform.tfvars" in found
    assert "helm/values-prod.yaml" in found
    assert "k8s/deployment.yaml" in found
    assert "docker-compose.prod.yaml" in found
    assert "serverless.yml" in found


def test_deployment_config_kind_is_valid_and_has_deployed_in_field():
    item = ContextItem(kind="deployment_config", text="GITHUB_ENABLED=false in prd",
                        where="Pulumi.prd.yaml:150", deployed_in="prd")
    assert item.validate() == []
    assert item.deployed_in == "prd"


_DIAGRAM = "```mermaid\nflowchart LR\n  A[public ingress] --> B[authz: PRESENT]\n```"


def test_render_markdown_includes_diagram_when_set():
    c = _ctx()
    c.diagram = _DIAGRAM
    md = render_markdown(c)
    assert "## Claimed-control status diagram" in md
    assert "flowchart LR" in md


def test_render_markdown_omits_diagram_section_when_empty():
    md = render_markdown(_ctx())
    assert "Claimed-control status diagram" not in md
    assert "mermaid" not in md


def test_save_load_round_trips_diagram(tmp_path):
    ws = Workspace(tmp_path); ws.ensure()
    c = _ctx(); c.diagram = _DIAGRAM
    save(ws, c)
    assert load(ws).diagram == _DIAGRAM
    assert "## Claimed-control status diagram" in (ws.kb / "CONTEXT.md").read_text()


def test_render_markdown_includes_deployment_config_section():
    c = Context(items=[
        ContextItem(kind="deployment_config", text="GITHUB_ENABLED=false in prd",
                    where="Pulumi.prd.yaml:150", deployed_in="prd"),
    ])
    md = render_markdown(c)
    assert "Deployment config" in md
    assert "GITHUB_ENABLED=false in prd" in md
```

Note: `test_render_markdown_omits_diagram_section_when_empty` asserts the string `mermaid` never appears in a diagram-less `CONTEXT.md`. Confirm `_ctx()` produces no content containing "mermaid"; if the local `_ctx()` differs, this assertion still holds because the diagram section is the only mermaid source.

- [ ] **Step 2: Run to verify red**

Run: `cd $B/helpers && uv run pytest tests/test_context.py -q -k "iac or deployment_config or diagram"`
Expected: FAIL (kind rejected by `validate`; `deployed_in`/`diagram` not fields; no diagram section).

- [ ] **Step 3: Edit `context.py` — KINDS + globs**

Change the `KINDS` tuple to insert `"deployment_config"` before `"note"`:

```python
KINDS = ("trust_boundary", "claimed_control", "prior_finding", "attack_lead",
         "source_pointer", "deployment_config", "note")
```

After the `_CONTEXT_GLOBS` tuple (before `_DIAGRAM_TEXT_GLOBS`), add:

```python
_DEPLOYMENT_CONFIG_GLOBS = (
    "Pulumi.*.yaml", "Pulumi.*.yml", "*.tfvars", "terraform.tfvars",
    "helm/**/values*.yaml", "helm/**/values*.yml",
    "k8s/**/*.yaml", "k8s/**/*.yml",
    "docker-compose*.yaml", "docker-compose*.yml", "serverless.yml", "serverless.yaml",
)
```

- [ ] **Step 4: Edit `context.py` — dataclass fields**

In `ContextItem`, after `verify_status: str = ""`, add:

```python
    deployed_in: str = ""  # which environment(s) this control/claim is actually active in
```

In `Context`, after `provenance: dict = field(default_factory=dict)  # ...`, add:

```python
    # Raw mermaid block (```mermaid ... ```) the C1 agent builds — the claimed-control
    # status map. Rendered into CONTEXT.md by render_markdown; "" = no diagram.
    diagram: str = ""
```

- [ ] **Step 5: Edit `context.py` — to_dict/from_dict**

Change `Context.to_dict` to include `diagram`:

```python
    def to_dict(self) -> dict:
        return {"items": [asdict(i) for i in self.items], "provenance": self.provenance,
                "diagram": self.diagram}
```

Change `Context.from_dict` return to include `diagram`:

```python
        return cls(items=items, provenance=d.get("provenance", {}), diagram=d.get("diagram", ""))
```

(`ContextItem.from_dict` filtering already whitelists dataclass fields, so `deployed_in` round-trips without further change — confirm the local `from_dict` uses the `__dataclass_fields__` filter shown upstream.)

- [ ] **Step 6: Edit `context.py` — discover + render**

In `discover_context_files`, change the `globs` assembly to include the new globs:

```python
    globs = _CONTEXT_GLOBS + _DEPLOYMENT_CONFIG_GLOBS + _DIAGRAM_TEXT_GLOBS + _DIAGRAM_IMAGE_GLOBS
```

In `render_markdown`, after the intro `lines += [...]` block and before the kind/title loop, add:

```python
    if ctx.diagram:
        lines += ["## Claimed-control status diagram", "", ctx.diagram.strip(), ""]
```

In the kind/title loop tuple, add the `deployment_config` row before `("note", "Notes")`:

```python
                        ("source_pointer", "Source pointers"),
                        ("deployment_config", "Deployment config"),
                        ("note", "Notes")):
```

- [ ] **Step 7: Run to verify green**

Run: `cd $B/helpers && uv run pytest tests/test_context.py -q` then `uv run pytest -q`.
Expected: PASS, no new failures.

- [ ] **Step 8: Update docs and commit**

`$B/helpers/README.md` `context.py` row: append (keep existing text):

```markdown
Also discovers IaC/deployment-config files (Pulumi, Terraform, Helm, k8s, docker-compose, serverless) as `deployment_config` items, carrying a `deployed_in` env tag. `Context.diagram` holds the C1 agent's claimed-control status map (a raw mermaid block); `render_markdown` writes it into `CONTEXT.md`, which is regenerated on every `save()` and never hand-edited.
```

`CHANGELOG.md` `### Added`: "Add the `deployment_config` context kind, `deployed_in` tag, and `Context.diagram` slot rendered into `CONTEXT.md`."

```bash
git add $B/helpers/sec_overlay/context.py $B/helpers/tests/test_context.py \
        $B/helpers/README.md README.md CHANGELOG.md
git commit -m "feat(sec-overlay): add deployment_config kind and context diagram"
```

---

### Task 6: redteam questions, prompt wiring, doc sync

**Files:**
- Modify: `$B/helpers/sec_overlay/redteam.py` (`_question_block`, "Questions to ask" section — merge-sensitive)
- Test: `$B/helpers/tests/test_redteam.py`
- Modify (prompts): `$B/agents/architecture.md`, `threat-model.md`, `context-ingest.md`, `recon.md`, `redteam.md` (merge-sensitive), `trace.md`, `patch.md`, `critic.md`, `investigate.md`, `validate.md`, `validate-fix.md`, `context-adversary.md`, `phase-adversary.md`
- Modify (docs): `$B/CLAUDE.md`, `$B/SKILL.md` (merge-sensitive), `$B/agents/README.md` (merge-sensitive)
- Modify: root `README.md`, `CHANGELOG.md`, `$B/agents/README.md`, `$B/helpers/README.md`

**Interfaces:**
- Consumes: `Finding.open_questions` (Task 2), the three prompt blocks (Task 1), `Context.diagram` (Task 5).
- Produces: `_question_block(f: Finding) -> str`; `render_plan` emits a "## Questions to ask" section (`_none_` when no finding carries questions).

**Invariant:** the "Questions to ask" section pulls `open_questions` from all discriminated buckets (`plan + below + settled`), not just needs-runtime.

- [ ] **Step 1: Write the failing tests**

Append to `$B/helpers/tests/test_redteam.py` (confirm it imports `discriminate`, `render_plan`, `Finding`, `FindingStatus`, `Severity`):

```python
def test_render_plan_includes_questions_to_ask_section():
    f_with_question = Finding(
        id="AUTHZ-0001", rule_id="r", cls="authz", status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH, file="a.go", line=1, message="m",
        risk_score=8,
        open_questions=[{
            "question": "Is there an Azure AD group-membership check enforced "
                         "anywhere outside this repo?",
            "why_it_matters": "This finding assumes no such check exists anywhere.",
            "who_to_ask_or_check": "identity/security-platform team",
        }],
    )
    disc = discriminate([f_with_question])
    md = render_plan(disc)
    assert "## Questions to ask" in md
    assert "Is there an Azure AD group-membership check" in md
    assert "identity/security-platform team" in md


def test_render_plan_questions_section_says_none_when_empty():
    f_no_question = Finding(
        id="F-0001", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
        severity=Severity.HIGH, file="a.py", line=1, message="m", risk_score=8,
    )
    disc = discriminate([f_no_question])
    md = render_plan(disc)
    assert "## Questions to ask" in md
    assert "_none_" in md
```

- [ ] **Step 2: Run to verify red**

Run: `cd $B/helpers && uv run pytest tests/test_redteam.py -q -k "questions"`
Expected: FAIL (no "Questions to ask" section).

- [ ] **Step 3: Add `_question_block` and the section to `redteam.py` (merge-sensitive)**

After `_directive_block` (before `render_plan`), add:

```python
def _question_block(f: Finding) -> str:
    """Render one finding's ``open_questions`` as a Markdown bullet list.

    Args:
        f: The finding with open_questions to render.

    Returns:
        Newline-joined markdown lines with question details (id, class, question text,
        why_it_matters, and who_to_ask_or_check).
    """
    lines = []
    for q in f.open_questions:
        lines.append(f"- **{f.id}** ({f.cls}): {q.get('question', '')}")
        if q.get("why_it_matters"):
            lines.append(f"  - Why it matters: {q['why_it_matters']}")
        if q.get("who_to_ask_or_check"):
            lines.append(f"  - Ask/check: {q['who_to_ask_or_check']}")
    return "\n".join(lines)
```

In `render_plan`, immediately before the final `return "\n".join(out) + "\n"`, add (do not disturb the local `signal_lines`-based directive rendering above it):

```python
    all_findings = plan + below + settled
    questions = [f for f in all_findings if f.open_questions]
    out += ["", "## Questions to ask", "",
            ("_Unknowns a live-exploit test can't settle — org policy, external config, "
             "an affected-version range. Answer these by asking the named person/team or "
             "checking the named system, not by testing the running application._"), ""]
    if questions:
        for f in questions:
            out.append(_question_block(f))
            out.append("")
    else:
        out.append("_none_")
```

(Confirm the local `render_plan` uses the bucket variable names `plan`, `below`, `settled`. Grep: `rg -n "settled|below|plan =" $B/helpers/sec_overlay/redteam.py`. If the local names differ, match them.)

- [ ] **Step 4: Run to verify green**

Run: `cd $B/helpers && uv run pytest tests/test_redteam.py -q` then `uv run pytest -q`.
Expected: PASS, no new failures.

- [ ] **Step 5: Apply the agent-prompt import additions**

These are single-line `## Imports` edits — add the named block(s) to each prompt's import line. Use the local import-path token confirmed in Task 1 Step 1.

- `$B/agents/patch.md`: add `FIELD_OWNERSHIP` → `Include the TOOL_TRUST + OUTPUT_WRITE_FALLBACK + FIELD_OWNERSHIP blocks from ...`.
- `$B/agents/critic.md`: `EXHAUSTIVENESS, TOOL_TRUST, and FIELD_OWNERSHIP blocks from ...`.
- `$B/agents/investigate.md`: `... TOOL_TRUST, OUTPUT_WRITE_FALLBACK, and FIELD_OWNERSHIP blocks from ...`.
- `$B/agents/validate.md`: `EXHAUSTIVENESS, TOOL_TRUST, and FIELD_OWNERSHIP blocks from ...`.
- `$B/agents/validate-fix.md`: `... SEVERITY_GUIDANCE, EXHAUSTIVENESS, and FIELD_OWNERSHIP blocks from ...`.
- `$B/agents/context-adversary.md`: `Include ANTI_MANIPULATION, EXCLUSION_RULES, TOOL_TRUST, and FIELD_OWNERSHIP from ...`.
- `$B/agents/phase-adversary.md`: `Include ANTI_MANIPULATION, EXCLUSION_RULES, TOOL_TRUST, and FIELD_OWNERSHIP from ...`.
- `$B/agents/recon.md`: add a new `## Imports` section (place after the `## Inputs` section):
  ```markdown
  ## Imports
  Include QUALIFIER_PROOF from `{{HARNESS_ROOT}}/references/prompt-constants.md`.
  ```
- `$B/agents/trace.md`: `Include ANTI_MANIPULATION, EXHAUSTIVENESS, TOOL_TRUST, FIELD_OWNERSHIP from ...`.
- `$B/agents/redteam.md` (merge-sensitive): `Include ANTI_MANIPULATION, SEVERITY_GUIDANCE, TOOL_TRUST, OUTPUT_WRITE_FALLBACK, and FIELD_OWNERSHIP from ...`. Keep the local envelope/`render_util`-related lines.
- `$B/agents/threat-model.md`: add a new `## Imports` section after the title/intro:
  ```markdown
  ## Imports
  Include DIAGRAM_STYLE and FIELD_OWNERSHIP from `{{HARNESS_ROOT}}/references/prompt-constants.md`.
  ```
- `$B/agents/architecture.md`: add a new `## Imports` section after `## Inputs`:
  ```markdown
  ## Imports
  Include DIAGRAM_STYLE, FIELD_OWNERSHIP, and QUALIFIER_PROOF from `{{HARNESS_ROOT}}/references/prompt-constants.md`.
  ```
- `$B/agents/context-ingest.md`: change the existing `## Imports` line to:
  ```markdown
  Include ANTI_MANIPULATION + TOOL_TRUST + OUTPUT_WRITE_FALLBACK + QUALIFIER_PROOF +
  DIAGRAM_STYLE + FIELD_OWNERSHIP from `{{HARNESS_ROOT}}/references/prompt-constants.md`.
  ```

- [ ] **Step 6: Apply the substantive prompt-body edits**

`$B/agents/architecture.md` — add the canonical-source lens paragraph and the 3-diagram sequence. After the `## Output (REQUIRED)` heading, insert:

```markdown

**Lens for this document: the single canonical source of structural truth (components,
data flows, trust boundaries). Every other KB doc references this one instead of
restating its content — if you find yourself writing something that reads like
`CONTEXT.md`'s doc-claims-vs-reality language or `THREAT_MODEL.md`'s attacker-profile
language, that content belongs in this document only as the underlying fact those other
docs point back to, not duplicated prose.**
```

In the `kb/architecture.md` output bullet list, after the `**External dependencies**` bullet, add:

```markdown
   - **Diagrams** (mermaid, follow DIAGRAM_STYLE — 10-entity cap, one job each):
     1. **Component overview** — subsystems as nodes, calls as edges.
     2. **DFD** — data flow from each entrypoint (from the profile) to its sinks. If the
        profile has more entrypoints than fit the cap, group by subsystem and produce one
        DFD per subsystem instead of one giant diagram.
     3. **Trust-boundary diagram** — subgraphs = boundaries. This is the CANONICAL version;
        `THREAT_MODEL.md` references it and must not redraw its own copy.
     Place all diagrams in `architecture.md` itself (not in `kb/entities/`), near the
     section they illustrate.
```

`$B/agents/threat-model.md` — replace the `**Trust boundaries** (from architecture, restated crisply)` bullet with:

```markdown
- **Trust boundaries** — do NOT restate architecture.md's boundary list. Write one
  sentence per boundary that's ATTACKER-RELEVANT and not already obvious from
  architecture.md (e.g. "boundary X is where profile Y's access ends") — a pointer,
  not a copy: "See `architecture.md`'s trust-boundary diagram for the full structural
  picture."
```

After the `**Prioritized hunt list**` bullet (before `**Provenance**`), add:

```markdown
- **Diagrams** (mermaid, follow DIAGRAM_STYLE — 10-entity cap, one job each):
  1. **Attacker-profile → entrypoint reachability** — one node per attacker profile,
     one per entrypoint it reaches, edges show reachability. This is the attacker
     lens; it is NOT a repeat of architecture.md's DFD (that shows data flow for
     defenders reading code, this shows reachability for defenders prioritizing hunts).
  2. **Threat diagram for the top hunt-list item(s)** — a traditional STRIDE-style
     diagram (or attack-tree) for whichever hunt-list row is ranked #1 (and #2 if the
     the two are unrelated attack shapes). A genuinely different diagram TYPE from
     the DFD, not the same shape relabeled.
  Both diagrams go in `THREAT_MODEL.md` itself, near the sections they illustrate.
```

`$B/agents/context-ingest.md` — apply the four body edits: (a) add the `deployment_config` item-kind bullet, (b) add the `## Cross-check claims against deployment config (new)` section, (c) add the `## Output` lens paragraph, (d) rewrite the output paragraph to mention `deployed_in` + the diagram. Use these verbatim insertions (matching the upstream diff hunks captured for this file):

Add after the `source_pointer` item-kind bullet:
```markdown
- `deployment_config` — an IaC/deployment file (Pulumi/Terraform/Helm/k8s/docker-compose/
  serverless) states a feature flag, env var, or config value that gates whether a
  claimed_control or attack surface is actually active in a given environment. Set
  `deployed_in` on the CORRESPONDING `claimed_control` item to name which environment(s)
  it's live in (e.g. `"dev,stg"` if a flag is true there and false in prd) — do not
  guess this from code alone if a deployment_config file states it explicitly.
```

Add after the C1-rework verification section (before `## Output`):
```markdown
## Cross-check claims against deployment config (new)
Before finalizing `verify_status`/`deployed_in` on any `claimed_control`, check
whether any discovered `deployment_config` file (Pulumi/Terraform/Helm/k8s/
docker-compose/serverless) states a flag or env var gating that control's
subsystem. A control can be `PRESENT` in code and still be dark in a specific
environment (or vice versa) — a doc-vs-reality mismatch missed here has
twice cost a full adversary-review round-trip to catch. Record the finding
in the `claimed_control`'s `deployed_in` field, not just in prose.
```

Under `## Output`, add the lens paragraph, then update the write instructions and add the diagram paragraph:
```markdown
**Lens for this document: what the repo claims about itself, and whether that claim
holds — not structural/architectural facts (those belong to `architecture.md`, which this
document must not restate).** `trust_boundary` items are the one place structure meets
trust, so they appear here — but only as the anchor a claim hangs on: CONTEXT.md records
whether a claimed control AT that boundary holds up, never what the boundary IS
structurally (components, data flow, call paths — `architecture.md`'s job).
```
Change the "Write `kb/context.json` via the schema ... with `verify_status` set on claimed_controls" sentence to read "with `verify_status` and `deployed_in` set on claimed_controls", drop the old trailing "Return a 3-5 line summary..." sentence per the upstream diff, and add:
```markdown
**Diagram (one):** a claimed-control status map — one small diagram (follow
DIAGRAM_STYLE's 10-entity cap) showing each `claimed_control`'s `verify_status`
(PRESENT/MISSING/BYPASSABLE) grouped by the `trust_boundary` it relates to. This is a
compliance-style view (claim vs. reality), not a structural diagram — do not draw
components or data flow here. Build it as a mermaid string (fenced ```` ```mermaid ````
block) and set it on the `Context` object's `diagram` field BEFORE calling `save()`;
`render_markdown` writes it into `CONTEXT.md` automatically. Never hand-edit `CONTEXT.md`
— it is regenerated from `context.json` on every `save()`.
```

`$B/agents/trace.md` — in the `## Procedure — per confirmed finding` list, after the reachability-blocker bullet, add the external-fact `open_questions` bullet:
```markdown
   - **not reachable, but the reason is an external fact (not a code control)**: if
     the only thing standing between "reachable" and "not reachable" is something
     this repo cannot answer (an org policy, a runtime config value, a version range
     you can't confirm from source) — do NOT mark it `not reachable` with a guessed
     blocker, and do NOT leave it silently `unassessed`. Instead leave `reachable`
     unset/absent and add ONE entry to the finding's `open_questions` list:
     `{"question": ..., "why_it_matters": ..., "who_to_ask_or_check": ...}`. The
     question must name a specific person/team/system to check, not be vague
     ("verify this is safe" is not acceptable; "ask the identity team whether
     Conditional Access enforces group X" is).
```

`$B/agents/redteam.md` (merge-sensitive) — in the `## Procedure` list, after the `needs-runtime` bullet, add the neither-static-nor-live bullet:
```markdown
   - **neither static-settled nor a live-exploit test** — some findings hinge on a
     fact only a human can supply (an affected-version range for a dependency CVE,
     whether a documented backstop is actually deployed, an org policy question).
     For these, do NOT force a `runtime_test` payload that doesn't really test
     anything (e.g. a curl command that always "passes"). Instead add an entry to
     the finding's `open_questions` list per the same quality bar as trace.md's:
     name a specific person/team/system, not a vague "verify this." A finding may
     carry both a `runtime_test` and `open_questions` if it genuinely needs both.
```

`$B/agents/context-adversary.md` — add a `5. **Diagram consistency.**` item to the `## Procedure — attack the verification` list:
```markdown
5. **Diagram consistency.** If `CONTEXT.md`'s claimed-control diagram (added per the
   doc's new lens) shows a `verify_status` that contradicts the prose you're already
   reviewing for that same control, flag it as a correction on that claim — same
   WEAKENED/INVALIDATED verdict mechanism as any other claim, not a new check type.
```

`$B/agents/phase-adversary.md` — add a `4. **Diagram consistency.**` item to the `## Procedure — challenge each ...` list:
```markdown
4. **Diagram consistency.** If the phase's output includes a mermaid diagram (per
   `architecture.md`'s or `threat-model.md`'s new diagram requirements) and it shows
   something that contradicts a claim you're already re-deriving from code, flag it
   with the same WEAKENED/INVALIDATED verdict you'd give a contradicting prose claim
   — no new verdict type, no separate diagram-specific check.
```

- [ ] **Step 7: Apply the doc-sync edits**

`$B/CLAUDE.md` — in the workspace-artifacts block, change the `kb/THREAT_MODEL.md` line to:
```
kb/THREAT_MODEL.md       attacker profiles, prioritized hunt list (references architecture.md)
```

`$B/SKILL.md` (merge-sensitive) — in the Phase 0–1 threat-model bullet, change "writes `kb/THREAT_MODEL.md` (trust boundaries, attacker profiles, prioritized hunt list)." to "writes `kb/THREAT_MODEL.md` (attacker profiles, prioritized hunt list)."

`$B/agents/README.md` (merge-sensitive) — apply the upstream table edits: the C1 `context-ingest.md`/`context-adversary.md` rows (doc-claims-vs-reality lens, IaC + `deployed_in`, `Context.diagram`, diagram-consistency check), the Phase-2 `architecture.md`/`threat-model.md`/`phase-adversary.md` rows (canonical structural source + 3-diagram sequence; attacker-lens diagrams + referenced boundaries; diagram-consistency), the Phase-5.5 `trace.md`/`redteam.md` rows (populate `open_questions`), and add the FIELD_OWNERSHIP paragraph after the "Every agent wraps untrusted repo text..." line:
```markdown
The agents most prone to cross-phase field writes import `FIELD_OWNERSHIP` to enforce
phase field-ownership boundaries: `investigate.md`, `critic.md`, `validate.md`, `trace.md`,
`patch.md`, `validate-fix.md`, `redteam.md`, `context-ingest.md`, `context-adversary.md`,
`phase-adversary.md`, plus `architecture.md` / `threat-model.md` (which write no Finding
fields, but consume the same ownership table when citing findings). Agents that never touch
a finding record (`judge.md`, `recon.md`, `tune-config.md`, the `classes/` extensions) do not.
```

`$B/helpers/README.md` — apply the upstream `redteam.py` row edit (add `_question_block()` / "Questions to ask" note; keep the local `render_util`/`signal_lines` text):
```markdown
| `redteam.py` | Render `redteam-plan.md` from findings marked `needs-runtime`, filtered by risk bar; includes markdown renderers `_bullets()` and `_signal()` for runtime directives (both accept list/dict *or* plain-string `runtime_test` values), and `_question_block()` to render `open_questions` from all statuses into a "Questions to ask" section. The "static-settled" footer counts `disc["static_settled"]` (not the needs-runtime code-settled subset). CLI-callable. |
```
(If the local `helpers/README.md` `redteam.py` row already carries local `render_util` wording, merge the `_question_block()` clause into it rather than overwriting.)

- [ ] **Step 8: Full suite + plugin validation**

Run: `cd $B/helpers && uv run pytest -q`
Expected: PASS (all five new modules green; local `render_util`/`expected_signal` tests still green).
Run: `cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools && claude plugin validate plugins/sec-overlay`
Expected: validation passes.

- [ ] **Step 9: Update docs and commit**

`CHANGELOG.md` `### Added`: "Render a Questions-to-ask section in the red-team plan and wire the diagram/field-ownership/qualifier guidance and deployment-config lens into the agent prompts." Update root `README.md` status/next-steps.

```bash
git add $B/helpers/sec_overlay/redteam.py $B/helpers/tests/test_redteam.py \
        $B/agents/ $B/CLAUDE.md $B/SKILL.md $B/helpers/README.md \
        README.md CHANGELOG.md
git commit -m "feat(sec-overlay): add redteam questions and diagram prompts"
```

---

## Post-implementation

- [ ] Run the full `helpers/` suite one final time; confirm green.
- [ ] Run `claude plugin validate plugins/sec-overlay`; confirm pass.
- [ ] Ask the user before merging `feat/kb-doc-diagram-redesign` into `main`; delete the branch after merge.

## Self-review notes (author-verified against the spec)

- Spec coverage: Commit 1 → Task 1; Commit 2 → Task 2; Commit 3 → Task 3; Commit 4 → Task 4 (includes the `verify_findings` conflict guard the spec's Commit 4 names); Commit 5 → Task 5; Commit 6 → Task 6. All seven merge-sensitive files are flagged at their point of edit.
- Placeholder scan: every code step carries verbatim, name-normalized code; no "TBD"/"handle edge cases"/"similar to Task N".
- Type consistency: `open_questions: list[dict]` (Task 2) is the same field consumed by `_question_block` (Task 6) and referenced in `trace.md`/`redteam.md` (Task 6); `Context.diagram: str` (Task 5) matches the `render_markdown` section and the `context-ingest.md` prompt (Task 6); `_placeholder_version_bump`/`verify:conflict` (Task 4) names match the test assertions.
- Open verification points flagged for the executor (grep-confirm before editing, since the local fork's prose diverged): the import-path token in prompt-constants; presence of `_parse_ref`, `target_root`, `changed`, `verifier`, and the `plan`/`below`/`settled` bucket names in the local helpers; and the exact local text of each merge-sensitive README row.
