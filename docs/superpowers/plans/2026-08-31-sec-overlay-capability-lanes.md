# sec-overlay Capability Lanes Implementation Plan (Part E group 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the five capability-lane requirements — REQ-33, REQ-34, REQ-12, REQ-14, REQ-30 — so a finding page carries the eight Part D elements, a red-team directive lists the no-egress in-band oracle first, the STE linter stops rejecting its own mandated sentence, a Go plus CodeQL run stops tripping the working-tree fence, and an opt-in lane can prove a finding by execution.

**Architecture:** Four of the five requirements extend existing modules in place. REQ-33 renders eight optional finding fields that ride the `_unknown_keys` overflow, so `models.py` stays byte-identical. REQ-34 widens `signal_lines` to a channel list while keeping its dict and string branches. REQ-12 rewords one prompt constant and teaches `_prose_blocks` to fold a wrapped list item. REQ-14 adds `--build-mode=none` to the Go CodeQL argv. REQ-30 adds a new non-frozen module `sec_overlay/prove.py`, a new agent prompt `agents/prove.md`, and one new `PhaseSpec` between `redteam` and `artifact-gate`, all behind `scan_options.prove_findings` (default off).

**Tech Stack:** Python 3.12, standard library only. Dev tools: `pytest`, `ruff`, `ty`, all run through `uv` from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

**Spec:** `/Users/christopher/Workspace/review_enforce/spec_secoverlay-improvements_20260823_1219.md`, plus the user's build addendum, which overrides the spec where the two disagree.

## Global Constraints

- Work on branch `feat/sec-overlay-improvements`. Never commit to `main`.
- One REQ per task. Each task is a red/green commit pair. The RED commit adds the failing test only. The GREEN commit adds the code. Put the REQ id in both commit subjects.
- Conventional Commits. The summary after `type(scope): ` must stay under 50 characters. Put the REQ id in the commit body when the subject has no room.
- Stage explicit paths. Never run `git add -A`, `git add .`, `git add -u`, or `git commit -a`. Never pass `--no-verify`.
- Do not add a `Co-Authored-By` trailer.
- Every commit that touches anything under `plugins/sec-overlay/` must also stage `plugins/sec-overlay/CHANGELOG.md`.
- Every commit must stage the immediate folder `README.md` of each file it touches. Tracked READMEs: `helpers/README.md`, `helpers/tests/README.md`, `helpers/sec_overlay/README.md`, `helpers/rules/README.md`, `helpers/bench/README.md`, `helpers/bench/corpus_seed/README.md`, `agents/README.md`, `references/README.md`.
- `helpers/sec_overlay/README.md` and `helpers/tests/README.md` are append-only narrative logs. Add to the end. Do not rewrite earlier entries.
- Bump `version` in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit as any shipping-file change. A `feat` bumps minor. Every other type bumps patch. `CHANGELOG.md` is not a shipping file.
- Run `prek run` before each commit. Fix every warning before committing.
- The plugin core is standard-library only. Do not add a dependency.
- `helpers/sec_overlay/models.py` and `helpers/sec_overlay/evidence.py` are byte-pinned by `tests/test_frozen_contract.py:30-31`. Do not edit either file. Do not bump the pinned digests.
- Run every `git` command from the repository root. A stray nested git repository sits at `helpers/.git`.
- The Bash working directory resets between calls. Prefix each call with an absolute `cd`.
- Group gate, run from `helpers/`: `uv run pytest -q`, `uv run ruff check sec_overlay/ bench/ tests/`, `uv run ty check`. All three must pass at the end of the group.
- Ruff enforces ISC004. Parenthesize an implicit string concatenation inside a collection literal.

---

## Pre-flight scan

Every `file:line` below was confirmed against HEAD `cef855b`.

### Conflicts and rulings

