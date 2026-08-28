from bs4 import BeautifulSoup

from lead_scraper.site_enricher import EMAIL_RE, PINTEREST_RE, _find_owner_name


def test_email_regex_finds_address():
    html = "<p>Reach us at contact@example.com for orders.</p>"
    assert EMAIL_RE.search(html).group(0) == "contact@example.com"


def test_pinterest_regex_finds_link():
    html = '<a href="https://pinterest.com/examplebrand">Pinterest</a>'
    assert PINTEREST_RE.search(html).group(0) == "https://pinterest.com/examplebrand"


def test_find_owner_name_from_name_then_title():
    soup = BeautifulSoup("<p>Jane Smith, Founder & CEO</p>", "html.parser")
    assert _find_owner_name(soup) == "Jane Smith"


def test_find_owner_name_from_title_then_name():
    soup = BeautifulSoup("<p>Founder: John Doe</p>", "html.parser")
    assert _find_owner_name(soup) == "John Doe"


def test_find_owner_name_returns_empty_when_absent():
    soup = BeautifulSoup("<p>Welcome to our store.</p>", "html.parser")
    assert _find_owner_name(soup) == ""
