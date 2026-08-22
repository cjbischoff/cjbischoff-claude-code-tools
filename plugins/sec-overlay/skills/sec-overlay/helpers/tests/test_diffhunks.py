"""Tests for the unified-diff hunk parser (DIFF-04)."""

from __future__ import annotations

import dataclasses

from sec_overlay.diffhunks import (
    NO_NEWLINE_MARKER,
    Hunk,
    added_line_numbers,
    hunk_for_line,
    line_in_hunk,
    parse_hunks,
)

_SINGLE_HUNK = """diff --git a/f.py b/f.py
index 1111111..2222222 100644
--- a/f.py
+++ b/f.py
@@ -1,3 +1,4 @@
 line one
+added line
 line two
 line three
"""

_MULTI_HUNK = """diff --git a/f.py b/f.py
index 1111111..2222222 100644
--- a/f.py
+++ b/f.py
@@ -1,2 +1,3 @@
 top
+first added
 second
@@ -10,2 +11,3 @@
 middle
+second added
 end
"""


def test_single_hunk_diff_yields_one_hunk_with_the_four_header_numbers_parsed():
    hunks = parse_hunks(_SINGLE_HUNK)
    assert len(hunks) == 1
    hunk = hunks[0]
    assert (hunk.old_start, hunk.old_count, hunk.new_start, hunk.new_count) == (1, 3, 1, 4)


def test_multi_hunk_diff_yields_hunks_in_file_order_with_independent_line_numbering():
    hunks = parse_hunks(_MULTI_HUNK)
    assert len(hunks) == 2
    assert hunks[0].new_start == 1
    assert hunks[1].new_start == 11
    assert added_line_numbers(hunks) == {2, 12}


def test_header_with_absent_old_and_new_count_treats_both_as_one():
    diff_text = "@@ -5 +5 @@\n context\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.old_count == 1
    assert hunk.new_count == 1


def test_header_with_zero_new_side_count_yields_no_added_lines():
    diff_text = "@@ -5,3 +5,0 @@\n-one\n-two\n-three\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.added == ()


def test_lines_before_the_first_header_are_ignored():
    diff_text = "diff --git a/f.py b/f.py\nindex 111..222 100644\n@@ -1 +1 @@\n context\n"
    hunks = parse_hunks(diff_text)
    assert len(hunks) == 1
    assert list(hunks[0].context) == ["context"]


def test_plusplusplus_and_minusminusminus_file_header_lines_are_not_counted_as_lines():
    hunks = parse_hunks(_SINGLE_HUNK)
    assert added_line_numbers(hunks) == {2}
    assert hunks[0].deleted == ()


def test_leading_plus_line_new_side_number_advances_correctly_with_interleaving():
    diff_text = "@@ -1,2 +1,4 @@\n context\n+added\n-deleted\n context\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.added == ((2, "added"),)
    assert list(hunk.context) == ["context", "context"]


def test_leading_minus_line_becomes_deleted_and_does_not_advance_new_side_number():
    diff_text = "@@ -1,2 +1,1 @@\n-deleted\n context\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.deleted == ((1, "deleted"),)
    assert hunk.new_start == 1


def test_context_line_advances_new_side_number_and_strips_leading_marker():
    diff_text = "@@ -1,2 +1,2 @@\n context one\n context two\n"
    hunk = parse_hunks(diff_text)[0]
    assert list(hunk.context) == ["context one", "context two"]


def test_no_newline_marker_line_is_skipped_and_becomes_no_line_kind():
    diff_text = f"@@ -1,1 +1,1 @@\n+added\n{NO_NEWLINE_MARKER}\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.added == ((1, "added"),)
    assert hunk.deleted == ()
    assert list(hunk.context) == []


def test_crlf_diff_body_parses_with_no_carriage_return_surviving_into_a_stored_line():
    diff_text = "@@ -1,1 +1,2 @@\r\n context\r\n+added\r\n"
    hunk = parse_hunks(diff_text)[0]
    assert hunk.added == ((2, "added"),)
    assert list(hunk.context) == ["context"]
    for _, content in hunk.added:
        assert "\r" not in content
    for content in hunk.context:
        assert "\r" not in content


def test_diff_body_with_zero_headers_yields_empty_hunk_list():
    hunks = parse_hunks("no headers here\nat all\n")
    assert hunks == []
    assert added_line_numbers(hunks) == set()
    assert line_in_hunk(hunks, 1) is False


def test_added_line_numbers_returns_exactly_the_new_side_numbers_of_added_lines():
    hunks = parse_hunks(_MULTI_HUNK)
    assert added_line_numbers(hunks) == {2, 12}


def test_line_in_hunk_true_at_range_boundaries_false_one_outside_either_end():
    diff_text = "@@ -1,5 +1,5 @@\n a\n b\n c\n d\n e\n"
    hunks = parse_hunks(diff_text)
    assert line_in_hunk(hunks, 1) is True
    assert line_in_hunk(hunks, 5) is True
    assert line_in_hunk(hunks, 0) is False
    assert line_in_hunk(hunks, 6) is False


def test_hunk_for_line_returns_the_containing_hunk_or_none():
    hunks = parse_hunks(_MULTI_HUNK)
    assert hunk_for_line(hunks, 2) is hunks[0]
    assert hunk_for_line(hunks, 12) is hunks[1]
    assert hunk_for_line(hunks, 999) is None


def test_parse_hunks_called_twice_on_the_same_text_returns_equal_results():
    assert parse_hunks(_MULTI_HUNK) == parse_hunks(_MULTI_HUNK)


def test_hunk_is_frozen_with_tuple_collections():
    assert Hunk.__dataclass_params__.frozen is True
    hunk = parse_hunks(_SINGLE_HUNK)[0]
    for field in dataclasses.fields(hunk):
        if field.name in ("added", "deleted", "context"):
            assert isinstance(getattr(hunk, field.name), tuple)


def test_line_in_hunk_contiguous_sweep_matches_the_union_of_hunk_ranges():
    hunks = parse_hunks(_MULTI_HUNK)
    ranges = [range(hunk.new_start, hunk.new_start + hunk.new_count) for hunk in hunks]
    expected_members = {line for r in ranges for line in r}
    sweep_start = min(r.start for r in ranges) - 1
    sweep_end = max(r.stop for r in ranges) + 1
    actual_members = {line for line in range(sweep_start, sweep_end) if line_in_hunk(hunks, line)}
    assert actual_members == expected_members
