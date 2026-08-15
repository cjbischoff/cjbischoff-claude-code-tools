import pytest

from sec_overlay.prompts import render_prompt


def test_fills_all_tokens():
    out = render_prompt("scan {{TARGET}} at {{SHA}}", {"TARGET": "/r", "SHA": "abc"})
    assert out == "scan /r at abc"


def test_unfilled_token_raises_and_names_it():
    with pytest.raises(ValueError) as exc:
        render_prompt("scan {{TARGET}} class {{ATTACK_CLASS}}", {"TARGET": "/r"})
    assert "ATTACK_CLASS" in str(exc.value)


def test_extra_subs_are_ignored():
    assert render_prompt("hi {{A}}", {"A": "x", "B": "y"}) == "hi x"