| # | Conflict | Ruling | Cost if wrong |
|---|----------|--------|---------------|
| A | REQ-33 adds eight finding fields. Adding dataclass fields to `models.py` breaks `_MODELS_SHA256`. | Apply the settled REQ-27 precedent. Declare the eight fields in `references/finding.schema.json`, read them from the `_unknown_keys` overflow in `report.py`, and leave `models.py` byte-identical. | A later Go port must mirror the schema fields by hand. |
| B | Spec REQ-30 surface 7 directs adding `"reproduction"` to `_MECHANICAL` and `TIER1_RECEIPTS` in the byte-pinned `evidence.py`. | Leave `evidence.py` untouched. Put `REPRODUCTION_RECEIPT = "reproduction"` and `is_reproduction_receipt()` in the new non-frozen `prove.py`. Teach the non-frozen `findings_gate.py` to accept `is_tool_receipt(src) or is_reproduction_receipt(src)`. | Two receipt vocabularies instead of one. A later Go port must mirror the prove-lane constant separately. |
| C | REQ-33 does not say where each section goes. | One helper `_optional_sections(extra, keys)` plus a module-level `_OPTIONAL_LABELS` map, called twice. Context keys go after the Compliance block. Evidence keys go after the Severity Rationale block. | A reader finds a section in an unexpected place. |
| D | REQ-34 changes `expected_signal` to a list. Findings already on disk carry a dict or a bare string. | `signal_lines` gains a list branch and keeps its dict and string branches. `finding.schema.json` gains `"array"` to the `expected_signal` type list. | None observed. The three branches are mutually exclusive on type. |
| E | REQ-14 says to run autobuild inside `.sec-overlay/` or against a copy, else skip. | For `language == "go"`, add `--build-mode=none` to the `codeql database create` argv so nothing compiles inside `--source-root`. Keep the existing error path so a CodeQL that rejects the flag records `skipped_reasons["codeql-go"] = "build-unfenceable"`. | A no-build Go database yields weaker dataflow than a full build. That beats tripping the fence, and the fallback keeps the never-silent contract. |
| F | The decision log has two candidate homes. | Follow Directive D verbatim: `docs/decisions/2026-08-31-prove-lane-execution.md` at the repository root, as its own commit. That commit touches outside `plugins/`, so it also updates the root `CHANGELOG.md` and root `README.md`. | The repository carries a `docs/decisions/` directory the global preference did not ask for. |

### Drift rows

| Spec cite | Reality at HEAD `cef855b` |
|-----------|---------------------------|
| `run.py:253` second `fence()` call | `run.py:249`. |
| REQ-12 sentence in `agents/architecture.md` | `references/prompt-constants.md:203-204`, inside the `STE_PROSE` block. The four fixtures at `tests/test_driver.py:360,379,398,404` already use the short semicolon-free form and will not break. |
| `codeql.py` build argv | `codeql.py:211-214`. It carries no `--command` and no `--build-mode`. |
| `profile.py` `scan_options` | Documented at `:40-43`, field at `:60`. |
| `expected_signal` as a top-level field | It is nested inside `Finding.runtime_test`. |
| `agents/classes/` holds 14 files | 13 class prompts plus `README.md`. Exclude `README.md` from any directory scan. |
| REQ-35 | Phantom. `spec:81` names it, Part C has no block. REQ-14 covers that ground. |

### Task-pair scan

| Pair | Shared surface | Finding |
|------|----------------|---------|
| 1 and 5 | `references/finding.schema.json` | Task 1 adds eight optional properties. Task 5 adds a `reproduction` object. Disjoint keys, no conflict. |
| 1 and 5 | `report.py` overflow read | Task 1 introduces `_optional_sections`. Task 5 reuses it for the reproduction receipt line. Task 5 consumes Task 1's helper, so Task 1 lands first. |
| 2 and 5 | `agents/redteam.md` | Task 2 adds the in-band-channel-first rule. Task 5 does not touch `redteam.md`. No conflict. |
| 3 and 5 | `ste_lint.py` | Task 3 changes `_prose_blocks`. Task 5 writes `agents/prove.md`, which the linter never reads. No conflict. |
| 4 and 5 | `prefilter.py` `skipped_reasons` | Task 4 adds the `codeql-go` key. Task 5 does not touch `prefilter.py`. No conflict. |
| Each task with itself | — | Each task's tests name only files that task creates or modifies. No internal contradiction found. |

Build order: REQ-33, REQ-34, REQ-12, REQ-14, REQ-30. REQ-30 consumes REQ-33's optional-field renderer and is the riskiest, so it lands last against settled surfaces.

---

## File Structure

| File | Responsibility | Task |
|------|----------------|------|
| `helpers/sec_overlay/report.py` | Render the eight optional sections from the overflow. | 1, 5 |
| `references/finding.schema.json` | Declare the eight optional fields, widen `expected_signal`, declare the reproduction payload. | 1, 2, 5 |
| `agents/investigate.md`, `agents/validate.md` | Instruct the agents to populate the eight fields. | 1 |
| `helpers/sec_overlay/render_util.py` | Render a channel list, a dict, or a bare string. | 2 |
| `agents/redteam.md` | Require the in-band channel first. | 2 |
| `references/prompt-constants.md` | Reword the mandated front-matter sentence. | 3 |
| `helpers/sec_overlay/ste_lint.py` | Fold a wrapped list item into one logical block. | 3 |
| `helpers/sec_overlay/codeql.py` | Add `--build-mode=none` for Go. | 4 |
| `helpers/sec_overlay/prefilter.py` | Record `codeql-go: build-unfenceable`. | 4 |
| `helpers/sec_overlay/prove.py` | New. The prove lane: gating, oracles, the loopback collector, the receipt vocabulary. | 5 |
| `helpers/sec_overlay/phases.py` | New `prove` `PhaseSpec` between `redteam` and `artifact-gate`. | 5 |
| `helpers/sec_overlay/findings_gate.py` | Accept a reproduction receipt alongside a tool receipt. | 5 |
| `helpers/sec_overlay/workspace.py` | New `repro` directory property. | 5 |
| `agents/prove.md` | New. The prove-phase prompt. | 5 |
| `docs/decisions/2026-08-31-prove-lane-execution.md` | New. Log the invariant reversal. | 5 |

