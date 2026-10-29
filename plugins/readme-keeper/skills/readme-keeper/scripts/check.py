#!/usr/bin/env python3
"""Check a README against the repo it describes. Stdlib only, offline by default.

``check.py`` reads one or more README files and compares each claim with the files in
the repo: commands, paths, anchors, license, badges, and region markers. With ``--links``
it also asks each external URL whether it answers. With ``--prose`` it adds a small list
of prose tells. It reports findings with a severity and a line number. It reports no
score, because a score invites a loop that games the number.

Severity tiers:

* P0: the README says something the repo contradicts. Exit code 1.
* P1: likely drift or a broken reference. Exit code 1 only with ``--strict``.
* P2: style, or a link that may be flaky.

The checker only reads files. It never runs code from the target repo, and it never
runs a command from a README. Manifests are parsed as data (``json``, ``tomllib``,
line scans). The only subprocess is ``git ls-files`` for ``--all``, with the
``core.fsmonitor`` hook turned off. The only network access is ``--links``.

The prose lists live in ``references/tells.md`` for human readers and in the constants
below. A test (``tests/test_check.py``) fails when the two disagree.

Usage:
    python3 check.py                        # README.md in the current directory
    python3 check.py docs/README.md         # one file, relative to --root
    python3 check.py --all --root REPO      # every tracked README.md
    python3 check.py --links --prose        # also external links and prose tells
    python3 check.py --json --strict        # machine-readable, P1 fails the run

Exit codes: 0 when there is no P0 finding (and no P1 with ``--strict``), 1 when there is
one, 2 on a usage error or an unreadable file.

Example:
    >>> slugify("Hello, World!")
    'hello-world'
    >>> exit_code([{"severity": "P1"}], strict=True)
    1
"""

from __future__ import annotations

import argparse
import functools
import http.client
import io
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ---------------------------------------------------------------- lexicons
# Mirrors references/tells.md. Entries are lowercase.


def _csv(entries: str) -> tuple[str, ...]:
    """Split a comma-separated lexicon string into a tuple of entries.

    Args:
        entries: Entries separated by commas, as written in ``tells.md``.

    Returns:
        The stripped, non-empty entries in their original order.

    Example:
        >>> _csv("delve, bolster")
        ('delve', 'bolster')
    """
    return tuple(e.strip() for e in entries.split(",") if e.strip())


AI_WORDS = _csv(
    "delve, bolster, tapestry, synergy, beacon, interplay, intricacies, intricate, vibrant, "
    "meticulous, cutting-edge, game-changing, unparalleled, ever-evolving, showcase, "
    "showcasing, leverage, leveraging, foster, fostering, multifaceted, utilize, utilizing, "
    "facilitate, cornerstone, realm, paradigm, holistic, impactful, paramount, groundbreaking, "
    "transformative"
)

MARKETING = _csv(
    "empower, unlock, elevate, seamless, streamline, revolutioniz, supercharge, next-level, "
    "best-in-class, world-class, game-changer, harness the power"
)

TRANSITIONS = _csv(
    "additionally, furthermore, moreover, importantly, notably, ultimately, consequently, "
    "in fact, needless to say, in other words, essentially, indeed"
)

# Name -> entries, for the sync test. One entry per `Entries:` line in tells.md.
LEXICONS = {"ai_words": AI_WORDS, "marketing": MARKETING, "transitions": TRANSITIONS}

# ---------------------------------------------------------------- constants

REGIONS = ("badges", "install", "quickstart", "commands", "env", "structure", "license", "toc")
SHELL_INFO = frozenset({"", "sh", "bash", "shell", "zsh", "console", "shellsession", "terminal"})
SKIP_DIRS = frozenset({"node_modules", ".git", ".venv", "venv"})
LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
USER_AGENT = "readme-keeper-check"

LOCKS = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
}
ECOSYSTEMS = {"npm": "node", "pnpm": "node", "yarn": "node", "uv": "py", "poetry": "py"}
INSTALL_VERBS = {
    "npm": {"install", "i", "ci", "add"},
    "pnpm": {"install", "i", "add"},
    "yarn": {"install", "add"},
    "uv": {"sync", "add"},
    "poetry": {"install", "add"},
}
# pnpm and yarn run a package.json script for any word that is not one of their own commands.
NODE_BUILTINS: frozenset[str] = frozenset(
    "install i add remove rm uninstall update up upgrade dlx exec init create link unlink "
    "publish pack audit outdated why list ls ci config cache store env setup patch rebuild "
    "prune fetch import deploy dedupe info login logout whoami version help workspace "
    "workspaces global set bin licenses check".split()
)
# A flag from this set means the script may live in another package, so the command is skipped.
SCOPE_FLAGS: frozenset[str] = frozenset(
    "-w --workspace --workspaces -ws --filter -F -r --recursive --prefix -C --cwd --dir".split()
)
PY_BUILTINS = frozenset({"python", "python3", "pip"})
PATH_EXTS = frozenset(
    "md py js ts tsx jsx json toml yaml yml sh go rs txt cfg ini lock html css mod sum png jpg "
    "svg gif rb java c h cpp env example".split()
)
COVERAGE_FILES = (
    ".coveragerc",
    "codecov.yml",
    ".codecov.yml",
    ".coveralls.yml",
    "coveralls.yml",
    ".nycrc",
    ".nycrc.json",
    ".c8rc.json",
    "tarpaulin.toml",
    ".tarpaulin.toml",
)
LICENSE_NAMES = {
    "MIT": r"(?<![a-z])mit(?![a-z])",
    "APACHE": r"apache",
    "BSD": r"(?<![a-z])bsd(?![a-z])",
    "AGPL": r"agpl|affero",
    "LGPL": r"lgpl|lesser general",
    "GPL": r"(?<![a-z])gpl|gnu general public",
    "MPL": r"(?<![a-z])mpl(?![a-z])|mozilla public",
    "ISC": r"(?<![a-z])isc(?![a-z])",
    "UNLICENSE": r"unlicense(?!d)",
    "UNLICENSED": r"unlicensed|proprietary",
    "CC0": r"cc0",
}
LICENSE_DISPLAY = {"APACHE": "Apache-2.0", "UNLICENSE": "Unlicense", "UNLICENSED": "UNLICENSED"}
LICENSE_FILE_PHRASES = (
    ("permission is hereby granted, free of charge", "MIT"),
    ("apache license", "APACHE"),
    ("gnu affero", "AGPL"),
    ("gnu lesser general", "LGPL"),
    ("gnu general public", "GPL"),
    ("redistribution and use in source and binary forms", "BSD"),
    ("mozilla public license", "MPL"),
    ("permission to use, copy, modify, and/or distribute", "ISC"),
    ("free and unencumbered software", "UNLICENSE"),
)

