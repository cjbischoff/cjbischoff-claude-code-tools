"""Tests for the DETECTION_COVERAGE.md renderer (F6)."""

from pathlib import Path

_COVERAGE_DOC = Path(__file__).resolve().parents[2] / "references" / "DETECTION_COVERAGE.md"


def test_coverage_document_records_the_dependency_internal_sink_limit():
    from sec_overlay.detection_coverage import generate

    text = generate()
    assert "dependency-internal sink" in text
    assert "dependency-sinks.json" in text


def test_tracked_coverage_document_matches_the_renderer():
    """The tracked file must equal generate()'s output, byte for byte.

    A mismatch means someone edited detection_coverage.py without
    regenerating references/DETECTION_COVERAGE.md. Fix: run generate()
    and overwrite references/DETECTION_COVERAGE.md with its output.
    """
    from sec_overlay.detection_coverage import generate

    assert generate() == _COVERAGE_DOC.read_text(), (
        "references/DETECTION_COVERAGE.md is stale. Fix: regenerate "
        "references/DETECTION_COVERAGE.md from detection_coverage.py."
    )
