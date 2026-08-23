# Absence Detection and Catalog-Gated Proof Tuples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect a dangerous construction that omits its safe option, and let a proof tuple cite a sink that lives inside a dependency instead of in first-party source.

**Architecture:** Two deterministic surfaces plus one prompt change. A new tracked semgrep pack `helpers/rules/absence/` holds `patterns` + `pattern-not` rules that fire on a construction without its safe option, and recon always includes that pack in `sast_plan.semgrep.rulesets`. `astgrep.py` gains a relational-rule path so an agent can express the same absence structurally through `ast-grep scan --inline-rules`. A new receipt source `dependency-catalog` joins `_MECHANICAL` and `TIER2_RECEIPTS`, so a dependency-internal sink can locate a finding without confirming it alone; `findings_gate` validates the receipt's id against the catalog.

**Tech Stack:** Python 3.11+, stdlib only. semgrep (`patterns` / `pattern-not`), ast-grep 0.45.0 (`scan --inline-rules`, relational `has` / `not`). pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-22-sec-overlay-recall-gaps-design.md` — features F1 (§4) and F4 (§7). Build order places these third, after the dependency-sink catalog and the policy-engine indicators.

**Prerequisite:** `docs/superpowers/plans/2026-08-22-sec-overlay-dependency-sinks-policy-indicators.md` is merged. Task 4 of this plan imports `sec_overlay.dependency_sinks.catalog_ids`.

## Global Constraints

Copied verbatim from spec §11. Every task's requirements include this section.

- **Stdlib only.** The `sec_overlay` core has no runtime dependency. Do not add one. Dev dependencies stay `pytest`, `ruff`, `ty`.
- **Test-first.** Tests ship in the same change as the code they cover.
- **Folder README in the same commit.** `scripts/hooks/pre-commit-check.sh` rejects a commit that stages a file in a folder with a tracked `README.md` without staging that `README.md`. Never bypass with `--no-verify`.
- **Preserve every agent prompt's hard rules** — model-family diversity, the tool-receipt safety contract, and the count-invariant verdict tables.
- **Bench regression.** Run `python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>` before and after each feature. A `locked` positive that stops being detected is a hard failure.
- **One plugin version bump per shipping change.** Bump `version` in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit.

**Rule for first-party semgrep rules (spec §3):** never place a first-party rule under `helpers/rules/semgrep/`. That directory is a gitignored, shallow clone of `semgrep/semgrep-rules` that `preflight.py` recreates with `git clone --depth 1`; a rule written there is deleted on the next preflight and is never committed. First-party rules live in `helpers/rules/absence/`, a tracked sibling directory next to the existing tracked `helpers/rules/smoke.yaml`.

**Version sequence.** This plan starts at `1.74.1` (the value the dependency-sink plan leaves behind) and each task states the version its commit sets. If the working tree's current version differs, apply the same increment type to the actual current value.

**Paths.** All paths are repo-relative. Python commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/go-policy-engines.yaml` | Go absence rules: an engine constructed without its capability-restricting option. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/python-templates.yaml` | Python absence rules: a template environment built without the sandboxed form. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/rules/README.md` | Records the tracked-versus-vendored split and the absence-rule idiom. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/astgrep.py` | Gains `build_rule` and `run_astgrep_rule` for relational (absence) rules. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_gaps.py` | `emit_semgrep_rule` learns to emit the absence shape. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py` | Adds the `dependency-catalog` receipt to `_MECHANICAL` and `TIER2_RECEIPTS`. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py` | Validates a `dependency-catalog:<id>` receipt against the catalog. |
| `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` | `EVIDENCE_VOCABULARY` gains the new receipt; `TOOL_TRUST` gains the absence-rule caution. |
| `plugins/sec-overlay/skills/sec-overlay/agents/classes/ssrf.md` | Proof-tuple element 2 admits an absence receipt; element 1 admits a catalog receipt. |
| `plugins/sec-overlay/skills/sec-overlay/agents/investigate.md` | Documents the relational ast-grep flags and the catalog receipt's limits. |
| `plugins/sec-overlay/skills/sec-overlay/agents/recon.md` | Always includes `rules/absence` in the semgrep rulesets. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/` | Fixture pair: one construction missing the safe option, one carrying it. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/bench/corpus_seed/absence.json` | Corpus entries pinning the positive and the negative. |

---

## Task 1: The tracked absence rule pack

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/go-policy-engines.yaml`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/python-templates.yaml`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/vulnerable.go`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/safe.go`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/render.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_absence_rules.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a rule pack path other tasks name as `rules/absence` (relative to the helpers directory, matching how `agents/recon.md:70` states ruleset paths), and rule ids of the form `sec-overlay.absence.<language>-<construction>-missing-<option>`.

- [ ] **Step 1: Write the fixture pair**

Create `helpers/fixtures/absence_repo/vulnerable.go`:

```go
package main

import (
	"context"

	"github.com/open-policy-agent/opa/rego"
)

// BuildEvaluator omits rego.Capabilities, so the policy may call http.send.
func BuildEvaluator(ctx context.Context, module string) (rego.PreparedEvalQuery, error) {
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
	)
	return r.PrepareForEval(ctx)
}
```

Create `helpers/fixtures/absence_repo/safe.go`:

```go
package main

import (
	"context"

	"github.com/open-policy-agent/opa/ast"
	"github.com/open-policy-agent/opa/rego"
)

// BuildSafeEvaluator removes http.send from the builtin set before evaluating.
func BuildSafeEvaluator(ctx context.Context, module string) (rego.PreparedEvalQuery, error) {
	caps := ast.CapabilitiesForThisVersion()
	kept := caps.Builtins[:0]
	for _, b := range caps.Builtins {
		if b.Name != "http.send" {
			kept = append(kept, b)
		}
	}
	caps.Builtins = kept
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
		rego.Capabilities(caps),
	)
	return r.PrepareForEval(ctx)
}
```

Create `helpers/fixtures/absence_repo/render.py`:

```python
"""Template rendering fixture: one unsandboxed environment, one sandboxed."""

from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment


def render_unsafe(template_text: str, data: dict) -> str:
    """Unsandboxed: attribute traversal from the template reaches Python objects."""
    return Environment().from_string(template_text).render(**data)


def render_safe(template_text: str, data: dict) -> str:
    """Sandboxed: the environment blocks unsafe attribute access."""
    return SandboxedEnvironment().from_string(template_text).render(**data)
```

- [ ] **Step 2: Write the failing test**

Create `helpers/tests/test_absence_rules.py`:

```python
"""The absence pack must fire on the missing-option site and stay silent on the safe one."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_HELPERS = Path(__file__).resolve().parents[1]
_PACK = _HELPERS / "rules" / "absence"
_FIXTURE = _HELPERS / "fixtures" / "absence_repo"

pytestmark = pytest.mark.skipif(shutil.which("semgrep") is None, reason="semgrep not installed")


def _scan() -> list[dict]:
    completed = subprocess.run(
        ["semgrep", "scan", "--config", str(_PACK), "--json", "--quiet",
         "--no-git-ignore", str(_FIXTURE)],
        capture_output=True, text=True, check=False,
    )
    return json.loads(completed.stdout)["results"]


def test_pack_flags_the_construction_that_omits_the_safe_option():
    hits = {(Path(r["path"]).name, r["check_id"].rsplit(".", 1)[-1]) for r in _scan()}
    assert ("vulnerable.go", "go-rego-new-missing-capabilities") in hits
    assert ("render.py", "python-jinja2-environment-missing-sandbox") in hits


def test_pack_stays_silent_on_the_construction_that_carries_the_safe_option():
    """The whole value of an absence rule is that the fixed site produces no finding."""
    flagged = {Path(r["path"]).name for r in _scan()}
    assert "safe.go" not in flagged


def test_every_absence_rule_declares_its_class_in_metadata():
    """The prefilter routes a semgrep hit by metadata.cls; a rule without one routes nowhere."""
    import re

    for path in sorted(_PACK.glob("*.yaml")):
        text = path.read_text()
        ids = re.findall(r"^\s*-?\s*id:\s*(\S+)", text, re.MULTILINE)
        assert ids, f"{path.name}: no rule ids"
        assert text.count("cls:") >= len(ids), f"{path.name}: a rule is missing metadata.cls"
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/test_absence_rules.py -q
```

Expected: FAIL — semgrep errors on the missing `rules/absence` config path. If semgrep is absent the module skips; install it before continuing, because this task's acceptance rests on a live scan.

- [ ] **Step 4: Write the Go pack**

Create `helpers/rules/absence/go-policy-engines.yaml`:

```yaml
# First-party absence rules. NEVER move these under rules/semgrep/ — that
# directory is a gitignored clone that preflight.py recreates, so a rule placed
# there is deleted and never committed.
#
# The idiom: `patterns` requires the dangerous construction, `pattern-not`
# requires that the safe option is absent from it. A rule with only the
# `pattern` half reports every call site, safe ones included.
rules:
  - id: go-rego-new-missing-capabilities
    languages: [go]
    severity: WARNING
    message: >-
      rego.New without rego.Capabilities. A policy evaluated here may call the
      http.send builtin, so caller-supplied policy text is an outbound-request
      sink inside OPA. Pass rego.Capabilities with http.send removed.
    metadata:
      cls: ssrf
      source: sec-overlay:absence
      safe_option: rego.Capabilities
    patterns:
      - pattern: rego.New(...)
      - pattern-not: rego.New(..., rego.Capabilities(...), ...)

  - id: go-cel-env-missing-declarations
    languages: [go]
    severity: WARNING
    message: >-
      cel.NewEnv with no declaration list. Every host function the environment
      inherits is reachable from caller-supplied expression text.
    metadata:
      cls: expr-eval-rce
      source: sec-overlay:absence
      safe_option: cel.Declarations
    patterns:
      - pattern: cel.NewEnv(...)
      - pattern-not: cel.NewEnv(..., cel.Declarations(...), ...)
      - pattern-not: cel.NewEnv(..., cel.Variable(...), ...)

  - id: go-lua-state-missing-skipopenlibs
    languages: [go]
    severity: WARNING
    message: >-
      lua.NewState without SkipOpenLibs. The default standard library exposes os
      and io functions to caller-supplied Lua.
    metadata:
      cls: expr-eval-rce
      source: sec-overlay:absence
      safe_option: SkipOpenLibs
    patterns:
      - pattern: lua.NewState(...)
      - pattern-not: |
          lua.NewState(&lua.Options{..., SkipOpenLibs: true, ...})
```

- [ ] **Step 5: Write the Python pack**

Create `helpers/rules/absence/python-templates.yaml`:

```yaml
# First-party absence rules. See go-policy-engines.yaml for the placement rule.
rules:
  - id: python-jinja2-environment-missing-sandbox
    languages: [python]
    severity: WARNING
    message: >-
      jinja2.Environment renders caller-supplied template text. Attribute
      traversal from a template reaches Python objects. Use
      jinja2.sandbox.SandboxedEnvironment.
    metadata:
      cls: ssti
      source: sec-overlay:absence
      safe_option: SandboxedEnvironment
    patterns:
      - pattern-either:
          - pattern: Environment(...).from_string(...)
          - pattern: jinja2.Environment(...).from_string(...)
      - pattern-not: SandboxedEnvironment(...).from_string(...)
      - pattern-not: jinja2.sandbox.SandboxedEnvironment(...).from_string(...)

  - id: python-requests-missing-timeout
    languages: [python]
    severity: WARNING
    message: >-
      requests call with no timeout. A slow or hostile endpoint holds the worker
      until the socket closes.
    metadata:
      cls: resource
      source: sec-overlay:absence
      safe_option: timeout
    patterns:
      - pattern-either:
          - pattern: requests.get(...)
          - pattern: requests.post(...)
          - pattern: requests.request(...)
      - pattern-not: requests.$M(..., timeout=$T, ...)
```

- [ ] **Step 6: Run the test to verify it passes**

```bash
uv run pytest tests/test_absence_rules.py -q
semgrep scan --config rules/absence --json --quiet --no-git-ignore fixtures/absence_repo | head -40
```

Expected: three tests pass. If a `pattern-not` fails to suppress `safe.go`, do not weaken the assertion — narrow the pattern until the safe site is silent. A rule that fires on the fixed code is worse than no rule, because it trains the reviewer to ignore the pack.

- [ ] **Step 7: Update the folder READMEs**

- `helpers/rules/README.md`: add an "Absence rules" section — the tracked-versus-vendored split, the reason a first-party rule must never live under `rules/semgrep/`, the `patterns` + `pattern-not` idiom, the required `metadata.cls`, and the rule that a pack change must keep the safe fixture silent.
- `helpers/tests/README.md`: add the `test_absence_rules.py` row naming the three guards and the `semgrep`-missing skip.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.75.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/go-policy-engines.yaml \
        plugins/sec-overlay/skills/sec-overlay/helpers/rules/absence/python-templates.yaml \
        plugins/sec-overlay/skills/sec-overlay/helpers/rules/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/vulnerable.go \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/safe.go \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/render.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_absence_rules.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add absence rule pack"
```

---

## Task 2: Always run the absence pack

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/recon.md:70`
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md:60-70`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/golden_scan_profile.json`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py`

**Interfaces:**
- Consumes: the `rules/absence` path from Task 1.
- Produces: the invariant that every scan profile the plugin ships or documents carries `rules/absence` in `semgrep.rulesets`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_contracts.py`:

```python
def test_recon_prompt_requires_the_absence_pack():
    """The vendored pack has no absence rule, so omitting rules/absence loses the class."""
    from pathlib import Path

    recon = (Path(__file__).resolve().parents[2] / "agents" / "recon.md").read_text()
    assert "rules/absence" in recon
    assert "always" in recon.lower().split("rules/absence")[0][-400:]


def test_golden_scan_profile_carries_the_absence_pack():
    import json
    from pathlib import Path

    profile = json.loads(
        (Path(__file__).resolve().parents[1] / "fixtures" / "golden_scan_profile.json").read_text()
    )
    assert any("rules/absence" in r for r in profile["semgrep"]["rulesets"])
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_contracts.py -q -k absence
```

Expected: both FAIL.

- [ ] **Step 3: Change the recon instruction**

In `agents/recon.md:70`, extend the `semgrep` bullet. Keep every existing sentence; append:

```markdown
     ALWAYS include "rules/absence" in rulesets, for every language, in addition to the
     vendored per-language dirs. The vendored clone has no missing-safe-option rule, so an
     omitted `rules/absence` silently loses every absence finding. `rules/absence` is tracked
     and always present; it needs no existence check.
```

- [ ] **Step 4: Change the playbook note**

In `SKILL.md:60-70`, after the existing sentence about the vendored clone, add:

```markdown
`helpers/rules/absence/` is a tracked, first-party pack that ships with the plugin. Its rules
pair a `pattern` for a dangerous construction with a `pattern-not` for its safe option, so a
call site that already passes the option produces no finding. Never write a first-party rule
under `helpers/rules/semgrep/`: `preflight.py` recreates that directory with
`git clone --depth 1`, which deletes anything you put there.
```

- [ ] **Step 5: Update the golden profile**

In `helpers/fixtures/golden_scan_profile.json`, add `rules/absence` to the `semgrep.rulesets` array, keeping the existing entry:

```json
{"semgrep": {"run": true, "rulesets": ["skills/sec-overlay/helpers/rules/smoke.yaml", "rules/absence"]}}
```

Read the file first and preserve every other key exactly as it is.

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contracts.py tests/test_prefilter.py -q
```

Expected: PASS. If a prefilter test asserts the exact golden-profile ruleset list, update that assertion to include the new entry.

- [ ] **Step 7: Update the folder READMEs**

- `agents/README.md`: note that recon always emits `rules/absence`.
- `helpers/tests/README.md`: add the two contract guards.
- `skills/sec-overlay/README.md`: mention the tracked absence pack in the architecture section.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.76.0
git add plugins/sec-overlay/skills/sec-overlay/agents/recon.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/golden_scan_profile.json \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): always run the absence pack"
```

---

## Task 3: Relational ast-grep rules

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/astgrep.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/investigate.md:50`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` (`TOOL_TRUST`, line 78)
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/rego-absence.yaml`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_astgrep.py`

