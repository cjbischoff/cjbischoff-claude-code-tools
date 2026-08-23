# Route Census and Recall Adversary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Derive the route inventory from code instead of from recon's own output, key coverage by sink site instead of by attack class, and add an adversary whose only job is to name what recon left out.

**Architecture:** A new stdlib-only `route_census.py` extracts route registrations from the target with ripgrep, using a JSON framework table. `route_control.build_route_control_table` prefers the census over `kb/scan-profile.json`, which breaks the circularity that let recon check itself. `coverage_ledger` keys a surface per sink site rather than one per class, so a second sink in a covered class can no longer be marked covered by the first. A new `recall-adversary.md` agent then compares the census and the dependency-sink catalog against recon's profile and emits `OMISSION` rows, which route through the existing `record_route_gaps` path.

**Tech Stack:** Python 3.11+, stdlib only (`json`, `re`, `subprocess`, `dataclasses`, `pathlib`, `argparse`). ripgrep for extraction. pytest, ruff, ty.

**Spec:** `docs/superpowers/specs/2026-08-22-sec-overlay-recall-gaps-design.md` — features F6 (§9) and F2 (§5). The spec's build order places these last, because F2 consumes the census F6 produces.

**Prerequisites:** both earlier plans are merged.
- `docs/superpowers/plans/2026-08-22-sec-overlay-dependency-sinks-policy-indicators.md` — Task 7 imports `dependency_sinks.match_manifests`.
- `docs/superpowers/plans/2026-08-22-sec-overlay-absence-detection.md` — Task 6 cites the `dependency-catalog` receipt.

## Global Constraints

Copied verbatim from spec §11. Every task's requirements include this section.

- **Stdlib only.** The `sec_overlay` core has no runtime dependency. Do not add one. Dev dependencies stay `pytest`, `ruff`, `ty`.
- **Test-first.** Tests ship in the same change as the code they cover.
- **Folder README in the same commit.** `scripts/hooks/pre-commit-check.sh` rejects a commit that stages a file in a folder with a tracked `README.md` without staging that `README.md`. Never bypass with `--no-verify`.
- **Preserve every agent prompt's hard rules** — model-family diversity, the tool-receipt safety contract, and the count-invariant verdict tables.
- **Bench regression.** Run `python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>` before and after each feature. A `locked` positive that stops being detected is a hard failure.
- **One plugin version bump per shipping change.** Bump `version` in `plugins/sec-overlay/.claude-plugin/plugin.json` in the same commit.

**Verdict-table rule (spec §5).** `agents/phase-adversary.md` carries count-invariant verdict tables. Do not edit them. The recall adversary is a **new** agent file with its own output contract, because a recall verdict adds rows that the existing table's counts forbid.

**Version sequence.** This plan starts at `1.80.0` (the value the absence-detection plan leaves behind) and ends at `1.86.0`. Each task states the version its commit sets. If the working tree's current version differs, apply the same increment type to the actual current value.

**Paths.** All paths are repo-relative. Python commands run from `plugins/sec-overlay/skills/sec-overlay/helpers/`.

---

## File Structure

| Path | Responsibility |
|------|----------------|
| `plugins/sec-overlay/skills/sec-overlay/references/route-frameworks.json` | Per-framework route-registration patterns the census greps for. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py` | Extracts route sites from the target; writes `kb/route-census.json`. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py` | Prefers the census over the scan profile; adds census and catalog checks. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage_ledger.py` | Keys a surface per sink site instead of one per class. |
| `plugins/sec-overlay/skills/sec-overlay/references/coverage-ledger.schema.json` | Admits the `cls@file:line` surface id plus optional `cls` and `site`. |
| `plugins/sec-overlay/skills/sec-overlay/agents/recall-adversary.md` | New opus adversary that names recon's omissions. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py` | Records recall verdicts in the gate record. |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Documents the census step and the recall gate. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/route_repo/` | Fixture with three registered routes across two frameworks. |

---

## Task 1: The framework table and the census extractor

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/references/route-frameworks.json`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/route_repo/app.py`
- Create: `plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/route_repo/server.go`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_census.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `FRAMEWORKS_PATH: Path` — resolves to `references/route-frameworks.json`.
  - `RouteFramework` frozen dataclass: `name: str`, `language: str`, `globs: tuple[str, ...]`, `pattern: str`, `method_group: int | None`, `path_group: int | None`.
  - `RouteSite` frozen dataclass: `id: str`, `file: str`, `line: int`, `method: str`, `path: str`, `framework: str`.
  - `load_frameworks(path: Path = FRAMEWORKS_PATH) -> list[RouteFramework]`.
  - `census(root: str | Path, *, path: Path = FRAMEWORKS_PATH, runner=subprocess.run) -> list[RouteSite]`.

- [ ] **Step 1: Write the fixture**

Create `helpers/fixtures/route_repo/app.py`:

```python
"""Two Flask routes; one is a policy-evaluation endpoint."""

from flask import Flask, request

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return {"ok": True}


@app.route("/policy/evaluate", methods=["POST"])
def evaluate():
    return {"allow": _evaluate(request.json["policy"])}


def _evaluate(policy_text: str) -> bool:
    raise NotImplementedError
```

Create `helpers/fixtures/route_repo/server.go`:

```go
package main

import "net/http"

func register(mux *http.ServeMux) {
	mux.HandleFunc("/admin/reload", reload)
}

func reload(w http.ResponseWriter, r *http.Request) {}
```

- [ ] **Step 2: Write the failing test**

Create `helpers/tests/test_route_census.py`:

```python
"""The census must derive routes from code, never from recon's own output."""

from __future__ import annotations

from pathlib import Path

import pytest

from sec_overlay.route_census import FRAMEWORKS_PATH, census, load_frameworks

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "route_repo"