---

## Task 1: REQ-33 — the eight Part D finding elements

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py:118-158`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/investigate.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/validate.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report_optional_sections.py` (create)

**Interfaces:**
- Consumes: `sec_overlay.workspace._OVERFLOW_ATTR` (the string `"_unknown_keys"`), already reachable — `report.py:11-24` imports from `sec_overlay.workspace`.
- Produces: `report._optional_sections(extra: dict, keys: tuple[str, ...]) -> list[str]`, `report._OPTIONAL_LABELS: dict[str, str]`, `report._CONTEXT_KEYS`, `report._EVIDENCE_KEYS`. Task 5 calls `_optional_sections`.

The eight fields, their labels, and their render shape:

| Key | Label | Shape |
|-----|-------|-------|
| `attacker` | `Attacker` | inline |
| `privilege` | `Privilege required` | inline |
| `exact_request` | `Exact request` | fenced block, language `http` |
| `exfil_channels` | `Exfiltration channels` | bullet list |
| `library_version` | `Library version` | inline |
| `refutation` | `Refutation attempted` | inline |
| `negative_results` | `Negative results` | bullet list |
| `baseline` | `Baseline` | inline |

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_report_optional_sections.py`:

```python
"""REQ-33: the eight Part D elements render from the finding overflow."""

from __future__ import annotations

from sec_overlay.models import Finding, FindingStatus, Severity
from sec_overlay.report import render_finding
from sec_overlay.workspace import _OVERFLOW_ATTR

_EXTRA = {
    "attacker": "an unauthenticated internet client",
    "privilege": "none",
    "exact_request": "POST /api/fetch HTTP/1.1\nHost: t\n\nurl=http://169.254.169.254/",
    "exfil_channels": ["response body", "DNS resolution"],
    "library_version": "requests 2.31.0",
    "refutation": "checked for an allowlist on the host component; none present",
    "negative_results": ["no egress filter in the deployment manifest"],
    "baseline": "the same call in v1.2 used a fixed host",
}


def _finding(severity: str = "high") -> Finding:
    f = Finding(
        id="F-001",
        rule_id="semgrep:ssrf",
        cls="ssrf",
        status=FindingStatus.CONFIRMED,
        severity=Severity(severity),
        file="app/fetch.py",
        line=12,
        message="User-controlled URL reaches an HTTP client.",
        evidence_sources=["semgrep:ssrf"],
    )
    setattr(f, _OVERFLOW_ATTR, dict(_EXTRA))
    return f


def test_every_optional_section_renders() -> None:
    md = render_finding(_finding())
    for label in (
        "Attacker",
        "Privilege required",
        "Exact request",
        "Exfiltration channels",
        "Library version",
        "Refutation attempted",
        "Negative results",
        "Baseline",
    ):
        assert f"**{label}.**" in md, label


def test_list_values_render_as_bullets() -> None:
    md = render_finding(_finding())
    assert "- response body" in md
    assert "- DNS resolution" in md


def test_exact_request_renders_in_an_http_fence() -> None:
    md = render_finding(_finding())
    assert "```http" in md
    assert "POST /api/fetch HTTP/1.1" in md


def test_absent_fields_render_nothing() -> None:
    f = _finding()
    setattr(f, _OVERFLOW_ATTR, {})
    md = render_finding(f)
    assert "**Attacker.**" not in md
    assert "**Baseline.**" not in md


def test_condensed_tier_still_renders_the_sections() -> None:
    md = render_finding(_finding("medium"))
    assert "**Attacker.**" in md
    assert "**Baseline.**" in md
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_report_optional_sections.py -q
```

Expected: failures on the assertion, not on import.

- [ ] **Step 3: Commit RED**

Append one line to `helpers/tests/README.md`. Add a CHANGELOG entry under an `## Unreleased` heading. No version bump — a test file is a shipping file under `helpers/`, so bump the patch version too.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_report_optional_sections.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin the Part D finding elements" -m "REQ-33: assert the eight optional sections render."
```

- [ ] **Step 4: Add the renderer**

In `report.py`, after `_FULL_TIERS` at `:46`:

```python
# REQ-33: Part D elements. They ride the finding overflow (workspace._OVERFLOW_ATTR),
# never a `Finding` field — models.py is byte-pinned by the D-15 frozen-contract test.
_OPTIONAL_LABELS = {
    "attacker": "Attacker",
    "privilege": "Privilege required",
    "exact_request": "Exact request",
    "exfil_channels": "Exfiltration channels",
    "library_version": "Library version",
    "refutation": "Refutation attempted",
    "negative_results": "Negative results",
    "baseline": "Baseline",
}
_CONTEXT_KEYS = ("attacker", "privilege", "exact_request", "exfil_channels")
_EVIDENCE_KEYS = ("library_version", "refutation", "negative_results", "baseline")


