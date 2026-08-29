from lead_scraper.contact_finder import Contact, extract_contact, find_owner_name


def test_extract_contact_finds_email():
    html = "<p>Reach us at contact@example.com for orders.</p>"
    assert extract_contact(html).email == "contact@example.com"


def test_extract_contact_finds_pinterest_link():
    html = '<a href="https://pinterest.com/examplebrand">Pinterest</a>'
    assert extract_contact(html).pinterest == "https://pinterest.com/examplebrand"


def test_find_owner_name_from_name_then_title():
    assert find_owner_name("<p>Jane Smith, Founder & CEO</p>") == "Jane Smith"


def test_find_owner_name_from_title_then_name():
    assert find_owner_name("<p>Founder: John Doe</p>") == "John Doe"


def test_find_owner_name_returns_empty_when_absent():
    assert find_owner_name("<p>Welcome to our store.</p>") == ""


def test_contact_merge_fills_only_blank_fields():
    base = Contact(email="a@example.com")
    addition = Contact(email="b@example.com", owner_name="Jane Smith")
    merged = base.merge(addition)
    assert merged.email == "a@example.com"  # existing value wins
    assert merged.owner_name == "Jane Smith"  # blank field gets filled


def test_contact_complete_requires_all_three_fields():
    assert not Contact(email="a@example.com").complete
    assert Contact(email="a@example.com", owner_name="Jane", pinterest="https://pinterest.com/x").complete