def test_every_framework_entry_carries_a_pattern_and_globs():
    frameworks = load_frameworks()
    assert frameworks
    for fw in frameworks:
        assert fw.name and fw.language and fw.pattern
        assert fw.globs, f"{fw.name}: no globs, so the census would scan every file"


def test_framework_names_are_unique():
    names = [fw.name for fw in load_frameworks()]
    assert len(names) == len(set(names))


def test_frameworks_path_points_at_the_reference_file():
    assert FRAMEWORKS_PATH.name == "route-frameworks.json"
    assert FRAMEWORKS_PATH.exists()


@pytest.mark.skipif(
    __import__("shutil").which("rg") is None, reason="ripgrep not installed"
)
def test_census_finds_every_registered_route_in_the_fixture():
    sites = census(_FIXTURE)
    found = {(Path(s.file).name, s.path) for s in sites}
    assert ("app.py", "/health") in found
    assert ("app.py", "/policy/evaluate") in found
    assert ("server.go", "/admin/reload") in found


@pytest.mark.skipif(
    __import__("shutil").which("rg") is None, reason="ripgrep not installed"
)
def test_census_site_ids_are_stable_and_unique():
    sites = census(_FIXTURE)
    ids = [s.id for s in sites]
    assert len(ids) == len(set(ids))
    assert ids == [s.id for s in census(_FIXTURE)]


def test_census_returns_empty_when_the_tool_fails():
    """A missing or failing ripgrep must not raise into the phase driver."""

    def fake(cmd, **kwargs):
        class R:
            stdout = ""
            returncode = 2

        return R()

    assert census(_FIXTURE, runner=fake) == []
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
uv run pytest tests/test_route_census.py -q
```

Expected: `ModuleNotFoundError: No module named 'sec_overlay.route_census'`.

- [ ] **Step 4: Write the framework table**

Create `references/route-frameworks.json`:

```json
{
  "frameworks": [
    {
      "name": "flask",
      "language": "python",
      "globs": ["*.py"],
      "pattern": "@(?:[A-Za-z_][A-Za-z0-9_]*)\\.(?:route|get|post|put|patch|delete)\\(\\s*[\"']([^\"']+)[\"']",
      "method_group": null,
      "path_group": 1
    },
    {
      "name": "fastapi",
      "language": "python",
      "globs": ["*.py"],
      "pattern": "@(?:[A-Za-z_][A-Za-z0-9_]*)\\.(get|post|put|patch|delete)\\(\\s*[\"']([^\"']+)[\"']",
      "method_group": 1,
      "path_group": 2
    },
    {
      "name": "django-urls",
      "language": "python",
      "globs": ["urls.py"],
      "pattern": "(?:path|re_path|url)\\(\\s*[\"']([^\"']*)[\"']",
      "method_group": null,
      "path_group": 1
    },
    {
      "name": "go-nethttp",
      "language": "go",
      "globs": ["*.go"],
      "pattern": "\\.(?:HandleFunc|Handle)\\(\\s*[\"']([^\"']+)[\"']",
      "method_group": null,
      "path_group": 1
    },
    {
      "name": "go-chi-gin-echo",
      "language": "go",
      "globs": ["*.go"],
      "pattern": "\\.(GET|POST|PUT|PATCH|DELETE)\\(\\s*\"([^\"]+)\"",
      "method_group": 1,
      "path_group": 2
    },
    {
      "name": "express",
      "language": "javascript",
      "globs": ["*.js", "*.ts", "*.mjs"],
      "pattern": "\\.(get|post|put|patch|delete|all)\\(\\s*[\"'`]([^\"'`]+)[\"'`]",
      "method_group": 1,
      "path_group": 2
    },
    {
      "name": "spring",
      "language": "java",
      "globs": ["*.java", "*.kt"],
      "pattern": "@(?:Request|Get|Post|Put|Patch|Delete)Mapping\\(\\s*(?:value\\s*=\\s*)?[\"']([^\"']+)[\"']",
      "method_group": null,
      "path_group": 1
    }
  ]
}
```

Note that `flask` and `fastapi` overlap on decorator syntax. That is intentional: the census reports a site once per matching framework and Step 5 de-duplicates on `(file, line, path)`, so a Flask app with `@app.get(...)` is found by whichever pattern matches, not lost between them.

- [ ] **Step 5: Implement the module**

Create `helpers/sec_overlay/route_census.py`:

```python
"""Derive the target's route inventory from its source code.

The route-to-control table used to read recon's own `kb/scan-profile.json`, so a
route recon never noticed could not appear as a gap: the check compared recon
against itself. This module reads the code instead, which makes an omission
visible.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

FRAMEWORKS_PATH = Path(__file__).resolve().parents[2] / "references" / "route-frameworks.json"

_SKIP = ("--glob", "!vendor/*", "--glob", "!node_modules/*", "--glob", "!.git/*")


@dataclass(frozen=True)
class RouteFramework:
    """One framework's route-registration signature."""

    name: str
    language: str
    globs: tuple[str, ...]
    pattern: str
    method_group: int | None
    path_group: int | None


@dataclass(frozen=True)
class RouteSite:
    """One route registration found in the target's source."""

    id: str
    file: str
    line: int
    method: str
    path: str
    framework: str


def load_frameworks(path: Path = FRAMEWORKS_PATH) -> list[RouteFramework]:
    """Load the framework table.

    Args:
        path: Table location; override in tests.

    Returns:
        One RouteFramework per entry, in file order.

    Raises:
        FileNotFoundError: The table is missing. This is a packaging error, not a
            target property, so it fails loudly.
    """
    raw = json.loads(path.read_text())
    return [
        RouteFramework(
            name=e["name"],
            language=e["language"],
            globs=tuple(e["globs"]),
            pattern=e["pattern"],
            method_group=e.get("method_group"),
            path_group=e.get("path_group"),
        )
        for e in raw["frameworks"]
    ]