def _optional_sections(extra: dict, keys: tuple[str, ...]) -> list[str]:
    """Render the present Part D elements for ``keys`` as Markdown lines.

    Args:
        extra: The finding's overflow mapping; absent keys render nothing.
        keys: The ordered subset of :data:`_OPTIONAL_LABELS` to render.

    Returns:
        Markdown lines, empty when no key is present.
    """
    out: list[str] = []
    for key in keys:
        value = extra.get(key)
        if value is None or value == "" or value == []:
            continue
        label = _OPTIONAL_LABELS[key]
        if isinstance(value, list):
            out += [f"**{label}.**", *(f"- {item}" for item in value), ""]
        elif key == "exact_request":
            out += [f"**{label}.**", "```http", str(value).strip(), "```", ""]
        else:
            out += [f"**{label}.** {value}", ""]
    return out
```

Add `_OVERFLOW_ATTR` to the existing `sec_overlay.workspace` import at `report.py:11-24`.

Inside `render_finding`, right after the `full = ...` assignment at `:111`:

```python
    extra = getattr(f, _OVERFLOW_ATTR, {}) or {}
```

After the Compliance block that ends at `:126`, before the `# §2 Mechanism` comment:

```python
    out += _optional_sections(extra, _CONTEXT_KEYS)
```

After the Severity Rationale block that ends at `:158`, before `if not full:`:

```python
    out += _optional_sections(extra, _EVIDENCE_KEYS)
```

- [ ] **Step 5: Declare the fields in the schema**

In `references/finding.schema.json`, inside `"properties"`, add:

```json
    "attacker": { "type": ["string", "null"] },
    "privilege": { "type": ["string", "null"] },
    "exact_request": { "type": ["string", "null"] },
    "exfil_channels": { "type": ["array", "null"], "items": { "type": "string" } },
    "library_version": { "type": ["string", "null"] },
    "refutation": { "type": ["string", "null"] },
    "negative_results": { "type": ["array", "null"], "items": { "type": "string" } },
    "baseline": { "type": ["string", "null"] },
```

The schema has no `additionalProperties` key, so nothing else changes.

- [ ] **Step 6: Instruct the agents**

Add one short block to `agents/investigate.md` and `agents/validate.md` telling the agent to populate the eight fields when it knows them, and to omit a field it cannot support with evidence. Name each key exactly. Keep the prose STE-compliant: active voice, one claim per sentence, 25 words or fewer, no semicolon.

- [ ] **Step 7: Run the test and confirm it passes**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_report_optional_sections.py -q && uv run pytest -q
```

- [ ] **Step 8: Commit GREEN**

Update `helpers/sec_overlay/README.md`, `agents/README.md`, `references/README.md`, the CHANGELOG, and bump the minor version (`feat`).

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/investigate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/validate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): render Part D finding elements" -m "REQ-33: eight optional fields render from the finding overflow."
```

---

## Task 2: REQ-34 — multi-channel expected signal

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/render_util.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json:46`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/redteam.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_signal_channels.py` (create)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `render_util.signal_lines` accepting `list[dict]`. Both existing callers (`redteam._signal` at `redteam.py:141-145`, `report.render_ndt` at `report.py:191`) already delegate, so neither changes.

Channel object: `{"name": str, "needs_egress": bool, "secure": str, "insecure": str}`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_signal_channels.py`:

```python
"""REQ-34: expected_signal renders a list of observation channels."""

from __future__ import annotations

from sec_overlay.render_util import signal_lines

_CHANNELS = [
    {
        "name": "in-band valid boolean",
        "needs_egress": False,
        "secure": "valid=false for an internal host",
        "insecure": "valid=true for http://169.254.169.254/",
    },
    {
        "name": "out-of-band collector hit",
        "needs_egress": True,
        "secure": "no request reaches the collector",
        "insecure": "the collector logs one GET",
    },
]


def test_two_channels_render_with_names() -> None:
    lines = signal_lines(_CHANNELS)
    text = "\n".join(lines)
    assert "in-band valid boolean" in text
    assert "out-of-band collector hit" in text


