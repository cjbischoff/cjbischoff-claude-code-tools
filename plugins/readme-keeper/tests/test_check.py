"""Tests for skills/readme-keeper/scripts/check.py, run through the real CLI."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN / "skills" / "readme-keeper" / "scripts" / "check.py"
TELLS = PLUGIN / "skills" / "readme-keeper" / "references" / "tells.md"
FIX = PLUGIN / "tests" / "fixtures"
FINDING_KEYS = {"check", "severity", "line", "message", "evidence"}
LOCAL_ENV = {**os.environ, "no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"}


def run(*args: str, env: dict | None = None, timeout: float | None = None):
    """Run check.py with the current interpreter.

    Args:
        *args: Command-line arguments after the script path.
        env: Environment for the child process, or None to inherit.
        timeout: Seconds before the run counts as a hang, or None for no limit.

    Returns:
        The completed process with text stdout and stderr.
    """
    assert SCRIPT.is_file(), f"missing script: {SCRIPT}"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=timeout,
    )


def report(root: Path, *flags: str, env: dict | None = None) -> tuple[int, dict]:
    """Run check.py with --json on a repo and parse the report.

    Args:
        root: Repo root, passed as --root.
        *flags: Extra arguments such as paths, `--all`, or `--strict`.
        env: Environment for the child process, or None to inherit.

    Returns:
        The exit code and the parsed JSON report.
    """
    result = run("--root", str(root), "--json", *flags, env=env)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode, json.loads(result.stdout)


def find(
    rep: dict, check: str, path: str = "README.md", contains: str = "", severity: str | None = None
) -> list[dict]:
    """Select findings of one check in one file.

    Args:
        rep: Parsed JSON report.
        check: Check name, such as `commands`.
        path: Report path of the README.
        contains: Case-insensitive text the message must hold.
        severity: Required severity, or None for any.

    Returns:
        The matching findings in report order.
    """
    files = {f["path"]: f["findings"] for f in rep["files"]}
    return [
        f
        for f in files.get(path, [])
        if f["check"] == check
        and contains.lower() in f["message"].lower()
        and severity in (None, f["severity"])
    ]


def line_of(root: Path, needle: str, path: str = "README.md") -> int:
    """Return the 1-based number of the first line that equals the needle once stripped."""
    lines = (root / path).read_text(encoding="utf-8").splitlines()
    return next(n for n, line in enumerate(lines, 1) if line.strip() == needle)


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """Write files under tmp_path and return it as the repo root."""
    for name, text in files.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------- commands


def test_npm_known_script_passes():
    _, rep = report(FIX / "node-npm")
    messages = [f["message"] for f in find(rep, "commands")]
    assert not any("build" in m for m in messages), messages


def test_npm_unknown_script_is_p0():
    _, rep = report(FIX / "node-npm")
    hits = find(rep, "commands")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0"
    assert "deploy" in hits[0]["message"]
    assert hits[0]["line"] == line_of(FIX / "node-npm", "npm run deploy")
    assert "build" in hits[0]["evidence"]


def test_make_target():
    _, rep = report(FIX / "make")
    hits = find(rep, "commands")
    assert [h["severity"] for h in hits] == ["P0"]
    assert "deploy" in hits[0]["message"]


def test_just_recipe():
    _, rep = report(FIX / "just")
    hits = find(rep, "commands")
    assert [h["severity"] for h in hits] == ["P0"]
    assert "release" in hits[0]["message"]


def test_uv_run_entry_point():
    _, rep = report(FIX / "py-uv")
    hits = find(rep, "commands")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0" and "ghost" in hits[0]["message"]


def test_poetry_run_script():
    _, rep = report(FIX / "py-poetry")
    hits = find(rep, "commands")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0" and "nope" in hits[0]["message"]


def test_cargo_run_bin():
    _, rep = report(FIX / "rust")
    hits = find(rep, "commands")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0" and "ghost" in hits[0]["message"]


def test_go_run_path():
    _, rep = report(FIX / "go")
    hits = find(rep, "commands")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0" and "cmd/ghost" in hits[0]["message"]


def test_unrecognized_command_skipped():
    _, rep = report(FIX / "make")
    text = " ".join(f["message"] for f in find(rep, "commands"))
    for name in ("docker", "terraform", "rake"):
        assert name not in text


PYPROJECT_DEV = (
    '[project]\nname = "h"\nversion = "0"\n\n'
    '[dependency-groups]\ndev = ["pytest>=8", "ruff>=0.6", "ty>=0.0.1a1"]\n'
    'lint = ["Black[colorama]==24.1"]\n'
)


def test_uv_run_accepts_dependency_groups_and_strips_specifiers(tmp_path):
    body = "# T\n\n```sh\nuv run pytest -q\nuv run ruff check\nuv run ty\nuv run black .\nuv run ghost\n```\n"
    root = make_repo(tmp_path, {"pyproject.toml": PYPROJECT_DEV, "README.md": body})
    _, rep = report(root)
    hits = find(rep, "commands")
    assert len(hits) == 1 and "ghost" in hits[0]["message"], hits


def test_run_accepts_optional_uv_dev_and_poetry_group_dependencies(tmp_path):
    pyproject = (
        '[project]\nname = "h"\nversion = "0"\n\n'
        '[project.optional-dependencies]\ndocs = ["mkdocs>=1"]\n\n'
        '[tool.uv]\ndev-dependencies = ["mypy>=1"]\n\n'
        '[tool.poetry.group.test.dependencies]\nhypothesis = "^6"\n\n'
        '[tool.poetry.group.lint.dependencies]\nflake8 = {version = "^7"}\n'
    )
    body = (
        "# T\n\n```sh\nuv run mkdocs build\nuv run mypy .\n"
        "poetry run hypothesis\npoetry run flake8\npoetry run ghost\n```\n"
    )
    root = make_repo(tmp_path, {"pyproject.toml": pyproject, "README.md": body})
    _, rep = report(root)
    hits = find(rep, "commands")
    assert len(hits) == 1 and "ghost" in hits[0]["message"], hits


# ---------------------------------------------------------------- cd


def test_cd_and_then_command_uses_that_directory_manifest(tmp_path):
    body = "# T\n\n```sh\ncd helpers && uv run pytest -q\ncd helpers; uv run ghost\n```\n"
    root = make_repo(tmp_path, {"helpers/pyproject.toml": PYPROJECT_DEV, "README.md": body})
    _, rep = report(root)
    hits = find(rep, "commands")
    assert len(hits) == 1 and "ghost" in hits[0]["message"], hits
    assert hits[0]["line"] == line_of(root, "cd helpers; uv run ghost")


def test_cd_on_its_own_line_applies_to_later_lines_of_the_block(tmp_path):
    body = "# T\n\n```sh\ncd tools\nmake build\nmake deploy\n```\n\n```sh\nmake build\n```\n"
    root = make_repo(tmp_path, {"tools/Makefile": "build:\n\techo\n", "README.md": body})
    _, rep = report(root)
    msgs = [h["message"] for h in find(rep, "commands")]
    # `make deploy` fails inside tools/. The second block has no cd, and the root has no Makefile.
    assert len(msgs) == 2, msgs
    assert any("deploy" in m for m in msgs) and any("make build" in m for m in msgs)


def test_cd_resolves_readme_folder_first_then_root(tmp_path):
    body = "# D\n\n```sh\ncd helpers && uv run pytest\ncd missing-dir && uv run ghost\n```\n"
    root = make_repo(tmp_path, {"helpers/pyproject.toml": PYPROJECT_DEV, "docs/README.md": body})
    _, rep = report(root, "docs/README.md")
    assert find(rep, "commands", path="docs/README.md") == []


# ---------------------------------------------------------------- package manager


def test_npm_install_with_pnpm_lock_is_p1():
    root = FIX / "node-pnpm-workspace"
    _, rep = report(root)
    hits = find(rep, "package-manager")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P1"
    assert "npm install" in hits[0]["message"]
    assert "pnpm-lock.yaml" in hits[0]["evidence"]
    assert hits[0]["line"] == line_of(root, "npm install")


def test_matching_manager_passes():
    _, rep = report(FIX / "node-npm")
    assert not find(rep, "package-manager")
    _, rep = report(FIX / "py-poetry")
    assert not find(rep, "package-manager")
    _, rep = report(FIX / "py-uv")
    hits = find(rep, "package-manager")
    assert len(hits) == 1 and "poetry install" in hits[0]["message"]


def test_matching_lockfile_passes_even_without_the_fixture_lock(tmp_path):
    root = make_repo(
        tmp_path,
        {
            "package.json": '{"name": "x", "scripts": {"build": "y"}}',
            "package-lock.json": "{}",
            "README.md": "# T\n\n```sh\nnpm install\nnpm run build\n```\n",
        },
    )
    _, rep = report(root)
    assert find(rep, "package-manager") == [] and find(rep, "commands") == []


# ---------------------------------------------------------------- paths


def test_missing_relative_link_is_p0():
    root = FIX / "node-npm"
    _, rep = report(root)
    hits = find(rep, "paths", contains="docs/missing.md")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P0"
    assert hits[0]["line"] == line_of(root, "- [Missing page](docs/missing.md)")


def test_existing_path_passes():
    _, rep = report(FIX / "node-npm")
    text = " ".join(f["message"] for f in find(rep, "paths"))
    assert "guide.md" not in text
    assert "src/index.js" not in text


def test_url_encoded_path():
    _, rep = report(FIX / "node-npm")
    text = " ".join(f["message"] for f in find(rep, "paths"))
    assert "my%20file" not in text and "my file" not in text


def test_unresolved_inline_path_is_p2_never_p0_or_p1():
    _, rep = report(FIX / "node-npm")
    hits = find(rep, "paths", contains="src/ghost.js")
    assert len(hits) == 1, hits
    assert hits[0]["severity"] == "P2"
    assert "unresolved path, check intent" in hits[0]["message"]
    assert not find(rep, "paths", contains="src/index.js")
    for name in ("node-npm", "claude-plugin", "py-uv", "rust"):
        _, rep = report(FIX / name)
        inline = [f for f in find(rep, "paths") if "unresolved path" in f["message"]]
        assert all(f["severity"] == "P2" for f in inline), (name, inline)


def test_missing_link_and_image_stay_p0(tmp_path):
    body = '# T\n\n[x](docs/nope.md)\n\n![y](assets/nope.png)\n\n<img src="assets/nope2.png">\n'
    _, rep = report(make_repo(tmp_path, {"README.md": body}))
    hits = find(rep, "paths", severity="P0")
    assert {h["line"] for h in hits} == {3, 5, 7}, hits
    assert find(rep, "paths", severity="P1") == []


def test_claude_plugin_link_to_missing_file_is_p0():
    _, rep = report(FIX / "claude-plugin")
    assert find(rep, "paths", contains="commands/ghost.md", severity="P0")
    assert not find(rep, "paths", contains="commands/create.md")


def test_inline_path_found_in_readme_folder_or_root(tmp_path):
    root = make_repo(
        tmp_path,
        {
            "README.md": "# R\n",
            "src/app.py": "",
            "docs/sub/README.md": "# S\n\nSee `local.py` and `sub/x.py`, `src/app.py`.\n",
            "docs/sub/sub/x.py": "",
            "docs/sub/local.py": "",
        },
    )
    _, rep = report(root, "docs/sub/README.md")
    assert find(rep, "paths", path="docs/sub/README.md") == []


def test_inline_path_suffix_match_against_tracked_files(tmp_path):
    root = make_repo(
        tmp_path,
        {
            "plugins/p/skills/s/scripts/lint.py": "",
            "plugins/p/commands/README.md": (
                "# C\n\nRuns `scripts/lint.py` from `skills/s/` and `s/scripts/`.\n"
            ),
        },
    )
    _, rep = report(root, "plugins/p/commands/README.md")
    assert find(rep, "paths", path="plugins/p/commands/README.md") == []


def test_inline_path_suffix_match_keeps_leading_dot(tmp_path):
    root = make_repo(
        tmp_path,
        {
            "pkg/.github/ci.yml": "",
            "docs/README.md": "# C\n\nSee `.github/ci.yml` and `github/ci.yml`.\n",
        },
    )
    _, rep = report(root, "docs/README.md")
    hits = find(rep, "paths", path="docs/README.md")
    assert [h["message"].split("`")[1] for h in hits] == ["github/ci.yml"]


def test_inline_path_unresolved_when_suffix_is_not_whole_segments(tmp_path):
    root = make_repo(
        tmp_path,
        {"a/xscripts/lint.py": "", "README.md": "# C\n\nRuns `scripts/lint.py`.\n"},
    )
    _, rep = report(root)
    assert [h["severity"] for h in find(rep, "paths")] == ["P2"]


def test_extension_pair_and_prose_slash_are_not_paths(tmp_path):
    text = "# T\n\nUse `.h/.c` or `npm/yarn` or `and/or`, not `a/b`.\n"
    _, rep = report(make_repo(tmp_path, {"README.md": text}))
    assert find(rep, "paths") == []


# ---------------------------------------------------------------- anchors

ANCHORS = (
    "# Hello, World!\n\n## Install & Use\n\n## Usage\n\n## Usage\n\n## `code` Title\n\n"
    '## \U0001f680 Launch\n\n<a id="custom"></a>\n\n'
    "[a](#hello-world) [b](#install--use) [c](#usage) [d](#usage-1) [e](#code-title) "
    "[f](#-launch) [g](#Hello-World) [h](#custom) [i](#top)\n"
)


def test_anchor_slug_rules(tmp_path):
    root = make_repo(tmp_path, {"README.md": ANCHORS})
    _, rep = report(root)
    assert find(rep, "anchors") == []


def test_missing_anchor_is_p1(tmp_path):
    root = make_repo(tmp_path, {"README.md": ANCHORS + "\n[x](#nope) [y](#usage-2)\n"})
    _, rep = report(root)
    hits = find(rep, "anchors")
    assert [h["severity"] for h in hits] == ["P1", "P1"]
    assert "nope" in hits[0]["message"] and "usage-2" in hits[1]["message"]
    assert hits[0]["line"] == line_of(root, "[x](#nope) [y](#usage-2)")


# ---------------------------------------------------------------- license


def test_license_mismatch_is_p0():
    _, rep = report(FIX / "py-uv")
    hits = find(rep, "license")
    assert len(hits) == 1 and hits[0]["severity"] == "P0"
    assert "MIT" in hits[0]["message"] and "Apache" in hits[0]["evidence"]


def test_license_without_source_is_p0():
    root = FIX / "py-poetry"
    _, rep = report(root)
    hits = find(rep, "license")
    assert len(hits) == 1 and hits[0]["severity"] == "P0"
    assert hits[0]["line"] == line_of(root, "Apache-2.0")


def test_license_match_passes(tmp_path):
    for name in ("rust", "node-npm", "claude-plugin"):
        _, rep = report(FIX / name)
        assert not find(rep, "license"), name
    root = make_repo(
        tmp_path,
        {
            "README.md": "# T\n\n## License\n\nMIT\n",
            "LICENSE": "MIT License\n\nPermission is hereby granted, free of charge, to any person\n",
        },
    )
    _, rep = report(root)
    assert not find(rep, "license")


# ---------------------------------------------------------------- badges


def test_ci_and_coverage_badges_without_evidence_are_p1():
    _, rep = report(FIX / "node-npm")
    hits = find(rep, "badges")
    assert len(hits) == 2, hits
    assert all(h["severity"] == "P1" for h in hits)
    text = " ".join(h["message"] for h in hits)
    assert "ci.yml" in text and "coverage" in text.lower()


def test_registry_badge_with_private_manifest_is_p1():
    _, rep = report(FIX / "node-pnpm-workspace")
    hits = find(rep, "badges")
    assert len(hits) == 1 and hits[0]["severity"] == "P1"
    assert "private" in hits[0]["message"].lower()
    assert not find(rep, "badges", path="packages/app/README.md")


def test_badges_with_evidence_pass(tmp_path):
    root = make_repo(
        tmp_path,
        {
            "README.md": (
                "# T\n\n"
                "![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)\n"
                "![cov](https://codecov.io/gh/o/r/branch/main/graph/badge.svg)\n"
            ),
            ".github/workflows/ci.yml": "name: ci\n",
            ".coveragerc": "[run]\n",
        },
    )
    _, rep = report(root)
    assert find(rep, "badges") == []


# ---------------------------------------------------------------- markers


def marker_hits(tmp_path: Path, body: str, contains: str) -> list[dict]:
    """Check a README body and return its marker findings that hold the text."""
    root = make_repo(tmp_path, {"README.md": body})
    _, rep = report(root)
    return find(rep, "markers", contains=contains, severity="P0")


def test_unpaired_markers_are_p0(tmp_path):
    start = "# T\n\n<!-- readme-keeper:start install -->\ntext\n"
    assert marker_hits(tmp_path, start, "unpaired")
    end = "# T\n\ntext\n<!-- readme-keeper:end install -->\n"
    assert marker_hits(tmp_path, end, "unpaired")


def test_nested_markers_are_p0(tmp_path):
    body = (
        "<!-- readme-keeper:start install -->\n<!-- readme-keeper:start env -->\nx\n"
        "<!-- readme-keeper:end env -->\n<!-- readme-keeper:end install -->\n"
    )
    assert marker_hits(tmp_path, body, "nested")


def test_duplicate_markers_are_p0(tmp_path):
    region = "<!-- readme-keeper:start install -->\nx\n<!-- readme-keeper:end install -->\n"
    assert marker_hits(tmp_path, region + "\n" + region, "duplicate")


def test_unknown_marker_id_is_p0(tmp_path):
    body = "<!-- readme-keeper:start bogus -->\nx\n<!-- readme-keeper:end bogus -->\n"
    assert marker_hits(tmp_path, body, "unknown")


def test_well_formed_markers_pass():
    _, rep = report(FIX / "claude-plugin")
    assert find(rep, "markers") == []


def test_marker_inside_inline_code_is_ignored(tmp_path):
    body = (
        "# T\n\nWrite `<!-- readme-keeper:start x -->` to open a region and\n"
        "``<!-- readme-keeper:end install -->`` to close it.\n"
    )
    root = make_repo(tmp_path, {"README.md": body})
    _, rep = report(root)
    assert find(rep, "markers") == []


def test_inline_code_marker_does_not_open_or_close_a_real_region(tmp_path):
    body = (
        "<!-- readme-keeper:start install -->\nUse `<!-- readme-keeper:end install -->` to end.\n"
        "<!-- readme-keeper:end install -->\n\n"
        "`<!-- readme-keeper:start env -->`\n"
    )
    root = make_repo(tmp_path, {"README.md": body})
    _, rep = report(root)
    assert find(rep, "markers") == []
    broken = "<!-- readme-keeper:start install -->\nUse `<!-- readme-keeper:end install -->`.\n"
    _, rep = report(make_repo(tmp_path / "b", {"README.md": broken}))
    assert find(rep, "markers", contains="unpaired", severity="P0")


def test_marker_inside_code_fence_is_ignored(tmp_path):
    body = "```markdown\n<!-- readme-keeper:start install -->\n```\n"
    root = make_repo(tmp_path, {"README.md": body})
    _, rep = report(root)
    assert find(rep, "markers") == []


# ---------------------------------------------------------------- links


@pytest.fixture
def server():
    """Serve 127.0.0.1 on a free port. Yields the base URL and the list of requests seen."""
    seen: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def _answer(self):
            seen.append((self.command, self.path))
            if self.path == "/ok":
                code = 200
            elif self.path == "/nohead":
                code = 405 if self.command == "HEAD" else 200
            elif self.path == "/boom":
                code = 500
            else:
                code = 404
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = do_HEAD = _answer

        def log_message(self, format, *args):
            return None

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}", seen
    srv.shutdown()
    srv.server_close()


def link_readme(base: str) -> str:
    """Build a README that links four local URLs."""
    return (
        f"# T\n\n[ok]({base}/ok)\n\n[gone]({base}/gone)\n\n"
        f"[nohead]({base}/nohead)\n\n[boom]({base}/boom)\n"
    )


def test_links_flag_checks_external_urls(tmp_path, server):
    base, seen = server
    root = make_repo(tmp_path, {"README.md": link_readme(base)})
    _, rep = report(root, "--links", env=LOCAL_ENV)
    hits = find(rep, "links")
    by_url = {h["message"].split(base)[1].split()[0].strip("`:"): h for h in hits}
    assert set(by_url) == {"/gone", "/boom"}, hits
    assert by_url["/gone"]["severity"] == "P1"
    assert by_url["/boom"]["severity"] == "P2"
    assert ("HEAD", "/ok") in seen
    assert ("HEAD", "/nohead") in seen and ("GET", "/nohead") in seen


def test_links_skipped_without_flag(tmp_path, server):
    base, seen = server
    root = make_repo(tmp_path, {"README.md": link_readme(base)})
    _, rep = report(root, env=LOCAL_ENV)
    assert find(rep, "links") == []
    assert seen == []


# ---------------------------------------------------------------- prose


def test_prose_flags_em_dash_and_stock_words(tmp_path):
    text = "# T\n\nWe delve into a seamless plan \u2014 for you.\n\nMoreover, it works.\n"
    root = make_repo(tmp_path, {"README.md": text})
    code, rep = report(root, "--prose")
    hits = find(rep, "prose")
    assert hits and all(h["severity"] == "P2" for h in hits)
    text = " ".join(h["message"] for h in hits).lower()
    for needle in ("em dash", "delve", "seamless", "moreover"):
        assert needle in text, needle
    assert code == 0


def test_prose_off_by_default_and_skips_code(tmp_path):
    text = "# T\n\nWe delve in \u2014 now.\n"
    root = make_repo(tmp_path, {"README.md": text})
    _, rep = report(root)
    assert find(rep, "prose") == []
    code = "# T\n\nUse `delve` here.\n\n```\ndelve \u2014 seamless\n```\n"
    root = make_repo(tmp_path / "b", {"README.md": code})
    _, rep = report(root, "--prose")
    assert find(rep, "prose") == []


# ---------------------------------------------------------------- cli


def test_all_finds_every_readme():
    _, rep = report(FIX / "node-pnpm-workspace", "--all")
    assert {f["path"] for f in rep["files"]} == {"README.md", "packages/app/README.md"}


def test_all_skips_vendored_directories(tmp_path):
    files = {
        "README.md": "# T\n",
        "docs/README.md": "# D\n",
        "node_modules/x/README.md": "# N\n",
        ".venv/lib/README.md": "# V\n",
        ".git/README.md": "# G\n",
    }
    _, rep = report(make_repo(tmp_path, files), "--all")
    assert {f["path"] for f in rep["files"]} == {"README.md", "docs/README.md"}


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_all_uses_tracked_files_when_git_is_present(tmp_path):
    root = make_repo(tmp_path, {"README.md": "# T\n", "sub/README.md": "# S\n"})
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    _, rep = report(root, "--all")
    assert [f["path"] for f in rep["files"]] == ["README.md"]


EXCLUDE_TREE = {
    "README.md": "# T\n",
    "docs/README.md": "# D\n",
    "vendor/README.md": "# V\n",
    "tests/fixtures/a/README.md": "# F\n",
    "x/__fixtures__/README.md": "# F\n",
    "y/testdata/README.md": "# F\n",
    "z/test-data/README.md": "# F\n",
}


def paths_of(rep: dict) -> set[str]:
    """Return the report paths of a parsed report."""
    return {f["path"] for f in rep["files"]}


def test_all_skips_fixture_directories_by_default(tmp_path):
    _, rep = report(make_repo(tmp_path, EXCLUDE_TREE), "--all")
    assert paths_of(rep) == {"README.md", "docs/README.md", "vendor/README.md"}


def test_exclude_glob_is_repeatable_and_applies_to_all(tmp_path):
    root = make_repo(tmp_path, EXCLUDE_TREE)
    _, rep = report(root, "--all", "--exclude", "vendor/*")
    assert paths_of(rep) == {"README.md", "docs/README.md"}
    _, rep = report(root, "--all", "--exclude", "vendor/*", "--exclude", "docs/*")
    assert paths_of(rep) == {"README.md"}


def test_explicit_path_is_never_excluded(tmp_path):
    root = make_repo(tmp_path, EXCLUDE_TREE)
    _, rep = report(root, "--all", "--exclude", "vendor/*", "vendor/README.md")
    assert "vendor/README.md" in paths_of(rep)
    _, rep = report(root, "tests/fixtures/a/README.md")
    assert paths_of(rep) == {"tests/fixtures/a/README.md"}


def test_root_inside_a_fixture_directory_still_checks_its_readmes(tmp_path):
    inner = make_repo(
        tmp_path / "tests" / "fixtures" / "f", {"README.md": "# F\n", "s/README.md": "#\n"}
    )
    _, rep = report(inner, "--all")
    assert paths_of(rep) == {"README.md", "s/README.md"}


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_all_excludes_tracked_fixture_readmes_too(tmp_path):
    root = make_repo(tmp_path, EXCLUDE_TREE)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    _, rep = report(root, "--all", "--exclude", "vendor/*")
    assert paths_of(rep) == {"README.md", "docs/README.md"}


def test_explicit_path_is_relative_to_root():
    _, rep = report(FIX / "node-pnpm-workspace", "packages/app/README.md")
    assert [f["path"] for f in rep["files"]] == ["packages/app/README.md"]
    assert find(rep, "commands", path="packages/app/README.md", contains="missing")


def test_json_shape():
    _, rep = report(FIX / "node-npm")
    assert set(rep) == {"files"}
    (entry,) = rep["files"]
    assert set(entry) == {"path", "findings"} and entry["path"] == "README.md"
    assert entry["findings"]
    for finding in entry["findings"]:
        assert set(finding) == FINDING_KEYS
        assert finding["severity"] in {"P0", "P1", "P2"}
        assert isinstance(finding["line"], int) and finding["message"]


def test_human_report_lists_findings():
    result = run("--root", str(FIX / "node-npm"))
    assert result.returncode == 1
    for needle in ("README.md", "P0", "deploy", str(line_of(FIX / "node-npm", "npm run deploy"))):
        assert needle in result.stdout, needle


def test_exit_code_0_when_clean(tmp_path):
    root = make_repo(tmp_path, {"README.md": "# Clean\n\nPlain text.\n"})
    assert run("--root", str(root)).returncode == 0


def test_exit_code_1_on_p0():
    assert run("--root", str(FIX / "node-npm")).returncode == 1


def test_exit_code_2_on_usage_and_unreadable(tmp_path):
    missing = run("--root", str(tmp_path), "nope.md")
    assert missing.returncode == 2 and missing.stderr.strip() and missing.stdout == ""
    assert run("--root", str(tmp_path)).returncode == 2
    assert run("--bogus").returncode == 2


def test_strict_turns_p1_into_exit_1(tmp_path):
    root = make_repo(tmp_path, {"README.md": "# T\n\n[x](#nope)\n"})
    assert run("--root", str(root)).returncode == 0
    assert run("--root", str(root), "--strict").returncode == 1


# ---------------------------------------------------------------- sync and safety


def test_tells_md_in_sync():
    spec = importlib.util.spec_from_file_location("readme_keeper_check", SCRIPT)
    assert spec is not None and spec.loader is not None
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    known = {entry.lower() for entries in check.LEXICONS.values() for entry in entries}
    listed = []
    for line in TELLS.read_text(encoding="utf-8").splitlines():
        if line.startswith("Entries:"):
            listed += [e.strip() for e in line[len("Entries:") :].split(",") if e.strip()]
    assert len(listed) > 30
    missing = [e for e in listed if e.lower() not in known]
    assert not missing, f"in tells.md but not in check.py: {missing}"


HOSTILE = {
    "brackets": "[" * 80000,
    "unclosed_comment": "<!--" * 20000,
    "backticks": "`" * 80000,
    "fence_lines": "```\n" * 20000,
    "link_opens": "](" * 40000,
    "image_opens": "![](" * 20000,
    "mixed": "[`<!--" * 13000,
    "heading_spaces": "# " + " " * 80000 + "#",
    "marker_spam": "<!-- readme-keeper:start x " * 3000,
    "sentences": ". " * 40000,
    "duplicate_headings": "# a\n" * 40000,
}


def test_hostile_input_finishes_fast(tmp_path):
    for name, text in HOSTILE.items():
        root = make_repo(tmp_path / name, {"README.md": text})
        try:
            result = run("--root", str(root), "--prose", "--json", timeout=1.5)
        except subprocess.TimeoutExpired:
            raise AssertionError(f"{name}: check.py did not finish in 1.5 s") from None
        assert result.returncode in (0, 1), (name, result.stderr)


def test_license_badge_host_is_parsed(tmp_path):
    # A license badge counts only when its host is shields.io or badgen.net, not when that
    # string appears elsewhere in the URL.
    real = "![license](https://img.shields.io/badge/license-MIT-blue)"
    lookalike = "![license](https://example.com/img?src=shields.io/license-MIT)"
    for badge, expected in ((real, 1), (lookalike, 0)):
        root = make_repo(tmp_path / str(expected), {"README.md": f"# T\n\n{badge}\n"})
        _, rep = report(root)
        assert len(find(rep, "license")) == expected, badge