def _rg(fw: RouteFramework, root: str, runner) -> list[tuple[str, int, str]]:
    cmd = ["rg", "--no-heading", "--line-number", "--only-matching", "--", fw.pattern, root]
    for g in fw.globs:
        cmd[1:1] = ["--glob", g]
    cmd[1:1] = list(_SKIP)
    completed = runner(cmd, capture_output=True, text=True, check=False)
    out = []
    for raw in (completed.stdout or "").splitlines():
        parts = raw.split(":", 2)
        if len(parts) != 3 or not parts[1].isdigit():
            continue
        out.append((parts[0], int(parts[1]), parts[2]))
    return out


def census(
    root: str | Path,
    *,
    path: Path = FRAMEWORKS_PATH,
    runner=subprocess.run,
) -> list[RouteSite]:
    """Extract every route registration under ``root``.

    Args:
        root: Target directory.
        path: Framework table location.
        runner: Injection point for tests.

    Returns:
        One RouteSite per distinct ``(file, line, path)``, sorted by id. Empty when
        ripgrep is missing or fails — a census failure must not halt a phase, it
        must produce zero claims.
    """
    root = str(root)
    seen: dict[tuple[str, int, str], RouteSite] = {}
    for fw in load_frameworks(path):
        compiled = re.compile(fw.pattern)
        for file, line, text in _rg(fw, root, runner):
            m = compiled.search(text)
            if m is None:
                continue
            route = m.group(fw.path_group) if fw.path_group else ""
            if not route:
                continue
            method = (m.group(fw.method_group).upper() if fw.method_group else "ANY")
            key = (file, line, route)
            if key in seen:
                continue
            seen[key] = RouteSite(
                id=f"route:{file}:{line}:{route}",
                file=file,
                line=line,
                method=method,
                path=route,
                framework=fw.name,
            )
    return sorted(seen.values(), key=lambda s: s.id)


