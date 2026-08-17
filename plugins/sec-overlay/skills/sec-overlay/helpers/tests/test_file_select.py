"""Tests for sec_overlay.file_select — allowlist, exclude globs, and partitioning."""

from __future__ import annotations

import fnmatch

import pytest

from sec_overlay.diffscope import ChangedFile
from sec_overlay.file_select import (
    ALLOWED_EXTENSIONS,
    DEFAULT_EXCLUDE_GLOBS,
    DEFAULT_MAX_DIFF_LINES,
    EXCLUSION_REASONS,
    ExcludedFile,
    Selection,
    _is_generated,
    _normalize_path,
    partition,
)

_REPRESENTATIVE_EXTENSIONS = [
    ".py", ".go", ".rs", ".ts", ".tsx", ".java", ".rb", ".c", ".sql", ".yaml",
]


@pytest.mark.parametrize("ext", _REPRESENTATIVE_EXTENSIONS)
def test_representative_extensions_are_allowlisted(ext: str) -> None:
    assert ext in ALLOWED_EXTENSIONS


def test_absent_extension_is_not_allowlisted() -> None:
    assert ".exe" not in ALLOWED_EXTENSIONS


def test_extension_match_is_case_insensitive() -> None:
    records = [ChangedFile(path="src/main.PY", status="M")]
    selection = partition(records)
    assert selection.reviewable == records
    assert selection.excluded == []


def test_path_with_no_extension_is_not_allowlisted() -> None:
    records = [ChangedFile(path="Makefile", status="M")]
    selection = partition(records)
    assert selection.excluded == [ExcludedFile(path="Makefile", reason="not-allowlisted")]


_GLOB_EXAMPLES: list[tuple[str, str]] = [
    ("**/*_test.go", "pkg/foo_test.go"),
    ("**/src/test/java/**/*.java", "root/src/test/java/pkg/foo.java"),
    ("**/src/test/**/*.kt", "root/src/test/pkg/foo.kt"),
    ("**/*.test.js", "src/app.test.js"),
    ("**/*.test.jsx", "src/app.test.jsx"),
    ("**/*.test.ts", "src/app.test.ts"),
    ("**/*.test.tsx", "src/app.test.tsx"),
    ("**/*.spec.js", "src/app.spec.js"),
    ("**/*.spec.jsx", "src/app.spec.jsx"),
    ("**/*.spec.ts", "src/app.spec.ts"),
    ("**/*.spec.tsx", "src/app.spec.tsx"),
    ("**/__tests__/**", "src/__tests__/foo.js"),
    ("**/test/**/*_test.py", "root/test/sub/foo_test.py"),
    ("**/tests/**/*_test.py", "root/tests/sub/foo_test.py"),
    ("**/*_test.py", "sub/foo_test.py"),
    ("**/*_spec.rb", "sub/foo_spec.rb"),
    ("**/spec/**/*_spec.rb", "root/spec/sub/foo_spec.rb"),
    ("**/*test.java", "sub/footest.java"),
    ("**/*tests.java", "sub/footests.java"),
    ("**/*_test.rs", "sub/foo_test.rs"),
    ("**/oh_modules/**", "sub/oh_modules/foo.js"),
    ("**/*.test.ets", "sub/app.test.ets"),
    ("**/test/**/*.jl", "root/test/sub/foo.jl"),
    ("**/test/**/*.hs", "root/test/sub/foo.hs"),
    ("**/*spec.hs", "sub/foospec.hs"),
    ("**/test/**/*.lhs", "root/test/sub/foo.lhs"),
    ("**/*spec.lhs", "sub/foospec.lhs"),
    ("**/tests/**/*.nim", "root/tests/sub/foo.nim"),
    ("**/__snapshots__/**", "sub/__snapshots__/foo.snap"),
    ("**/*.snap", "sub/foo.snap"),
    ("**/testdata/**", "sub/testdata/foo.json"),
    ("**/fixtures/**", "sub/fixtures/foo.json"),
    ("**/*.generated.*", "sub/foo.generated.go"),
    ("**/*.gen.go", "sub/foo.gen.go"),
    ("**/*.pb.go", "sub/foo.pb.go"),
    ("**/*.pb.cc", "sub/foo.pb.cc"),
    ("**/*.pb.h", "sub/foo.pb.h"),
    ("**/*test.swift", "sub/footest.swift"),
    ("**/*tests.swift", "sub/footests.swift"),
    ("**/tests/**/*.swift", "root/tests/sub/foo.swift"),
]


