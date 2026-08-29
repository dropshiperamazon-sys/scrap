"""Reads back a (possibly hand-edited) CSV/XLSX of Website + Company Name rows,
as produced by `lead_scraper.cli scrape`.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .pipeline import domain_of


@dataclass
class ImportedRow:
    domain: str
    company_name: str


def load_domain_company_table(path: str) -> list[ImportedRow]:
    df = pd.read_excel(path) if path.lower().endswith(".xlsx") else pd.read_csv(path)

    columns_lower = {column.lower().strip(): column for column in df.columns}
    website_column = next((columns_lower[key] for key in columns_lower if "website" in key), None)
    company_column = next((columns_lower[key] for key in columns_lower if "company" in key), None)
    if not website_column or not company_column:
        raise ValueError('Input file needs a "Website" column and a "Company Name" column.')

    rows: list[ImportedRow] = []
    for _, record in df.iterrows():
        website_value = record[website_column]
        company_value = record[company_column]
        domain = domain_of(str(website_value)) if pd.notna(website_value) else ""
        company_name = str(company_value).strip() if pd.notna(company_value) else ""
        if domain or company_name:
            rows.append(ImportedRow(domain=domain, company_name=company_name))
    return rows