def main(argv: list[str] | None = None) -> int:
    """CLI: print one ``file:line<TAB>METHOD<TAB>path<TAB>framework`` row per site."""
    ap = argparse.ArgumentParser(prog="sec_overlay.route_census")
    ap.add_argument("--root", required=True)
    args = ap.parse_args(argv)
    for s in census(args.root):
        print(f"{s.file}:{s.line}\t{s.method}\t{s.path}\t{s.framework}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/test_route_census.py -q
uv run python -m sec_overlay.route_census --root fixtures/route_repo
uv run ruff check sec_overlay/route_census.py tests/test_route_census.py
uv run ty check
```

Expected: six tests pass; the CLI prints three rows.

- [ ] **Step 7: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: add `route_census.py` to the module table, in the group that holds `route_control.py`, and note it is CLI-callable.
- `references/README.md`: add `route-frameworks.json`, naming `route_census.py` as its only consumer.
- `helpers/tests/README.md`: add the six `test_route_census.py` guards and the ripgrep skip.

- [ ] **Step 8: Update the CLI-callable list**

Add `route_census` to the CLI-callable module list in `plugins/sec-overlay/CLAUDE.md`.

- [ ] **Step 9: Commit**

```bash
# set plugin.json "version" to 1.81.0
git add plugins/sec-overlay/skills/sec-overlay/references/route-frameworks.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/route_repo/app.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/fixtures/route_repo/server.go \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_census.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add code-derived route census"
```

---

## Task 2: Persist the census and break the circularity

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_census.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_control.py`

**Interfaces:**
- Consumes: `RouteSite`, `census` from Task 1.
- Produces:
  - `write_census(ws, sites: list[RouteSite]) -> Path` — writes `ws.kb / "route-census.json"`.
  - `load_census(ws) -> list[RouteSite]` — empty list when the file is absent.
  - `build_route_control_table(ws, *, census=None) -> dict` — the existing three keys plus `"source"`, which is `"route-census"` when the census supplies the routes and `"scan-profile"` when it falls back.
  - `check_census_routes(census_sites: list[RouteSite], profile: dict) -> list[dict]` — one `_gap(...)` row per census route the profile never mentions.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_route_census.py`:

```python
def test_write_and_load_census_round_trip(tmp_path):
    from sec_overlay.route_census import RouteSite, load_census, write_census
    from sec_overlay.workspace import Workspace  # match the module's real import path

    ws = Workspace(tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    sites = [RouteSite("route:a.py:3:/x", "a.py", 3, "GET", "/x", "flask")]
    out = write_census(ws, sites)
    assert out.name == "route-census.json"
    assert load_census(ws) == sites


def test_load_census_is_empty_when_absent(tmp_path):
    from sec_overlay.route_census import load_census
    from sec_overlay.workspace import Workspace

    ws = Workspace(tmp_path)
    ws.kb.mkdir(parents=True, exist_ok=True)
    assert load_census(ws) == []
```

Append to `helpers/tests/test_route_control.py`:

```python
def test_route_control_table_prefers_the_census_over_the_scan_profile(tmp_path):
    """Deriving routes from the scan profile made the check compare recon to itself."""
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import build_route_control_table

    ws = _workspace_with_profile(tmp_path, {"entrypoints": ["/health"]})
    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    table = build_route_control_table(ws, census=sites)
    assert table["source"] == "route-census"
    assert any("/policy/evaluate" in str(r) for r in table["routes"])


def test_route_control_table_falls_back_to_the_profile_without_a_census(tmp_path):
    from sec_overlay.route_control import build_route_control_table

    ws = _workspace_with_profile(tmp_path, {"entrypoints": ["/health"]})
    assert build_route_control_table(ws)["source"] == "scan-profile"


def test_check_census_routes_reports_a_route_the_profile_never_mentions(tmp_path):
    """This is the whole point of F6: an unmentioned route becomes a gap row."""
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import check_census_routes

    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    gaps = check_census_routes(sites, {"entrypoints": ["/health"]})
    assert len(gaps) == 1
    assert gaps[0]["disposition"] == "needs_follow_up"
    assert "/policy/evaluate" in gaps[0]["id"]


def test_check_census_routes_is_silent_when_the_profile_mentions_the_route(tmp_path):
    from sec_overlay.route_census import RouteSite
    from sec_overlay.route_control import check_census_routes

    sites = [RouteSite("route:app.py:9:/policy/evaluate", "app.py", 9, "POST",
                       "/policy/evaluate", "flask")]
    assert check_census_routes(sites, {"entrypoints": ["POST /policy/evaluate"]}) == []
```

Read the top of `test_route_control.py` and reuse its existing workspace-and-profile helper in place of `_workspace_with_profile`, and its real `Workspace` import path in place of the guessed one above. Keep every assertion as written.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_route_census.py tests/test_route_control.py -q
```

Expected: `ImportError` on `write_census`, and `TypeError: build_route_control_table() got an unexpected keyword argument 'census'`.

- [ ] **Step 3: Add persistence to the census module**

Append to `helpers/sec_overlay/route_census.py`:

```python
def write_census(ws, sites: list[RouteSite]) -> Path:
    """Write the census to ``kb/route-census.json``.

    Args:
        ws: Workspace.
        sites: Sites from ``census``.

    Returns:
        The written path.
    """
    out = ws.kb / "route-census.json"
    out.write_text(json.dumps([vars(s) for s in sites], indent=2) + "\n")
    return out


def load_census(ws) -> list[RouteSite]:
    """Read the census back.

    Returns:
        One RouteSite per record; empty when the file is absent or unreadable, so a
        consumer never has to guard the call.
    """
    src = ws.kb / "route-census.json"
    if not src.exists():
        return []
    try:
        raw = json.loads(src.read_text())
    except json.JSONDecodeError:
        return []
    return [RouteSite(**r) for r in raw]
```

- [ ] **Step 4: Prefer the census in the route-control table**

In `helpers/sec_overlay/route_control.py`, change the signature to `build_route_control_table(ws, *, census=None)`. When `census` is `None`, call `load_census(ws)` and use its result if non-empty. Build `routes` from `f"{s.method} {s.path}"` per site, stamp `"source": "route-census"`, and keep the whole existing profile-derived path as the fallback with `"source": "scan-profile"`. Leave `controls` and `entrypoints` unchanged, and keep the line-32 comment that records `controls` is a proxy.

Then add the new check:

```python
def check_census_routes(census_sites, profile: dict) -> list[dict]:
    """Report every code-derived route the recon profile never mentions.

    Args:
        census_sites: RouteSite records from route_census.
        profile: The recon scan profile.

    Returns:
        One gap row per unmentioned route. An empty list means recon named every
        route the code registers.
    """
    text = json.dumps(profile).lower()
    return [
        _gap(f"{s.method} {s.path} ({s.file}:{s.line})", "route")
        for s in census_sites
        if not _mentions(s.path, text)
    ]
```

`_mentions(token, text)` at `route_control.py:59` takes the token first and an
already-lowercased string second, and it guards alphanumeric neighbours only, so a route
path carrying `/` still matches. Reuse it as written; do not change its signature. The
`json.dumps(profile)` blob is deliberate: a route may be named in `entrypoints`,
`subsystems`, or a free-text field, and a gap row is only correct when no field names it.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_route_census.py tests/test_route_control.py -q
uv run ruff check sec_overlay/route_census.py sec_overlay/route_control.py
uv run ty check
```

Expected: PASS. Every existing `test_route_control.py` test must still pass: the profile path is a fallback, not a removal.

- [ ] **Step 6: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note `write_census` / `load_census`, the `census=` keyword on `build_route_control_table`, `check_census_routes`, and that the circularity is closed.
- `helpers/tests/README.md`: add the six new guards.

- [ ] **Step 7: Commit**

```bash
# set plugin.json "version" to 1.82.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_census.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_census.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_control.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): derive routes from the census"
```

---

## Task 3: Key coverage by sink site

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage_ledger.py:50-73`
- Modify: `plugins/sec-overlay/skills/sec-overlay/references/coverage-ledger.schema.json`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_coverage_ledger.py`

**Interfaces:**
- Consumes: nothing from Tasks 1–2.
- Produces: `build_coverage_ledger(ws)` emits one surface per sink site, with `id` of the form `f"{cls}@{file}:{line}"`, plus `cls` and `site` fields. A class with no finding still emits one class-level surface with `id` equal to the class name, so an untouched class does not vanish from the ledger.

**The problem this closes (spec §9):** the ledger built one surface per attack class, so one terminal finding marked the whole class covered. A second `ssrf` sink in a different file inherited "covered" from the first and was never followed up.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_coverage_ledger.py`:

```python
def test_two_sinks_in_one_class_produce_two_surfaces(tmp_path):
    """One terminal finding used to mark the whole class covered, so a second sink
    inherited a coverage claim nobody made."""
    from sec_overlay.coverage_ledger import build_coverage_ledger

    ws = _workspace_with_findings(
        tmp_path,
        [
            {"id": "f1", "cls": "ssrf", "file": "a.py", "line": 10, "status": "confirmed"},
            {"id": "f2", "cls": "ssrf", "file": "b.py", "line": 20, "status": "candidate"},
        ],
    )
    ledger = build_coverage_ledger(ws)
    ids = {s["id"] for s in ledger["surfaces"]}
    assert "ssrf@a.py:10" in ids
    assert "ssrf@b.py:20" in ids


def test_a_pending_sink_keeps_the_ledger_partial(tmp_path):
    """The candidate sink must hold the class open even though its sibling is confirmed."""
    from sec_overlay.coverage_ledger import build_coverage_ledger

    ws = _workspace_with_findings(
        tmp_path,
        [
            {"id": "f1", "cls": "ssrf", "file": "a.py", "line": 10, "status": "confirmed"},
            {"id": "f2", "cls": "ssrf", "file": "b.py", "line": 20, "status": "candidate"},
        ],
    )
    ledger = build_coverage_ledger(ws)
    pending = [s for s in ledger["surfaces"] if s["disposition"] == "needs_follow_up"]
    assert any(s["id"] == "ssrf@b.py:20" for s in pending)
    assert ledger["completeness"] != "complete"


def test_a_class_with_no_finding_still_appears_as_one_surface(tmp_path):
    from sec_overlay.coverage_ledger import build_coverage_ledger

    ws = _workspace_with_findings(tmp_path, [], planned_classes=["authz"])
    ids = {s["id"] for s in build_coverage_ledger(ws)["surfaces"]}
    assert "authz" in ids


def test_surface_ids_stay_unique(tmp_path):
    from sec_overlay.coverage_ledger import build_coverage_ledger

    ws = _workspace_with_findings(
        tmp_path,
        [
            {"id": "f1", "cls": "ssrf", "file": "a.py", "line": 10, "status": "confirmed"},
            {"id": "f2", "cls": "ssrf", "file": "a.py", "line": 10, "status": "rejected"},
        ],
    )
    ids = [s["id"] for s in build_coverage_ledger(ws)["surfaces"]]
    assert len(ids) == len(set(ids))
```

Reuse the file's existing workspace-and-findings helper in place of `_workspace_with_findings`; read the top of `test_coverage_ledger.py` and match its signature, keeping the assertions as written. If the existing helper takes no `planned_classes` argument, extend it rather than adding a second helper.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_coverage_ledger.py -q -k "sinks or pending or unique"
```

Expected: the first two FAIL — the current ledger emits one `ssrf` surface.

- [ ] **Step 3: Change the surface key**

In `helpers/sec_overlay/coverage_ledger.py:50-73`, replace the one-surface-per-class loop. For each non-`deps` class:

- If the class has findings, emit one surface per distinct `(file, line)`, with `id = f"{cls}@{file}:{line}"`, `cls = cls`, `site = f"{file}:{line}"`, and the disposition derived from that site's findings using the existing `_REPORTED` / `_SETTLED_NO_ISSUE` logic.
- If it has none, emit one surface with `id = cls`, no `site`, and the existing class-level disposition.

Keep the `completeness` derivation exactly as it is: it already demotes on any `needs_follow_up` surface, so a per-site surface makes it stricter with no change to that code. Do not weaken it.

- [ ] **Step 4: Extend the schema**

In `references/coverage-ledger.schema.json`, keep `id` as a string and add two optional properties to the `surfaces[]` item schema:

```json
"cls": {"type": "string", "description": "Attack class this surface belongs to."},
"site": {"type": "string", "description": "file:line of the sink, when the surface is site-keyed."}
```

Leave `required` at `["id", "disposition"]`: a class-level surface has no site.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_coverage_ledger.py tests/test_schemas.py -q
uv run ruff check sec_overlay/coverage_ledger.py
uv run ty check
```

Expected: PASS. If a report or artifact-gate test asserts a surface count, update that assertion to the new per-site count and check the number by hand — do not relax the assertion to a range.

- [ ] **Step 6: Run the full suite**

```bash
uv run pytest -q
```

Expected: only the two documented environment-only failures. The ledger feeds the report and the artifact gate, so a change here has the widest blast radius in this plan.

- [ ] **Step 7: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note the per-site surface key on `coverage_ledger.py` and why it is stricter.
- `references/README.md`: note the two optional schema properties.
- `helpers/tests/README.md`: add the four guards.

- [ ] **Step 8: Commit**

```bash
# set plugin.json "version" to 1.83.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/coverage_ledger.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/references/coverage-ledger.schema.json \
        plugins/sec-overlay/skills/sec-overlay/references/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_coverage_ledger.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): key coverage by sink site"
```

---

## Task 4: Run the census as a deterministic phase before recon

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py:92-94`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py:292-306`
- Modify: `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py`

**Interfaces:**
- Consumes: `census`, `write_census` from Tasks 1–2.
- Produces: a `route-census` deterministic phase that runs **before** `recon`, so `kb/route-census.json` exists for the recon gate, `check_census_routes`, and the recall adversary.

**Why a phase and not an inline call:** the census must be independent of recon's output. A phase with no declared inputs and one declared output cannot depend on the scan profile by construction, and the phase table already carries the ordering and the `record_stage` bookkeeping.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_phases.py`:

```python
def test_route_census_runs_before_recon():
    """The census must not be able to read recon's output, so it runs first."""
    from sec_overlay.phases import PHASE_TABLE

    names = [p.name for p in PHASE_TABLE]
    assert names.index("route-census") < names.index("recon")


def test_route_census_declares_no_inputs():
    from sec_overlay.phases import PHASE_TABLE

    spec = next(p for p in PHASE_TABLE if p.name == "route-census")
    assert spec.kind == "deterministic"
    assert spec.inputs == ()
    assert len(spec.outputs) == 1
```

Append to `helpers/tests/test_driver.py`:

```python
def test_route_census_phase_writes_the_census_file(tmp_path):
    """The recall adversary and the recon gate both read this file."""
    from sec_overlay.driver import DETERMINISTIC_ACTIONS

    ctx = _context(tmp_path, target=str(_ROUTE_FIXTURE))
    DETERMINISTIC_ACTIONS["route-census"](ctx)
    assert (ctx.ws.kb / "route-census.json").exists()
```

Read `test_driver.py` first and reuse its existing context-building helper in place of `_context`, matching its real signature. Set `_ROUTE_FIXTURE` to `Path(__file__).resolve().parents[1] / "fixtures" / "route_repo"`. Keep the assertion as written.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_phases.py tests/test_driver.py -q -k census
```

Expected: `StopIteration` / `ValueError` — no `route-census` phase exists.

- [ ] **Step 3: Add the phase**

In `helpers/sec_overlay/phases.py`, add the output accessor next to the other `_*` helpers:

```python
def _route_census(ws: Workspace) -> Path:
    return ws.kb / "route-census.json"
```

Then insert the phase as the first entry of `PHASE_TABLE`, before `recon`:

```python
    PhaseSpec("route-census", "deterministic", (), (_route_census,)),
```

- [ ] **Step 4: Add the action**

In `helpers/sec_overlay/driver.py`, add the action beside the other `_act_*` functions:

```python
def _act_route_census(ctx: AuditContext) -> None:
    """Write the code-derived route inventory.

    Runs before recon so the inventory cannot be derived from recon's own output.
    """
    write_census(ctx.ws, census(ctx.target))
```

Import `census` and `write_census` from `sec_overlay.route_census` at the top of the module, and register `"route-census": _act_route_census` in the `DETERMINISTIC_ACTIONS.update({...})` block.

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run pytest tests/test_phases.py tests/test_driver.py -q
uv run ruff check sec_overlay/phases.py sec_overlay/driver.py
uv run ty check
```

Expected: PASS. If a test asserts the length of `PHASE_TABLE` or the identity of its first phase, update that assertion to the new value by hand.

- [ ] **Step 6: Update the phase-order documentation**

`tests/test_docs_invariants.py::test_claude_md_phase_order_tracks_phase_table` compares `PHASE_TABLE` against the phase block in `skills/sec-overlay/CLAUDE.md`, so that block must gain the new phase in the same change. Add the row above the recon row in the CLAUDE.md phase-order listing:

```
R0 Route census     python -m sec_overlay.route_census --root <T>   # code-derived route inventory; runs BEFORE recon
```

Read the surrounding rows first and match their exact column format — the test compares order, so a row in the wrong place fails.

Then run:

```bash
uv run pytest tests/test_docs_invariants.py -q
```

- [ ] **Step 7: Document the step in SKILL.md**

In the recon phase description, add:

```markdown
The `route-census` phase runs before recon and writes `kb/route-census.json` from
`sec_overlay.route_census.census`. The inventory is derived from source, not from recon's
output, so a route recon never named appears as a gap. `route_control` prefers the census and
falls back to the scan profile only when the census is empty; the table records which source
it used in its `source` field.
```

- [ ] **Step 8: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: note the `route-census` action in the `driver.py` entry and the new phase in the `phases.py` entry.
- `skills/sec-overlay/README.md`: add the census to the pipeline diagram, before recon.
- `helpers/tests/README.md`: add the three guards.

- [ ] **Step 9: Commit**

```bash
# set plugin.json "version" to 1.84.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phases.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_driver.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/CLAUDE.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): run the route census before recon"
```

---

## Task 5: The catalog-class check

**Files:**
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_control.py`

**Interfaces:**
- Consumes: `dependency_sinks.match_manifests` and `SinkEntry` from the dependency-sink plan; `_gap` and `_mentions` from `route_control`.
- Produces: `check_catalog_classes(entries: list, profile: dict) -> list[dict]` — one gap row per catalog entry whose class the profile's `attack_surface` never names.

- [ ] **Step 1: Write the failing test**

Append to `helpers/tests/test_route_control.py`:

```python
def test_check_catalog_classes_reports_a_matched_class_recon_omitted():
    """The OPA case: go.mod declares OPA, so ssrf must be in attack_surface."""
    from sec_overlay.dependency_sinks import load_catalog
    from sec_overlay.route_control import check_catalog_classes

    entry = next(e for e in load_catalog() if e.id == "opa-rego-http-send")
    gaps = check_catalog_classes([entry], {"attack_surface": ["authz"]})
    assert len(gaps) == 1
    assert "ssrf" in gaps[0]["id"]
    assert gaps[0]["disposition"] == "needs_follow_up"


def test_check_catalog_classes_is_silent_when_recon_named_the_class():
    from sec_overlay.dependency_sinks import load_catalog
    from sec_overlay.route_control import check_catalog_classes

    entry = next(e for e in load_catalog() if e.id == "opa-rego-http-send")
    assert check_catalog_classes([entry], {"attack_surface": ["ssrf"]}) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_route_control.py -q -k catalog
```

Expected: `ImportError: cannot import name 'check_catalog_classes'`.

- [ ] **Step 3: Implement the check**

Add to `helpers/sec_overlay/route_control.py`:

```python
def check_catalog_classes(entries, profile: dict) -> list[dict]:
    """Report every catalog-matched class the recon profile never named.

    A declared dependency that contains its own sink is invisible to a first-party
    scan, so recon can omit its class with no signal. Each row names the catalog
    entry so the reviewer can read why the class applies.

    Args:
        entries: SinkEntry records from dependency_sinks.match_manifests.
        profile: The recon scan profile.

    Returns:
        One gap row per omitted class.
    """
    surface = profile.get("attack_surface") or []
    seen: set[str] = set()
    gaps = []
    for e in entries:
        if e.cls in surface or e.cls in seen:
            continue
        seen.add(e.cls)
        gaps.append(_gap(f"{e.cls} (dependency-catalog:{e.id}, sink {e.sink})", "class"))
    return gaps
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/test_route_control.py -q
uv run ruff check sec_overlay/route_control.py
uv run ty check
```

Expected: PASS.

- [ ] **Step 5: Update the folder READMEs**

- `helpers/sec_overlay/README.md`: add `check_catalog_classes` to the `route_control.py` entry.
- `helpers/tests/README.md`: add the two guards.

- [ ] **Step 6: Commit**

```bash
# set plugin.json "version" to 1.85.0
git add plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/route_control.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_route_control.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): flag omitted catalog classes"
```

---

## Task 6: The recall adversary

**Files:**
- Create: `plugins/sec-overlay/skills/sec-overlay/agents/recall-adversary.md`
- Modify: `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py`
- Modify: `plugins/sec-overlay/skills/sec-overlay/SKILL.md:25-50`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py`
- Test: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py`

**Interfaces:**
- Consumes: `check_census_routes` and `check_catalog_classes` from Tasks 2 and 5; `_gap`, `record_route_gaps` from `route_control`.
- Produces:
  - `recall_claims(ws, profile, *, target_root) -> list[dict]` in `phase_gate` — one `{"id","refs"}` claim per deterministic omission, for the adversary's prompt.
  - `agents/recall-adversary.md` with a fixed output contract: rows of `OMISSION | <what> | <where to look> | <why recon could miss it>`, or the single line `NO OMISSION FOUND`.

**Why a new agent (spec §5):** `agents/phase-adversary.md` challenges what recon *claimed*. Its verdict tables are count-invariant — a verdict count must equal a claim count — so it structurally cannot report a finding about something absent from the claim list. A recall verdict has no matching claim by definition. Editing those tables would break the invariant; a separate agent keeps both contracts intact.

- [ ] **Step 1: Write the failing tests**

Append to `helpers/tests/test_phase_gate.py`:

```python
def test_recall_claims_include_a_census_route_recon_omitted(tmp_path):
    from sec_overlay.phase_gate import recall_claims

    ws = _workspace_with_census(
        tmp_path,
        [{"id": "route:app.py:9:/policy/evaluate", "file": "app.py", "line": 9,
          "method": "POST", "path": "/policy/evaluate", "framework": "flask"}],
    )
    claims = recall_claims(ws, {"entrypoints": ["/health"], "attack_surface": []},
                           target_root=str(tmp_path))
    assert any("/policy/evaluate" in c["id"] for c in claims)
    assert all(c["refs"] for c in claims), "a recall claim with no ref is unactionable"


def test_recall_claims_are_empty_when_recon_named_everything(tmp_path):
    from sec_overlay.phase_gate import recall_claims

    ws = _workspace_with_census(
        tmp_path,
        [{"id": "route:app.py:9:/policy/evaluate", "file": "app.py", "line": 9,
          "method": "POST", "path": "/policy/evaluate", "framework": "flask"}],
    )
    assert recall_claims(ws, {"entrypoints": ["POST /policy/evaluate"],
                              "attack_surface": []}, target_root=str(tmp_path)) == []
```

Append to `helpers/tests/test_contracts.py`:

```python
def test_recall_adversary_prompt_exists_and_states_its_contract():
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "recall-adversary.md").read_text()
    assert "OMISSION" in txt
    assert "NO OMISSION FOUND" in txt
    assert "opus" in txt.lower()


