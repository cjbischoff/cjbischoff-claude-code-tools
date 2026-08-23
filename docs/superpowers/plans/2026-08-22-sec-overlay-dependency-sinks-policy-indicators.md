# Dependency-Sink Catalog and Policy-Engine Indicators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach recon that a declared dependency can itself contain the sink, by shipping a JSON dependency-sink catalog that routes attack classes from manifest matches, and by naming server-side policy and rule engines as indicators of the `expr-eval-rce` class.

**Architecture:** A new stdlib-only module `dependency_sinks.py` loads `references/dependency-sinks.json`, walks the target for dependency manifests, and reports the attack classes of every matched entry. `partition.reconcile_plan` gains an optional `target_root` keyword and merges those classes into the agent list, so a matched catalog entry cannot be dropped by an incomplete `attack_surface`. Feature F5 is documentation and prompt work: `references/attack-classes.md` gains policy-engine indicators, a new `agents/classes/expr-eval-rce.md` gives the class its proof tuple, and a test pins the catalog against the indicator table so the two never drift.

**Tech Stack:** Python 3.11+, stdlib only (`json`, `dataclasses`, `pathlib`, `argparse`), pytest, ruff, ty. Markdown prompt files.

**Spec:** `docs/superpowers/specs/2026-08-22-sec-overlay-recall-gaps-design.md` — features F3 (§6) and F5 (§8). Build order places F3 first and F5 second.

## Global Constraints

Copied verbatim from spec §11. Every task's requirements include this section.

- **Stdlib only.** The `sec_overlay` core has no runtime dependency. Do not add one. Dev dependencies stay `pytest`, `ruff`, `ty`.
- **Test-first.** Tests ship in the same change as the code they cover.
- **Folder README in the same commit.** `scripts/hooks/pre-commit-check.sh` rejects a commit that stages a file in a folder with a tracked `README.md` without staging that `README.md`. Never bypass with `--no-verify`.
- **Preserve every agent prompt's hard rules** — model-family diversity, the tool-receipt safety contract, and the count-invariant verdict tables.
- **Bench regression.** Run `python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>` before and after each feature. A `locked` positive that stops being detected is a hard failure.
- **One plugin version bump per shipping change.** Bump `version` in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit.

**Rule for first-party semgrep rules (spec §3):** never place a first-party rule under `helpers/rules/semgrep/`. That directory is a gitignored, shallow clone of `semgrep/semgrep-rules` that `preflight.py` recreates.

**Version sequence.** The plugin is at `1.69.15` before Task 1. Each task below states the version its commit must set. The sequence assumes the three recall-gap plans run in order (this plan, then absence-rules, then route-census). If the working tree's current version differs, apply the same increment type (`feat` bumps minor, every other type bumps patch) to the actual current value.

**Paths.** All paths are repo-relative. The plugin root is `plugins/sec-overlay/`. Python commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `plugins/sec-overlay/skills/sec-overlay/references/dependency-sinks.json` | The catalog. One entry per dependency that contains a sink inside its own code. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py` | Loads and validates the catalog, matches manifests under a target root, reports matched attack classes. CLI-callable. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/partition.py` | `reconcile_plan` gains `target_root` and merges catalog classes. |
| `plugins/sec-overlay/skills/sec-overlay/agents/classes/expr-eval-rce.md` | Class prompt extension: proof tuple and class boundary for expression and policy-engine escape. |
| `plugins/sec-overlay/skills/sec-overlay/references/attack-classes.md` | Indicator table row for `expr-eval-rce` plus recon selection guidance for policy engines. |
| `plugins/sec-overlay/skills/sec-overlay/references/DETECTION_COVERAGE.md` | Records that a dependency-internal sink is out of reach for the vendored rulesets, and that the catalog closes the routing half of that gap. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py` | Unit tests for the loader, the validator, and manifest matching. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_partition.py` | Extended with the catalog-routing test. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py` | Extended with the catalog-to-indicator drift guard. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/dep_sink_repo/` | Fixture target: a `go.mod` that declares OPA and a Go file that builds a Rego evaluator. |

---

## Task 1: Catalog file and loader

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/references/dependency-sinks.json`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `SinkEntry` frozen dataclass with fields `id: str`, `package: str`, `ecosystem: str`, `manifests: tuple[str, ...]`, `cls: str`, `sink: str`, `why: str`, `safe_option: str`, `indicators: tuple[str, ...]`.
  - `CATALOG_PATH: Path`
  - `load_catalog(path: Path = CATALOG_PATH) -> list[SinkEntry]`
  - `catalog_ids(path: Path = CATALOG_PATH) -> frozenset[str]`
  - `validate_catalog(raw: dict) -> list[str]`

- [ ] **Step 1: Write the failing test**

Create `helpers/tests/test_dependency_sinks.py`:

```python
from __future__ import annotations

import json

import pytest

