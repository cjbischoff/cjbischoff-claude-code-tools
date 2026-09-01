# sec-overlay Verification-and-Scoring Group Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the verify verdict say why it reached its answer, make it independent of one caller-supplied scalar, widen the trace to the findings and channels it misses, let evidence strength move the score, correct the patch-applied test order, and stop a load-and-save round trip from dropping unknown finding keys.

**Architecture:** Six requirements, each a red/green commit pair. Four change
deterministic Python in `helpers/sec_overlay/`. One changes a prompt file only
(`agents/trace.md`), and folds REQ-19 into the same commit because both edit the
same two sentences. Three requirements deliberately reverse a contract an
existing test pins; each of those three names the exact rewrite so an
implementer does not mistake it for loosening a gate.

**Tech Stack:** Python 3.12, stdlib only. pytest, ruff, ty as dev tools.

**Spec:** `docs/superpowers/specs/2026-08-23-sec-overlay-improvements-design.md`
(group 3 is its lines 144-155)

**Requirements document (the binding authority):**
`/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md`

## Global Constraints

- Branch is `feat/sec-overlay-improvements`. Never commit to `main`. Do not create a branch.
- Two commits per requirement: a RED commit whose test fails, then a GREEN commit that passes it. Both subjects name the requirement id in the body, never in the subject.
- Commit subject form: `<type>(sec-overlay): <imperative summary under 50 characters>`, all lowercase after the colon. The commit-msg hook rejects a subject that starts with an uppercase letter or `REQ`.
- Bump `plugins/sec-overlay/.claude-plugin/plugin.json` `version` in every commit that changes a shipping file. `feat` bumps minor; every other type bumps patch. Read the current version before you edit it. The version entering this group is `1.112.0`.
- Add a `plugins/sec-overlay/CHANGELOG.md` entry in each commit.
- Stage explicit paths with one `git add <path>` per path. Never `git add -A`, `.`, `-u`, or `-a`. Never pass `--no-verify`.
- Run `prek run` before each commit. When a hook names a folder README, add one true sentence there, stage it, and record the addition in your report.
- The plugin core is stdlib-only. Do not add a dependency.
- Do not edit `helpers/sec_overlay/models.py` or `helpers/sec_overlay/evidence.py`. `tests/test_frozen_contract.py` pins their sha256 and will fail.
- Do not edit `references/finding.schema.json`. No task in this group needs it.
- Gates, run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:
  `uv run pytest -q`, `uv run ruff check sec_overlay/ bench/ tests/`, `uv run ty check`.
  One environmental failure is acceptable:
  `tests/test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd`
  fails when the gitignored semgrep clone is absent.
- Baseline test count entering this group is 1665 passed.
- Functions stay under 100 lines with cyclomatic complexity under 8 and at most five positional parameters. Public functions carry Google-style docstrings.
- Every path below is relative to `plugins/sec-overlay/skills/sec-overlay/` unless stated otherwise.
- Run every `git` command from the repository root. A stray nested git repository exists at `helpers/.git`; a `git` command run from inside `helpers/` targets the wrong repository.

---

## File Structure

| File | Responsibility in this group |
|------|------------------------------|
| `helpers/sec_overlay/verify.py` | gains a cause enum and its verification map (REQ-21); gains `resolve_configs` and accepts a config list (REQ-22) |
| `agents/trace.md` | widens the traced status set and names the in-band channel (REQ-06, REQ-19) |
| `helpers/sec_overlay/calibrate.py` | receipt tier, verification strength, and reachability move the derived score (REQ-20) |
| `helpers/sec_overlay/patch_status.py` | forward check runs first (REQ-01) |
| `helpers/sec_overlay/workspace.py` | unknown finding keys survive a load-and-save round trip (REQ-27) |

---

## Three deliberate contract reversals

Three tasks change behaviour an existing test pins. In each case the existing
test encodes the very contract the requirement reverses, so rewriting it is the
requirement, not a loosened gate. No other test in this group may be edited. If
any test outside this list fails, report the failure verbatim before changing
any expectation.

| Task | Test to rewrite | Why |
|------|-----------------|-----|
| 1 (REQ-21) | `tests/test_verify.py:48-50` `test_verify_patch_static_only_when_class_not_detectable` | `verify_patch` now returns a cause, not a verification value |
| 5 (REQ-01) | `tests/test_patch_status.py` `test_check_patch_applied_reverse_succeeds_means_applied` | the reverse check no longer runs first |
| 5 (REQ-01) | `tests/test_patch_status.py` `test_check_patch_applied_forward_succeeds_means_not_applied` | the forward check now runs first and alone |

---

## Task 1: REQ-21 — the verify verdict names its cause

**Files:**
- Modify: `helpers/sec_overlay/verify.py:224-345`
- Modify: `helpers/tests/test_verify.py:46-50` (one test, per the reversal table)
- Test: `helpers/tests/test_verify_causes.py` (create)

**Interfaces:**
- Produces: `VERIFY_CAUSES: frozenset[str]` and `_CAUSE_TO_VERIFICATION: dict[str, str]` in `sec_overlay.verify`. `verify_patch` now returns a cause, not a verification value. `verify_findings` maps the cause to a verification value and records `{"event": f"verify:cause:{cause}"}` in the finding's history.
- Task 2 also edits `verify_patch` and `verify_findings`. Task 2 runs after this one and builds on this signature.

