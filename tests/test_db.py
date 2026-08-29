from database.db import Database


def make_db(tmp_path):
    return Database(str(tmp_path / "leads.db"))


def test_insert_and_find_matching_business_by_domain(tmp_path):
    db = make_db(tmp_path)
    business_id = db.insert_business(
        {
            "company_name": "Example Furniture",
            "normalized_name": "examplefurniture",
            "website": "https://example.com",
            "normalized_domain": "example.com",
            "phone": "+1 212-355-9100",
            "normalized_phone": "12123559100",
            "email": "",
            "pinterest": "",
            "keyword": "furniture store",
            "location": "New York, NY",
            "status": "PARTIAL",
        }
    )
    assert business_id > 0

    match = db.find_matching_business("example.com", "", "")
    assert match is not None
    assert match["company_name"] == "Example Furniture"
    db.close()


def test_find_matching_business_falls_back_to_phone_then_name(tmp_path):
    db = make_db(tmp_path)
    db.insert_business(
        {
            "company_name": "Example Furniture",
            "normalized_name": "examplefurniture",
            "website": "",
            "normalized_domain": "",
            "phone": "+1 212-355-9100",
            "normalized_phone": "12123559100",
            "email": "",
            "pinterest": "",
            "status": "PARTIAL",
        }
    )
    assert db.find_matching_business("", "12123559100", "") is not None
    assert db.find_matching_business("", "", "examplefurniture") is not None
    assert db.find_matching_business("other.com", "19995550000", "somethingelse") is None
    db.close()


def test_update_business_merges_fields(tmp_path):
    db = make_db(tmp_path)
    business_id = db.insert_business(
        {"company_name": "Example Furniture", "email": "", "pinterest": "", "status": "PARTIAL"}
    )
    db.update_business(business_id, {"email": "info@example.com"})
    row = db.get_business(business_id)
    assert row["email"] == "info@example.com"
    db.close()


def test_get_export_rows_excludes_blank_company_name(tmp_path):
    db = make_db(tmp_path)
    db.insert_business({"company_name": "Example Furniture", "status": "COMPLETE"})
    rows = db.get_export_rows()
    assert len(rows) == 1
    assert rows[0]["company_name"] == "Example Furniture"
    db.close()


def test_search_lifecycle_tracks_resume_state(tmp_path):
    db = make_db(tmp_path)
    assert db.get_search_status("furniture store", "Chicago, IL") is None
    db.start_search("furniture store", "Chicago, IL")
    assert db.get_search_status("furniture store", "Chicago, IL") == "IN_PROGRESS"
    db.complete_search("furniture store", "Chicago, IL")
    assert db.get_search_status("furniture store", "Chicago, IL") == "COMPLETE"
    db.close()


def test_log_error_does_not_raise(tmp_path):
    db = make_db(tmp_path)
    db.log_error("DISCOVERY", "boom", keyword="furniture store", location="Chicago, IL")
    db.close()