from sec_overlay.dependency_sinks import (
    CATALOG_PATH,
    SinkEntry,
    catalog_ids,
    load_catalog,
    validate_catalog,
)


def test_shipped_catalog_loads_and_validates():
    raw = json.loads(CATALOG_PATH.read_text())
    assert validate_catalog(raw) == []
    entries = load_catalog()
    assert entries, "shipped catalog must not be empty"
    assert all(isinstance(e, SinkEntry) for e in entries)


def test_shipped_catalog_covers_the_opa_rego_case():
    """The gap this feature closes: OPA's own code holds the outbound-request sink."""
    entry = next(e for e in load_catalog() if e.id == "opa-rego-http-send")
    assert entry.cls == "ssrf"
    assert entry.package == "github.com/open-policy-agent/opa"
    assert "go.mod" in entry.manifests
    assert entry.sink == "http.send"
    assert entry.safe_option


def test_catalog_ids_are_unique():
    ids = [e.id for e in load_catalog()]
    assert len(ids) == len(set(ids))
    assert catalog_ids() == frozenset(ids)


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ({"version": 1}, "entries"),
        ({"version": 1, "entries": [{"id": "x"}]}, "package"),
        (
            {
                "version": 1,
                "entries": [
                    {
                        "id": "dup",
                        "package": "p",
                        "ecosystem": "go",
                        "manifests": ["go.mod"],
                        "cls": "ssrf",
                        "sink": "s",
                        "why": "w",
                        "safe_option": "o",
                        "indicators": ["i"],
                    }
                ]
                * 2,
            },
            "duplicate",
        ),
    ],
)
def test_validate_catalog_reports_defects(raw, fragment):
    errors = validate_catalog(raw)
    assert any(fragment in e for e in errors), errors
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `plugins/sec-overlay/skills/sec-overlay/helpers`:

```bash
uv run pytest tests/test_dependency_sinks.py -q
```

Expected: collection error, `ModuleNotFoundError: No module named 'sec_overlay.dependency_sinks'`.

- [ ] **Step 3: Write the catalog**

Create `references/dependency-sinks.json`:

```json
{
  "version": 1,
  "entries": [
    {
      "id": "opa-rego-http-send",
      "package": "github.com/open-policy-agent/opa",
      "ecosystem": "go",
      "manifests": ["go.mod", "go.sum"],
      "cls": "ssrf",
      "sink": "http.send",
      "why": "A Rego policy can call the builtin http.send, so policy text reaching an OPA evaluator is an outbound-request sink inside the dependency.",
      "safe_option": "rego.Capabilities with http.send removed from the builtin set",
      "indicators": ["rego.New", "rego.Module", "http.send", "rego.Capabilities"]
    },
    {
      "id": "cel-go-expression-eval",
      "package": "github.com/google/cel-go",
      "ecosystem": "go",
      "manifests": ["go.mod", "go.sum"],
      "cls": "expr-eval-rce",
      "sink": "Program.Eval",
      "why": "CEL evaluates caller-supplied expression text against a host environment, so the environment's exposed functions become reachable sinks.",
      "safe_option": "cel.NewEnv restricted to a reviewed declaration list, with no host function that performs IO",
      "indicators": ["cel.NewEnv", "cel.Compile", "Program.Eval"]
    },
    {
      "id": "starlark-go-exec",
      "package": "go.starlark.net",
      "ecosystem": "go",
      "manifests": ["go.mod", "go.sum"],
      "cls": "expr-eval-rce",
      "sink": "starlark.ExecFile",
      "why": "Starlark executes caller-supplied script text; every predeclared builtin the host installs is reachable from that script.",
      "safe_option": "A predeclared StringDict that exposes no IO builtin, with load() disabled",
      "indicators": ["starlark.ExecFile", "starlark.Thread", "starlark.StringDict"]
    },
    {
      "id": "goja-javascript-vm",
      "package": "github.com/dop251/goja",
      "ecosystem": "go",
      "manifests": ["go.mod", "go.sum"],
      "cls": "expr-eval-rce",
      "sink": "Runtime.RunString",
      "why": "goja runs caller-supplied JavaScript in-process; any Go value set on the runtime is callable from that script.",
      "safe_option": "A runtime with no Set() of a host object, plus an interrupt deadline",
      "indicators": ["goja.New", "Runtime.RunString", "vm.Set"]
    },
    {
      "id": "gopher-lua-script",
      "package": "github.com/yuin/gopher-lua",
      "ecosystem": "go",
      "manifests": ["go.mod", "go.sum"],
      "cls": "expr-eval-rce",
      "sink": "LState.DoString",
      "why": "gopher-lua executes caller-supplied Lua; the default standard library exposes os and io functions.",
      "safe_option": "lua.NewState with SkipOpenLibs and an explicit allowlist of opened libraries",
      "indicators": ["lua.NewState", "DoString", "SkipOpenLibs"]
    },
    {
      "id": "jinja2-sandbox-escape",
      "package": "jinja2",
      "ecosystem": "python",
      "manifests": ["requirements.txt", "pyproject.toml", "poetry.lock", "Pipfile"],
      "cls": "ssti",
      "sink": "Environment.from_string",
      "why": "Jinja2 compiles caller-supplied template text; attribute traversal from a template reaches Python objects unless the sandboxed environment is used.",
      "safe_option": "jinja2.sandbox.SandboxedEnvironment instead of jinja2.Environment",
      "indicators": ["from_string", "Template(", "SandboxedEnvironment"]
    }
  ]
}
```

