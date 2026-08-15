# tests/test_class_ext.py
from sec_overlay.class_ext import class_extension_status


def test_alias_maps_coarse_file(tmp_path):
    (tmp_path / "injection.md").write_text("injection family")
    st = class_extension_status(["sqli", "cmdi", "xss"], tmp_path)
    assert st["present"] == {"sqli": "injection.md", "cmdi": "injection.md", "xss": "injection.md"}
    assert st["gaps"] == []


def test_direct_file_counts(tmp_path):
    (tmp_path / "ssrf.md").write_text("ssrf")
    st = class_extension_status(["ssrf"], tmp_path)
    assert st["present"] == {"ssrf": "ssrf.md"}


def test_uncovered_key_logs_gap(tmp_path):
    st = class_extension_status(["xxe"], tmp_path)  # no xxe.md, no alias
    assert st["present"] == {}
    assert len(st["gaps"]) == 1
    g = st["gaps"][0]
    assert g["id"] == "xxe" and g["disposition"] == "needs_follow_up"
    assert g["reason"] and g["next_step"]
