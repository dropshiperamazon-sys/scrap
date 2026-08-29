from lead_scraper.maps_scraper import MapsListing
from lead_scraper.pipeline import dedupe_listings, domain_of


def test_domain_strips_scheme_and_www():
    assert domain_of("https://www.example.com/") == "example.com"


def test_domain_handles_bare_host():
    assert domain_of("example.com") == "example.com"


def test_domain_empty_website_returns_empty():
    assert domain_of("") == ""


def test_dedupe_listings_drops_repeat_domain():
    listings = [
        MapsListing(name="A", website="https://example.com"),
        MapsListing(name="A duplicate", website="https://www.example.com/"),
        MapsListing(name="B", website="https://other.com"),
    ]
    deduped = list(dedupe_listings(listings))
    assert [listing.name for listing in deduped] == ["A", "B"]


def test_dedupe_listings_falls_back_to_phone_when_no_website():
    listings = [
        MapsListing(name="A", phone="+1 555-0100"),
        MapsListing(name="A duplicate", phone="+1 555-0100"),
    ]
    deduped = list(dedupe_listings(listings))
    assert len(deduped) == 1


def test_dedupe_listings_drops_rows_with_neither_website_nor_phone():
    listings = [MapsListing(name="No contact info")]
    assert list(dedupe_listings(listings)) == []