def test_phase_adversary_verdict_tables_are_untouched_by_recall():
    """The count-invariant tables are load-bearing; recall gets its own agent."""
    from pathlib import Path

    txt = (Path(__file__).resolve().parents[2] / "agents" / "phase-adversary.md").read_text()
    assert "OMISSION" not in txt
```

Reuse the workspace helper style already in `test_phase_gate.py` for `_workspace_with_census`; it must create `kb/route-census.json` with the given records. Keep the assertions as written.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_phase_gate.py tests/test_contracts.py -q -k recall
```

Expected: `ImportError` on `recall_claims`, and a missing-file error for the prompt.

- [ ] **Step 3: Implement `recall_claims`**

Add to `helpers/sec_overlay/phase_gate.py`:

```python
def recall_claims(ws, profile: dict, *, target_root) -> list[dict]:
    """Build one claim per deterministic omission, for the recall adversary.

    A claim here is the inverse of a normal phase claim: it names something recon
    did NOT say, so the adversary judges whether the omission matters rather than
    whether a statement holds.

    Args:
        ws: Workspace holding kb/route-census.json.
        profile: The recon scan profile.
        target_root: Target directory, for the dependency-catalog match.

    Returns:
        One ``{"id", "refs"}`` claim per omission; empty when recon named everything
        the census and the catalog found.
    """
    from sec_overlay.dependency_sinks import match_manifests
    from sec_overlay.route_census import load_census
    from sec_overlay.route_control import check_catalog_classes, check_census_routes

    sites = load_census(ws)
    by_path = {f"{s.method} {s.path}": f"{s.file}:{s.line}" for s in sites}
    claims = []
    for gap in check_census_routes(sites, profile):
        ref = next((v for k, v in by_path.items() if k in gap["id"]), None)
        claims.append({"id": gap["id"], "refs": [ref] if ref else [str(target_root)]})
    for gap in check_catalog_classes(match_manifests(target_root), profile):
        claims.append({"id": gap["id"], "refs": ["references/dependency-sinks.json"]})
    return claims
```