- [ ] **Step 4: Write the loader**

Create `helpers/sec_overlay/dependency_sinks.py`:

```python
"""Dependency-sink catalog: dependencies whose OWN code holds the sink.

The prefilter and the investigate agents look for a sink in first-party source.
When the sink lives inside a declared dependency (an OPA policy calling
``http.send``, a CEL program calling a host function), no first-party pattern
matches and recon can omit the whole attack class. This catalog names those
dependencies so a manifest match routes the class regardless.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "references" / "dependency-sinks.json"

_REQUIRED = ("id", "package", "ecosystem", "manifests", "cls", "sink", "why",
             "safe_option", "indicators")


@dataclass(frozen=True)
class SinkEntry:
    """One dependency that contains a sink inside its own code.

    Attributes:
        id: Stable catalog id, used as the ``dependency-catalog:<id>`` receipt suffix.
        package: Manifest-visible package name matched as a substring.
        ecosystem: Package ecosystem (``go``, ``python``, ``node``, ...).
        manifests: Manifest filenames that can declare this package.
        cls: Attack class this dependency routes.
        sink: The sink inside the dependency, named for the proof tuple.
        why: One sentence explaining why the dependency is the sink.
        safe_option: The option that removes or narrows the sink.
        indicators: Source tokens that show the dependency is actually used.
    """

    id: str
    package: str
    ecosystem: str
    manifests: tuple[str, ...]
    cls: str
    sink: str
    why: str
    safe_option: str
    indicators: tuple[str, ...]


def validate_catalog(raw: dict) -> list[str]:
    """Return human-readable defects in a parsed catalog document.

    Args:
        raw: Parsed catalog JSON.

    Returns:
        One message per defect; empty when the document is valid.
    """
    errors: list[str] = []
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        return ["entries: must be a non-empty list"]
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"entries[{i}]: must be an object")
            continue
        for key in _REQUIRED:
            if not e.get(key):
                errors.append(f"entries[{i}]: missing or empty {key}")
        eid = e.get("id")
        if isinstance(eid, str) and eid in seen:
            errors.append(f"entries[{i}]: duplicate id {eid}")
        if isinstance(eid, str):
            seen.add(eid)
    return errors


def load_catalog(path: Path = CATALOG_PATH) -> list[SinkEntry]:
    """Load and validate the catalog.

    Args:
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        One ``SinkEntry`` per catalog entry.

    Raises:
        ValueError: The document is invalid; every defect is listed.
    """
    raw = json.loads(path.read_text())
    errors = validate_catalog(raw)
    if errors:
        raise ValueError(f"invalid dependency-sink catalog {path}: " + "; ".join(errors))
    return [
        SinkEntry(
            id=e["id"],
            package=e["package"],
            ecosystem=e["ecosystem"],
            manifests=tuple(e["manifests"]),
            cls=e["cls"],
            sink=e["sink"],
            why=e["why"],
            safe_option=e["safe_option"],
            indicators=tuple(e["indicators"]),
        )
        for e in raw["entries"]
    ]


def catalog_ids(path: Path = CATALOG_PATH) -> frozenset[str]:
    """Return every catalog id, for receipt-id validation in the findings gate."""
    return frozenset(e.id for e in load_catalog(path))


def main(argv: list[str] | None = None) -> int:
    """CLI: print the catalog, one ``id<TAB>cls<TAB>package`` line per entry."""
    parser = argparse.ArgumentParser(prog="sec-overlay-dependency-sinks")
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    args = parser.parse_args(argv)
    for e in load_catalog(Path(args.catalog)):
        print(f"{e.id}\t{e.cls}\t{e.package}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run pytest tests/test_dependency_sinks.py -q
uv run ruff check sec_overlay/dependency_sinks.py tests/test_dependency_sinks.py
uv run ty check
```

Expected: tests pass, no lint findings, no type errors.

- [ ] **Step 6: Update the folder READMEs**

- In `references/README.md`, add `dependency-sinks.json` to the reference-file table: "Dependencies whose own code holds the sink; consumed by `sec_overlay.dependency_sinks` and by recon routing."
- In `helpers/sec_overlay/README.md`, add `dependency_sinks.py` to the module inventory and to the CLI-callable list.
- In `helpers/tests/README.md`, add a `test_dependency_sinks.py` row describing the four guards (shipped catalog validates, the OPA entry exists, ids are unique, the validator reports defects).

