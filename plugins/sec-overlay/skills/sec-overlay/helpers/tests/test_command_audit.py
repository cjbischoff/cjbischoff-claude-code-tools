from pathlib import Path

# parents[2]=skills/sec-overlay, [3]=skills, [4]=plugin root (plugins/sec-overlay)
_CMD = Path(__file__).resolve().parents[4] / "commands" / "audit.md"


def test_command_documents_routing_and_correlate():
    text = _CMD.read_text()
    assert "/sec-overlay:audit" in text
    assert "python -m sec_overlay.run" in text or "run.drive" in text
    assert "python -m sec_overlay.correlate" in text
    assert "--out" in text  # correlation output lands in the CWD
    assert "confirm" in text.lower()  # N-repo confirm step
