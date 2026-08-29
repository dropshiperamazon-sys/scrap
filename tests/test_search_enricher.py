from lead_scraper.search_enricher import _filter_result_links, build_query


def test_build_query_substitutes_both_placeholders():
    query = build_query("{company} {domain} owner email", "example.com", "Example Co")
    assert query == "Example Co example.com owner email"


def test_build_query_handles_missing_placeholders():
    assert build_query("just a static query", "example.com", "Example Co") == "just a static query"


def test_filter_result_links_drops_google_domains():
    links = [
        "https://www.google.com/search?q=x",
        "https://example.com/about",
        "https://webcache.googleusercontent.com/x",
        "https://example.com/about",  # duplicate
        "https://other.com/",
    ]
    assert _filter_result_links(links) == ["https://example.com/about", "https://other.com/"]
