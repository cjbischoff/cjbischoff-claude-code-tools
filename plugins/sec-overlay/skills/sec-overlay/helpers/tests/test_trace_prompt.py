"""REQ-06 and REQ-19: the trace prompt covers needs-runtime findings and in-band channels."""

from __future__ import annotations

from pathlib import Path

TRACE = Path(__file__).resolve().parents[2] / "agents" / "trace.md"


def _text():
    return TRACE.read_text()


def test_trace_covers_needs_deployment_testing():
    text = _text()
    assert "needs-deployment-testing" in text


def test_trace_does_not_filter_to_confirmed_alone():
    assert 'with `status == "confirmed"`.' not in _text()


def test_trace_names_the_in_band_channel():
    text = _text().lower()
    assert "in-band" in text
    assert "observable to the caller" in text