**Interfaces:**
- Consumes: `parse_astgrep_json`, `_binary` from the existing module.
- Produces:
  - `build_rule(pattern: str, lang: str, *, not_pattern: str | None = None, inside: str | None = None, rule_id: str = "sec-overlay-adhoc") -> str` — returns inline-rule YAML text.
  - `run_astgrep_rule(yaml_text: str, root: str, *, runner=subprocess.run) -> list[dict]` — same `{file,line,text}` dicts as `run_astgrep`.
  - CLI: `run --not <pattern>` and `rule --file <path>`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_astgrep.py`:

```python
def test_build_rule_emits_a_relational_absence_rule():
    from sec_overlay.astgrep import build_rule

    text = build_rule("Environment($$$)", "python", not_pattern="SandboxedEnvironment($$$)")
    assert "language: python" in text
    assert "pattern: Environment($$$)" in text
    assert "not:" in text
    assert "SandboxedEnvironment($$$)" in text


def test_run_astgrep_rule_passes_the_rule_inline():
    from sec_overlay.astgrep import run_astgrep_rule

    seen = {}

    def fake(cmd, **kwargs):
        seen["cmd"] = cmd

        class R:
            stdout = "[]"

        return R()

    run_astgrep_rule("rule: {}", "/tmp/x", runner=fake)
    assert "scan" in seen["cmd"]
    assert "--inline-rules" in seen["cmd"]
    assert "rule: {}" in seen["cmd"]
    assert "--json" in seen["cmd"]


def test_run_astgrep_rule_returns_parsed_matches():
    from sec_overlay.astgrep import run_astgrep_rule

    payload = '[{"file":"a.py","range":{"start":{"line":4}},"text":"Environment()"}]'

    def fake(cmd, **kwargs):
        class R:
            stdout = payload

        return R()

    assert run_astgrep_rule("rule: {}", "/tmp/x", runner=fake) == [
        {"file": "a.py", "line": 5, "text": "Environment()"}
    ]


@pytest.mark.skipif(not astgrep_available(), reason="ast-grep not installed")
def test_relational_rule_finds_the_go_construction_that_omits_the_option(tmp_path):
    """Go needs kind/has anchoring: a bare `rego.New($ARGS)` pattern matches nothing."""
    from pathlib import Path

    from sec_overlay.astgrep import run_astgrep_rule

    rule = (
        Path(__file__).resolve().parents[1]
        / "fixtures" / "absence_repo" / "rego-absence.yaml"
    ).read_text()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "absence_repo"
    hits = {Path(m["file"]).name for m in run_astgrep_rule(rule, str(fixture))}
    assert "vulnerable.go" in hits
    assert "safe.go" not in hits
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_astgrep.py -q
```

Expected: `ImportError: cannot import name 'build_rule'`.

- [ ] **Step 3: Write the verified Go rule fixture**

Create `helpers/fixtures/absence_repo/rego-absence.yaml`. This exact shape is verified against ast-grep 0.45.0 (spec §4); a bare selector pattern such as `rego.New($ARGS)` matches nothing in Go, so the `kind` plus `has: {field: function, regex: ...}` anchoring is required:

```yaml
id: go-absence-rego-capabilities
language: go
rule:
  kind: call_expression
  all:
    - has:
        field: function
        regex: "^rego\\.New$"
    - not:
        has:
          stopBy: end
          kind: call_expression
          has:
            field: function
            regex: "^rego\\.Capabilities$"
severity: warning
message: rego.New without rego.Capabilities
```

- [ ] **Step 4: Implement the two functions**

Add to `helpers/sec_overlay/astgrep.py`, after `run_astgrep`:

```python
def build_rule(
    pattern: str,
    lang: str,
    *,
    not_pattern: str | None = None,
    inside: str | None = None,
    rule_id: str = "sec-overlay-adhoc",
) -> str:
    """Build inline-rule YAML for a relational ast-grep query.

    A plain pattern cannot express an absence. This wraps a pattern in the
    relational form so a caller can ask for "this construction, but NOT
    containing that option" — the structural half of the absence idiom.

    Args:
        pattern: The construction to match.
        lang: ast-grep language name (``go``, ``python``, ``typescript``, ...).
        not_pattern: When given, a match is kept only if this pattern is absent
            from anywhere inside it.
        inside: When given, a match is kept only if it sits inside this pattern.
        rule_id: Rule id, echoed in ast-grep's output.

    Returns:
        YAML text suitable for ``run_astgrep_rule``.

    Note:
        Go needs ``kind``/``has`` anchoring that this helper does not generate:
        a selector-call pattern such as ``rego.New($ARGS)`` matches nothing.
        For Go, write the rule by hand and pass it to ``run_astgrep_rule``
        directly, or through the ``rule --file`` CLI subcommand.
    """
    lines = [f"id: {rule_id}", f"language: {lang}", "rule:"]
    if not_pattern is None and inside is None:
        lines.append(f"  pattern: {pattern}")
    else:
        lines.append("  all:")
        lines.append(f"    - pattern: {pattern}")
        if not_pattern is not None:
            lines.append("    - not:")
            lines.append("        has:")
            lines.append("          stopBy: end")
            lines.append(f"          pattern: {not_pattern}")
        if inside is not None:
            lines.append("    - inside:")
            lines.append("        stopBy: end")
            lines.append(f"        pattern: {inside}")
    lines.append("severity: warning")
    lines.append(f"message: {rule_id}")
    return "\n".join(lines) + "\n"


