"""REQ-34: expected_signal renders a list of observation channels."""

from __future__ import annotations

from sec_overlay.render_util import signal_lines

_CHANNELS = [
    {
        "name": "in-band valid boolean",
        "needs_egress": False,
        "secure": "valid=false for an internal host",
        "insecure": "valid=true for http://169.254.169.254/",
    },
    {
        "name": "out-of-band collector hit",
        "needs_egress": True,
        "secure": "no request reaches the collector",
        "insecure": "the collector logs one GET",
    },
]


def test_two_channels_render_with_names() -> None:
    lines = signal_lines(_CHANNELS)
    text = "\n".join(lines)
    assert "in-band valid boolean" in text
    assert "out-of-band collector hit" in text


def test_egress_marker_distinguishes_the_channels() -> None:
    text = "\n".join(signal_lines(_CHANNELS))
    assert "no egress" in text
    assert "needs egress" in text


def test_each_channel_carries_secure_and_insecure() -> None:
    text = "\n".join(signal_lines(_CHANNELS))
    assert text.count("**secure:**") == 2
    assert text.count("**insecure:**") == 2


def test_dict_shape_still_renders() -> None:
    lines = signal_lines({"secure": "a", "insecure": "b"})
    assert lines == ["  - **secure:** a", "  - **insecure:** b"]


def test_bare_string_still_renders() -> None:
    assert signal_lines("boom") == ["  - **insecure:** boom"]


def test_empty_list_renders_nothing() -> None:
    assert signal_lines([]) == []