**Why this shape.** `Finding.verification` is a closed enum: `evidence.py:24-26`
declares `VERIFICATION_VALUES = frozenset({"verified-static", "static-only",
"not-fixed", "verify-error", "fact-checked"})`, and `evidence.py` is frozen by
`tests/test_frozen_contract.py`. The cause therefore cannot become a new
verification value. It lives in `verify.py` and lands in `history`, which is a
free-form list of dicts.

Today `verify_patch` returns `"static-only"` from three distinct sites and a
reader cannot tell them apart:

- `verify.py:262` — the class was never detectable pre-patch.
- `verify.py:269` — the patch failed to apply to the copy.
- `verify.py:272` — the post-patch re-scan could not run.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_verify_causes.py`:

```python
"""REQ-21: the verify verdict names why it reached its answer."""

from __future__ import annotations

import pytest

from sec_overlay import verify as verify_mod
from sec_overlay.evidence import VERIFICATION_VALUES
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.verify import VERIFY_CAUSES, verify_findings, verify_patch
from sec_overlay.workspace import Workspace, read_findings, write_findings

_DIFF = "--- a/app.py\n+++ b/app.py\n"


class _Hits:
    """Fake ``_file_has_hit``: pops the next result from ``results`` per call."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self._results.pop(0)


def _target(tmp_path):
    repo = tmp_path / "target"
    repo.mkdir()
    (repo / "app.py").write_text("x = 1\n")
    return str(repo)


def _patch_backend(monkeypatch, results, applied=True):
    hits = _Hits(results)
    monkeypatch.setattr(verify_mod, "_file_has_hit", hits)
    monkeypatch.setattr(verify_mod, "apply_patch", lambda repo, diff: applied)
    return hits


@pytest.mark.parametrize(
    ("results", "applied", "cause"),
    [
        ([None], True, "rule-no-match"),
        ([False], True, "rule-no-match"),
        ([True], False, "patch-not-applied"),
        ([True, None], True, "unconfirmed"),
        ([True, False], True, "verified-static"),
        ([True, True], True, "not-fixed"),
    ],
)
def test_verify_patch_returns_a_named_cause(tmp_path, monkeypatch, results, applied, cause):
    _patch_backend(monkeypatch, results, applied=applied)
    got = verify_patch(_target(tmp_path), _DIFF, "cfg", "app.py", "sqli")
    assert got == cause
    assert got in VERIFY_CAUSES


def test_every_cause_maps_to_a_legal_verification():
    mapping = verify_mod._CAUSE_TO_VERIFICATION
    assert set(mapping) == set(VERIFY_CAUSES)
    assert set(mapping.values()) <= VERIFICATION_VALUES


def _confirmed(id_="F-1"):
    return Finding(id=id_, rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=Severity.HIGH, file="app.py", line=1, message="m",
                   patch_diff=_DIFF)


@pytest.mark.parametrize(
    ("cause", "verification"),
    [
        ("verified-static", "verified-static"),
        ("not-fixed", "not-fixed"),
        ("patch-not-applied", "static-only"),
        ("rule-no-match", "static-only"),
        ("unconfirmed", "static-only"),
    ],
)
def test_verify_findings_records_the_cause(tmp_path, cause, verification):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_confirmed()])
    verify_findings(ws, "t", "c", verifier=lambda *a, **k: cause)
    out = read_findings(ws)[0]
    assert out.verification == verification
    assert {"event": f"verify:cause:{cause}"} in out.history


def test_an_unknown_cause_degrades_to_static_only(tmp_path):
    """A verifier that returns an unmapped string must never launder a clean verdict."""
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    write_findings(ws, [_confirmed()])
    verify_findings(ws, "t", "c", verifier=lambda *a, **k: "static-only")
    assert read_findings(ws)[0].verification == "static-only"
```

Then rewrite the one existing test named in the reversal table. In
`helpers/tests/test_verify.py`, replace lines 46-50:

```python
@needs_semgrep
def test_verify_patch_static_only_when_class_not_detectable():
    # no ssrf rule fires in the fixture -> cannot auto-verify
    assert verify_patch(str(FIXTURE), GOLDEN, CONFIG, "app.py", "ssrf") == "static-only"
```

with:

```python
@needs_semgrep
def test_verify_patch_rule_no_match_when_class_not_detectable():
    # no ssrf rule fires in the fixture -> the cause is that no rule matched pre-patch
    assert verify_patch(str(FIXTURE), GOLDEN, CONFIG, "app.py", "ssrf") == "rule-no-match"
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_verify_causes.py -v`
Expected: `ImportError` on `VERIFY_CAUSES`.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing verify-cause tests`

- [ ] **Step 4: Add the cause enum**

Near the top of `verify.py`, after the imports, add:

```python
# The cause of a verify verdict. ``Finding.verification`` is a closed enum owned by the
# frozen ``evidence.py``, so the cause cannot become a verification value — it is returned
# by ``verify_patch``, mapped below, and recorded in the finding's history.
VERIFY_CAUSES = frozenset({
    "verified-static", "not-fixed", "patch-not-applied", "rule-no-match", "unconfirmed",
})

_CAUSE_TO_VERIFICATION = {
    "verified-static": "verified-static",
    "not-fixed": "not-fixed",
    "patch-not-applied": "static-only",
    "rule-no-match": "static-only",
    "unconfirmed": "static-only",
}
```

- [ ] **Step 5: Return the cause from `verify_patch`**

Three edits inside `verify_patch`:

- `verify.py:262`, the `if not pre:` branch — change `return "static-only"` to
  `return "rule-no-match"`.
- `verify.py:269`, the `if not apply_patch(repo, patch_diff):` branch — change
  `return "static-only"` to `return "patch-not-applied"`.
- `verify.py:272`, the `if post is None:` branch — change `return "static-only"`
  to `return "unconfirmed"`.

Then rewrite the docstring `Returns:` block (it currently names the three
verification values) to:

```
    Returns:
        A member of :data:`VERIFY_CAUSES`. ``"verified-static"`` (was flagged, now
        gone), ``"not-fixed"`` (still flagged after a clean apply),
        ``"rule-no-match"`` (not detectable pre-patch), ``"patch-not-applied"``
        (the patch failed to apply to the copy), or ``"unconfirmed"`` (the
        post-patch re-scan could not run). :func:`verify_findings` maps each
        cause to a legal ``Finding.verification`` value.
```

- [ ] **Step 6: Map the cause in `verify_findings`**

In `verify_findings` (`verify.py:278-345`), replace the block that runs from
`result = verifier(...)` to the end of the loop body with:

```python
        cause = verifier(
            target, f.patch_diff, config, f.file, f.cls, f.evidence_sources,
            language=language, db_dir=db_dir,
        )
        # An unmapped cause degrades to static-only: never launder an unknown verdict clean.
        verification = _CAUSE_TO_VERIFICATION.get(cause, "static-only")
        if verification == "verified-static" and validate_fix_said_not_fixed:
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
        f.history.append({"event": f"verify:cause:{cause}"})
        f.verification = verification
        changed = True
        if verification == "verified-static":
            f.status = FindingStatus.FIXED
            f.history.append({"event": "verify:fixed"})
            fixed += 1
        elif verification == "static-only":
            f.status = FindingStatus.NEEDS_DEPLOYMENT_TESTING
            f.history.append({"event": "verify:needs-deployment-testing"})
```

Three details are load-bearing. Do not reorder them.

1. The `.get(..., "static-only")` default keeps `test_verify.py:69-76` green
   with no edit — that test injects a verifier returning the literal
   `"static-only"`, which is not a cause.
2. The cause is appended AFTER the conflict `continue`, so the idempotence check
   (`f.history[-1].get("event") == "verify:conflict"`) still sees the conflict
   event as the last entry on a re-run.
3. Both status branches key off `verification`, not `cause`.

- [ ] **Step 7: Run the gates**

`uv run pytest tests/test_verify_causes.py tests/test_verify.py -v`, then the
three group gates. Expect 1665 + 12 = 1677 passed.

- [ ] **Step 8: Commit GREEN**

Subject: `feat(sec-overlay): name the cause of a verify verdict`
Body: names REQ-21 and records that `tests/test_verify.py:48-50` was rewritten
because it pinned the contract the requirement reverses.

---

## Task 2: REQ-22 — the verdict does not depend on one caller-supplied scalar

**Files:**
- Modify: `helpers/sec_overlay/verify.py:174-190` (`_check`), `:224-276` (`verify_patch`), `:278-345` (`verify_findings`)
- Test: `helpers/tests/test_verify_configs.py` (create)

**Interfaces:**
- Consumes: Task 1's cause return from `verify_patch`.
- Produces: `resolve_configs(ws: Workspace, fallback: str) -> list[str]` in `sec_overlay.verify`. `verify_patch`'s third parameter widens from `str` to `str | list[str]`.

**Why this shape.** `verify_findings` passes its own `config` scalar — whatever
the driver happened to hand `drive(config=…)` — to every finding. A finding
found by a ruleset the recon phase planned is then re-scanned with an unrelated
ruleset, and the verdict silently becomes `rule-no-match`. The planned rulesets
already live in the workspace at
`profile.sast_plan["semgrep"]["rulesets"]`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_verify_configs.py`:

```python
"""REQ-22: the verify verdict reads the planned rulesets, not the caller's scalar."""