_FAMILIES = {name: re.compile(rx, re.I) for name, rx in LICENSE_NAMES.items()}
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:")
_PATH_CHARS = re.compile(r"[\w.@+\-/]+")
_LINK = re.compile(r"(!?)\[[^\[\]\n]*\]\(\s*(<[^<>\n]*>|[^()\s]*)")
_REFDEF = re.compile(r"^ {0,3}\[[^\[\]\n]+\]:[ \t]*(<[^<>\n]*>|\S+)")
_ATTR = re.compile(r"""\b(href|src|id|name)=["']([^"'\n]*)["']""", re.I)
_AUTOLINK = re.compile(r"<(https?://[^<>\s]+)>", re.I)
_CODE = re.compile(r"`([^`\n]+)`")
_MARKER = re.compile(r"<!--[ \t]*readme-keeper:(start|end)[ \t]+([\w-]+)[ \t]*-->")
_MD_LINK_TEXT = re.compile(r"!?\[([^\[\]]*)\]\([^()]*\)")
_HTML_TAG = re.compile(r"<[^<>]*>")
_LINK_TARGET = re.compile(r"\]\([^()]*\)")
_URL = re.compile(r"https?://\S+")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CMD_SPLIT = re.compile(r"&&|\|\||;|\|")
_GH_WORKFLOW = re.compile(
    r"github\.com/[^/]+/[^/]+/actions/workflows/([^/?#]+)/badge\.svg"
    r"|shields\.io/github/actions/workflow/status/[^/]+/[^/]+/([^/?#]+)",
    re.I,
)
_REGISTRY = re.compile(r"shields\.io/(npm|pypi|crates)/(?!l/)|badge\.fury\.io/(js|py)/", re.I)
_COVERAGE = re.compile(r"codecov|coveralls|badge/coverage", re.I)
_REGISTRY_ECO = {"npm": "npm", "js": "npm", "pypi": "pypi", "py": "pypi", "crates": "crates"}
_REGISTRY_FILE = {"npm": "package.json", "pypi": "pyproject.toml", "crates": "Cargo.toml"}
_CI_FILES = (("travis", ".travis.yml"), ("circleci", ".circleci/config.yml"))

# ---------------------------------------------------------------- license names


def families(text: str) -> set[str]:
    """Find the license families a piece of text names.

    Matching is case-insensitive and respects word edges, so ``permit`` is not MIT and
    ``LGPL`` is not GPL. Versions are not compared.

    Args:
        text: A README line, a manifest ``license`` value, or the head of a license file.

    Returns:
        Upper-case family keys such as ``MIT``, ``APACHE``, ``GPL``.

    Example:
        >>> sorted(families("MIT OR Apache-2.0"))
        ['APACHE', 'MIT']
        >>> sorted(families("LGPL-3.0, not a permit"))
        ['LGPL']
    """
    return {name for name, rx in _FAMILIES.items() if rx.search(text)}


def _license_label(fams: set[str]) -> str:
    """Format a set of families for a message."""
    return ", ".join(sorted(LICENSE_DISPLAY.get(f, f) for f in fams)) or "unknown"


def _file_families(text: str) -> set[str]:
    """Find the family of a LICENSE file from its boilerplate or its title."""
    low = text[:8000].lower()
    found = {fam for phrase, fam in LICENSE_FILE_PHRASES if phrase in low}
    return found or families(text[:300])


# ---------------------------------------------------------------- facts from the repo


class Facts:
    """Evidence read from the manifests in a directory chain.

    Holds only sets and small dicts, so two chains merge by union. Nothing here comes
    from running code: every value is read from a file as data.

    Example:
        >>> f = Facts()
        >>> f.scripts["npm"].add("build")
        >>> g = Facts()
        >>> g.merge(f)
        >>> sorted(g.scripts["npm"])
        ['build']
    """

    SCRIPT_KINDS = ("npm", "node-deps", "make", "just", "py", "py-deps", "cargo")

    def __init__(self) -> None:
        """Create empty evidence."""
        self.scripts: dict[str, set[str]] = {k: set() for k in self.SCRIPT_KINDS}
        self.locks: dict[str, str] = {}  # manager -> lockfile name
        self.registry: set[str] = set()  # ecosystems with a public, named manifest
        self.private: set[str] = set()  # ecosystems whose manifest is private
        self.licenses: set[str] = set()  # license families the repo states
        self.license_sources: list[str] = []  # where the repo states a license
        self.coverage = False

    def merge(self, other: Facts) -> None:
        """Add the evidence of another Facts object into this one.

        Args:
            other: The evidence to add. It is not changed.
        """
        for kind, names in other.scripts.items():
            self.scripts[kind] |= names
        self.locks.update(other.locks)
        self.registry |= other.registry
        self.private |= other.private
        self.licenses |= other.licenses
        self.license_sources += other.license_sources
        self.coverage = self.coverage or other.coverage