def run_astgrep_rule(yaml_text: str, root: str, *, runner=subprocess.run) -> list[dict]:
    """Run a relational ast-grep rule and return its matches.

    Args:
        yaml_text: Inline-rule YAML, from ``build_rule`` or written by hand.
        root: File or directory to scan.
        runner: Injection point for tests.

    Returns:
        One ``{"file", "line", "text"}`` dict per match; empty on any parse or
        tool failure, so a broken rule never blocks the caller.
    """
    cmd = [_binary(), "scan", "--inline-rules", yaml_text, "--json", root]
    completed = runner(cmd, capture_output=True, text=True, check=False)
    text = (completed.stdout or "").strip()
    if not text:
        return []
    try:
        return parse_astgrep_json(json.loads(text))
    except json.JSONDecodeError:
        return []
```

- [ ] **Step 5: Extend the CLI**

In `main`, add `--not` to the `run` subparser and a new `rule` subparser:

```python
    r.add_argument("--not", dest="not_pattern", default=None,
                   help="Keep a match only when this pattern is absent from it.")
    q = sub.add_parser("rule", help="Run a hand-written inline rule file.")
    q.add_argument("--file", required=True)
    q.add_argument("--root", required=True)
```

and in the dispatch body:

```python
    if args.cmd == "run":
        if args.not_pattern:
            matches = run_astgrep_rule(
                build_rule(args.pattern, args.lang, not_pattern=args.not_pattern), args.root
            )
        else:
            matches = run_astgrep(args.pattern, args.lang, args.root)
        for m in matches:
            print(f"{m['file']}:{m['line']}\t{m['text']}")
        return 0
    if args.cmd == "rule":
        for m in run_astgrep_rule(Path(args.file).read_text(), args.root):
            print(f"{m['file']}:{m['line']}\t{m['text']}")
        return 0
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/test_astgrep.py -q
uv run python -m sec_overlay.astgrep rule --file fixtures/absence_repo/rego-absence.yaml --root fixtures/absence_repo
uv run ruff check sec_overlay/astgrep.py tests/test_astgrep.py
uv run ty check
```

Expected: tests pass; the CLI prints a `vulnerable.go` line and no `safe.go` line.

- [ ] **Step 7: Document the flags for the investigate agent**

At `agents/investigate.md:50`, below the existing `astgrep run` line, add:

```markdown
- Absence check (a construction that omits its safe option):
  `uv run python -m sec_overlay.astgrep run --pattern <p> --not <safe> --lang <l> --root {{TARGET}}`
- Go needs a hand-written rule: a selector-call pattern such as `rego.New($ARGS)` matches
  nothing. Write the `kind: call_expression` + `has: {field: function, regex: ...}` form to a
  file and run `uv run python -m sec_overlay.astgrep rule --file <f> --root {{TARGET}}`.
  Confirm the rule fires on a known-bad line before you trust its silence.
```

- [ ] **Step 8: Extend TOOL_TRUST**

In `references/prompt-constants.md`, inside the `## TOOL_TRUST` block, after the sentence that warns a too-rigid pattern silently matches nothing, add:

```markdown
An absence check inverts that risk: an over-rigid pattern reports every call site as unsafe,
including the ones already fixed. Before you cite an absence, run the rule against a site you
know carries the safe option and confirm it produces no match. A rule that fires on the fixed
code is not evidence.
```

- [ ] **Step 9: Run the doc-invariant suite**

```bash
uv run pytest tests/test_docs_invariants.py tests/test_contracts.py -q
```

Expected: PASS.

- [ ] **Step 10: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: add `build_rule` / `run_astgrep_rule` and the `run --not` / `rule --file` subcommands to the `astgrep.py` entry, with the Go-anchoring caveat.
- `references/README.md`: note the `TOOL_TRUST` absence caution.
- `agents/README.md`: note the investigate agent's absence-check tooling.
- `helpers/tests/README.md`: add the four `test_astgrep.py` guards.

- [ ] **Step 11: Commit**

```bash
# set plugin.json "version" to 1.77.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/astgrep.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/absence_repo/rego-absence.yaml \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_astgrep.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/investigate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add relational ast-grep rules"
```

---

## Task 4: The `dependency-catalog` receipt

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py:14-22`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md` (`EVIDENCE_VOCABULARY`, line 153)
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_evidence.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–3.
- Produces: `dependency-catalog` as a member of `_MECHANICAL` and `TIER2_RECEIPTS`. `receipt_tier("dependency-catalog:opa-rego-http-send") == 2`; `confirms_alone({"dependency-catalog:x"}) is False`.

**Why Tier 2, not Tier 1:** a catalog match proves the dependency is declared. It does not prove the sink is reached. Tier 2 means the receipt locates a finding and never confirms it alone — the same status `ripgrep` and `ast-grep` already hold.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_evidence.py`:

```python
def test_dependency_catalog_is_a_tier_two_receipt():
    from sec_overlay.evidence import TIER1_RECEIPTS, TIER2_RECEIPTS, is_tool_receipt, receipt_tier

    assert "dependency-catalog" in TIER2_RECEIPTS
    assert "dependency-catalog" not in TIER1_RECEIPTS
    assert is_tool_receipt("dependency-catalog:opa-rego-http-send")
    assert receipt_tier("dependency-catalog:opa-rego-http-send") == 2