def test_egress_marker_distinguishes_the_channels() -> None:
    text = "\n".join(signal_lines(_CHANNELS))
    assert "no egress" in text
    assert "needs egress" in text


def test_each_channel_carries_secure_and_insecure() -> None:
    text = "\n".join(signal_lines(_CHANNELS))
    assert text.count("**secure:**") == 2
    assert text.count("**insecure:**") == 2


def test_dict_shape_still_renders() -> None:
    lines = signal_lines({"secure": "a", "insecure": "b"})
    assert lines == ["  - **secure:** a", "  - **insecure:** b"]


def test_bare_string_still_renders() -> None:
    assert signal_lines("boom") == ["  - **insecure:** boom"]


def test_empty_list_renders_nothing() -> None:
    assert signal_lines([]) == []
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_signal_channels.py -q
```

Expected: the four list tests fail. The dict and string tests pass already.

- [ ] **Step 3: Commit RED**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_signal_channels.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin multi-channel expected signal" -m "REQ-34: assert a two-channel expected_signal renders both."
```

- [ ] **Step 4: Widen `signal_lines`**

Replace the body of `signal_lines` in `render_util.py` with a three-branch form. Keep the docstring and add the list branch:

```python
def _channel_lines(channel: dict) -> list[str]:
    name = channel.get("name") or "_unnamed channel_"
    egress = "needs egress" if channel.get("needs_egress") else "no egress"
    return [
        f"  - **{name}** ({egress})",
        f"    - **secure:** {channel.get('secure', '_unspecified_')}",
        f"    - **insecure:** {channel.get('insecure', '_unspecified_')}",
    ]


def signal_lines(d: object) -> list[str]:
    if isinstance(d, list):
        return [ln for c in d if isinstance(c, dict) for ln in _channel_lines(c)]
    if isinstance(d, str):
        d = {"insecure": d} if d.strip() else {}
    if not isinstance(d, dict) or not d:
        return []
    lines: list[str] = []
    if "secure" in d:
        lines.append(f"  - **secure:** {d.get('secure', '_unspecified_')}")
    lines.append(f"  - **insecure:** {d.get('insecure', '_unspecified_')}")
    return lines
```

- [ ] **Step 5: Widen the schema**

`references/finding.schema.json:46` currently reads:

```json
"expected_signal": {"type": ["object", "string", "null"]}
```

Change it to:

```json
"expected_signal": {"type": ["array", "object", "string", "null"]}
```

- [ ] **Step 6: Add the red-team rule**

In `agents/redteam.md`, near the `expected_signal` guidance at `:61`, add the rule: for any finding whose sink reply is caller-observable, enumerate the in-band channel first, and mark it `needs_egress: false`. Add an out-of-band channel after it. Keep the prose STE-compliant.

- [ ] **Step 7: Run the tests and confirm they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_signal_channels.py -q && uv run pytest -q
```

- [ ] **Step 8: Commit GREEN**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/render_util.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/redteam.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): render signal channels" -m "REQ-34: expected_signal accepts a channel list, in-band first."
```

---

## Task 3: REQ-12 — the linter stops rejecting its own sentence

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md:203-204`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/ste_lint.py:42-82`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_ste_lint_wrapped.py` (create)

**Interfaces:**
- Consumes: nothing from Tasks 1 and 2.
- Produces: nothing later tasks consume.

The mandated sentence at `prompt-constants.md:203-204` reads:

```
Prose follows an ASD-STE100-inspired clarity standard (structural rules enforced; lexical dictionary not verified).
```

The semicolon makes `lint_prose` reject the sentence the same block mandates. The replacement:

```
Prose follows an ASD-STE100-inspired clarity standard. A linter enforces the structural rules. The lexical dictionary stays unverified.
```

`main`'s `--require-frontmatter` check tests for the substring `ASD-STE100`, which the replacement keeps.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_ste_lint_wrapped.py`:

```python
"""REQ-12: the mandated sentence lints clean and a wrapped list item is one line."""

from __future__ import annotations

from pathlib import Path

from sec_overlay.ste_lint import lint_prose

_CONSTANTS = (
    Path(__file__).resolve().parents[2] / "references" / "prompt-constants.md"
)

_MANDATED = (
    "Prose follows an ASD-STE100-inspired clarity standard. "
    "A linter enforces the structural rules. The lexical dictionary stays unverified."
)


def test_the_mandated_sentence_lints_clean() -> None:
    errors, _ = lint_prose(_MANDATED)
    assert errors == []


def test_prompt_constants_publishes_the_reworded_sentence() -> None:
    text = _CONSTANTS.read_text()
    assert "structural rules enforced; lexical dictionary not verified" not in text
    assert "A linter enforces the structural rules." in text


def test_wrapped_list_item_counts_as_one_sentence() -> None:
    doc = "- The service reads a header value\n  and passes it to the client.\n"
    errors, _ = lint_prose(doc)
    assert errors == []


def test_wrapped_list_item_still_flags_a_real_violation() -> None:
    tail = " ".join(["word"] * 30)
    doc = f"- The service reads a header value\n  and {tail}.\n"
    errors, _ = lint_prose(doc)
    assert any("sentence over 25 words" in e for e in errors)


def test_an_unindented_paragraph_after_a_list_stays_separate() -> None:
    doc = "- One item here.\nA separate paragraph follows.\n"
    errors, warnings = lint_prose(doc)
    assert errors == []
    assert warnings == []
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_ste_lint_wrapped.py -q
```