- [ ] **Step 7: Commit**

```bash
cd /Users/christopher/Documents/Development/_me/cjbischoff-claude-code-tools
# set plugins/sec-overlay/.claude-plugin/plugin.json "version" to 1.70.0
git add plugins/sec-overlay/skills/sec-overlay/references/dependency-sinks.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add dependency-sink catalog loader"
```

Add the `CHANGELOG.md` entry under `## Unreleased` → `### Added` before committing: "Dependency-sink catalog (`references/dependency-sinks.json`) and its loader, naming dependencies whose own code holds the sink."

---

## Task 2: Manifest matching and the CLI

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/dep_sink_repo/go.mod`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/dep_sink_repo/policy.go`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py`

**Interfaces:**
- Consumes: `SinkEntry`, `load_catalog` from Task 1.
- Produces:
  - `match_manifests(root: str | Path, *, path: Path = CATALOG_PATH) -> list[SinkEntry]`
  - `matched_classes(root: str | Path, *, path: Path = CATALOG_PATH) -> list[str]` — sorted, deduplicated attack classes.
  - CLI subcommand `match --root <dir>`.

- [ ] **Step 1: Write the fixture target**

Create `helpers/fixtures/dep_sink_repo/go.mod`:

```
module example.com/dep-sink-fixture

go 1.22

require (
	github.com/open-policy-agent/opa v0.68.0
)
```

Create `helpers/fixtures/dep_sink_repo/policy.go`:

```go
package main

import (
	"context"

	"github.com/open-policy-agent/opa/rego"
)

// EvalPolicy builds an evaluator from caller-supplied policy text. No
// rego.Capabilities call, so the policy may call the http.send builtin.
func EvalPolicy(ctx context.Context, module string, input map[string]any) (rego.ResultSet, error) {
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
	)
	q, err := r.PrepareForEval(ctx)
	if err != nil {
		return nil, err
	}
	return q.Eval(ctx, rego.EvalInput(input))
}
```

- [ ] **Step 2: Write the failing test**

Append to `helpers/tests/test_dependency_sinks.py`:

```python
from pathlib import Path

from sec_overlay.dependency_sinks import match_manifests, matched_classes

_DEP_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dep_sink_repo"


def test_match_manifests_finds_the_declared_opa_dependency():
    matched = match_manifests(_DEP_FIXTURE)
    assert [e.id for e in matched] == ["opa-rego-http-send"]


def test_matched_classes_returns_sorted_unique_classes():
    assert matched_classes(_DEP_FIXTURE) == ["ssrf"]


def test_match_manifests_ignores_a_repo_with_no_catalogued_dependency(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/x\n\ngo 1.22\n")
    assert match_manifests(tmp_path) == []


def test_match_manifests_skips_vendor_and_node_modules(tmp_path):
    vendored = tmp_path / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / "go.mod").write_text("require github.com/open-policy-agent/opa v0.68.0\n")
    assert match_manifests(tmp_path) == []
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/test_dependency_sinks.py -q
```

Expected: `ImportError: cannot import name 'match_manifests'`.

- [ ] **Step 4: Implement matching**

Add to `helpers/sec_overlay/dependency_sinks.py`, above `main`:

```python
_SKIP_DIRS = {".git", "node_modules", "vendor", ".venv", "venv", "__pycache__",
              ".sec-overlay", "dist", "build", "target"}


def _manifest_files(root: Path, names: set[str]) -> list[Path]:
    """Collect manifest files under ``root``, skipping vendored and cache trees."""
    found: list[Path] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name not in _SKIP_DIRS:
                    stack.append(child)
            elif child.name in names:
                found.append(child)
    return found


def match_manifests(root: str | Path, *, path: Path = CATALOG_PATH) -> list[SinkEntry]:
    """Return every catalog entry whose package is declared under ``root``.

    Args:
        root: Target repository root.
        path: Catalog path; defaults to the shipped reference file.

    Returns:
        Matched entries in catalog order. A match is a substring hit on the
        package name inside a manifest file the entry names.
    """
    entries = load_catalog(path)
    names = {name for e in entries for name in e.manifests}
    texts: dict[str, list[str]] = {}
    for manifest in _manifest_files(Path(root), names):
        try:
            texts.setdefault(manifest.name, []).append(manifest.read_text(errors="replace"))
        except OSError:
            continue
    matched: list[SinkEntry] = []
    for e in entries:
        for name in e.manifests:
            if any(e.package in text for text in texts.get(name, ())):
                matched.append(e)
                break
    return matched


def matched_classes(root: str | Path, *, path: Path = CATALOG_PATH) -> list[str]:
    """Return the sorted, deduplicated attack classes of every matched entry."""
    return sorted({e.cls for e in match_manifests(root, path=path)})
