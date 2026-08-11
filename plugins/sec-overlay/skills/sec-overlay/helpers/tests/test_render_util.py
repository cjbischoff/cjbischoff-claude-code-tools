"""Tests for the shared expected-signal renderer (report + redteam both use it)."""

from sec_overlay.render_util import signal_lines


def test_dict_signal_renders_both_labeled_lines():
    lines = signal_lines({"secure": "403", "insecure": "201 + record"})
    assert lines == ["  - **secure:** 403", "  - **insecure:** 201 + record"]


def test_dict_missing_keys_fall_back_to_unspecified():
    lines = signal_lines({"secure": "403"})
    assert lines == ["  - **secure:** 403", "  - **insecure:** _unspecified_"]


def test_bare_string_is_treated_as_the_insecure_signal():
    # A red-team agent may write expected_signal as a bare string; it means the
    # insecure signal, everywhere it is rendered.
    lines = signal_lines("201 + CE-B record")
    assert lines == ["  - **insecure:** 201 + CE-B record"]


def test_empty_values_render_nothing():
    assert signal_lines(None) == []
    assert signal_lines({}) == []
    assert signal_lines("   ") == []
