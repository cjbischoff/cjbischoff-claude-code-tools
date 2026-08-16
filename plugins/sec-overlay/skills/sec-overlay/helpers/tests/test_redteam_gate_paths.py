"""Tests for red-team gate path consistency (O-65: adversary vs producer)."""

from pathlib import Path


def test_redteam_adversary_agent_owns_redteam_adversary_json():
    """Verify redteam-adversary.md uses redteam-adversary.json and not redteam.json.

    The redteam producer (redteam.py:357) writes kb/gates/redteam.json.
    The redteam adversary (agents/redteam-adversary.md) must write to
    kb/gates/redteam-adversary.json to avoid collision (O-65).
    """
    # Navigate from tests/ to agents/ (parents[2] = helpers, parents[3] = skills/sec-overlay)
    agents_dir = Path(__file__).parents[2] / "agents"
    agent_file = agents_dir / "redteam-adversary.md"

    assert agent_file.exists(), f"Agent file not found: {agent_file}"

    content = agent_file.read_text()
    assert "kb/gates/redteam-adversary.json" in content
    assert "kb/gates/redteam.json" not in content
