from sec_overlay.ste_lint import lint_prose


def test_clean_prose_passes():
    errs, warns = lint_prose("The gateway rejects the request. The log records the failure.\n")
    assert errs == [] and warns == []


def test_long_sentence_rejected():
    text = " ".join(["word"] * 26) + ".\n"
    errs, _ = lint_prose(text)
    assert any("25 words" in e for e in errs)


def test_semicolon_rejected():
    errs, _ = lint_prose("Open the file; check the header.\n")
    assert any("semicolon" in e for e in errs)


def test_semicolon_in_code_span_ok():
    errs, _ = lint_prose("Run `a; b` to reproduce the failure.\n")
    assert errs == []


def test_code_fence_exempt():
    errs, _ = lint_prose("```python\nx = 1; y = 2\n```\n")
    assert errs == []


def test_long_paragraph_rejected():
    para = " ".join(f"Sentence number {i} is short." for i in range(7))
    errs, _ = lint_prose(para + "\n")
    assert any("6 sentences" in e for e in errs)


def test_heading_and_table_exempt():
    text = (
        "# A Very Long Heading With Many Capitalized Words Here\n\n"
        "| a | b |\n|---|---|\n| x; y | z |\n"
    )
    errs, _ = lint_prose(text)
    # table CELLS are linted; the semicolon inside a cell is a real error
    assert any("semicolon" in e for e in errs)


def test_noun_cluster_warns():
    _, warns = lint_prose("The Gateway Token Validation Service Handler fails.\n")
    assert any("noun cluster" in w for w in warns)


def test_buried_sequence_warns():
    _, warns = lint_prose("Open the file then read the header then check the version.\n")
    assert any("sequence" in w for w in warns)


def test_unbalanced_fence_reported():
    text = "```python\nx = 1\nOpen the file; check the header.\n"
    errs, _ = lint_prose(text)
    assert any("unbalanced" in e for e in errs)


def test_abbreviation_does_not_split_paragraph():
    para = (
        "Use the flag for a common case, e.g. formatting or linting, and check the output. "
        "It runs the same tool twice, e.g. once for lint and once for format. "
        "Save the file when it is clean."
    )
    errs, _ = lint_prose(para + "\n")
    assert not any("6 sentences" in e for e in errs)


def test_abbreviation_does_not_hide_long_sentence():
    words = ["word"] * 15
    text = " ".join(words) + " e.g. " + " ".join(words) + ".\n"
    errs, _ = lint_prose(text)
    assert any("25 words" in e for e in errs)