def _load(path: Path, loader) -> dict:
    """Parse a manifest as data. Returns {} when it is missing, broken, or not a table."""
    try:
        data = loader(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


def _d(value: object) -> dict:
    """Return the value when it is a dict, else an empty dict."""
    return value if isinstance(value, dict) else {}


def _keys(value: object) -> set[str]:
    """Return the string keys of a dict, or an empty set."""
    return {k for k in value if isinstance(k, str)} if isinstance(value, dict) else set()


def _norm(name: str) -> str:
    """Normalize a Python package name for comparison."""
    return name.lower().replace("_", "-")


def _req_names(items: object) -> set[str]:
    """Read package names out of a list of requirement strings."""
    names = set()
    for item in items if isinstance(items, list) else []:
        if isinstance(item, str) and (m := re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", item)):
            names.add(_norm(m.group()))
    return names


def _state_license(f: Facts, source: str, value: object) -> None:
    """Record a license value found in a manifest."""
    if isinstance(value, dict):
        value = value.get("type") or value.get("text") or "see file"
    if isinstance(value, str) and value.strip():
        fams = families(value)
        f.licenses |= fams
        f.license_sources.append(f"{source}: {value.strip()[:40]}")


def _read_node(d: Path, f: Facts) -> None:
    """Read package.json."""
    pkg = _load(d / "package.json", json.loads)
    if not pkg:
        return
    f.scripts["npm"] |= _keys(pkg.get("scripts"))
    f.scripts["node-deps"] |= _keys(pkg.get("dependencies")) | _keys(pkg.get("devDependencies"))
    _state_license(f, "package.json", pkg.get("license"))
    if isinstance(pkg.get("name"), str) and pkg["name"]:
        (f.private if pkg.get("private") is True else f.registry).add("npm")
    scripts = " ".join(str(v) for v in _d(pkg.get("scripts")).values())
    if "nyc" in pkg or "c8" in pkg or "coverage" in scripts:
        f.coverage = True


def _read_python(d: Path, f: Facts) -> None:
    """Read pyproject.toml."""
    data = _load(d / "pyproject.toml", tomllib.loads)
    if not data:
        return
    proj, tool = _d(data.get("project")), _d(data.get("tool"))
    poetry = _d(tool.get("poetry"))
    f.scripts["py"] |= _keys(proj.get("scripts")) | _keys(proj.get("gui-scripts"))
    f.scripts["py"] |= _keys(poetry.get("scripts"))
    deps = _req_names(proj.get("dependencies")) | _req_names(
        _d(tool.get("uv")).get("dev-dependencies")
    )
    for group in (
        *_d(proj.get("optional-dependencies")).values(),
        *_d(data.get("dependency-groups")).values(),
    ):
        deps |= _req_names(group)
    deps |= {
        _norm(k) for k in _keys(poetry.get("dependencies")) | _keys(poetry.get("dev-dependencies"))
    }
    for group in _d(poetry.get("group")).values():
        deps |= {_norm(k) for k in _keys(_d(group).get("dependencies"))}
    f.scripts["py-deps"] |= deps
    _state_license(f, "pyproject.toml", proj.get("license") or poetry.get("license"))
    classifiers = proj.get("classifiers")
    classifiers = classifiers if isinstance(classifiers, list) else []
    for cls in classifiers:
        if isinstance(cls, str) and cls.startswith("License ::"):
            f.licenses |= families(cls.rsplit("::", 1)[-1])
            f.license_sources.append(f"pyproject.toml: {cls[:50]}")
    name = proj.get("name") or poetry.get("name")
    private = "Private :: Do Not Upload" in classifiers
    if isinstance(name, str) and name:
        (f.private if private else f.registry).add("pypi")
    if "coverage" in tool or "--cov" in str(_d(tool.get("pytest"))):
        f.coverage = True


def _read_cargo(d: Path, f: Facts) -> None:
    """Read Cargo.toml and the default binary layout."""
    data = _load(d / "Cargo.toml", tomllib.loads)
    pkg = _d(data.get("package"))
    if not pkg:
        return
    name = pkg.get("name")
    bins_table = data.get("bin")
    for entry in bins_table if isinstance(bins_table, list) else []:
        if isinstance(_d(entry).get("name"), str):
            f.scripts["cargo"].add(entry["name"])
    if isinstance(name, str) and (d / "src" / "main.rs").exists():
        f.scripts["cargo"].add(name)
    bins = d / "src" / "bin"
    if bins.is_dir():
        for p in bins.iterdir():
            if p.suffix == ".rs" or (p / "main.rs").exists():
                f.scripts["cargo"].add(p.stem if p.suffix == ".rs" else p.name)
    if pkg.get("license-file") or isinstance(pkg.get("license"), dict):
        f.license_sources.append("Cargo.toml: license inherited or in a file")
    _state_license(f, "Cargo.toml", pkg.get("license"))
    if isinstance(name, str) and name:
        (f.private if pkg.get("publish") in (False, []) else f.registry).add("crates")


def _make_targets(text: str) -> set[str]:
    """List the targets a Makefile defines, without running make.

    Args:
        text: Makefile source.

    Returns:
        Target names. Variables, pattern rules, and special targets such as ``.PHONY``
        are left out.

    Example:
        >>> sorted(_make_targets(".PHONY: a\\na b: c\\n\\techo x\\nV := 1\\n%.o: %.c\\n"))
        ['a', 'b']
    """
    out = set()
    for line in text.splitlines():
        if not line or line[0] in " \t#":
            continue
        head, sep, rest = line.partition(":")
        if not sep or rest.startswith("=") or any(c in head for c in "=$%"):
            continue
        for tok in head.split():
            if re.fullmatch(r"[\w.\-/]+", tok) and not (tok[0] == "." and tok[1:].isupper()):
                out.add(tok)
    return out


def _just_recipes(text: str) -> set[str]:
    """List the recipes and aliases a justfile defines, without running just.

    Args:
        text: justfile source.

    Returns:
        Recipe and alias names.

    Example:
        >>> sorted(_just_recipes("set x := 1\\nalias t := test\\ntest arg='a':\\n  echo\\n"))
        ['t', 'test']
    """
    out = set()
    for line in text.splitlines():
        if not line or line[0] in " \t#[":
            continue
        if ":=" in line:
            parts = line.split()
            if parts[0] == "alias" and len(parts) > 1:
                out.add(parts[1])
            continue
        head, sep, _ = line.partition(":")
        words = head.split()
        if sep and words and re.fullmatch(r"[A-Za-z_][\w-]*", words[0].lstrip("@")):
            out.add(words[0].lstrip("@"))
    return out


@functools.lru_cache(maxsize=None)
def _dir_facts(d: Path) -> Facts:
    """Read every manifest, lockfile, and license file of one directory."""
    f = Facts()
    try:
        entries = {e.name: e for e in os.scandir(d)}
    except OSError:
        return f
    for lock, manager in LOCKS.items():
        if lock in entries:
            f.locks[manager] = lock
    _read_node(d, f)
    _read_python(d, f)
    _read_cargo(d, f)
    plugin = _load(d / ".claude-plugin" / "plugin.json", json.loads)
    _state_license(f, ".claude-plugin/plugin.json", plugin.get("license"))
    for name, entry in entries.items():
        if name in ("Makefile", "makefile", "GNUmakefile"):
            f.scripts["make"] |= _make_targets(_read_text(Path(entry.path)))
        elif name in ("justfile", "Justfile", ".justfile"):
            f.scripts["just"] |= _just_recipes(_read_text(Path(entry.path)))
        elif name in COVERAGE_FILES:
            f.coverage = True
        elif name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "UNLICENSE")):
            if entry.is_file():
                fams = _file_families(_read_text(Path(entry.path)))
                f.licenses |= fams
                f.license_sources.append(f"{name}: {_license_label(fams)}")
    return f


def _read_text(path: Path) -> str:
    """Read at most 200 KB of a file as text. Returns '' on any read error."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(200_000)
    except OSError:
        return ""


def _chain(readme_dir: Path, root: Path) -> list[Path]:
    """List the directories from the README's directory up to the root, nearest first."""
    if readme_dir != root and root not in readme_dir.parents:
        return [readme_dir]
    out = [readme_dir]
    while out[-1] != root:
        out.append(out[-1].parent)
    return out


def _facts(chain: list[Path]) -> Facts:
    """Merge the facts of every directory in a chain."""
    merged = Facts()
    for d in chain:
        merged.merge(_dir_facts(d))
    return merged


# ---------------------------------------------------------------- the README