```

Replace `main` with the subcommand form:

```python
def main(argv: list[str] | None = None) -> int:
    """CLI: list the catalog, or the entries a target repo matches."""
    parser = argparse.ArgumentParser(prog="sec-overlay-dependency-sinks")
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Print every catalog entry.")
    m = sub.add_parser("match", help="Print the entries a target repo declares.")
    m.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    catalog = Path(args.catalog)
    if args.cmd == "list":
        for e in load_catalog(catalog):
            print(f"{e.id}\t{e.cls}\t{e.package}")
        return 0
    for e in match_manifests(args.root, path=catalog):
        print(f"{e.id}\t{e.cls}\t{e.sink}\t{e.safe_option}")
    return 0
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_dependency_sinks.py -q
uv run python -m sec_overlay.dependency_sinks match --root fixtures/dep_sink_repo
uv run ruff check sec_overlay/dependency_sinks.py tests/test_dependency_sinks.py
uv run ty check
```

Expected: tests pass; the CLI prints one line starting `opa-rego-http-send	ssrf	http.send`.

- [ ] **Step 6: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: extend the `dependency_sinks.py` entry with `match_manifests` / `matched_classes` and the `list` / `match` subcommands.
- `helpers/tests/README.md`: extend the `test_dependency_sinks.py` row with the four matching guards, naming the `fixtures/dep_sink_repo` fixture.

- [ ] **Step 7: Commit**

```bash
# set plugin.json "version" to 1.71.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_dependency_sinks.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/dep_sink_repo/go.mod \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/dep_sink_repo/policy.go \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): match dependency-sink catalog to manifests"
```

---

## Task 3: Route catalog classes through `reconcile_plan`

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/partition.py:93-118`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py:367`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_partition.py`

**Interfaces:**
- Consumes: `matched_classes(root)` from Task 2.
- Produces: `reconcile_plan(ws, agents_to_spawn, *, target_root: str | Path | None = None) -> list[str]`. The existing two-argument call sites keep working; passing `target_root` merges catalog classes. The function still never removes a planned class.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_partition.py`:

```python
from pathlib import Path

_DEP_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "dep_sink_repo"


def test_reconcile_plan_adds_a_catalog_matched_class(tmp_path):
    """A declared OPA dependency routes `ssrf` even when recon omitted it."""
    from sec_overlay.partition import reconcile_plan
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.ensure()
    plan = reconcile_plan(ws, ["authz"], target_root=_DEP_FIXTURE)
    assert plan[0] == "authz", "a planned class is never removed or reordered"
    assert "ssrf" in plan


def test_reconcile_plan_without_target_root_is_unchanged(tmp_path):
    from sec_overlay.partition import reconcile_plan
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.ensure()
    assert reconcile_plan(ws, ["authz"]) == ["authz"]


def test_reconcile_plan_does_not_duplicate_an_already_planned_class(tmp_path):
    from sec_overlay.partition import reconcile_plan
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.ensure()
    plan = reconcile_plan(ws, ["ssrf"], target_root=_DEP_FIXTURE)
    assert plan.count("ssrf") == 1
```

If `test_partition.py` already constructs a `Workspace` through a shared helper or fixture, use that helper instead of the inline construction above and keep the assertions as written.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_partition.py -q -k catalog
```

Expected: `TypeError: reconcile_plan() got an unexpected keyword argument 'target_root'`.

- [ ] **Step 3: Change the signature and merge the classes**

In `helpers/sec_overlay/partition.py`, add the import at the top of the module:

```python
from sec_overlay.dependency_sinks import matched_classes
```

Change the `reconcile_plan` signature to:

```python
def reconcile_plan(ws, agents_to_spawn, *, target_root: str | Path | None = None) -> list[str]:
```

Extend the docstring with:

```
    A dependency can hold the sink inside its own code (an OPA policy calling
    http.send), which leaves no first-party pattern for recon to see. When
    ``target_root`` is given, every attack class of a matched dependency-sink
    catalog entry is added too.
```

Immediately before the existing `return base + extra`, insert:

```python
    if target_root is not None:
        planned = set(base) | set(extra)
        extra = sorted(extra + [c for c in matched_classes(target_root) if c not in planned])
```

- [ ] **Step 4: Pass the target root at the call site**

At `helpers/sec_overlay/driver.py:367`, change the `reconcile_plan` call to pass the target root the driver already holds, for example:

```python
agents_to_spawn = reconcile_plan(ws, agents_to_spawn, target_root=target)
```

Read the surrounding lines first and use the local variable that actually holds the target repository path; do not introduce a new parameter to reach it.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_partition.py tests/test_wiring.py tests/test_driver.py -q
uv run ruff check sec_overlay/partition.py sec_overlay/driver.py tests/test_partition.py
uv run ty check
```

Expected: all pass.

- [ ] **Step 6: Run the bench regression**

```bash
uv run python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench-f3 --workspaces /tmp/bench-f3-ws
```

Expected: every `locked` positive is still detected. If the corpus seed is absent, record that the check could not run — the seed is local-only per the skill `CLAUDE.md` §1.

- [ ] **Step 7: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note that `reconcile_plan` takes `target_root` and merges dependency-sink catalog classes.
- `helpers/tests/README.md`: add the three `test_partition.py` catalog-routing guards.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.72.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/partition.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_partition.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): route catalog classes into the agent plan"
```