The imports are function-local on purpose: `route_control` already imports from `phase_gate`, so a module-level import here would be circular.

- [ ] **Step 4: Run the phase-gate tests to verify they pass**

```bash
uv run pytest tests/test_phase_gate.py -q
```

Expected: PASS.

- [ ] **Step 5: Write the adversary prompt**

Create `agents/recall-adversary.md`. Match the frontmatter shape of the existing `agents/phase-adversary.md` (read it first), with `model: opus` — the producer is sonnet, so the adversary must be a different family, and this file preserves that rule.

Body:

```markdown
You judge what the recon phase LEFT OUT. You never judge what it claimed; another
adversary does that.

## Inputs

- `{{PROFILE}}` — recon's scan profile, verbatim.
- `{{CENSUS}}` — `kb/route-census.json`, the route inventory derived from source, not
  from recon. A route here that the profile never names is a deterministic omission.
- `{{CATALOG_MATCHES}}` — dependency-sink catalog entries whose package the target
  declares. Each names a sink inside the dependency's own code.
- `{{CLAIMS}}` — the deterministic omissions `sec_overlay.phase_gate.recall_claims`
  already found. Each carries a `file:line` ref.

## What to do

1. For every claim in `{{CLAIMS}}`, read the ref with the Read tool. Confirm the route
   or the dependency really is there. A claim you cannot confirm at its ref is dropped —
   say so and move on.
2. Look for omissions the deterministic checks cannot see:
   - A sink reached through a framework the census table does not know. Name the
     framework and the registration form.
   - An attack class the code implies but no indicator matches — a server-side rule or
     policy engine, a template renderer, an expression evaluator.
   - A route the census found once but that exists in a second form (a versioned prefix,
     a catch-all, a mounted sub-app).
3. Do not report a class recon already named. Read `attack_surface` before you write a
   row.

## Output contract

One row per omission, nothing else:

```
OMISSION | <what recon left out> | <file:line or manifest path to look at> | <why recon could miss it>
```

When you find nothing, output exactly one line:

```
NO OMISSION FOUND
```

Rules:
- Never output a row without a real path in column 3. An omission with nowhere to look is
  not actionable, and the gate rejects it.
- Never output a severity, a CVSS score, or a finding id. You produce follow-up work, not
  findings.
- Never restate a claim from `{{CLAIMS}}` you could not confirm at its ref.
```