def test_dependency_catalog_alone_cannot_confirm():
    """A manifest match proves the dependency is declared, not that the sink is reached."""
    from sec_overlay.evidence import confirms_alone

    assert confirms_alone({"dependency-catalog:opa-rego-http-send"}) is False
    assert confirms_alone({"dependency-catalog:opa-rego-http-send",
                           "semgrep:sec-overlay.absence.go-rego-new-missing-capabilities"}) is True
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_evidence.py -q -k dependency_catalog
```

Expected: FAIL on the `TIER2_RECEIPTS` membership assertion.

- [ ] **Step 3: Add the receipt to both sets**

In `helpers/sec_overlay/evidence.py`, add `"dependency-catalog"` to `_MECHANICAL` and to `TIER2_RECEIPTS`. The module-level assert that partitions `_MECHANICAL` into the two tiers forces both edits in one change; do not weaken that assert. Extend the Tier-2 comment to read:

```python
# Tier 2 locates a sink; it never confirms alone. `dependency-catalog` proves a
# dependency is declared and names the sink inside it, which is location, not reach.
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_evidence.py -q
```

Expected: the new tests pass. `test_docs_invariants.py::test_evidence_vocabulary_block_lists_all_values` now FAILS, because that test walks every value of `TIER1_RECEIPTS | TIER2_RECEIPTS | SHIPPING_STATUSES | RUNTIME_DISPOSITIONS` and asserts it appears inside the `## EVIDENCE_VOCABULARY` block. Step 5 closes it.

- [ ] **Step 5: Extend EVIDENCE_VOCABULARY**

In `references/prompt-constants.md`, inside the `## EVIDENCE_VOCABULARY` block (starting line 153), add the receipt to the Tier-2 list and add this paragraph:

```markdown
`dependency-catalog:<entry-id>` — Tier 2. The target declares a
`references/dependency-sinks.json` package, and the entry names a sink inside that
dependency's own code. Use it when no first-party line holds the sink (an OPA policy calling
`http.send`). It locates the sink; it never confirms a finding alone. `<entry-id>` must be a
real catalog id — the findings gate rejects an unknown id.
```

- [ ] **Step 6: Run the doc-invariant test to verify it passes**

```bash
uv run pytest tests/test_docs_invariants.py tests/test_evidence.py -q
```

Expected: PASS.

- [ ] **Step 7: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note the new receipt in the `evidence.py` entry and restate why it is Tier 2.
- `references/README.md`: note the `EVIDENCE_VOCABULARY` addition.
- `helpers/tests/README.md`: add the two evidence guards.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.78.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/evidence.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_evidence.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/prompt-constants.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add dependency-catalog receipt"
```

---

## Task 5: Gate the receipt id against the catalog

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py`

**Interfaces:**
- Consumes: `catalog_ids()` from the dependency-sink plan; the receipt from Task 4.
- Produces: `validate_findings` returns an error string for any `dependency-catalog:<id>` whose `<id>` is absent from the catalog. No new `Finding` field — the receipt travels in `evidence_sources`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_findings_gate.py`:

```python
def test_findings_gate_rejects_an_unknown_catalog_id(tmp_path):
    """A free-text catalog receipt would be an unfalsifiable claim dressed as a receipt."""
    from sec_overlay.findings_gate import validate_findings

    ws = _workspace_with_finding(
        tmp_path,
        evidence_sources=["dependency-catalog:not-a-real-entry"],
        status="candidate",
    )
    errors = validate_findings(ws)
    assert any("not-a-real-entry" in e for e in errors), errors


def test_findings_gate_accepts_a_known_catalog_id(tmp_path):
    from sec_overlay.findings_gate import validate_findings

    ws = _workspace_with_finding(
        tmp_path,
        evidence_sources=["dependency-catalog:opa-rego-http-send"],
        status="candidate",
    )
    assert not any("dependency-catalog" in e for e in validate_findings(ws))
```

Reuse the file's existing workspace-and-finding helper rather than the placeholder name above; read the top of `test_findings_gate.py` and match its fixture style, keeping the two assertions as written.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_findings_gate.py -q -k catalog
```

Expected: the reject test FAILS — the gate currently accepts any namespaced source.

- [ ] **Step 3: Add the check**

In `helpers/sec_overlay/findings_gate.py`, import the catalog ids at module level:

```python
from sec_overlay.dependency_sinks import catalog_ids
```

Inside `validate_findings`, in the loop that already walks each finding's `evidence_sources` for receipt tiers, add:

```python
        for source in f.evidence_sources:
            if not source.startswith("dependency-catalog:"):
                continue
            entry_id = source.split(":", 1)[1]
            if entry_id not in _CATALOG_IDS:
                errors.append(
                    f"{f.id}: dependency-catalog receipt names unknown catalog entry "
                    f"{entry_id!r}; add the entry to references/dependency-sinks.json or "
                    f"cite a first-party sink line"
                )
```

Resolve the catalog once at module level so a large findings file does not re-read it per finding:

```python
_CATALOG_IDS = catalog_ids()
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_findings_gate.py -q
uv run ruff check sec_overlay/findings_gate.py tests/test_findings_gate.py
uv run ty check
```

Expected: PASS.

- [ ] **Step 5: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note the catalog-id check in the `findings_gate.py` entry.
- `helpers/tests/README.md`: add the two gate guards.

- [ ] **Step 6: Commit**

```bash
# set plugin.json "version" to 1.78.1
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_findings_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "fix(sec-overlay): reject unknown catalog receipt ids"
```

---

## Task 6: Proof tuples admit the two new receipts

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/classes/ssrf.md:29-36`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/investigate.md:124-131`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py`

**Interfaces:**
- Consumes: the receipt namespaces from Tasks 1, 3, and 4.
- Produces: the invariant that every class file naming a proof-tuple element names which receipt satisfies it.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_contracts.py`:

