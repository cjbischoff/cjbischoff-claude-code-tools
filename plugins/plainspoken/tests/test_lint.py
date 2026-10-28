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


HOSTILE = {
    "acronym_chain": " ".join(["ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJ-x"] * 3),
    "unclosed_comment": "<!--" * 20000,
    "unclosed_image": "![" * 20000,
    "unclosed_image_url": "![](" * 20000,
    "unclosed_link": "[\\" * 20000,
    "unclosed_tag": "<A" * 20000,
}


def test_hostile_input_finishes_fast():
    for name, text in HOSTILE.items():
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "-", "--json"],
                input=text,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
        except subprocess.TimeoutExpired:
            raise AssertionError(f"{name}: lint.py did not finish in 1.5 s") from None
        assert result.returncode == 0, name


def filler(words: int) -> str:
    """Build plain filler text with an exact word count and no lexicon hits."""
    return " ".join(["cats"] * words) + "."


def test_cluster_words_per_paragraph(tmp_path):
    text = "We harness data to empower the team.\n\nWe harness the data once.\n"
    clusters = lint_json(tmp_path, text)["sweep"]["cluster_words"]
    assert clusters == [{"paragraph": 1, "words": ["harness", "empower"]}]
    assert "cluster_words" not in lint_json(tmp_path, "We harness the data once.\n")["sweep"]


def test_cluster_words_count_paragraphs_separately(tmp_path):
    text = "We harness the data.\n\nThe team will empower users.\n"
    assert "cluster_words" not in lint_json(tmp_path, text)["sweep"]
    split = "We harness the data.\n\nWe harness data to empower users.\n"
    assert lint_json(tmp_path, split)["sweep"]["cluster_words"] == [
        {"paragraph": 2, "words": ["harness", "empower"]}
    ]


def test_density_words_need_two_hits_and_three_percent(tmp_path):
    two_in_40 = "A significant gain and a significant cost. " + filler(31)
    found = lint_json(tmp_path, two_in_40)["sweep"]["density_words"]
    assert [d["word"] for d in found] == ["significant"]
    assert found[0]["share"] >= 0.03
    once_in_30 = "A significant gain. " + filler(26)
    assert "density_words" not in lint_json(tmp_path, once_in_30)["sweep"]
    two_in_200 = "A significant gain and a significant cost. " + filler(191)
    assert "density_words" not in lint_json(tmp_path, two_in_200)["sweep"]


def test_wordy_and_redundant_and_defense(tmp_path):
    text = (
        "We stopped due to the fact that it rained. The past history is clear. "
        "Needless to say, we left.\n"
    )
    sweep = lint_json(tmp_path, text)["sweep"]
    assert "due to the fact that" in sweep["wordy_constructions"]
    assert "past history" in sweep["redundant_pairs"]
    assert "needless to say" in sweep["defense_phrases"]


def test_social_breadth_cutoff_ack_reasoning(tmp_path):
    cases = {
        "social_openers": "Excited to share our launch.",
        "false_breadth": "It suits everyone from beginners to experts.",
        "cutoff_phrases": "As of my last update, the price held.",
        "acknowledgment_loops": "You're asking about the price.",
        "reasoning_residue": "Let me think step by step.",
    }
    for key, line in cases.items():
        assert key in lint_json(tmp_path, line + "\n")["sweep"], key


def test_analogy_scaffolding_sentence_start_only(tmp_path):
    start = lint_json(tmp_path, "Imagine a gateway. It routes calls.\n")["sweep"]
    assert start["analogy_scaffolding"] == ["imagine"]
    middle = lint_json(tmp_path, "You can imagine it. It routes calls.\n")["sweep"]
    assert "analogy_scaffolding" not in middle


def test_curly_quotes_counted(tmp_path):
    text = "He said “stop” and it’s done.\n"
    assert lint_json(tmp_path, text)["sweep"]["curly_quotes"] == 3


def test_emoji_lines_headings_and_bullets(tmp_path):
    text = (
        "# Launch \U0001f680\n\n- Fast ✅\n- Plain item\n\nA prose line with \U0001f680 inside.\n"
    )
    assert lint_json(tmp_path, text)["sweep"]["emoji_lines"] == 2


def test_new_keys_quiet_on_plain_text(tmp_path):
    text = (
        "I fixed the login bug on Tuesday. The cause was a stale cookie that the old app "
        "kept after every logout. Users on the new app never saw the error.\n"
    )
    sweep = lint_json(tmp_path, text)["sweep"]
    new = {
        "cluster_words", "density_words", "wordy_constructions", "redundant_pairs",
        "defense_phrases", "social_openers", "false_breadth", "analogy_scaffolding",
        "cutoff_phrases", "acknowledgment_loops", "reasoning_residue", "curly_quotes",
        "emoji_lines",
    }  # fmt: skip
    assert sweep == {} and not new & set(sweep)