- [ ] **Step 6: Wire the gate step**

In `SKILL.md:25-50`, after the existing phase-adversary description, add:

```markdown
For the recon phase only, one extra adversary runs after the phase adversary:
`agents/recall-adversary.md` (opus, fresh context). Its input is
`sec_overlay.phase_gate.recall_claims(ws, profile, target_root=<T>)` plus
`kb/route-census.json`. Every `OMISSION` row it returns is written through
`route_control.record_route_gaps`, which appends the row to `kb/coverage-ledger.json` and
demotes `completeness` to `partial`. An omission therefore cannot be lost by the audit
reporting `complete`.

The recall adversary has its own output contract because `agents/phase-adversary.md`'s
verdict tables are count-invariant: a verdict count must match a claim count, and a recall
row has no matching claim by construction.
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
uv run pytest tests/test_contracts.py tests/test_docs_invariants.py tests/test_wiring.py -q
```

Expected: PASS. If `test_wiring.py` enumerates agent prompt files, add `recall-adversary.md` to that list.

- [ ] **Step 8: Run the full suite and the bench**

```bash
uv run pytest -q
uv run ruff check sec_overlay/ bench/ tests/
uv run ty check
uv run python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench-f6 --workspaces /tmp/bench-f6-ws
```

Expected: only the two documented environment-only failures; no `locked` positive lost.