```python
def test_ssrf_proof_tuple_admits_the_dependency_internal_sink():
    """Without this, an OPA http.send finding can never leave `raw`: there is no
    first-party line to cite for element 1."""
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "classes" / "ssrf.md").read_text()
    assert "dependency-catalog" in txt
    assert "sec-overlay.absence" in txt


def test_investigate_tool_grounding_names_the_two_new_receipts():
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "investigate.md").read_text()
    assert "dependency-catalog" in txt
    assert "never confirms alone" in txt or "cannot confirm alone" in txt
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_contracts.py -q -k "proof_tuple or tool_grounding"
```

Expected: both FAIL.

- [ ] **Step 3: Extend the SSRF proof tuple**

In `agents/classes/ssrf.md`, in the "## Proof tuple (required evidence)" section, extend elements 1 and 2. Keep the three-element structure and the existing wording; add to element 1:

```markdown
   When the request is built inside a dependency rather than in first-party source, cite the
   `references/dependency-sinks.json` entry with a `dependency-catalog:<entry-id>` receipt plus
   the `file:line` where the caller hands text to that dependency. The OPA reference case: the
   `rego.New` construction line is the citation, `dependency-catalog:opa-rego-http-send` names
   the `http.send` sink. This receipt is Tier 2 — it locates the sink and never confirms alone,
   so element 2 or element 3 must carry a Tier-1 receipt.
```

and to element 2:

```markdown
   An absence receipt satisfies this element:
   `semgrep:sec-overlay.absence.<rule-id>` from `helpers/rules/absence/`, which fires only on a
   construction that omits its safe option. State which option is absent by name
   (`rego.Capabilities`, `SandboxedEnvironment`, a `timeout` argument). "No guard found" with no
   named option is not element 2.
```

- [ ] **Step 4: Extend the investigate tool-grounding rule**

In `agents/investigate.md:124-131`, after the existing sentence that `llm-claimed:<what>` cannot satisfy a tool-grounded gate, add:

```markdown
`dependency-catalog:<entry-id>` is a mechanical receipt but a Tier-2 one: it satisfies the
"where is the sink" half of a gate and never confirms alone. A finding whose only mechanical
receipt is a catalog match stays `candidate`. Pair it with a Tier-1 receipt — a
`semgrep:sec-overlay.absence.*` hit on the missing safe option, or a codeql dataflow path to
the construction.
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contracts.py tests/test_docs_invariants.py -q
```

Expected: PASS.

- [ ] **Step 6: Update the folder READMEs**

- `agents/classes/README.md`: note that the `ssrf.md` proof tuple admits a catalog receipt for element 1 and an absence receipt for element 2.
- `agents/README.md`: note the Tier-2 catalog rule in the investigate gate-ladder description.
- `helpers/tests/README.md`: add the two contract guards.

- [ ] **Step 7: Commit**

```bash
# set plugin.json "version" to 1.79.0
git add plugins/sec-overlay/skills/sec-overlay/agents/classes/ssrf.md \
        plugins/sec-overlay/skills/sec-overlay/agents/classes/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/investigate.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): admit catalog and absence receipts"
```

---

## Task 7: Codify absences as rules, and pin the pair in the bench corpus

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_gaps.py`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/bench/corpus_seed/absence.json`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_gaps.py`

**Interfaces:**
- Consumes: the absence rule ids from Task 1; the receipt from Task 4.
- Produces: `emit_semgrep_rule(f, *, safe_option: str | None = None) -> dict` — with `safe_option`, the emitted rule carries a `pattern-not` and its id sits under `sec-overlay.absence.`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_rule_gaps.py`:

```python
def test_emit_semgrep_rule_emits_the_absence_shape_when_a_safe_option_is_named():
    """Codifying a finding as a presence-only rule reports every call site, so the
    next run drowns in noise on already-fixed code."""
    from sec_overlay.rule_gaps import emit_semgrep_rule

    f = _finding(cls="ssrf", file="policy.go", line=12, snippet="rego.New(")
    rule = emit_semgrep_rule(f, safe_option="rego.Capabilities")["rules"][0]
    assert rule["id"].startswith("sec-overlay.absence.")
    patterns = rule["patterns"]
    assert any("pattern-not" in p for p in patterns)
    assert any("rego.Capabilities" in str(p) for p in patterns)
    assert rule["metadata"]["safe_option"] == "rego.Capabilities"


def test_emit_semgrep_rule_without_a_safe_option_is_unchanged():
    from sec_overlay.rule_gaps import emit_semgrep_rule

    f = _finding(cls="sqli", file="db.py", line=4, snippet="cur.execute(")
    rule = emit_semgrep_rule(f)["rules"][0]
    assert rule["id"].startswith("sec-overlay.sqli.")
    assert not any("pattern-not" in p for p in rule["patterns"])
```

Use the file's existing finding-builder helper in place of `_finding` and keep the assertions as written.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_rule_gaps.py -q -k absence
```

Expected: `TypeError: emit_semgrep_rule() got an unexpected keyword argument 'safe_option'`.

- [ ] **Step 3: Implement the absence shape**

In `helpers/sec_overlay/rule_gaps.py`, change the signature to:

```python
def emit_semgrep_rule(f, *, safe_option: str | None = None) -> dict:
```

Extend the docstring with:

```
    Args:
        f: The finding to codify.
        safe_option: When given, the emitted rule is an absence rule: it fires only
            on a construction that omits this option. Codifying a missing-safe-option
            finding as a presence-only rule would report every call site, including
            the ones already fixed.
