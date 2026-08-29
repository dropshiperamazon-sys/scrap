import pytest

from lead_scraper.importer import load_domain_company_table


def test_load_domain_company_table_reads_csv(tmp_path):
    csv_path = tmp_path / "leads.csv"
    csv_path.write_text('Website,Company Name\nhttps://www.example.com/,Example Co\nother.com,Other Co\n')

    rows = load_domain_company_table(str(csv_path))

    assert [r.domain for r in rows] == ["example.com", "other.com"]
    assert [r.company_name for r in rows] == ["Example Co", "Other Co"]


def test_load_domain_company_table_skips_fully_blank_rows(tmp_path):
    csv_path = tmp_path / "leads.csv"
    csv_path.write_text("Website,Company Name\n,\nexample.com,Example Co\n")

    rows = load_domain_company_table(str(csv_path))

    assert len(rows) == 1
    assert rows[0].company_name == "Example Co"


def test_load_domain_company_table_requires_expected_columns(tmp_path):
    csv_path = tmp_path / "leads.csv"
    csv_path.write_text("Foo,Bar\n1,2\n")

    with pytest.raises(ValueError):
        load_domain_company_table(str(csv_path))