def _blank_comments(text: str) -> str:
    """Replace closed HTML comments by spaces in linear time, keeping every line break.

    A regex such as ``<!--.*?-->`` rescans to the end of the text from every unclosed
    ``<!--``, which is quadratic. An unclosed comment stays in the text.

    Args:
        text: Markdown source.

    Returns:
        Text of the same length and the same line breaks.

    Example:
        >>> _blank_comments("a<!--x\\n-->b<!--open").replace(" ", ".")
        'a.....\\n...b<!--open'
    """
    out, i = [], 0
    while (j := text.find("<!--", i)) != -1:
        k = text.find("-->", j + 4)
        if k == -1:
            break
        out.append(text[i:j])
        out.append("".join("\n" if c == "\n" else " " for c in text[j : k + 3]))
        i = k + 3
    out.append(text[i:])
    return "".join(out)


def _fence(line: str) -> tuple[str, int, str] | None:
    """Read a code-fence line. Returns (character, length, info string) or None."""
    s = line.lstrip(" ")
    if len(line) - len(s) > 3 or not s or s[0] not in "`~":
        return None
    n = len(s) - len(s.lstrip(s[0]))
    info = s[n:].strip()
    if n < 3 or (s[0] == "`" and "`" in info):
        return None
    return s[0], n, info


def _heading(line: str) -> str | None:
    """Return the text of an ATX heading line, or None when the line is not one."""
    s = line.lstrip(" ")
    if len(line) - len(s) > 3 or not s.startswith("#"):
        return None
    body = s.lstrip("#")
    if len(s) - len(body) > 6 or (body and body[0] not in " \t"):
        return None
    body = body.strip()
    bare = body.rstrip("#")
    if bare != body and (not bare or bare[-1] in " \t"):
        body = bare.rstrip()
    return body


def _setext(line: str) -> bool:
    """Tell whether a line underlines the previous line as a setext heading."""
    s = line.strip()
    return len(s) >= 2 and (set(s) == {"="} or set(s) == {"-"})


def slugify(heading: str) -> str:
    """Turn a heading into its GitHub anchor.

    GitHub lower-cases the text, drops markup and punctuation (underscore and hyphen
    stay), and turns each space into a hyphen. A leading emoji leaves a leading hyphen.

    Args:
        heading: The heading text without its ``#`` marks.

    Returns:
        The anchor, without the ``#``. Duplicate headings get ``-1``, ``-2`` from the caller.

    Example:
        >>> slugify("Install & Use")
        'install--use'
        >>> slugify("`code` [Title](x.md)")
        'code-title'
    """
    text = _HTML_TAG.sub("", _MD_LINK_TEXT.sub(r"\1", heading))
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


class Doc:
    """A README split into the parts the checks need.

    ``blocks`` holds fenced code as ``(first line, info, [(line, text)])``. ``plain`` is
    the text with fenced code removed and comments kept (markers live in comments).
    ``visible`` also has comments blanked. Line numbers match the file in every list.

    Example:
        >>> d = Doc("# A b\\n\\n```sh\\nnpm test\\n```\\n[x](#a-b)\\n")
        >>> d.headings, d.refs, d.blocks[0][1]
        ([(1, 'A b')], [(6, '#a-b', False)], 'sh')
    """

    def __init__(self, text: str) -> None:
        """Parse a README.

        Args:
            text: README source.
        """
        raw = text.splitlines()
        self.blocks: list[tuple[int, str, list[tuple[int, str]]]] = []
        plain, fence = [], None
        for n, line in enumerate(raw, 1):
            found = _fence(line)
            if fence is None:
                if found:
                    fence = (found[0], found[1], n, found[2], [])
                plain.append("" if found else line)
            else:
                if found and found[0] == fence[0] and found[1] >= fence[1] and not found[2]:
                    self.blocks.append((fence[2], fence[3], fence[4]))
                    fence = None
                else:
                    fence[4].append((n, line))
                plain.append("")
        if fence:
            self.blocks.append((fence[2], fence[3], fence[4]))
        self.plain = plain
        self.visible = _blank_comments("\n".join(plain)).split("\n")
        self.refs: list[tuple[int, str, bool]] = []  # (line, target, is_image)
        self.ids: set[str] = set()
        self.headings: list[tuple[int, str]] = []
        prev = ""
        for n, line in enumerate(self.visible, 1):
            self._scan_refs(n, line)
            h = _heading(line)
            if h is None and prev.strip() and _setext(line):
                if not prev.lstrip().startswith(("#", ">", "|", "-", "*", "+", "<", "[")):
                    h = prev.strip()
            if h:
                self.headings.append((n, h))
            prev = line
        self.slugs = self._slugs()

    def _scan_refs(self, n: int, line: str) -> None:
        """Collect link targets and HTML ids from one visible line."""
        if "](" in line:
            for m in _LINK.finditer(line):
                self._add(n, m.group(2), bool(m.group(1)))
        if "]:" in line and (m := _REFDEF.match(line)):
            self._add(n, m.group(1), False)
        if "://" in line and "<" in line:
            for m in _AUTOLINK.finditer(line):
                self._add(n, m.group(1), False)
        if "=" in line:
            for m in _ATTR.finditer(line):
                attr, value = m.group(1).lower(), m.group(2)
                if attr in ("id", "name"):
                    self.ids.add(value.lower())
                else:
                    self._add(n, value, attr == "src")

    def _add(self, n: int, target: str, image: bool) -> None:
        """Record a non-empty link target."""
        target = target.strip().strip("<>").strip()
        if target:
            self.refs.append((n, target, image))

    def _slugs(self) -> set[str]:
        """Compute the anchors of all headings, with GitHub's duplicate suffixes."""
        seen: set[str] = set()
        counts: dict[str, int] = {}
        for _, text in self.headings:
            base = slugify(text)
            n = counts.get(base, 0)
            slug = base if n == 0 else f"{base}-{n}"
            while slug in seen:
                n += 1
                slug = f"{base}-{n}"
            counts[base] = n + 1
            seen.add(slug)
        return seen


def _f(check: str, severity: str, line: int, message: str, evidence: str = "") -> dict:
    """Build one finding."""
    return {
        "check": check,
        "severity": severity,
        "line": line,
        "message": message,
        "evidence": evidence,
    }


def _names(items: set[str]) -> str:
    """List up to eight names for an evidence string."""
    return ", ".join(sorted(items)[:8]) or "none"


# ---------------------------------------------------------------- markers


