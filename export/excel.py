"""Writes the final leads.xlsx: exactly Email, Company Name, Website,
Phone, Pinterest -- in that order, nothing else.

Regenerated from the database's current state on every call, so a merged
duplicate is reflected without ever producing a duplicate row, and a
crash mid-write never corrupts the file (write to a temp file, then
atomically replace).
"""

from __future__ import annotations

import os

from openpyxl import Workbook

COLUMNS = ["Email", "Company Name", "Website", "Phone", "Pinterest"]


def write_excel(rows, output_path: str) -> None:
    """`rows` are sqlite3.Row (or any mapping) objects with keys:
    company_name, website, phone, email, pinterest."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Leads"
    sheet.append(COLUMNS)

    for row in rows:
        sheet.append(
            [
                row["email"] or "",
                row["company_name"] or "",
                row["website"] or "",
                row["phone"] or "",
                row["pinterest"] or "",
            ]
        )

    for column_cells in sheet.columns:
        longest = max((len(str(cell.value)) for cell in column_cells if cell.value), default=10)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(longest + 2, 60)

    tmp_path = f"{output_path}.tmp"
    workbook.save(tmp_path)
    os.replace(tmp_path, output_path)
