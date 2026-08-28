"""Exports scraped leads to an .xlsx file in the requested column order."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from .pipeline import Lead

COLUMNS = ["Email", "Owner/Founder/CEO Name", "Company Name", "Website", "Pinterest Link", "Phone Number"]


def leads_to_dataframe(leads: Iterable[Lead]) -> pd.DataFrame:
    rows = [
        {
            "Email": lead.email,
            "Owner/Founder/CEO Name": lead.owner_name,
            "Company Name": lead.company_name,
            "Website": lead.website,
            "Pinterest Link": lead.pinterest,
            "Phone Number": lead.phone,
        }
        for lead in leads
    ]
    return pd.DataFrame(rows, columns=COLUMNS)


def export_xlsx(leads: Iterable[Lead], out_path: str) -> None:
    leads_to_dataframe(leads).to_excel(out_path, index=False)