def scan_markers(lines: list[str]) -> list[tuple[int, str]]:
    """Find marker faults: unpaired, nested, duplicate, and unknown region ids.

    Args:
        lines: README lines with fenced code already removed.

    Returns:
        One ``(line number, message)`` pair per fault, in line order.

    Example:
        >>> scan_markers(["<!-- readme-keeper:start install -->", "x"])
        [(1, 'unpaired start marker `install`')]
        >>> scan_markers(["<!-- readme-keeper:start a -->"])[0][1]
        'unknown region id `a`'
    """
    out: list[tuple[int, str]] = []
    stack: list[tuple[str, int]] = []
    seen: set[str] = set()
    for n, line in enumerate(lines, 1):
        if "readme-keeper:" not in line:
            continue
        for m in _MARKER.finditer(line):
            kind, rid = m.group(1), m.group(2)
            if rid not in REGIONS:
                out.append((n, f"unknown region id `{rid}`"))
            if kind == "start":
                if rid in seen:
                    out.append((n, f"duplicate region `{rid}`"))
                if stack:
                    out.append((n, f"nested marker `{rid}` inside `{stack[-1][0]}`"))
                seen.add(rid)
                stack.append((rid, n))
            elif stack and stack[-1][0] == rid:
                stack.pop()
            else:
                out.append((n, f"unpaired end marker `{rid}`"))
    out += [(n, f"unpaired start marker `{rid}`") for rid, n in stack]
    return sorted(out, key=lambda item: item[0])


def _check_markers(doc: Doc) -> list[dict]:
    """Report marker faults as P0."""
    evidence = "region ids: " + ", ".join(REGIONS)
    return [_f("markers", "P0", n, msg, evidence) for n, msg in scan_markers(doc.plain)]


# ---------------------------------------------------------------- commands and package manager


def _segments(line: str):
    """Yield the token list of each command in one shell line."""
    line = line.strip()
    if line.startswith(("$ ", "> ", "% ")):
        line = line[2:]
    line = line.split(" #", 1)[0].rstrip("\\ ").strip()
    if not line or line.startswith("#"):
        return
    for part in _CMD_SPLIT.split(line):
        toks = part.split()
        while toks and "=" in toks[0] and toks[0].split("=")[0].isidentifier():
            toks.pop(0)
        if toks and toks[0] == "sudo":
            toks.pop(0)
        if toks:
            yield toks


def _pm_action(tool: str, args: list[str]) -> tuple[str | None, str | None]:
    """Classify a package-manager command as an install or a run of a named script."""
    if tool == "uv" and args[:2] == ["pip", "install"]:
        return "install", None
    if not args:
        return ("install", None) if tool == "yarn" else (None, None)
    verb = args[0]
    if verb in INSTALL_VERBS[tool]:
        return "install", None
    if verb in ("run", "run-script"):
        name = args[1] if len(args) > 1 and not args[1].startswith("-") else None
        return "run", name
    if tool in ("pnpm", "yarn") and not verb.startswith("-") and verb not in NODE_BUILTINS:
        return "run", verb
    return None, None


def _exists(rel: str, dirs: list[Path]) -> bool:
    """Tell whether a relative path exists under any directory of the chain."""
    return any((d / rel).exists() for d in dirs)


def _check_command(toks: list[str], facts: Facts, dirs: list[Path]) -> list[tuple]:
    """Check one command. Returns (check, severity, message, evidence) tuples."""
    tool, args = toks[0], toks[1:]
    cmd = " ".join(toks)[:80]
    s = facts.scripts
    out: list[tuple] = []

    def bad(message: str, evidence: str = "", check: str = "commands", sev: str = "P0") -> None:
        out.append((check, sev, f"`{cmd}`{message}", evidence))

    if tool in ECOSYSTEMS:
        kind, name = _pm_action(tool, args)
        if kind == "install" and not ({"-g", "--global"} & set(args)):
            present = {m for m in facts.locks if ECOSYSTEMS[m] == ECOSYSTEMS[tool]}
            if present and tool not in present:
                lock = _names({facts.locks[m] for m in present})
                bad(
                    f" uses {tool}, but the repo is locked to {_names(present)}",
                    f"lockfile: {lock}",
                    "package-manager",
                    "P1",
                )
        elif kind == "run" and name and not SCOPE_FLAGS & set(args):
            if tool in ("npm", "pnpm", "yarn"):
                known = s["npm"] | (s["node-deps"] if tool != "npm" else set())
                if name not in known:
                    bad(f": no script `{name}` in package.json", "scripts: " + _names(s["npm"]))
            elif "/" in name or name.endswith(".py"):
                if not _exists(name, dirs):
                    bad(f": path `{name}` does not exist")
            elif name not in PY_BUILTINS | s["py"] and _norm(name) not in s["py-deps"]:
                bad(
                    f": no entry point or dependency `{name}` in pyproject.toml",
                    "entry points: " + _names(s["py"]),
                )
    elif tool == "make" and not any(a.startswith(("-C", "-f", "--dir", "--file")) for a in args):
        for n in (a for a in args if not a.startswith("-") and "=" not in a and not a.isdigit()):
            if n not in s["make"]:
                bad(f": no make target `{n}`", "targets: " + _names(s["make"]))
    elif tool == "just" and args and not args[0].startswith("-") and not {"=", "::"} & set(args[0]):
        if args[0] not in s["just"]:
            bad(f": no just recipe `{args[0]}`", "recipes: " + _names(s["just"]))
    elif tool == "cargo" and args[:1] == ["run"]:
        for i, a in enumerate(args):
            name = a[6:] if a.startswith("--bin=") else None
            if a == "--bin" and i + 1 < len(args):
                name = args[i + 1]
            if name and name not in s["cargo"]:
                bad(f": no binary `{name}` in Cargo.toml", "binaries: " + _names(s["cargo"]))
    elif tool == "go" and args[:1] == ["run"]:
        paths = (
            a
            for a in args[1:]
            if a in (".", "..") or a.startswith(("./", "../")) or a.endswith(".go")
        )
        if (path := next(paths, None)) and not _exists(path, dirs):
            bad(f": path `{path}` does not exist")
    return out


def _cd_target(arg: str, cur: Path, readme_dir: Path, root: Path) -> Path | None:
    """Resolve the argument of ``cd``: the current directory, the README folder, then the root.

    Returns None for ``~``, ``-``, ``$VAR``, an absolute path, or a folder that does not
    exist inside the repo, because then the working directory is unknown.
    """
    arg = arg.strip("'\"")
    if not arg or arg.startswith(("~", "$", "-")) or os.path.isabs(arg):
        return None
    for base in dict.fromkeys((cur, readme_dir, root)):
        cand = Path(os.path.normpath(base / arg))
        if cand.is_dir() and (cand == root or root in cand.parents):
            return cand
    return None