Expected: `test_prompt_constants_publishes_the_reworded_sentence` fails on the old text. The wrapped-item tests fail because the continuation line becomes its own paragraph block.

- [ ] **Step 3: Commit RED**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_ste_lint_wrapped.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin the STE self-consistency rule" -m "REQ-12: assert the mandated sentence lints clean."
```

- [ ] **Step 4: Reword the constant**

Edit `references/prompt-constants.md:203-204`. Replace the parenthetical form with the three-sentence form above. Keep the surrounding sentence that tells the agent to put the statement in the document front matter.

- [ ] **Step 5: Fold a wrapped list item**

In `ste_lint.py`, rewrite `_prose_blocks` so a list item accumulates its indented continuation lines. Track the item separately from the paragraph buffer:

```python
    blocks: list[str] = []
    errors: list[str] = []
    in_fence = False
    current: list[str] = []
    item: list[str] = []

    def _flush() -> None:
        if item:
            blocks.append(" ".join(item))
            item.clear()
        if current:
            blocks.append(" ".join(current))
            current.clear()

    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith("```"):
            _flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            _flush()
            continue
        if stripped.startswith(("#", "%%")):
            _flush()
            continue
        if stripped.startswith("|"):
            _flush()
            if set(stripped) <= set("|-: "):
                continue  # separator row
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            blocks.extend(c for c in cells if c and len(c.split()) > 1)
            continue
        if stripped.startswith(("-", "*", "+")) or re.match(r"^\d+[.)]\s", stripped):
            _flush()
            item.append(stripped.lstrip("-*+ ").lstrip("0123456789.) "))
            continue
        # A wrapped list item continues on an indented line; an unindented line
        # starts a new paragraph.
        if item and ln[:1].isspace():
            item.append(stripped)
            continue
        _flush()
        current.append(stripped)
    _flush()
    if in_fence:
        errors.append(_UNBALANCED_FENCE)
    return blocks, errors
```

Invariant: after the loop, every non-exempt, non-blank line belongs to exactly one block, and a wrapped list item is one block.

Note that `_flush` empties the item before the paragraph, so block order follows document order.

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_ste_lint_wrapped.py tests/test_ste_lint.py tests/test_driver.py -q && uv run pytest -q
```

- [ ] **Step 7: Commit GREEN**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/ste_lint.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): make the STE rule self-consistent" -m "REQ-12: reword the mandated sentence, fold a wrapped list item."
```

---

## Task 4: REQ-14 — a Go CodeQL run stops tripping the fence

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/codeql.py:210-224`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py:255-268`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_codeql_go_build.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `skipped_reasons["codeql-go"] = "build-unfenceable"` in `run_prefilter`'s return value.

`codeql.py:211-214` builds the argv with no `--command` and no `--build-mode`, so Go autobuild compiles inside `--source-root={target}` and writes into the target working tree. `run.py:249` then raises `WorkingTreeFenceError`.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_codeql_go_build.py`:

```python
"""REQ-14: a Go CodeQL database builds without compiling in the target tree."""

from __future__ import annotations

import subprocess
from pathlib import Path

from sec_overlay.codeql import run_codeql

_CALLS: list[list[str]] = []


def _runner(argv, **kwargs):
    _CALLS.append(list(argv))
    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")


def _create_argv(target: Path, language: str, db: Path) -> list[str]:
    _CALLS.clear()
    try:
        run_codeql(str(target), language, str(db), runner=_runner)
    except Exception:
        pass
    return next(a for a in _CALLS if "create" in a)


def test_go_create_passes_build_mode_none(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "go", tmp_path / "db")
    assert "--build-mode=none" in argv


def test_python_create_does_not_pass_build_mode(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "python", tmp_path / "db")
    assert not any(a.startswith("--build-mode") for a in argv)


def test_go_create_still_names_the_source_root(tmp_path: Path) -> None:
    argv = _create_argv(tmp_path, "go", tmp_path / "db")
    assert f"--source-root={tmp_path}" in argv
```

