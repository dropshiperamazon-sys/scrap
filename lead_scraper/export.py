"""Writers for the two output shapes this tool produces.

Both write .csv or .xlsx depending on the output path's extension.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from .maps_scraper import MapsListing
from .pipeline import domain_of

BASIC_COLUMNS = ["Website", "Company Name"]
FULL_COLUMNS = ["Email", "Owner/Founder/CEO Name", "Company Name", "Website", "Pinterest Link", "Phone Number"]


def _write(df: pd.DataFrame, out_path: str) -> None:
    if out_path.lower().endswith(".xlsx"):
        df.to_excel(out_path, index=False)
    else:
        df.to_csv(out_path, index=False)


def export_basic(listings: Iterable[MapsListing], out_path: str) -> None:
    """Step 1's simplified export: Website (domain only) + Company Name."""
    rows = [{"Website": domain_of(listing.website), "Company Name": listing.name} for listing in listings]
    _write(pd.DataFrame(rows, columns=BASIC_COLUMNS), out_path)


def export_full(rows: Iterable[dict], out_path: str) -> None:
    """Full 6-column export. Each row needs: email, owner_name, company_name,
    website, pinterest, phone (missing keys are treated as blank)."""
    table_rows = [
        {
            "Email": row.get("email", ""),
            "Owner/Founder/CEO Name": row.get("owner_name", ""),
            "Company Name": row.get("company_name", ""),
            "Website": row.get("website", ""),
            "Pinterest Link": row.get("pinterest", ""),
            "Phone Number": row.get("phone", ""),
        }
        for row in rows
    ]
    _write(pd.DataFrame(table_rows, columns=FULL_COLUMNS), out_path)
