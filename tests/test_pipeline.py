from lead_scraper.pipeline import _domain


def test_domain_strips_scheme_and_www():
    assert _domain("https://www.example.com/") == "example.com"


def test_domain_handles_bare_host():
    assert _domain("example.com") == "example.com"


def test_domain_empty_website_returns_empty():
    assert _domain("") == ""