Add to the same file a prefilter-level test that a Go plan whose CodeQL unit raises records the reason. Read `tests/test_prefilter.py` first and copy its existing plan fixture shape rather than inventing one.

```python
def test_go_build_failure_records_a_reason(...):
    """A CodeQL Go unit that cannot build records codeql-go: build-unfenceable."""
```

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_codeql_go_build.py -q
```

- [ ] **Step 3: Commit RED**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_codeql_go_build.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin the Go CodeQL build mode" -m "REQ-14: assert Go passes --build-mode=none."
```

- [ ] **Step 4: Add the Go build mode**

In `codeql.py`, build the create argv conditionally:

```python
    # Go autobuild compiles inside --source-root and writes into the target tree,
    # which trips run.py's working-tree fence. A no-build database avoids that at
    # the cost of weaker dataflow.
    build_mode = ["--build-mode=none"] if language == "go" else []
    create = runner(
        [
            "codeql", "database", "create", db_dir,
            f"--language={language}", f"--source-root={target}", "--overwrite",
            *build_mode,
        ],
        capture_output=True, text=True, check=False,
    )
```

Keep the existing non-zero-exit handling untouched.

- [ ] **Step 5: Record the fallback reason**

In `prefilter.py`, inside the result fold at `:255-268`, when a `codeql` unit reports an error and the plan's language is Go, record `skipped_reasons["codeql-go"] = "build-unfenceable"` alongside the existing `failed` entry. Read the surrounding lines first — the language lives on the unit, not on the fold loop, so the unit may need to carry it back.

The never-silent contract at the tail of `run_prefilter` iterates a fixed backend tuple. Do not add `codeql-go` to that tuple; it is a reason key, not a backend.

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_codeql_go_build.py tests/test_codeql.py tests/test_prefilter.py -q && uv run pytest -q
```

- [ ] **Step 7: Commit GREEN**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/codeql.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prefilter.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "fix(sec-overlay): build Go CodeQL without a build" -m "REQ-14: --build-mode=none keeps autobuild out of the target tree."
```

---

## Task 5: REQ-30 — the proof-by-execution lane

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prove.py`
- Create: `plugins/sec-overlay/skills/sec-overlay/agents/prove.md`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prove.py`
- Create: `docs/decisions/2026-08-31-prove-lane-execution.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py:138-139`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py:140`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/preflight.py`

**Interfaces:**
- Consumes: `report._optional_sections` from Task 1, `Workspace` from `workspace.py`.
- Produces: `prove.REPRODUCTION_RECEIPT`, `prove.is_reproduction_receipt(src) -> bool`, `prove.prove_enabled(ws) -> bool`, `prove.AUTO_CONFIRMABLE`, `prove.HARNESS_ONLY`, `prove.run_prove(ws, target) -> dict`.

Ruling B applies: `evidence.py` stays byte-identical. The receipt vocabulary for this lane lives in `prove.py` and `findings_gate.py` consults both.

Contract:

- The flag is `scan_options.prove_findings` in `kb/scan-profile.json`. Default off. Read it the way `artifact_consistency._enabled` reads `consistency_gate`.
- `AUTO_CONFIRMABLE = frozenset({"ssrf", "cmdi", "path-traversal", "deserialization", "expr-eval-rce"})`.
- `HARNESS_ONLY = frozenset({"sqli", "authz"})`. Those two attach a human-runnable harness and never promote.
- A proof with `scope: "entrypoint"` and a passing oracle auto-confirms. A proof with `scope: "slice"` attaches the harness, stays `needs-runtime`, and never promotes.
- Degradation strings: `prove: slice-unbuildable`, `prove: toolchain-absent`.
- Build and run out-of-tree only, under `ws.repro`. Never build in the target tree and never run the target's tests in the target tree.
- The SSRF oracle is a `http.server` loopback collector from the standard library. No new dependency.

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_prove.py` covering, one test each:

1. `prove_enabled` returns False when `scan-profile.json` is absent.
2. `prove_enabled` returns False when `scan_options.prove_findings` is absent (default off).
3. `prove_enabled` returns True only when the key is exactly `true`.
4. `run_prove` returns an empty result and writes no receipt when the flag is off.
5. `is_reproduction_receipt("reproduction")` is True and `is_reproduction_receipt("semgrep:x")` is False.
6. `evidence.is_tool_receipt("reproduction")` is False — the frozen partition is untouched.
7. A `scope: "entrypoint"` proof on an `ssrf` finding promotes it to `confirmed`.
8. A `scope: "slice"` proof on the same finding leaves `runtime_disposition` at `needs-runtime` and does not promote.
9. A `sqli` finding never promotes even with `scope: "entrypoint"`.
10. A missing toolchain records `prove: toolchain-absent` and promotes nothing.
11. `findings_gate` accepts a `confirmed` finding whose only evidence source is `reproduction`.
12. The loopback collector records a request and reports the observed path.
13. `phases.PHASE_TABLE` contains `prove` between `redteam` and `artifact-gate`, kind `agent`, prompt `prove.md`.
14. `Workspace(...).repro` resolves under the workspace and `ensure()` creates it.
15. `references/finding.schema.json` declares a `reproduction` object with `command`, `exit_code`, `oracle`, `oracle_result`, `toolchain`, `resolved_version`, `scope`.
16. `import sec_overlay.evidence` succeeds — the partition assert at `evidence.py:28` still holds.

Write each test to assert one behaviour. Use `tmp_path` workspaces. Never run a real target build in a test; inject the runner the way `test_codeql_go_build.py` does.

- [ ] **Step 2: Run the test and confirm it fails**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_prove.py -q
```