---

## Task 4: Policy-engine indicators in the attack-class table

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/attack-classes.md:26` and the "Selection guidance for recon" list that starts at line 31
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py`

**Interfaces:**
- Consumes: `load_catalog()` from Task 1.
- Produces: no Python surface. The invariant it produces: every catalog entry's `sink` and every one of its `indicators` appears verbatim in `references/attack-classes.md`.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_docs_invariants.py`:

```python
_ATTACK_CLASSES = Path(__file__).resolve().parents[2] / "references" / "attack-classes.md"


def test_every_catalog_indicator_appears_in_the_attack_class_table():
    """Recon selects a class from attack-classes.md, so a catalogued dependency
    whose tokens are absent there is a routing gap the catalog cannot close alone."""
    from sec_overlay.dependency_sinks import load_catalog

    text = _ATTACK_CLASSES.read_text()
    missing = []
    for entry in load_catalog():
        for token in (entry.sink, *entry.indicators):
            if token not in text:
                missing.append(f"{entry.id}: {token}")
    assert not missing, f"catalog tokens absent from attack-classes.md: {missing}"


def test_attack_class_table_names_the_policy_engine_class_for_every_catalog_entry():
    from sec_overlay.dependency_sinks import load_catalog

    text = _ATTACK_CLASSES.read_text()
    for entry in load_catalog():
        assert f"`{entry.cls}`" in text or f"| {entry.cls} |" in text, entry.cls
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_docs_invariants.py -q -k catalog
```

Expected: FAIL listing tokens such as `opa-rego-http-send: rego.New` and `cel-go-expression-eval: cel.NewEnv`.

- [ ] **Step 3: Extend the indicator table**

In `references/attack-classes.md`, replace the `expr-eval-rce` row (line 26) with:

```markdown
| `expr-eval-rce` | Sandboxed expression, policy, or rule-engine escape | `jsep`, `expr-eval`, `mathjs`, `vm.runInContext`, `callee.apply`, `constructor.constructor`, custom formula/rules engines; server-side policy and script engines: `rego.New`, `rego.Module`, `rego.Capabilities`, `http.send`, `cel.NewEnv`, `cel.Compile`, `Program.Eval`, `starlark.ExecFile`, `starlark.Thread`, `starlark.StringDict`, `goja.New`, `Runtime.RunString`, `vm.Set`, `lua.NewState`, `DoString`, `SkipOpenLibs`, `SpelExpressionParser` | static only |
```

Directly under the two existing sentences that distinguish the class from `deserialization` and `ssti`, add:

```markdown
A **server-side policy or rule engine** is in this class even when the engine ships as a
dependency. The sink is a builtin the engine exposes to policy text (OPA's `http.send`, a
CEL host function, a Starlark predeclared builtin), so no first-party source line holds it.
`references/dependency-sinks.json` catalogues these dependencies; a `go.mod` or
`requirements.txt` match routes the class through `partition.reconcile_plan`.

An engine whose builtin performs an outbound request is `ssrf`, not `expr-eval-rce` — OPA's
`http.send` is the reference case. Route by the sink the builtin reaches, not by the engine.
```

- [ ] **Step 4: Extend the recon selection guidance**

Add this bullet to the "Selection guidance for recon" list:

```markdown
- **Server-side policy and script engines** (OPA/Rego, CEL, Starlark, goja, gopher-lua,
  Spring SpEL): select the class named by the matching `references/dependency-sinks.json`
  entry whenever the manifest declares the package, even when no first-party line matches an
  indicator. The evaluator's own builtins are the sink. Also record which safe option the
  call site passes (`rego.Capabilities`, a restricted `cel.NewEnv`, `SkipOpenLibs`); its
  absence is the finding, and the absence rule pack keys on it.
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
uv run pytest tests/test_docs_invariants.py -q
```

Expected: PASS.

- [ ] **Step 6: Update the folder READMEs**

- `references/README.md`: note that the `expr-eval-rce` row covers server-side policy engines and that its indicators are pinned to `dependency-sinks.json` by `test_docs_invariants.py`.
- `helpers/tests/README.md`: add the two new drift guards.

- [ ] **Step 7: Commit**

```bash
# set plugin.json "version" to 1.73.0
git add plugins/sec-overlay/skills/sec-overlay/references/attack-classes.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add policy-engine indicators"
```

---