- [ ] **Step 9: Update the folder READMEs**

- `agents/README.md`: add `recall-adversary.md` — role, opus tier, inputs, the `OMISSION` contract, and why it is separate from the phase adversary.
- `helpers/sec_overlay/README.md`: add `recall_claims` to the `phase_gate.py` entry.
- `skills/sec-overlay/README.md`: add the recall gate to the pipeline description.
- `helpers/tests/README.md`: add the four guards.

- [ ] **Step 10: Commit**

```bash
# set plugin.json "version" to 1.86.0
git add plugins/sec-overlay/skills/sec-overlay/agents/recall-adversary.md \
        plugins/sec-overlay/skills/sec-overlay/agents/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/phase_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_phase_gate.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_contracts.py \
        plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md \
        plugins/sec-overlay/skills/sec-overlay/SKILL.md \
        plugins/sec-overlay/skills/sec-overlay/README.md \
        plugins/sec-overlay/.claude-plugin/plugin.json \
        plugins/sec-overlay/CHANGELOG.md
git commit -m "feat(sec-overlay): add the recall adversary"
```

---

## Acceptance criteria (from the spec)

**F6 (spec §9):**
1. `sec_overlay.route_census --root fixtures/route_repo` prints all three registered routes across two frameworks.
2. `build_route_control_table(ws, census=<sites>)` reports `source == "route-census"`; with no census it reports `source == "scan-profile"`.
3. `check_census_routes` produces one gap row for a code route the recon profile never mentions, and none when it does. This is the circularity fix: the check no longer compares recon against recon.
4. `build_coverage_ledger` emits one surface per sink site. Two `ssrf` sinks in different files produce two surfaces, and a pending second sink keeps `completeness` below `complete`.
5. `kb/route-census.json` exists before the recon gate runs.

**F2 (spec §5):**
6. `recall_claims` returns one claim per deterministic omission, each carrying a ref, and an empty list when recon named everything.
7. `agents/recall-adversary.md` exists, runs on opus, and states both the `OMISSION` row format and the `NO OMISSION FOUND` line.
8. `agents/phase-adversary.md` is unchanged — pinned by a test that asserts `OMISSION` does not appear in it.
9. An `OMISSION` row routes through `record_route_gaps`, so the ledger cannot read `complete` while an omission is open.

**Trade-offs accepted:**
- The framework table is a hand-maintained regex list. A framework it does not know produces no census rows for that code, and the census reports silence rather than an error. The recall adversary's step 2 exists to catch exactly that case, but it is an LLM judgment, not a receipt.
- Regex route extraction misses a route built at runtime from a variable, a loop, or a config file. Those routes never appear in the census. Making the extraction structural (ast-grep per language) is a larger job than this feature needs, and a partial census still breaks the circularity that motivated F6.
- Per-site coverage keying makes `completeness == "complete"` harder to reach. Some audits that reported `complete` will now report `partial`. That is the intent: the old value was reached by inheriting coverage across sites in a class.
- The recall adversary produces follow-up work, not findings. It cannot confirm anything, so an omission it names still needs an investigate pass. This keeps the precision-first contract: no finding is created by an LLM claim.

---

## Pull request

```bash
git push -u origin feat/route-census-recall
gh pr create --title "feat(sec-overlay): route census and recall adversary" --body "<summary>"
```

Wait for CodeRabbit's walkthrough comment before merging (`gh pr view <n> --comments`).