Expected: collection fails on the missing `sec_overlay.prove` module.

- [ ] **Step 3: Commit RED**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_prove.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "test(sec-overlay): pin the prove lane contract" -m "REQ-30: assert gating, scope soundness, and the receipt vocabulary."
```

- [ ] **Step 4: Write `prove.py`**

Module docstring states the reversal plainly: this module is the one place the harness executes target-derived code, it runs only under `scan_options.prove_findings`, and it builds and runs out-of-tree under `ws.repro`.

Keep each function under 100 lines and complexity under 8. Structured Google-style docstrings on every public function.

- [ ] **Step 5: Wire the phase**

In `phases.py`, add a `_prove_json(ws)` path helper beside the others at `:41-102`, and insert between `redteam` at `:138` and `artifact-gate` at `:139`:

```python
    PhaseSpec("prove", "agent", (_findings_dir,), (_prove_json,), prompt="prove.md"),
```

Do not change `artifact-gate`'s or `postflight`'s inputs.

Note: an agent phase's outputs gate completion. If the lane is off, the phase must still write its output file recording `enabled: false`, or the driver stalls. Confirm against `driver.py`'s dispatch path before choosing between an always-written output and an empty `outputs` tuple, and record which you chose and why.

- [ ] **Step 6: Add `ws.repro`, the gate change, the schema, and the prompt**

- `workspace.py`: add a `repro` property returning `self.root / "repro"`, and create it in `ensure()` beside the other directories.
- `findings_gate.py:140`: change the receipt test to accept a reproduction receipt as well.
- `references/finding.schema.json`: add the `reproduction` object property with the seven keys.
- `preflight.py`: report the prove-lane toolchains, so `preflight_report` gains a consumer.
- `agents/prove.md`: the prompt. State the escalation ladder, the per-class oracle table, the soundness guard, and the no-in-tree-build rule.

- [ ] **Step 7: Run the tests and confirm they pass**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay/helpers
uv run pytest tests/test_prove.py -q && uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

- [ ] **Step 8: Commit GREEN**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/prove.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/workspace.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/preflight.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/prove.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/finding.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/CHANGELOG.md \
        plugins/sec-overlay/.claude-plugin/plugin.json
git commit -m "feat(sec-overlay): add the opt-in prove lane" -m "REQ-30: proof by execution behind scan_options.prove_findings."
```

- [ ] **Step 9: Log the decision**

Create `docs/decisions/2026-08-31-prove-lane-execution.md` following the decision-log format: Decision, Context, Alternatives considered, Reasoning, Trade-offs accepted, Supersedes. Record that REQ-30 reverses the "the harness never executes the target" invariant behind an opt-in flag, and that the host-execution risk is stated, not mitigated — the lane runs on darwin with no sandbox.

Create `docs/decisions/INDEX.md` if absent and add a row.

This commit touches outside `plugins/`, so it also updates the root `CHANGELOG.md` and root `README.md`.

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
git add docs/decisions/2026-08-31-prove-lane-execution.md docs/decisions/INDEX.md \
        CHANGELOG.md README.md
git commit -m "docs: log the prove-lane execution decision" -m "REQ-30 reverses the no-execution invariant behind an opt-in flag."
```

---

## Group gate

Run from `plugins/sec-overlay/skills/sec-overlay/helpers/`:

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

All three must pass. Baseline at `cef855b`: 1724 tests passed, ruff clean, ty clean.

## Final verification gate

After the group gate passes, re-run sec-overlay against `/Users/christopher/Workspace/review_enforce/enforce`. Confirm three things:

1. The finding page carries the eight Part D elements.
2. The red-team directive lists the no-egress in-band oracle first.
3. The reproduction receipt records the OPA version.

If that path is absent, stop and ask for the target path. Do not skip the gate.
