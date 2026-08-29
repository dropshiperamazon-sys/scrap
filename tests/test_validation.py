from scraper.validation import (
    clean_company_name,
    extract_emails,
    extract_phones,
    extract_pinterest_links,
    is_valid_email,
    pick_best_email,
    pick_best_pinterest,
)


def test_is_valid_email_accepts_normal_address():
    assert is_valid_email("Info@RealSite.com") is True


def test_is_valid_email_rejects_image_filename_lookalike():
    assert is_valid_email("logo@2x.png") is False


def test_is_valid_email_rejects_placeholder_domain():
    assert is_valid_email("test@example.com") is False
    assert is_valid_email("someone@example.com") is False  # example.com itself is always a placeholder


def test_extract_emails_dedupes_and_lowercases():
    html = "<p>Email Info@RealSite.com or info@realsite.com again.</p>"
    assert extract_emails(html) == ["info@realsite.com"]


def test_extract_emails_filters_invalid_candidates():
    html = "<img src='logo@2x.png'> contact us at hello@realsite.com"
    assert extract_emails(html) == ["hello@realsite.com"]


def test_extract_pinterest_links_finds_url():
    html = '<a href="https://www.pinterest.com/realbrand/">Pinterest</a>'
    assert extract_pinterest_links(html) == ["https://www.pinterest.com/realbrand/"]


def test_extract_phones_finds_us_format():
    html = "Call us at (212) 355-9100 for orders."
    assert extract_phones(html) == ["(212) 355-9100"]


def test_pick_best_email_prefers_business_domain():
    candidates = ["random@gmail.com", "info@realsite.com"]
    assert pick_best_email(candidates, "https://realsite.com") == "info@realsite.com"


def test_pick_best_email_prefers_contact_prefix_when_no_domain_match():
    candidates = ["random@gmail.com", "sales@gmail.com"]
    assert pick_best_email(candidates, "https://realsite.com") == "sales@gmail.com"


def test_pick_best_email_returns_empty_for_no_candidates():
    assert pick_best_email([], "https://realsite.com") == ""


def test_pick_best_pinterest_matches_company_name_slug():
    candidates = ["https://pinterest.com/unrelatedbrand", "https://pinterest.com/realbrandfurniture"]
    assert pick_best_pinterest(candidates, "Real Brand Furniture") == "https://pinterest.com/realbrandfurniture"


def test_pick_best_pinterest_falls_back_to_first_when_no_match():
    candidates = ["https://pinterest.com/somethingelse"]
    assert pick_best_pinterest(candidates, "Real Brand Furniture") == "https://pinterest.com/somethingelse"


def test_clean_company_name_strips_junk_tokens():
    assert clean_company_name("★ Example Furniture - Sponsored (1,234) 4.5 stars") == "Example Furniture"


def test_clean_company_name_leaves_normal_name_untouched():
    assert clean_company_name("Example Furniture Co.") == "Example Furniture Co."
