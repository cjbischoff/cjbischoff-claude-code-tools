from sec_overlay.cvss4_data import MACROVECTOR_LOOKUP, MAX_COMPOSED, MAX_SEVERITY


def test_lookup_shape():
    # 6-char keys of digits, scores within CVSS bounds
    assert len(MACROVECTOR_LOOKUP) > 250
    for k, v in MACROVECTOR_LOOKUP.items():
        assert len(k) == 6 and k.isdigit()
        assert 0.0 <= v <= 10.0


def test_interpolation_tables_nonempty():
    assert MAX_COMPOSED and MAX_SEVERITY
