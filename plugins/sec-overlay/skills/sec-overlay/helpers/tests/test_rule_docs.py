"""Conformance tests for the built-in rule docs (RULE-05).

Every assertion is driven from `BUILTIN_PATH_RULE_MAP`, `BUILTIN_DEFAULT_RULE`, and
`REQUIRED_RULE_SECTIONS`/`RULE_SECTION_SYNONYMS` rather than a hardcoded list of nine
filenames, so a future language addition only needs a map entry and a doc file — no
test edit — to be covered by these checks.
"""

from __future__ import annotations

import re

import pytest

from sec_overlay.rule_glob import (
    BUILTIN_DEFAULT_RULE,
    BUILTIN_PATH_RULE_MAP,
    REQUIRED_RULE_SECTIONS,
    RULE_SECTION_SYNONYMS,
    builtin_rule_docs_dir,
    resolve_rule_doc,
)

_HEADING_RE = re.compile(r"^#### (.+)$", re.MULTILINE)


def _sections(text: str) -> list[tuple[str, str]]:
    """Split a rule doc into (heading, body-until-next-heading) pairs, in order."""
    headings = list(_HEADING_RE.finditer(text))
    return [
        (m.group(1).strip(), text[m.end() : headings[i + 1].start() if i + 1 < len(headings) else len(text)])
        for i, m in enumerate(headings)
    ]


def _all_doc_names() -> list[str]:
    return sorted({*BUILTIN_PATH_RULE_MAP.values(), BUILTIN_DEFAULT_RULE})


# --- Task 1: map/constant shape --------------------------------------------------


def test_required_rule_sections_has_five_families():
    assert len(REQUIRED_RULE_SECTIONS) == 5
    assert set(REQUIRED_RULE_SECTIONS) == set(RULE_SECTION_SYNONYMS)


def test_builtin_path_rule_map_has_nine_distinct_docs():
    assert len(set(BUILTIN_PATH_RULE_MAP.values())) == 9


@pytest.mark.parametrize("doc_name", _all_doc_names())
def test_mapped_doc_exists_and_is_nonempty(doc_name):
    doc_path = builtin_rule_docs_dir() / doc_name
    assert doc_path.is_file(), f"{doc_name} referenced by the map but missing on disk"
    assert doc_path.read_text().strip(), f"{doc_name} is empty"


def test_no_orphan_rule_doc():
    referenced = set(BUILTIN_PATH_RULE_MAP.values())
    on_disk = {p.name for p in builtin_rule_docs_dir().glob("*.md") if p.name != "README.md"}
    orphans = on_disk - referenced
    assert not orphans, f"rule docs on disk but referenced by no map value: {orphans}"


# --- Task 2: every doc covers the five required families -------------------------


@pytest.mark.parametrize("doc_name", _all_doc_names())
def test_doc_covers_required_families_with_exclusion_blocks(doc_name):
    text = (builtin_rule_docs_dir() / doc_name).read_text()
    sections = _sections(text)
    assert len(sections) == len(REQUIRED_RULE_SECTIONS), (
        f"{doc_name} has {len(sections)} '####' sections, expected {len(REQUIRED_RULE_SECTIONS)}"
    )
    for family, (heading, body) in zip(REQUIRED_RULE_SECTIONS, sections):
        heading_lower = heading.lower()
        synonyms = RULE_SECTION_SYNONYMS[family]
        assert any(s in heading_lower for s in synonyms), (
            f"{doc_name} section {heading!r} does not match family {family!r} "
            f"(expected one of {synonyms})"
        )
        assert "do not report" in body.lower(), (
            f"{doc_name} section {heading!r} has no exclusion block"
        )


# --- Task 2: extension and representative-path resolution ------------------------


@pytest.mark.parametrize("ext", ["ts", "js", "tsx", "jsx"])
def test_ts_js_tsx_jsx_extensions_resolve_to_same_doc(ext):
    expected = (builtin_rule_docs_dir() / BUILTIN_PATH_RULE_MAP["**/*.{ts,js,tsx,jsx}"]).read_text()
    assert resolve_rule_doc(f"src/App.{ext}") == expected


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("main.go", "**/*.go"),
        ("Service.java", "**/*.java"),
        ("app.py", "**/*.py"),
        ("index.php", "**/*.{php,phtml}"),
        ("lib.rs", "**/*.rs"),
        ("Main.kt", "**/*.{kt}"),
        ("App.swift", "**/*.swift"),
    ],
)
def test_representative_path_resolves_to_mapped_doc(path, pattern):
    expected = (builtin_rule_docs_dir() / BUILTIN_PATH_RULE_MAP[pattern]).read_text()
    assert resolve_rule_doc(path) == expected


@pytest.mark.parametrize("path", ["Makefile", "docs/notes.rst"])
def test_unmatched_extension_and_no_extension_resolve_to_default(path):
    expected = (builtin_rule_docs_dir() / BUILTIN_DEFAULT_RULE).read_text()
    assert resolve_rule_doc(path) == expected


# --- Task 1/2 shared behavior: order and idempotence ------------------------------


def test_first_matching_map_entry_wins_on_collision(monkeypatch, tmp_path):
    (tmp_path / "first.md").write_text("first doc")
    (tmp_path / "second.md").write_text("second doc")
    monkeypatch.setattr("sec_overlay.rule_glob.builtin_rule_docs_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "sec_overlay.rule_glob.BUILTIN_PATH_RULE_MAP",
        {"**/a.py": "first.md", "**/*.py": "second.md"},
    )
    assert resolve_rule_doc("src/a.py") == "first doc"


def test_resolve_rule_doc_is_idempotent():
    first = resolve_rule_doc("src/a.py")
    second = resolve_rule_doc("src/a.py")
    assert first == second