from __future__ import annotations

from sec_overlay import kb
from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.profile import ScanProfile
from sec_overlay.verify import resolve_configs, verify_findings
from sec_overlay.workspace import Workspace, write_findings


def _ws(tmp_path):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    return ws


def _confirmed():
    return Finding(id="F-1", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                   severity=Severity.HIGH, file="app.py", line=1, message="m",
                   patch_diff="--- a/app.py\n+++ b/app.py\n")


def test_resolve_configs_reads_the_planned_rulesets(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": ["profile-rules.yaml"]}}))
    assert resolve_configs(ws, "caller.yaml") == ["profile-rules.yaml"]


def test_resolve_configs_falls_back_without_a_profile(tmp_path):
    assert resolve_configs(_ws(tmp_path), "caller.yaml") == ["caller.yaml"]


def test_resolve_configs_falls_back_on_an_empty_plan(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": []}}))
    assert resolve_configs(ws, "caller.yaml") == ["caller.yaml"]


def test_resolve_configs_falls_back_on_a_malformed_plan(tmp_path):
    ws = _ws(tmp_path)
    kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": "not-a-dict"}))
    assert resolve_configs(ws, "caller.yaml") == ["caller.yaml"]


def test_the_verdict_ignores_the_caller_scalar(tmp_path):
    """Two different caller scalars must produce the same config the verifier sees."""
    seen = []

    def spy(target, diff, config, file, cls, sources, **kwargs):
        seen.append(config)
        return "rule-no-match"

    for scalar in ("a.yaml", "b.yaml"):
        ws = _ws(tmp_path / scalar)
        kb.write_profile(ws, ScanProfile(sast_plan={"semgrep": {"rulesets": ["planned.yaml"]}}))
        write_findings(ws, [_confirmed()])
        verify_findings(ws, "t", scalar, verifier=spy)

    assert seen == [["planned.yaml"], ["planned.yaml"]]
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_verify_configs.py -v`
Expected: `ImportError` on `resolve_configs`.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing verify config tests`

- [ ] **Step 4: Add `resolve_configs`**

Add to `verify.py`, importing `read_profile` from `sec_overlay.kb` and
`Workspace` from `sec_overlay.workspace` at module level. `kb.py` imports only
`pathlib`, `sec_overlay.profile`, and `sec_overlay.workspace`, so there is no
import cycle.

```python
def resolve_configs(ws: Workspace, fallback: str) -> list[str]:
    """Return the semgrep rulesets the scan profile planned, or the caller's fallback.

    Args:
        ws: The campaign workspace.
        fallback: The caller-supplied config path, used when the profile is absent,
            unreadable, or plans no rulesets.

    Returns:
        A non-empty list of ruleset paths.
    """
    try:
        profile = read_profile(ws)
    except (OSError, ValueError):
        return [fallback]
    semgrep = profile.sast_plan.get("semgrep")
    rulesets = semgrep.get("rulesets") if isinstance(semgrep, dict) else None
    if not isinstance(rulesets, list):
        rulesets = []
    return [str(r) for r in rulesets] or [fallback]
```

`(OSError, ValueError)` covers all three failure modes: a missing file, a
malformed JSON body, and a profile whose shape `from_dict` rejects.

- [ ] **Step 5: Accept a config list in `_check` and `verify_patch`**

Replace `_check` (`verify.py:174-190`) with:

```python
def _check(
    target: str, configs: list[str], basename: str, cls: str, rules: set[str],
    backend: str, language: str | None, db_dir: str | None,
) -> bool | None:
    """Call ``_file_has_hit`` once per config, OR-combining the tri-state result.

    ``semgrep`` uses the original 5-positional-arg call (kept exact for
    backward compatibility with existing monkeypatches of ``_file_has_hit``);
    ``codeql``/``sca`` ignore ``configs`` entirely and run once, so a
    multi-ruleset plan never re-runs a database build per ruleset.
    """
    if backend != "semgrep":
        return _file_has_hit(
            target, configs[0], basename, cls, rules,
            backend=backend, language=language, db_dir=db_dir,
        )
    saw_none = False
    for config in configs:
        hit = _file_has_hit(target, config, basename, cls, rules)
        if hit:
            return True
        if hit is None:
            saw_none = True
    return None if saw_none else False
```

The invariant: `_check` returns `True` if any config flags the file, `None` if
no config flags it and at least one config could not run, and `False` only when
every config ran and none flagged the file. `None` must not collapse to `False`
— an unavailable backend is "cannot verify", never a clean result.

In `verify_patch`, widen the parameter and normalize once:

```python
def verify_patch(
    target: str, patch_diff: str, config: str | list[str], file: str, cls: str,
    evidence_sources: list[str] | None = None,
    *, language: str | None = None, db_dir: str | None = None,
) -> str:
```

Update the `config` line of its `Args:` block to:

```
        config: SAST rules config path, or a list of them (semgrep only).
```

Immediately after the `deps` short-circuit, add:

```python
    configs = [config] if isinstance(config, str) else list(config) or [""]
```

and pass `configs` to both `_check` calls at `verify.py:260` and `:270`.

- [ ] **Step 6: Resolve once in `verify_findings`**

In `verify_findings`, before the `for f in findings:` loop, add:

```python
    configs = resolve_configs(ws, config)
```

and change the `verifier(...)` call's third argument from `config` to `configs`.

- [ ] **Step 7: Run the gates**

`uv run pytest tests/test_verify_configs.py tests/test_verify.py tests/test_verify_causes.py -v`,
then the three group gates. Expect 1677 + 5 = 1682 passed.

`test_verify.py:126` monkeypatches `_file_has_hit` and depends on the exact
5-positional semgrep call. Step 5 preserves it. If that test fails, the call
shape changed — fix the call, not the test.

- [ ] **Step 8: Commit GREEN**

Subject: `fix(sec-overlay): verify against the planned rulesets`
Body: names REQ-22.

---

## Task 3: REQ-06 and REQ-19 — the trace covers the findings and channels it misses

**Files:**
- Modify: `agents/trace.md`
- Modify: `agents/README.md` (one sentence; the prek folder-README rule)
- Test: `helpers/tests/test_trace_prompt.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: nothing later tasks consume. This is a prompt-only change.

**Why one commit for two requirements.** REQ-06 widens the status filter and
REQ-19 adds the in-band channel sentence. Both edit the same `## Inputs` and
`## Procedure` block of `agents/trace.md`. Two commits would each touch the same
two lines. This is the only place in the group where two requirement ids share a
commit; the body names both.

**Why it matters.** `agents/trace.md:11` filters to `status == "confirmed"`, so
a `needs-deployment-testing` finding — the exact disposition that most needs a
reachability verdict before a human tests it — is never traced. Separately, the
backward trace stops at the sink and never states that a sink whose own reply is
visible to the caller is an exfiltration channel; that omission is why the
external SSRF finding recorded an out-of-band oracle first.

**No test references `trace.md` today.** The acceptance test is new. The idiom
is fixed by precedent at `tests/test_contracts.py:83` and
`tests/test_docs_invariants.py:19`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_trace_prompt.py`:

```python
"""REQ-06 and REQ-19: the trace prompt covers needs-runtime findings and in-band channels."""

from __future__ import annotations

from pathlib import Path

TRACE = Path(__file__).resolve().parents[2] / "agents" / "trace.md"


def _text():
    return TRACE.read_text()


def test_trace_covers_needs_deployment_testing():
    text = _text()
    assert "needs-deployment-testing" in text


def test_trace_does_not_filter_to_confirmed_alone():
    assert 'with `status == "confirmed"`.' not in _text()


def test_trace_names_the_in_band_channel():
    text = _text().lower()
    assert "in-band" in text
    assert "observable to the caller" in text
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_trace_prompt.py -v`
Expected: all three fail.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing trace prompt tests`

- [ ] **Step 4: Widen the status filter**

In `agents/trace.md`, replace this line:

```
- Findings to trace: `{{WORKSPACE}}/findings/*.json` with `status == "confirmed"`.
```

with:

```
- Findings to trace: `{{WORKSPACE}}/findings/*.json` with `status` in
  `{"confirmed", "needs-deployment-testing"}`. A `needs-deployment-testing` finding is real
  but unproven; it needs a reachability verdict before a human tests it, so trace it too.
```

Replace the heading:

```
## Procedure — per confirmed finding
```

with:

```
## Procedure — per traced finding
```

- [ ] **Step 5: Name the in-band channel**

In `agents/trace.md`, replace step 1 of the procedure:

```
1. Backward-trace from the sink toward an untrusted entry point using `callers` (exhaust ALL
   callers, not the first). Build the call chain `sink → … → entry`.
```

with:

```
1. Backward-trace from the sink toward an untrusted entry point using `callers` (exhaust ALL
   callers, not the first). Build the call chain `sink → … → entry`.
2. Enumerate EVERY path from source to sink, not the first one you find. Include any path
   where the sink's own reply is observable to the caller — a response body, an error
   message, a returned value, or a log the caller can read. That is an in-band channel, and
   it is an oracle a tester can use with no egress. Record it before any out-of-band channel.
```

Renumber the remaining steps of that procedure so the list stays sequential. Do
not change any other sentence in the file.

- [ ] **Step 6: Update the folder README**

`agents/README.md` documents every prompt. Add one true sentence to its
`trace.md` row or section stating that trace covers both `confirmed` and
`needs-deployment-testing` findings and records in-band channels first.

- [ ] **Step 7: Run the gates**

`uv run pytest tests/test_trace_prompt.py -v`, then the three group gates.
Expect 1682 + 3 = 1685 passed.

- [ ] **Step 8: Commit GREEN**

Subject: `feat(sec-overlay): widen the trace scope and channels`
Body: names REQ-06 and REQ-19, and states that both edit the same two lines of
`agents/trace.md`, so they ship as one commit.

---

## Task 4: REQ-20 — evidence strength and reachability move the score

**Files:**
- Modify: `helpers/sec_overlay/calibrate.py:152-165` (`_derived_score`)
- Test: `helpers/tests/test_calibrate_evidence.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_evidence_adjust(finding: Finding) -> int` in `sec_overlay.calibrate`, applied inside `_derived_score`.

**REQ-20's other half is already closed.** REQ-20 also required that
`_precondition_weight` be the single source for the precondition cap and that
`references/prompt-constants.md:51-60` be regenerated from it. Group 1 landed
that: `calibrate.py:106-107` now carries the comment "The risk_score ceiling by
precondition WEIGHT, not count. Published in prompt-constants.md
SEVERITY_PRECONDITION; the contract lint binds the two." Do not redo it. This
task builds only the scoring half.

**The design is reward-only. Do not add a penalty.** A first draft subtracted a
point when `receipt_tier` was `None`. `tests/test_calibrate.py` holds eight
exact-value score assertions whose fixtures all leave `receipt_tier` unset — a
penalty turns a scoring change into a mass test rewrite and changes findings the
requirement never named. Reward-only leaves every existing pinned score
untouched. The only fixture in the whole suite that sets any of the three new
input fields is `tests/test_calibrate.py:471`
(`reachability={"reachable": False, "blocker": "external-boundary"}`), whose
delta under reward-only is zero.

**Where the terms land.** They go in `_derived_score`, NOT `_heuristic_score`. A
finding with a valid CVSS vector never reaches the heuristic
(`calibrate.py:163-164`), so a term placed there would silently skip every
CVSS-scored finding.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_calibrate_evidence.py`:

```python
"""REQ-20: receipt tier, verification strength, and reachability move the derived score."""

from __future__ import annotations

from sec_overlay.calibrate import calibrate_score
from sec_overlay.models import Finding, FindingStatus, Severity


def _f(**kwargs):
    base = dict(
        id="F-1", rule_id="r", cls="xss", status=FindingStatus.CONFIRMED,
        severity=Severity.MEDIUM, file="app.py", line=1, message="m", dataflow=[],
    )
    base.update(kwargs)
    return Finding(**base)


def test_tier_one_receipt_outranks_tier_two():
    assert calibrate_score(_f(receipt_tier=1)) > calibrate_score(_f(receipt_tier=2))


def test_tier_two_receipt_outranks_no_receipt():
    assert calibrate_score(_f(receipt_tier=2)) > calibrate_score(_f())


def test_verified_static_outranks_static_only():
    assert calibrate_score(_f(verification="verified-static")) > calibrate_score(
        _f(verification="static-only")
    )


def test_an_assessed_reachable_finding_outranks_an_unreachable_one():
    reachable = _f(reachability={"reachable": True})
    unreachable = _f(reachability={"reachable": False})
    assert calibrate_score(reachable) > calibrate_score(unreachable)


def test_an_unassessed_finding_scores_as_it_did_before():
    """Reachability is reward-only: no assessment must not cost a point."""
    assert calibrate_score(_f()) == calibrate_score(_f(reachability={"reachable": False}))


def test_the_score_stays_in_range():
    top = _f(severity=Severity.CRITICAL, cls="sqli", dataflow=["a", "b", "c"],
             receipt_tier=1, verification="verified-static", reachability={"reachable": True})
    assert 1 <= calibrate_score(top) <= 10
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_calibrate_evidence.py -v`
Expected: the first four tests fail — every pair scores equal today.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing evidence-score tests`

- [ ] **Step 4: Add the evidence terms**

Add to `calibrate.py`, near the other module constants:

```python
# Reward-only, by design. A missing receipt or an unassessed reachability must not cost a
# point: a penalty would re-score every finding the requirement never named.
_RECEIPT_TERM = {1: 2, 2: 1}
_VERIFICATION_TERM = {"verified-static": 1}


def _evidence_adjust(finding: Finding) -> int:
    """Score delta from receipt tier, verification strength, and assessed reachability."""
    delta = _RECEIPT_TERM.get(finding.receipt_tier or 0, 0)
    delta += _VERIFICATION_TERM.get(finding.verification or "", 0)
    if finding.reachability is not None and is_reachable(finding):
        delta += 1
    return delta
```

Add the import `from sec_overlay.reachability import is_reachable`.
`reachability.py` imports only `sec_overlay.models`, so there is no cycle.

The `finding.reachability is not None` guard is what makes reachability
reward-only: `is_reachable` returns `True` for an unassessed finding by design
(`reachability.py`, the recall-safe default), so calling it without the guard
would hand a free point to every unassessed finding and move eight pinned
scores.

- [ ] **Step 5: Apply the terms in `_derived_score`**

In `_derived_score` (`calibrate.py:152-165`), replace the final line:

```python
    return min(raw, _precondition_cap(finding.preconditions))
```

with:

```python
    adjusted = max(1, min(10, raw + _evidence_adjust(finding)))
    return min(adjusted, _precondition_cap(finding.preconditions))
```

Update the docstring first line to:

```
    """Pre-floor score: CVSS/heuristic, evidence adjustment, then precondition cap."""
```

The order is load-bearing: the evidence adjustment clamps to `[1, 10]` before
the precondition cap applies, so a strong receipt can never lift a finding past
a cap its preconditions earned.

- [ ] **Step 6: Run the gates**

`uv run pytest tests/test_calibrate_evidence.py tests/test_calibrate.py tests/test_factcheck_baseline_envelope.py -v`,
then the three group gates. Expect 1685 + 6 = 1691 passed.

Every exact-value assertion in `tests/test_calibrate.py` (lines 29, 33, 38, 72,
90, 148, 149, 151) and in `tests/test_factcheck_baseline_envelope.py:35-37` must
stay green with no edit. If one moves, the change is not reward-only — fix the
implementation, not the test.

- [ ] **Step 7: Commit GREEN**

Subject: `feat(sec-overlay): score evidence strength and reach`
Body: names REQ-20, and records that REQ-20's `_precondition_weight` half was
already closed in group 1.

---

## Task 5: REQ-01 — a patch is applied only when it does not apply forward

**Files:**
- Modify: `helpers/sec_overlay/patch_status.py:48-60`
- Modify: `helpers/tests/test_patch_status.py` (two tests, per the reversal table)
- Test: `helpers/tests/test_patch_status_real_git.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: no signature change. `check_patch_applied(target, patch_diff, runner=...)` keeps its shape; only the order of the two checks changes.

**Requirements document, verbatim (`spec:195-212`).** "Root: RC-1. Location:
`helpers/sec_overlay/patch_status.py:48-60`. Current: `check_patch_applied` runs
`git apply --check --reverse` first and returns `APPLIED` on rc 0. For an
additive patch whose lines are absent, reverse-check exits 0 ("Skipped patch"),
so a not-applied patch is misread as live and the deployment caution is
suppressed. Required: a patch is APPLIED only when it does NOT apply forward AND
does apply reversed."

**Why the fake-runner tests must change.** `tests/test_patch_status.py`'s two
order-pinning tests assert the call ORDER this requirement reverses. They are
not loosened by the rewrite — they are re-pinned to the new order. The other
five tests in that file (`..._neither_succeeds_means_unknown`,
`..._empty_diff_short_circuits`, and three `not_applied_caution` tests) stay
green with no edit.

**Why a real-git test is also required.** A fake runner cannot show the
"Skipped patch" behaviour that causes the defect. The requirement's acceptance
test is stated in terms of a real additive diff, so the new file drives real
`git apply`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_patch_status_real_git.py`:

```python
"""REQ-01: an additive patch whose lines are absent is NOT_APPLIED, not APPLIED."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from sec_overlay.patch_status import PatchStatus, check_patch_applied

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

_ADDITIVE = """--- a/app.py
+++ b/app.py
@@ -1,2 +1,3 @@
 import os
+SAFE = True
 x = 1
"""


def _repo(tmp_path, body):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text(body)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
    return str(repo)


@needs_git
def test_absent_added_line_is_not_applied(tmp_path):
    target = _repo(tmp_path, "import os\nx = 1\n")
    assert check_patch_applied(target, _ADDITIVE) is PatchStatus.NOT_APPLIED


@needs_git
def test_present_added_line_is_applied(tmp_path):
    target = _repo(tmp_path, "import os\nSAFE = True\nx = 1\n")
    assert check_patch_applied(target, _ADDITIVE) is PatchStatus.APPLIED
```

Then rewrite the two existing tests named in the reversal table. In
`helpers/tests/test_patch_status.py`, replace:

```python
def test_check_patch_applied_reverse_succeeds_means_applied():
    runner = _runner([0])  # reverse check succeeds
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.APPLIED
    assert len(runner.calls) == 1


def test_check_patch_applied_forward_succeeds_means_not_applied():
    runner = _runner([1, 0])  # reverse fails, forward succeeds
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.NOT_APPLIED
    assert len(runner.calls) == 2
```

with:

```python
def test_check_patch_applied_forward_succeeds_means_not_applied():
    runner = _runner([0])  # forward check succeeds -> the patch is not in the tree yet
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.NOT_APPLIED
    assert len(runner.calls) == 1


def test_check_patch_applied_reverse_only_means_applied():
    runner = _runner([1, 0])  # forward fails, reverse succeeds -> the change is already live
    assert check_patch_applied("/tgt", "diff", runner=runner) is PatchStatus.APPLIED
    assert len(runner.calls) == 2
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_patch_status_real_git.py tests/test_patch_status.py -v`
Expected: `test_absent_added_line_is_not_applied` fails with
`PatchStatus.APPLIED`, and both rewritten fake-runner tests fail on the call
count.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing patch-order tests`

- [ ] **Step 4: Run the forward check first**

In `check_patch_applied` (`patch_status.py:48-60`), replace the two check blocks
with:

```python
    # Forward first, deliberately. ``git apply --check --reverse`` exits 0 on an additive
    # patch whose added lines are simply absent ("Skipped patch"), so a reverse-first order
    # reads a never-applied patch as live and suppresses the deployment caution.
    forward = runner(
        ["git", "apply", "--check"],
        cwd=str(target), input=patch_diff, capture_output=True, text=True,
    )
    if forward.returncode == 0:
        return PatchStatus.NOT_APPLIED
    reverse = runner(
        ["git", "apply", "--check", "--reverse"],
        cwd=str(target), input=patch_diff, capture_output=True, text=True,
    )
    if reverse.returncode == 0:
        return PatchStatus.APPLIED
    return PatchStatus.UNKNOWN
```

- [ ] **Step 5: Correct the docstring**

The `Returns:` block currently describes the old order. Replace it with:

```
    Returns:
        ``NOT_APPLIED`` if the diff still applies cleanly forward, ``APPLIED`` if it does
        not apply forward but does apply reversed (its changes are already present),
        ``UNKNOWN`` if neither check succeeds (e.g. the file has diverged since the patch
        was generated) or ``patch_diff`` is empty.
```

- [ ] **Step 6: Run the gates**

`uv run pytest tests/test_patch_status_real_git.py tests/test_patch_status.py -v`,
then the three group gates. Expect 1691 + 2 = 1693 passed.

`report.py` and `redteam.py` both call `check_patch_applied`, but their tests
monkeypatch it wholesale, so neither is affected. If either fails, report the
failure verbatim before changing any expectation.

- [ ] **Step 7: Commit GREEN**

Subject: `fix(sec-overlay): check patch forward before reverse`
Body: names REQ-01 and records that the two order-pinning tests in
`tests/test_patch_status.py` were re-pinned to the new order.

---

## Task 6: REQ-27 — an unknown finding key survives a load-and-save round trip

**Files:**
- Modify: `helpers/sec_overlay/workspace.py:131-145` (`write_findings`), `:174-186` (`read_findings`)
- Test: `helpers/tests/test_findings_overflow.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `read_findings` stashes unknown keys on each returned `Finding`; `write_findings` merges them back. No public signature changes.

**Line drift, record it.** The requirements document cites `models.py:154` as the
site that drops unknown keys. The drop is at `models.py:177`.

**Why this shape and not the obvious one.** The obvious fix is an overflow field
on `Finding`. That is forbidden: `models.py` is a byte-identical mirror of a
separate Go port (D-15) and `tests/test_frozen_contract.py:26-31` pins its
sha256. Editing it plus bumping the digest defeats the tripwire and books a Go
edit nobody in this repository can verify.

`Finding` is a plain `@dataclass` with no `slots=True` (`models.py:62`), so an
attribute can be set on an instance from outside the class. `asdict`/`to_dict`
ignore an attribute that is not a declared field. `models.py` and `evidence.py`
therefore stay byte-identical and no digest moves.

**Accepted cost, stated plainly.** `findings_gate.py:100` and `bench/run.py:101`
still drop unknown keys. Both are terminal consumers, not round-trippers, so no
rewrite loses data there. Record this residual in your report.

**Build rider, from the requirement's author, verbatim:** "make the overflow
merge deterministic (stable key order) so B does not itself perturb any
downstream diff."

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_findings_overflow.py`:

```python
"""REQ-27: an unknown finding key survives a load-and-save round trip."""

from __future__ import annotations

import json

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.workspace import Workspace, read_findings, write_findings


def _ws(tmp_path):
    ws = Workspace(tmp_path / "workspace")
    ws.ensure()
    return ws


def _raw(**extra):
    f = Finding(id="F-1", rule_id="r", cls="sqli", status=FindingStatus.CONFIRMED,
                severity=Severity.HIGH, file="app.py", line=1, message="m")
    raw = f.to_dict()
    raw.update(extra)
    return raw


def _round_trip(ws, raw):
    (ws.findings_dir / "F-1.json").write_text(json.dumps(raw, indent=2))
    write_findings(ws, read_findings(ws))
    return json.loads((ws.findings_dir / "F-1.json").read_text())


def test_an_unknown_key_survives_a_round_trip(tmp_path):
    out = _round_trip(_ws(tmp_path), _raw(proof_of_exploit={"scope": "entrypoint"}))
    assert out["proof_of_exploit"] == {"scope": "entrypoint"}


def test_a_round_trip_preserves_the_known_fields(tmp_path):
    out = _round_trip(_ws(tmp_path), _raw(proof_of_exploit={"scope": "slice"}))
    assert out["id"] == "F-1"
    assert out["cls"] == "sqli"
    assert out["status"] == "confirmed"


def test_the_merge_is_deterministic(tmp_path):
    """Two insertion orders of the same unknown keys must produce identical bytes."""
    a = _ws(tmp_path / "a")
    b = _ws(tmp_path / "b")
    (a.findings_dir / "F-1.json").write_text(json.dumps(_raw(zeta=1, alpha=2), indent=2))
    (b.findings_dir / "F-1.json").write_text(json.dumps(_raw(alpha=2, zeta=1), indent=2))
    write_findings(a, read_findings(a))
    write_findings(b, read_findings(b))
    assert (a.findings_dir / "F-1.json").read_text() == (b.findings_dir / "F-1.json").read_text()


def test_a_finding_with_no_unknown_key_is_unchanged(tmp_path):
    ws = _ws(tmp_path)
    raw = _raw()
    out = _round_trip(ws, raw)
    assert out == raw


def test_a_warning_names_the_preserved_keys(tmp_path, capsys):
    ws = _ws(tmp_path)
    (ws.findings_dir / "F-1.json").write_text(json.dumps(_raw(proof_of_exploit=1)))
    read_findings(ws)
    assert "proof_of_exploit" in capsys.readouterr().err
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_findings_overflow.py -v`
Expected: `test_an_unknown_key_survives_a_round_trip` fails with `KeyError:
'proof_of_exploit'`.

- [ ] **Step 3: Commit RED**

Subject: `test(sec-overlay): add failing finding overflow tests`

- [ ] **Step 4: Stash unknown keys on read**

Add near the top of `workspace.py`:

```python
# Unknown keys ride on the instance, not on ``Finding``: ``models.py`` is a byte-identical
# mirror of the Go port (D-15) and its sha256 is pinned. ``Finding`` is a plain dataclass with
# no ``slots``, so an instance attribute is legal and ``to_dict`` ignores it.
_OVERFLOW_ATTR = "_unknown_keys"
```

Replace the body of `read_findings` (`workspace.py:180-186`) with:

```python
    findings: list[Finding] = []
    for p in sorted(ws.findings_dir.glob("*.json")):
        try:
            raw = json.loads(p.read_text())
            finding = Finding.from_dict(raw)
            extra = {k: raw[k] for k in sorted(raw) if k not in Finding.__dataclass_fields__}
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"warning: skipping unparseable finding {p.name}: {exc}", file=sys.stderr)
            continue
        if extra:
            setattr(finding, _OVERFLOW_ATTR, extra)
            print(
                f"warning: preserving unknown keys on {p.name}: {', '.join(extra)}",
                file=sys.stderr,
            )
        findings.append(finding)
    return findings
```

The `sorted(raw)` comprehension is the determinism guarantee the build rider
requires: the overflow dict is built in sorted key order and dicts preserve
insertion order, so the merge below appends the same bytes regardless of the
source file's key order.

Extend the docstring with one sentence: "Unknown keys are preserved on the
returned instance so :func:`write_findings` can merge them back."

- [ ] **Step 5: Merge unknown keys on write**

Replace the loop body of `write_findings` (`workspace.py:143-145`) with:

```python
    for f in findings:
        record = f.to_dict()
        record.update(getattr(f, _OVERFLOW_ATTR, {}))
        _atomic_write(ws.findings_dir / f"{f.id}.json", json.dumps(record, indent=2))
```

An overflow key can never collide with a declared field — `read_findings`
excludes `Finding.__dataclass_fields__` — so `update` never overwrites a live
value. Unknown keys land at the end of the object in sorted order, so no
existing key is reordered.

Extend the docstring with one sentence: "Unknown keys stashed by
:func:`read_findings` are merged back in sorted order, so a load-and-save round
trip never drops data."

- [ ] **Step 6: Run the gates**

`uv run pytest tests/test_findings_overflow.py tests/test_workspace.py -v`, then
the three group gates. Expect 1693 + 5 = 1698 passed.

- [ ] **Step 7: Commit GREEN**

Subject: `fix(sec-overlay): preserve unknown finding keys`
Body: names REQ-27, records the `models.py:154` to `models.py:177` drift, and
names the accepted residual at `findings_gate.py:100` and `bench/run.py:101`.

---

## Group gate

After Task 6, run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

1. `uv run pytest -q` — expect 1698 passed, with the one acceptable
   environmental failure noted in Global Constraints.
2. `uv run ruff check sec_overlay/ bench/ tests/` — expect zero findings.
3. `uv run ty check` — expect zero findings.