def _check_commands(
    doc: Doc, facts: Facts, dirs: list[Path], readme_dir: Path, root: Path
) -> list[dict]:
    """Check every command in the shell blocks.

    A ``cd DIR`` in a block (alone on a line or before ``&&`` or ``;``) moves the working
    directory for the commands after it, to the end of the block. Those commands are
    checked against the manifests of DIR. When DIR cannot be resolved, the commands after
    the ``cd`` are skipped, never guessed.
    """
    out = []
    for _, info, body in doc.blocks:
        if (info.split(None, 1)[0].lower() if info else "") not in SHELL_INFO:
            continue
        cur, cur_dirs, cur_facts = readme_dir, dirs, facts
        known = True
        for n, line in body:
            for toks in _segments(line):
                if toks[0] == "cd":
                    target = _cd_target(toks[1], cur, readme_dir, root) if len(toks) == 2 else None
                    known = target is not None
                    if target:
                        cur, cur_dirs = target, _chain(target, root)
                        cur_facts = _facts(cur_dirs)
                    continue
                if not known:
                    continue
                for check, sev, msg, ev in _check_command(toks, cur_facts, cur_dirs):
                    out.append(_f(check, sev, n, msg, ev))
    return out


# ---------------------------------------------------------------- paths and anchors


def _local_target(target: str) -> str | None:
    """Reduce a link target to a decoded file path, or None for URLs and anchors."""
    t = target.strip()
    if (
        not t
        or t.startswith(("#", "//"))
        or _SCHEME.match(t)
        or any(c in t for c in "<$")
        or "{{" in t
    ):
        return None
    t = urllib.parse.unquote(t.split("#", 1)[0].split("?", 1)[0])
    return t or None


def _looks_like_path(s: str) -> bool:
    """Tell whether an inline-code span reads as a repo file path."""
    if not _PATH_CHARS.fullmatch(s) or s.startswith(("/", "-", "@", "~")):
        return False
    last = s.rsplit("/", 1)[-1]
    if last.startswith(".") and last.count(".") == 1:
        return False  # an extension pair such as `.h/.c`, not a file
    if s.startswith(("./", "../")):
        return True
    return "/" in s and (s.endswith("/") or s.rsplit("/", 1)[-1].rpartition(".")[2] in PATH_EXTS)


@functools.lru_cache(maxsize=None)
def _tracked_blob(root: str) -> str:
    """Join every tracked file path of the repo into one searchable string.

    Each path becomes ``/a/b/c.py/`` on its own line, so ``"/b/c.py/"`` and ``"/a/b/"``
    both match as whole path segments, for a file and for a directory above it. The list
    comes from ``git ls-files`` (fsmonitor off). When git is absent, fails, or lists
    nothing, the tree is walked and ``node_modules``, ``.git``, ``.venv``, and ``venv`` are
    skipped.

    Args:
        root: Repo root as a string, so the result can be cached.

    Returns:
        The joined paths, or an empty string when the root has no files.
    """
    names: list[str] = []
    try:
        listing = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", root, "ls-files", "-z"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout.decode("utf-8", "replace")
        names = [n for n in listing.split("\0") if n]
    except (OSError, subprocess.SubprocessError):
        pass
    if not names:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            rel = os.path.relpath(dirpath, root)
            names += [f if rel == "." else f"{rel}/{f}".replace(os.sep, "/") for f in filenames]
    return "".join(f"/{n}/\n" for n in names)


def _inline_path_found(span: str, readme_dir: Path, root: Path) -> bool:
    """Look for an inline-code path in the README folder, the repo root, then tracked files.

    The last step is a suffix match on whole path segments, so ``scripts/lint.py`` matches
    ``plugins/p/skills/s/scripts/lint.py`` and ``skills/s/`` matches a tracked directory.

    Args:
        span: The text of the inline-code span.
        readme_dir: Folder of the README.
        root: Repo root.

    Returns:
        True when the path exists in any of the three places.

    Example:
        >>> _inline_path_found("no/such/place.py", Path("/nonexistent/a"), Path("/nonexistent"))
        False
    """
    if any(os.path.exists(os.path.join(d, span)) for d in (readme_dir, root)):
        return True
    needle = os.path.normpath(span).replace(os.sep, "/")
    while needle.startswith("../"):
        needle = needle[3:]
    needle = needle.strip("/")
    return bool(needle) and f"/{needle}/" in _tracked_blob(str(root))


def _check_paths(doc: Doc, readme_dir: Path, root: Path) -> list[dict]:
    """Report missing link targets as P0 and unresolved inline-code paths as P2.

    A link, an image, or an ``<img src>`` that points at a missing relative file is P0.
    An inline-code path is a hint, not a promise, so it is never above P2.
    """
    out = []
    for n, target, _ in doc.refs:
        rel = _local_target(target)
        if rel is None:
            continue
        base = root if rel.startswith("/") else readme_dir
        full = os.path.normpath(os.path.join(base, rel.lstrip("/")))
        if full != str(root) and not full.startswith(str(root) + os.sep):
            continue  # a GitHub UI path such as ../../issues
        if not os.path.exists(full):
            where = os.path.relpath(base, root)
            out.append(_f("paths", "P0", n, f"`{target}` does not exist", f"looked in {where}"))
    for n, line in enumerate(doc.visible, 1):
        if "`" not in line:
            continue
        for span in _CODE.findall(line):
            if _looks_like_path(span) and not _inline_path_found(span, readme_dir, root):
                msg = f"`{span}`: unresolved path, check intent"
                ev = "not in the README folder, the repo root, or any tracked file"
                out.append(_f("paths", "P2", n, msg, ev))
    return out


def _check_anchors(doc: Doc) -> list[dict]:
    """Report in-page links that match no heading slug as P1."""
    out = []
    shown = ", ".join(sorted(doc.slugs)[:6]) or "no headings"
    for n, target, _ in doc.refs:
        if not target.startswith("#"):
            continue
        anchor = urllib.parse.unquote(target[1:]).lower()
        if anchor.startswith(("fn-", "fnref-", "fn:", "fnref:")):
            continue
        anchor = anchor.removeprefix("user-content-")
        if anchor in ("", "top") or anchor in doc.slugs or anchor in doc.ids:
            continue
        out.append(_f("anchors", "P1", n, f"no heading or id for `{target}`", f"anchors: {shown}"))
    return out


# ---------------------------------------------------------------- license and badges


def _license_claims(doc: Doc) -> list[tuple[int, set[str]]]:
    """Find where the README names a license, as (line, families) pairs.

    A claim is a line in a License section, a "licensed under" sentence, or a license
    badge. A badge with no readable name gives an empty family set.
    """
    claims, in_section = [], False
    for n, line in enumerate(doc.visible, 1):
        h = _heading(line)
        if h is not None:
            in_section = h.lstrip("*_` ").lower().startswith("licen")
        low = line.lower()
        if in_section or "licensed under" in low or "released under" in low:
            if fams := families(line):
                claims.append((n, fams))
    for n, target, image in doc.refs:
        low = target.lower()
        if image and ("shields.io" in low or "badgen.net" in low) and "licen" in low:
            claims.append((n, families(low.split("licen", 1)[1])))
    return sorted(claims, key=lambda c: c[0])