def test_glob_examples_cover_every_default_exclude_glob() -> None:
    assert [glob for glob, _ in _GLOB_EXAMPLES] == list(DEFAULT_EXCLUDE_GLOBS)


@pytest.mark.parametrize(("glob", "example_path"), _GLOB_EXAMPLES)
def test_each_default_exclude_glob_matches_its_example_path(glob: str, example_path: str) -> None:
    # Match against the specific pattern, not the _is_generated aggregate — several patterns
    # overlap (e.g. "**/*_test.py" also matches "**/test/**/*_test.py" examples), which would
    # hide a pattern that stopped matching its own documented example.
    assert fnmatch.fnmatch(example_path, glob)
    assert _is_generated(example_path)


def test_generated_glob_excludes_even_an_allowlisted_extension() -> None:
    records = [ChangedFile(path="sub/foo_test.py", status="M")]
    selection = partition(records)
    assert selection.excluded == [ExcludedFile(path="sub/foo_test.py", reason="generated")]
    assert selection.reviewable == []


def test_quoted_and_unquoted_nonascii_paths_normalize_to_the_same_string() -> None:
    plain = "café.py"
    quoted = '"caf\\303\\251.py"'
    assert _normalize_path(plain) == _normalize_path(quoted) == plain


def test_empty_record_list_returns_empty_selection() -> None:
    assert partition([]) == Selection(reviewable=[], excluded=[])


def test_deleted_record_is_excluded_with_deleted_reason() -> None:
    records = [ChangedFile(path="src/main.py", status="D")]
    selection = partition(records)
    assert selection.excluded == [ExcludedFile(path="src/main.py", reason="deleted")]


def test_binary_path_is_excluded_even_with_an_allowlisted_extension() -> None:
    records = [ChangedFile(path="src/main.py", status="M")]
    selection = partition(records, binary_paths=frozenset({"src/main.py"}))
    assert selection.excluded == [ExcludedFile(path="src/main.py", reason="binary")]
    assert selection.reviewable == []


def test_record_over_the_diff_line_cap_is_excluded_as_too_large() -> None:
    records = [ChangedFile(path="src/main.py", status="M")]
    selection = partition(
        records, diff_line_counts={"src/main.py": DEFAULT_MAX_DIFF_LINES + 1}
    )
    assert selection.excluded == [ExcludedFile(path="src/main.py", reason="too-large")]
    assert selection.reviewable == []


def test_record_at_exactly_the_diff_line_cap_is_reviewable() -> None:
    records = [ChangedFile(path="src/main.py", status="M")]
    selection = partition(records, diff_line_counts={"src/main.py": DEFAULT_MAX_DIFF_LINES})
    assert selection.reviewable == records
    assert selection.excluded == []


def test_excluded_file_construction_rejects_a_reason_outside_the_enum() -> None:
    with pytest.raises(ValueError, match="nope"):
        ExcludedFile(path="a.py", reason="nope")


def test_every_excluded_file_across_the_fixture_set_has_an_enum_reason() -> None:
    records = [
        ChangedFile(path="src/deleted.py", status="D"),
        ChangedFile(path="src/binary.bin", status="M"),
        ChangedFile(path="sub/foo_test.py", status="M"),
        ChangedFile(path="src/no_ext", status="M"),
        ChangedFile(path="src/huge.py", status="M"),
        ChangedFile(path="src/kept.py", status="M"),
    ]
    selection = partition(
        records,
        binary_paths=frozenset({"src/binary.bin"}),
        diff_line_counts={"src/huge.py": DEFAULT_MAX_DIFF_LINES + 1},
    )
    assert {excluded.reason for excluded in selection.excluded} <= EXCLUSION_REASONS
    assert selection.reviewable == [ChangedFile(path="src/kept.py", status="M")]
