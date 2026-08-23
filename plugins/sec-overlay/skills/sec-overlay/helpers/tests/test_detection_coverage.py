"""Tests for the DETECTION_COVERAGE.md renderer (F6)."""


def test_coverage_document_records_the_dependency_internal_sink_limit():
    from sec_overlay.detection_coverage import generate

    text = generate()
    assert "dependency-internal sink" in text
    assert "dependency-sinks.json" in text