def _check_license(doc: Doc, facts: Facts) -> list[dict]:
    """Compare README license claims with the LICENSE file and manifest fields."""
    claims = _license_claims(doc)
    if not claims:
        return []
    if not facts.license_sources:
        n, fams = claims[0]
        msg = f"README names a license ({_license_label(fams)}), but the repo has no LICENSE file or manifest license field"
        return [
            _f(
                "license",
                "P0",
                n,
                msg,
                "looked for LICENSE, COPYING, package.json, pyproject.toml, Cargo.toml",
            )
        ]
    if not facts.licenses:
        return []
    evidence = "; ".join(facts.license_sources[:3])
    return [
        _f(
            "license",
            "P0",
            n,
            f"README says {_license_label(fams)}, but the repo says {_license_label(facts.licenses)}",
            evidence,
        )
        for n, fams in claims
        if fams and not fams & facts.licenses
    ]


def _workflow_exists(root: Path, name: str) -> bool:
    """Tell whether a workflow file exists. A name with no extension matches any workflow."""
    folder = root / ".github" / "workflows"
    if name.endswith((".yml", ".yaml")):
        return (folder / name).is_file()
    return folder.is_dir() and any(p.suffix in (".yml", ".yaml") for p in folder.iterdir())


def _check_badges(doc: Doc, facts: Facts, root: Path) -> list[dict]:
    """Report badges that need repo evidence the repo does not have, as P1."""
    out = []
    for n, url, image in doc.refs:
        if not image:
            continue
        low, ev = url.lower(), f"badge: {url[:80]}"
        if m := _GH_WORKFLOW.search(url):
            name = urllib.parse.unquote(m.group(1) or m.group(2))
            if not _workflow_exists(root, name):
                msg = f"CI badge needs workflow `{name}`, but .github/workflows has no such file"
                out.append(_f("badges", "P1", n, msg, ev))
        for word, cfg in _CI_FILES:
            if word in low and not (root / cfg).exists():
                out.append(
                    _f("badges", "P1", n, f"CI badge needs `{cfg}`, which does not exist", ev)
                )
        if m := _REGISTRY.search(url):
            eco = _REGISTRY_ECO[(m.group(1) or m.group(2)).lower()]
            if eco not in facts.registry:
                if eco in facts.private:
                    why = "points at a private package"
                else:
                    why = f"has no {_REGISTRY_FILE[eco]} with a name"
                out.append(_f("badges", "P1", n, f"{eco} registry badge, but the repo {why}", ev))
        if _COVERAGE.search(url) and not facts.coverage:
            msg = "coverage badge, but the repo has no coverage config"
            out.append(_f("badges", "P1", n, msg, ev))
    return out


# ---------------------------------------------------------------- prose


def _lexicon_regex(entries: tuple[str, ...], lead: str = "(?<!\\w)") -> re.Pattern[str]:
    """Compile one alternation for a lexicon, longest entry first.

    One compiled pattern per lexicon keeps the cost per line small, because a hostile
    README can hold tens of thousands of lines.

    Args:
        entries: Lower-case lexicon entries.
        lead: Pattern put before the alternation. The default matches at a word start.

    Returns:
        A case-insensitive pattern whose group 1 is the matched entry.

    Example:
        >>> [m.group(1) for m in _lexicon_regex(("delve", "seam")).finditer("Delve, seamless")]
        ['Delve', 'seam']
    """
    alt = "|".join(re.escape(e) for e in sorted(entries, key=len, reverse=True))
    return re.compile(f"{lead}({alt})", re.I)


_AI_RE = _lexicon_regex(AI_WORDS)
_MARKETING_RE = _lexicon_regex(MARKETING)
_TRANSITION_RE = _lexicon_regex(TRANSITIONS, lead=r"[\W\d]*")


def _hits(rx: re.Pattern[str], text: str) -> list[str]:
    """List the distinct lexicon entries that a pattern finds, in lower case."""
    return list(dict.fromkeys(m.group(1).lower() for m in rx.finditer(text)))


def _transition_hits(text: str) -> list[str]:
    """List the filler transitions that open a sentence of the text."""
    found = []
    for part in _SENT_SPLIT.split(text):
        if (m := _TRANSITION_RE.match(part)) and not part[m.end(1) : m.end(1) + 1].isalnum():
            found.append(m.group(1).lower())
    return list(dict.fromkeys(found))


def _check_prose(doc: Doc) -> list[dict]:
    """Report em dashes and stock words outside code, as P2."""
    out = []
    for n, line in enumerate(doc.visible, 1):
        if not line.strip():
            continue
        text = _CODE.sub(" ", line) if "`" in line else line
        text = _URL.sub(" ", _LINK_TARGET.sub("]", text))
        snippet = text.strip()[:80]
        if "\u2014" in text:
            out.append(_f("prose", "P2", n, "em dash; use a colon, period, or comma", snippet))
        for word in _hits(_AI_RE, text):
            out.append(_f("prose", "P2", n, f"stock word `{word}`", snippet))
        for word in _hits(_MARKETING_RE, text):
            out.append(_f("prose", "P2", n, f"marketing word `{word}`", snippet))
        for word in _transition_hits(text):
            out.append(_f("prose", "P2", n, f"filler transition `{word}`", snippet))
    return out


# ---------------------------------------------------------------- links


def _probe(url: str) -> tuple[int | None, str]:
    """Ask one URL whether it answers: HEAD first, then GET when HEAD gets a 405."""
    try:
        host = urllib.parse.urlsplit(url).hostname or ""
        opener = urllib.request.build_opener(
            *([urllib.request.ProxyHandler({})] if host in LOOPBACK else [])
        )
        for method in ("HEAD", "GET"):
            req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
            try:
                with opener.open(req, timeout=10) as resp:
                    return resp.status, ""
            except urllib.error.HTTPError as exc:
                if exc.code == 405 and method == "HEAD":
                    continue
                return exc.code, ""
    except (OSError, ValueError, http.client.HTTPException) as exc:
        return None, str(getattr(exc, "reason", exc))
    return None, "no answer"


