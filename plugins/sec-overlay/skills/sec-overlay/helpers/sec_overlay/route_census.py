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
        One RouteSite per distinct ``(file, line, path)``, sorted by id. Empty
        when ripgrep exits nonzero or emits no parsable output — a census
        failure must not halt a phase, it must produce zero claims.
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