```

Before the return, build the two variable parts:

```python
    if safe_option:
        rule_id = f"sec-overlay.absence.{f.cls}.{fp}"
        patterns = [{"pattern": pattern}, {"pattern-not": f"{pattern[:-1]}, {safe_option}(...))"}]
    else:
        rule_id = f"sec-overlay.{f.cls}.{fp}"
        patterns = [{"pattern": pattern}]
```

Use `rule_id` and `patterns` in the returned dict, and add `"safe_option": safe_option` to `metadata` when `safe_option` is set. Read the existing `pattern` construction first: if it does not end in `)`, build the `pattern-not` from the same source text rather than slicing, and keep the slice only when the trailing `)` is guaranteed.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_rule_gaps.py -q
uv run ruff check sec_overlay/rule_gaps.py tests/test_rule_gaps.py
uv run ty check
```

Expected: PASS.

- [ ] **Step 5: Pin the pair in the bench corpus**

Create `helpers/bench/corpus_seed/absence.json`:

```json
[
  {
    "finding_id": "absence-rego-capabilities-positive",
    "kind": "positive",
    "source": "synthetic",
    "cls": "ssrf",
    "local_path": "fixtures/absence_repo",
    "file": "vulnerable.go",
    "line": 11,
    "description": "rego.New with no rego.Capabilities; a policy may call http.send.",
    "lifecycle": "locked"
  },
  {
    "finding_id": "absence-rego-capabilities-negative",
    "kind": "negative",
    "source": "synthetic",
    "cls": "ssrf",
    "local_path": "fixtures/absence_repo",
    "file": "safe.go",
    "line": 21,
    "description": "rego.New with rego.Capabilities and http.send removed; must not be reported."
  },
  {
    "finding_id": "absence-jinja2-sandbox-positive",
    "kind": "positive",
    "source": "synthetic",
    "cls": "ssti",
    "local_path": "fixtures/absence_repo",
    "file": "render.py",
    "line": 9,
    "description": "jinja2.Environment().from_string on caller text with no sandbox.",
    "lifecycle": "locked"
  }
]
```

Set each `line` to the actual line of the construction in the fixture files from Task 1; read the files and correct the numbers rather than trusting the values above.

- [ ] **Step 6: Run the bench regression**

```bash
uv run python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench-f1 --workspaces /tmp/bench-f1-ws
```

Expected: the two `locked` positives are detected and the negative is not reported. A `locked` positive that goes undetected is a hard failure — fix the rule, never the corpus entry.

- [ ] **Step 7: Run the full suite**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Expected: only the two documented environment-only failures remain.

- [ ] **Step 8: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note the `safe_option` keyword on `emit_semgrep_rule`.
- `helpers/bench/corpus_seed/README.md`: add `absence.json` and note that its two positives are `locked`.
- `helpers/bench/README.md`: note the absence-rule regression criterion.
- `helpers/tests/README.md`: add the two `test_rule_gaps.py` guards.

- [ ] **Step 9: Commit**

```bash
# set plugin.json "version" to 1.80.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/rule_gaps.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/corpus_seed/absence.json \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/corpus_seed/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/bench/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_gaps.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): codify absence findings as rules"
```

Note: `helpers/bench/corpus_seed/` is gitignored per the skill `CLAUDE.md`. Check `git check-ignore -v helpers/bench/corpus_seed/absence.json` before staging. If it is ignored, keep the file local, record that in the commit body, and add the entries to `helpers/bench/README.md` as the reproducible instruction instead — do not force-add against the ignore rule.

---

## Acceptance criteria (from the spec)

**F1 (spec §4):**
1. `semgrep scan --config rules/absence fixtures/absence_repo` reports `vulnerable.go` and `render.py` and does not report `safe.go`.
2. Every rule in the pack carries `metadata.cls`, so the prefilter routes its hit.
3. `sec_overlay.astgrep rule --file fixtures/absence_repo/rego-absence.yaml --root fixtures/absence_repo` reports `vulnerable.go` only. This proves the Go anchoring works; a bare selector pattern matches nothing.
4. `agents/recon.md` requires `rules/absence` in every scan profile — pinned by `test_contracts.py`.
5. `emit_semgrep_rule(f, safe_option=...)` emits a `pattern-not` half.

**F4 (spec §7):**
6. `receipt_tier("dependency-catalog:<id>") == 2` and `confirms_alone` on that source alone is `False`.
7. `validate_findings` rejects a `dependency-catalog:` receipt whose id is not in the catalog.
8. `references/prompt-constants.md`'s `EVIDENCE_VOCABULARY` block lists the receipt — pinned by the existing `test_evidence_vocabulary_block_lists_all_values`.
9. `agents/classes/ssrf.md` element 1 admits the catalog receipt and element 2 admits an absence receipt.

**Trade-offs accepted:**
- An absence rule is noisier than a presence rule at the same recall. A construction whose safe option is passed through a helper, a variable, or a builder chain still fires, because the `pattern-not` sees only the call site. The pack keeps severity at `WARNING` for that reason, and the class prompt requires the reviewer to name the absent option.
- `build_rule` does not generate Go's `kind`/`has` anchoring. Go absence checks need a hand-written rule file. Generating correct Go anchoring for any pattern is a larger job than this feature needs.
- The Tier-2 receipt means a dependency-internal sink cannot reach `confirmed` on the catalog alone. That is the point: precision is the plugin's first property, and a manifest match is not reach.

---

## Pull request

```bash
git push -u origin feat/absence-detection
gh pr create --title "feat(sec-overlay): absence detection and catalog-gated proof tuples" --body "<summary>"
```

Wait for CodeRabbit's walkthrough comment before merging (`gh pr view <n> --comments`).