def check_links(urls: list[tuple[int, str]]) -> list[dict]:
    """Check external URLs. This is the only function that uses the network.

    Each URL gets a HEAD request, then a GET when the server answers 405. The timeout
    is 10 seconds and four requests run at once. A 4xx answer is P1 (a 429 is P2,
    because a rate limit is not a dead link). A timeout, a refused connection, or a
    5xx answer is P2, because those are often temporary.

    Args:
        urls: ``(line number, URL)`` pairs. Only http and https URLs belong here.

    Returns:
        One finding per URL that failed.

    Example:
        >>> check_links([])
        []
    """
    unique = list(dict.fromkeys(url for _, url in urls))
    first = {}
    for n, url in urls:
        first.setdefault(url, n)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_probe, unique))
    out = []
    for url, (status, err) in zip(unique, results):
        if status is not None and status < 400:
            continue
        if status is None:
            out.append(_f("links", "P2", first[url], f"`{url}` did not answer", err))
        else:
            sev = "P1" if 400 <= status < 500 and status != 429 else "P2"
            out.append(_f("links", sev, first[url], f"`{url}` returned HTTP {status}", ""))
    return out


def _external_urls(doc: Doc) -> list[tuple[int, str]]:
    """List the http and https targets of a README with their line numbers."""
    return [(n, t) for n, t, _ in doc.refs if t.lower().startswith(("http://", "https://"))]


# ---------------------------------------------------------------- checking


def check_text(text: str, readme: Path | str, root: Path | str, prose: bool = False) -> list[dict]:
    """Run every offline check on one README.

    Args:
        text: The README source.
        readme: Path of the README, used to find the manifests near it.
        root: Repo root. Manifests are read from the README's directory up to this root.
        prose: When true, add the prose-tell findings.

    Returns:
        Findings ordered by line. Each is a dict with ``check``, ``severity``, ``line``,
        ``message``, and ``evidence``.

    Example:
        >>> check_text("# A\\n\\n[x](#b)\\n", "/tmp/r/README.md", "/tmp/r")[0]["check"]
        'anchors'
    """
    root, readme = Path(root).resolve(), Path(readme).resolve()
    doc = Doc(text)
    chain = _chain(readme.parent, root)
    facts = _facts(chain)
    found = (
        _check_markers(doc)
        + _check_commands(doc, facts, chain, readme.parent, root)
        + _check_paths(doc, readme.parent, root)
        + _check_anchors(doc)
        + _check_license(doc, facts)
        + _check_badges(doc, facts, root)
        + (_check_prose(doc) if prose else [])
    )
    unique = {(f["check"], f["line"], f["message"]): f for f in found}
    return sorted(unique.values(), key=lambda f: f["line"])


def exit_code(findings: list[dict], strict: bool = False) -> int:
    """Map findings to the process exit code.

    Args:
        findings: Findings from any number of files. Only ``severity`` is read.
        strict: When true, a P1 finding also fails the run.

    Returns:
        1 when a P0 (or, with ``strict``, a P1) is present, else 0.

    Example:
        >>> exit_code([{"severity": "P2"}]), exit_code([{"severity": "P0"}])
        (0, 1)
    """
    failing = {"P0", "P1"} if strict else {"P0"}
    return 1 if any(f["severity"] in failing for f in findings) else 0


def find_readmes(root: Path | str) -> list[Path]:
    """List the README.md files of a repo.

    Uses ``git ls-files`` (with the fsmonitor hook off, so the target repo cannot run
    code). When git is absent, fails, or lists no README, it walks the tree and skips
    ``node_modules``, ``.git``, ``.venv``, and ``venv``.

    Args:
        root: Repo root.

    Returns:
        README.md paths in sorted order.

    Example:
        >>> find_readmes("/path/that/does/not/exist")  # doctest: +SKIP
        []
    """
    root = Path(root)
    try:
        listing = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout.decode("utf-8", "replace")
        tracked = sorted(n for n in listing.split("\0") if n.rsplit("/", 1)[-1] == "README.md")
        found = [root / n for n in tracked if (root / n).is_file()]
    except (OSError, subprocess.SubprocessError):
        found = []
    if found:
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if "README.md" in filenames:
            found.append(Path(dirpath) / "README.md")
    return sorted(found)


def render(files: list[dict]) -> str:
    """Format the findings as a human-readable report.

    Args:
        files: Entries shaped like ``{"path": str, "findings": [finding, ...]}``.

    Returns:
        A multi-line report that ends with a count line.

    Example:
        >>> print(render([{"path": "README.md", "findings": []}]))
        README.md: no findings
        <BLANKLINE>
        1 file checked: 0 P0, 0 P1, 0 P2
    """
    lines, counts = [], {"P0": 0, "P1": 0, "P2": 0}
    for entry in files:
        if not entry["findings"]:
            lines.append(f"{entry['path']}: no findings")
            continue
        lines.append(entry["path"])
        for f in entry["findings"]:
            counts[f["severity"]] += 1
            lines.append(f"  {f['severity']}  line {f['line']:<4} {f['check']}: {f['message']}")
            if f["evidence"]:
                lines.append(f"        evidence: {f['evidence']}")
    noun = "file" if len(files) == 1 else "files"
    lines += [
        "",
        f"{len(files)} {noun} checked: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Arguments after the program name. None means ``sys.argv[1:]``.

    Returns:
        The exit code: 0 or 1 by the findings, 2 for an unreadable file or no README.

    Raises:
        SystemExit: With code 2 when the arguments are invalid (raised by argparse).

    Example:
        >>> main(["--root", "/missing", "nope.md"])  # doctest: +SKIP
        2
    """
    parser = argparse.ArgumentParser(description="Check a README against the repo it describes.")
    parser.add_argument("paths", nargs="*", help="README files, relative to --root")
    parser.add_argument("--all", action="store_true", help="check every tracked README.md")
    parser.add_argument("--root", default=".", help="repo root (default: current directory)")
    parser.add_argument("--links", action="store_true", help="check external URLs (network)")
    parser.add_argument("--prose", action="store_true", help="add prose-tell findings")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--strict", action="store_true", help="exit 1 on P1 as well as P0")
    args = parser.parse_args(argv)

    for stream in (sys.stdin, sys.stdout):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    root = Path(args.root).resolve()
    targets = [Path(p) if Path(p).is_absolute() else root / p for p in args.paths]
    if args.all:
        targets += find_readmes(root)
    elif not targets:
        targets = [root / "README.md"]

    texts = {}
    for path in dict.fromkeys(p.resolve() for p in targets):
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"check.py: cannot read {path}: {exc}", file=sys.stderr)
            return 2

    files = []
    for path, text in texts.items():
        findings = check_text(text, path, root, prose=args.prose)
        if args.links:
            findings += check_links(_external_urls(Doc(text)))
            findings.sort(key=lambda f: f["line"])
        rel = path.relative_to(root).as_posix() if root in path.parents else str(path)
        files.append({"path": rel, "findings": findings})

    print(
        json.dumps({"files": files}, indent=2, ensure_ascii=False) if args.json else render(files)
    )
    return exit_code([f for entry in files for f in entry["findings"]], args.strict)


if __name__ == "__main__":
    sys.exit(main())