## Task 5: The `expr-eval-rce` class prompt

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/agents/classes/expr-eval-rce.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py`

**Interfaces:**
- Consumes: the catalog from Task 1; the class boundary text from Task 4.
- Produces: a class-extension file with the same five sections as `agents/classes/ssrf.md` — Canonical fix shape, Discrimination requirement, Class boundary, Proof tuple (required evidence), Instance preservation.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_docs_invariants.py`:

```python
_CLASSES_DIR = Path(__file__).resolve().parents[2] / "agents" / "classes"


def test_expr_eval_rce_class_file_carries_the_required_sections():
    txt = (_CLASSES_DIR / "expr-eval-rce.md").read_text()
    for heading in ("Canonical fix shape", "Discrimination requirement",
                    "Class boundary", "Proof tuple (required evidence)",
                    "Instance preservation"):
        assert heading in txt, heading


def test_every_catalogued_expr_eval_class_has_a_class_file():
    from sec_overlay.dependency_sinks import load_catalog

    for entry in load_catalog():
        assert (_CLASSES_DIR / f"{entry.cls}.md").exists(), entry.cls
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_docs_invariants.py -q -k expr_eval
```

Expected: `FileNotFoundError` for `agents/classes/expr-eval-rce.md`.

- [ ] **Step 3: Write the class file**

Create `agents/classes/expr-eval-rce.md`:

```markdown
# Class extension: expr-eval-rce

Sandboxed expression, policy, or rule-engine escape. The evaluator is often a
dependency, so the sink is a builtin the engine exposes to evaluated text, not a
first-party call.

## Canonical fix shape

Narrow the engine's capability set at construction. Name the option in the fix:
`rego.Capabilities` with the unwanted builtin removed, a `cel.NewEnv` limited to a
reviewed declaration list, `lua.NewState` with `SkipOpenLibs`, a `goja.Runtime`
with no host object `Set`. A deny-list of expression substrings is not the fix
shape; the capability set is.

## Discrimination requirement

State which of these three the finding is, and cite the line:

1. The engine evaluates text the caller supplies at runtime.
2. The engine evaluates text that is a compile-time constant in this repo.
3. The engine is constructed but never evaluates caller text.

Only case 1 is a finding. Case 2 is `informational` unless the constant is loaded
from a writable path. Case 3 is `rejected`.

## Class boundary

IS this class: an evaluator that runs caller-supplied expression, policy, or
script text, where a builtin or host function reaches a capability the caller
should not have.

IS NOT this class:
- `eval()` or `exec()` on attacker text with no sandbox — that is `injection`.
- A template engine rendering untrusted markup — that is `ssti`.
- An object graph rebuilt from bytes — that is `deserialization`.
- An engine builtin that performs an outbound request — that is `ssrf`. Route by
  the sink the builtin reaches. OPA's `http.send` is `ssrf`.

## Proof tuple (required evidence)

All three elements, each with a `file:line` citation:

1. **Evaluator constructed and fed caller text.** Cite the construction line and
   the line where the expression, policy, or script text enters it. A
   `dependency-catalog:<id>` receipt names the dependency-internal sink when the
   sink has no first-party line; it locates the sink and never confirms alone.
2. **No capability restriction on every path to that evaluation.** Cite the
   absence: the construction call with no restricting option, or the option call
   with the dangerous builtin still present. An absence rule receipt
   (`semgrep:sec-overlay.absence.*`) satisfies this element.
3. **Attacker control of the evaluated text.** Cite the route, handler, or queue
   consumer that carries the text, and the assignment that reaches element 1.

An element with no citation makes the finding `raw`, never `confirmed`.

## Instance preservation

One finding per evaluator construction site. Two handlers building their own
evaluator are two findings even when the fix is the same option, because each
site can be fixed or missed independently.
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
uv run pytest tests/test_docs_invariants.py -q
```

Expected: PASS.

- [ ] **Step 5: Update the folder READMEs**

- `agents/classes/README.md`: add the `expr-eval-rce.md` row — role, the three-way discrimination, the `ssrf` boundary for request-performing builtins, and the `dependency-catalog` receipt in element 1.
- `agents/README.md`: add `expr-eval-rce` to the `classes/` extension list.
- `helpers/tests/README.md`: add the two new class-file guards.

- [ ] **Step 6: Commit**

```bash
# set plugin.json "version" to 1.74.0
git add plugins/sec-overlay/skills/sec-overlay/agents/classes/expr-eval-rce.md \
        plugins/sec-overlay/skills/sec-overlay/agents/classes/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_docs_invariants.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add expr-eval-rce class prompt"
```

---

## Task 6: Coverage documentation and recon wiring

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/DETECTION_COVERAGE.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/detection_coverage.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/agents/recon.md:70`
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md` (step 5, the `reconcile_plan` note)
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_detection_coverage.py`

**Interfaces:**
- Consumes: `matched_classes` (Task 2), `reconcile_plan(..., target_root=...)` (Task 3).
- Produces: no new Python surface. `detection_coverage.py` gains one row so the generated document and the reference file stay identical.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_detection_coverage.py`:

```python
def test_coverage_document_records_the_dependency_internal_sink_limit():
    from sec_overlay.detection_coverage import render_markdown

    text = render_markdown()
    assert "dependency-internal sink" in text
    assert "dependency-sinks.json" in text
```

If `detection_coverage.py` exposes the renderer under a different name, use that name; read the module first.

- [ ] **Step 2: Run the test to verify it fails**

```bash
uv run pytest tests/test_detection_coverage.py -q
```

Expected: FAIL on the missing `dependency-internal sink` string.

- [ ] **Step 3: Add the coverage row**

In `helpers/sec_overlay/detection_coverage.py`, next to the existing `"| semgrep | broad pattern SAST, all languages; vendored security rulesets |"` line, add a known-gap row:

```python
        "| dependency-internal sink | No backend reads a dependency's own source, so a sink "
        "inside OPA/CEL/Starlark/goja/Lua is invisible to pattern and dataflow rules. "
        "`references/dependency-sinks.json` closes the routing half: a manifest match routes "
        "the attack class. It does not prove the sink; the class prompt's proof tuple does. |",
```

Place the row in the same table the surrounding rows build, matching their column count.

- [ ] **Step 4: Regenerate the reference document and confirm it matches**

```bash
uv run pytest tests/test_detection_coverage.py -q
```

If the test compares the generated text with `references/DETECTION_COVERAGE.md`, write the generated text to that file so the two agree, then re-run.

- [ ] **Step 5: Wire recon and the playbook**

In `agents/recon.md:70`, after the existing `semgrep` ruleset instruction, add:

```markdown
   - Read `references/dependency-sinks.json`. For every entry whose `package` appears in a
     manifest of the target, include the entry's `cls` in `attack_surface` and record
     `{"id": <entry id>, "package": <package>, "sink": <sink>, "safe_option": <safe_option>}`
     in `dependency_sinks`. A dependency-internal sink has no first-party line to cite, so the
     manifest declaration is the evidence for selecting the class.
```

In `SKILL.md`, in the step 5 paragraph that documents `reconcile_plan`, add:

```markdown
`reconcile_plan(ws, agents_to_spawn, target_root=<T>)` also merges the attack class of every
`references/dependency-sinks.json` entry the target declares in a manifest. A dependency whose
own code holds the sink (OPA's `http.send`) leaves no first-party pattern, so recon can omit the
class; the catalog match restores it. The call never removes a planned class.
```

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
```

Expected: only the two documented environment-only failures from the skill `CLAUDE.md` §1 (missing vendored semgrep clone, missing bench corpus seed) remain.

- [ ] **Step 7: Update the folder READMEs**

- `references/README.md`: note the new `DETECTION_COVERAGE.md` row.
- `helpers/sec_overlay/README.md`: note the new `detection_coverage.py` row.
- `skills/sec-overlay/README.md`: add the dependency-sink catalog to the architecture description and to the pipeline diagram's prefilter step.
- `agents/README.md`: note that recon now emits `dependency_sinks`.
- `helpers/tests/README.md`: add the coverage-document guard.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.74.1
git add plugins/sec-overlay/skills/sec-overlay/references/DETECTION_COVERAGE.md \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/detection_coverage.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_detection_coverage.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/agents/recon.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "docs(sec-overlay): record dependency-sink routing"
```

---

## Acceptance criteria (from the spec)

Check each before opening the pull request.

**F3 (spec §6):**
1. `uv run python -m sec_overlay.dependency_sinks match --root fixtures/dep_sink_repo` prints the `opa-rego-http-send` entry.
2. `reconcile_plan(ws, ["authz"], target_root=fixtures/dep_sink_repo)` returns a list containing `ssrf`.
3. The catalog fails to load with a listed defect when an entry is missing a required field, so a malformed catalog cannot silently route nothing.

**F5 (spec §8):**
4. Every catalog entry's `sink` and `indicators` appear in `references/attack-classes.md` — enforced by `test_docs_invariants.py`.
5. `agents/classes/expr-eval-rce.md` exists and carries all five sections.
6. The `ssrf`-versus-`expr-eval-rce` routing rule for request-performing builtins is stated in both the reference table and the class file.

**Trade-off accepted:** the catalog is a hand-maintained list. It routes only the dependencies someone entered. A dependency-internal sink outside the catalog stays invisible, so the catalog needs an entry whenever a run finds a new one — and no test can detect that gap for us.

---

## Pull request

```bash
git push -u origin feat/dependency-sink-catalog
gh pr create --title "feat(sec-overlay): dependency-sink catalog and policy-engine indicators" --body "<summary>"
```

Wait for CodeRabbit's walkthrough comment before merging (`gh pr view <n> --comments`). Update the root `README.md`, root `CHANGELOG.md`, and `docs/README.md` in the branch if the pre-commit hook requires it for any staged path outside `plugins/`.
