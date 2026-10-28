"""Tests for skills/plainspoken/scripts/lint.py, run through the real CLI."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN / "skills" / "plainspoken" / "scripts" / "lint.py"
TELLS = PLUGIN / "skills" / "plainspoken" / "references" / "tells.md"
GROUPS = ("size", "cadence", "density", "high_signal_clusters", "look_here", "sweep")


def run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run lint.py with the current interpreter.

    Args:
        *args: Command-line arguments after the script path.
        stdin: Text to send on standard input, or None for no input.

    Returns:
        The completed process with text stdout and stderr.
    """
    assert SCRIPT.is_file(), f"missing script: {SCRIPT}"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def lint_json(tmp_path: Path, text: str, *flags: str) -> dict:
    """Write text to a file, lint it with --json, and return the parsed report.

    Args:
        tmp_path: Pytest temporary directory.
        text: Draft text to lint.
        *flags: Extra flags such as `--raw`.

    Returns:
        The parsed JSON report.
    """
    draft = tmp_path / "draft.md"
    draft.write_text(text, encoding="utf-8")
    result = run(str(draft), "--json", *flags)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def sentence(words: int) -> str:
    """Build a plain sentence with an exact word count and no lexicon hits."""
    return " ".join(["Cats"] + ["sleep"] * (words - 1)) + "."


def keys_at_any_depth(node) -> set[str]:
    """Collect every dict key at any depth."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found.add(key)
            found |= keys_at_any_depth(value)
    elif isinstance(node, list):
        for item in node:
            found |= keys_at_any_depth(item)
    return found


def test_strips_markdown_by_default(tmp_path):
    text = (
        "---\ntitle: delve\n---\n"
        "Keep this plain sentence.\n\n"
        "<!-- furthermore delve -->\n\n"
        '```python\ndelve = "seamless"\n```\n\n'
        "Use `unlock` here.\n\n"
        "| delve | seamless |\n|---|---|\n| a | b |\n\n"
        "Read [the docs](https://example.com/delve) or https://seamless.example.com now.\n"
    )
    report = lint_json(tmp_path, text)
    assert report["sweep"] == {}
    assert report["size"]["words"] == 11


def test_raw_keeps_markdown(tmp_path):
    text = "Plain line here.\n\n```\ndelve into it\n```\n"
    assert "ai_words" not in lint_json(tmp_path, text)["sweep"]
    assert "delve" in lint_json(tmp_path, text, "--raw")["sweep"]["ai_words"]


def test_counts_dashes_and_semicolons(tmp_path):
    sweep = lint_json(tmp_path, "A — B. C – D. E -- F; G.\n")["sweep"]
    assert sweep["dashes"] == 3
    assert sweep["semicolons"] == 1


def test_flags_stock_words_and_marketing(tmp_path):
    sweep = lint_json(tmp_path, "We delve into a seamless plan. It will shed light on cost.\n")[
        "sweep"
    ]
    assert "delve" in sweep["ai_words"]
    assert "seamless" in sweep["marketing_words"]
    assert "shed light on" in sweep["ai_phrases"]


def test_transition_only_at_sentence_start(tmp_path):
    start = lint_json(tmp_path, "However, the plan changed. We kept the date.\n")["sweep"]
    assert "however" in start["filler_transitions"]
    middle = lint_json(tmp_path, "The plan, however, held. We kept the date.\n")["sweep"]
    assert "filler_transitions" not in middle


def test_pause_and_point_and_closers(tmp_path):
    sweep = lint_json(tmp_path, "Here's the thing: we shipped late. The bottom line is simple.\n")[
        "sweep"
    ]
    assert "here's the thing" in sweep["pause_and_point"]
    assert "the bottom line" in sweep["closers"]


def test_bold_label_and_exclamations(tmp_path):
    sweep = lint_json(tmp_path, "**Speed.** It runs fast!\n\n**Cost:** It is low.\n")["sweep"]
    assert sweep["bold_label_starts"] == 2
    assert sweep["exclamation_marks"] == 1


def test_uniform_band_flagged(tmp_path):
    text = " ".join(sentence(n) for n in (12, 13, 14, 12, 13, 14)) + "\n"
    band = lint_json(tmp_path, text)["sweep"]["uniform_band"]
    assert band["sentences"] == 6
    assert band["share_within_5_of_median"] >= 0.7


def test_json_has_all_groups(tmp_path):
    report = lint_json(tmp_path, "A short plain note.\n")
    for group in GROUPS:
        assert group in report, group


def test_no_score_or_verdict(tmp_path):
    text = "However, we delve into a seamless plan! Here's the thing; it works.\n"
    report = lint_json(tmp_path, text)
    assert not keys_at_any_depth(report) & {"score", "verdict", "risk"}
    human = run(str(tmp_path / "draft.md")).stdout.lower()
    assert "verdict:" not in human
    assert "risk:" not in human


def test_stdin_dash():
    result = run("-", "--json", stdin="We delve into it. Then we stop.\n")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert "delve" in report["sweep"]["ai_words"]
    assert report["size"]["sentences"] == 2


def test_missing_file_exits_2(tmp_path):
    result = run(str(tmp_path / "nope.md"))
    assert result.returncode == 2
    assert result.stderr.strip()
    assert result.stdout == ""


def test_tells_md_in_sync():
    spec = importlib.util.spec_from_file_location("plainspoken_lint", SCRIPT)
    assert spec is not None and spec.loader is not None
    lint = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lint)
    known = {entry.lower() for entries in lint.LEXICONS.values() for entry in entries}
    listed = []
    for line in TELLS.read_text(encoding="utf-8").splitlines():
        if line.startswith("Entries:"):
            listed += [e.strip() for e in line[len("Entries:") :].split(",") if e.strip()]
    assert len(listed) > 100
    missing = [e for e in listed if e.lower() not in known]
    assert not missing, f"in tells.md but not in lint.py: {missing}"


def test_plain_human_text_is_quiet(tmp_path):
    text = (
        "I fixed the login bug on Tuesday. The cause was a stale cookie that the old app "
        "kept after every logout. Users on the new app never saw the error.\n"
    )
    assert lint_json(tmp_path, text)["sweep"] == {}
