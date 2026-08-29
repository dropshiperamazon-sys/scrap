from utils.normalizer import (
    clean_phone_display,
    normalize_domain,
    normalize_name_for_matching,
    normalize_phone_for_matching,
    normalize_website,
)


def test_normalize_domain_strips_scheme_and_www():
    assert normalize_domain("https://www.Example.com/") == "example.com"


def test_normalize_domain_handles_bare_host():
    assert normalize_domain("example.com") == "example.com"


def test_normalize_domain_empty_input():
    assert normalize_domain("") == ""


def test_normalize_website_drops_trailing_slash():
    assert normalize_website("https://example.com/") == "https://example.com"


def test_normalize_website_drops_tracking_params_keeps_others():
    result = normalize_website("https://example.com/shop?utm_source=fb&id=42")
    assert result == "https://example.com/shop?id=42"


def test_normalize_website_empty_input():
    assert normalize_website("") == ""


def test_normalize_phone_for_matching_adds_us_country_code():
    assert normalize_phone_for_matching("(212) 355-9100") == "12123559100"


def test_normalize_phone_for_matching_keeps_existing_country_code():
    assert normalize_phone_for_matching("+1 212-355-9100") == "12123559100"


def test_normalize_phone_for_matching_empty_input():
    assert normalize_phone_for_matching("") == ""


def test_clean_phone_display_collapses_whitespace():
    assert clean_phone_display("+1   212-355-9100 ") == "+1 212-355-9100"


def test_normalize_name_for_matching_strips_punctuation_and_case():
    assert normalize_name_for_matching("Example Furniture, Co.") == "examplefurnitureco"
