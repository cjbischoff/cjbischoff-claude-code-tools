"""Tests for review-unit grouping (SCALE-01): totality, determinism, real pairing.

`bundle.py` is a pure function over `Selection.reviewable`. These tests assert the
contract every caller relies on — no path lost or duplicated, deterministic
`unit_id`, input order preserved — and the two real grouping rules RESEARCH.md
names: impl/test pairs and locale/config siblings. Everything else falls back to
its own single-member unit.
"""

from sec_overlay.bundle import MAX_UNIT_TOKENS, ReviewUnit, group_bundles
from sec_overlay.diffscope import ChangedFile


def _cf(path: str) -> ChangedFile:
    return ChangedFile(path=path, status="M")


def test_group_bundles_empty_input_returns_empty_list():
    assert group_bundles([]) == []


def test_group_bundles_single_file_returns_one_unit():
    units = group_bundles([_cf("app.py")])
    assert len(units) == 1
    assert units[0].files == ("app.py",)


def test_group_bundles_every_path_appears_in_exactly_one_unit():
    paths = ["app.py", "tests/test_app.py", "locale/en.json", "locale/fr.json", "other.rb"]
    units = group_bundles([_cf(p) for p in paths])
    seen = [p for unit in units for p in unit.files]
    assert sorted(seen) == sorted(paths)
    assert len(seen) == len(set(seen))


def test_group_bundles_preserves_input_order():
    paths = ["z.py", "tests/test_z.py", "a.py"]
    units = group_bundles([_cf(p) for p in paths])
    # z.py and tests/test_z.py pair; a.py stands alone. z-pair appears first.
    assert units[0].files == ("z.py", "tests/test_z.py")
    assert units[1].files == ("a.py",)


def test_group_bundles_same_input_produces_byte_identical_unit_ids():
    paths = ["app.py", "tests/test_app.py"]
    first = group_bundles([_cf(p) for p in paths])
    second = group_bundles([_cf(p) for p in paths])
    assert [u.unit_id for u in first] == [u.unit_id for u in second]


def test_group_bundles_different_member_sets_produce_different_unit_ids():
    one = group_bundles([_cf("app.py")])
    two = group_bundles([_cf("other.py")])
    assert one[0].unit_id != two[0].unit_id


def test_group_bundles_pairs_python_impl_and_test_file():
    units = group_bundles([_cf("pkg/app.py"), _cf("pkg/test_app.py")])
    assert len(units) == 1
    assert set(units[0].files) == {"pkg/app.py", "pkg/test_app.py"}


def test_group_bundles_pairs_go_impl_and_test_file():
    units = group_bundles([_cf("pkg/server.go"), _cf("pkg/server_test.go")])
    assert len(units) == 1
    assert set(units[0].files) == {"pkg/server.go", "pkg/server_test.go"}


def test_group_bundles_pairs_ts_impl_and_spec_file():
    units = group_bundles([_cf("src/util.ts"), _cf("src/util.spec.ts")])
    assert len(units) == 1
    assert set(units[0].files) == {"src/util.ts", "src/util.spec.ts"}


def test_group_bundles_pairs_locale_siblings_in_same_directory():
    units = group_bundles([_cf("locale/en.json"), _cf("locale/fr.json")])
    assert len(units) == 1
    assert set(units[0].files) == {"locale/en.json", "locale/fr.json"}


def test_group_bundles_pairs_config_family_in_same_directory():
    units = group_bundles([_cf("conf/config.dev.yaml"), _cf("conf/config.prod.yaml")])
    assert len(units) == 1
    assert set(units[0].files) == {"conf/config.dev.yaml", "conf/config.prod.yaml"}


def test_group_bundles_does_not_pair_locale_files_across_directories():
    units = group_bundles([_cf("a/en.json"), _cf("b/fr.json")])
    assert len(units) == 2
    assert units[0].files == ("a/en.json",)
    assert units[1].files == ("b/fr.json",)


def test_group_bundles_unrelated_files_each_get_their_own_unit():
    units = group_bundles([_cf("app.py"), _cf("other.rb")])
    assert len(units) == 2
    assert units[0].files == ("app.py",)
    assert units[1].files == ("other.rb",)


# --- REQ-P1: C/C++ header-impl pairs, interface/impl stems, token cap split -----


def test_group_bundles_pairs_c_header_and_impl():
    units = group_bundles([_cf("src/foo.h"), _cf("src/foo.c")])
    assert len(units) == 1
    assert set(units[0].files) == {"src/foo.h", "src/foo.c"}


def test_group_bundles_pairs_cpp_header_and_impl():
    units = group_bundles([_cf("src/foo.hpp"), _cf("src/foo.cpp")])
    assert len(units) == 1
    assert set(units[0].files) == {"src/foo.hpp", "src/foo.cpp"}


def test_group_bundles_pairs_interface_and_impl_stem():
    units = group_bundles([_cf("src/svc.ts"), _cf("src/svc.impl.ts")])
    assert len(units) == 1
    assert set(units[0].files) == {"src/svc.ts", "src/svc.impl.ts"}


def test_group_bundles_does_not_pair_c_headers_across_directories():
    units = group_bundles([_cf("a/foo.h"), _cf("b/foo.c")])
    assert len(units) == 2


def test_group_bundles_splits_unit_exceeding_max_tokens():
    # Each file alone estimates above the cap, so the pair cannot share a unit.
    over = "x" * (MAX_UNIT_TOKENS * 4 + 8)
    diffs: dict[str, str] = {"src/foo.h": over, "src/foo.c": over}
    units = group_bundles([_cf("src/foo.h"), _cf("src/foo.c")], diffs=diffs)
    seen = sorted(p for u in units for p in u.files)
    assert seen == ["src/foo.c", "src/foo.h"]  # totality preserved
    assert len(units) == 2  # pair split apart


def test_group_bundles_keeps_unit_within_token_cap():
    small = "x" * 8
    diffs: dict[str, str] = {"src/foo.h": small, "src/foo.c": small}
    units = group_bundles([_cf("src/foo.h"), _cf("src/foo.c")], diffs=diffs)
    assert len(units) == 1


def test_review_unit_rejects_empty_files():
    try:
        ReviewUnit(unit_id="x", files=())
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
