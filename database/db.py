"""SQLite persistence: searches, businesses, and processing errors.

Schema is designed so a long-running job can be interrupted (VPS restart,
disconnect, crash, Ctrl+C) and resumed without reprocessing completed
work: `searches` tracks which keyword/location combos are done, and
`businesses` is matched on normalized domain/phone/name to prevent
duplicate leads across combos.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(keyword, location)
);

CREATE TABLE IF NOT EXISTS businesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    normalized_name TEXT,
    website TEXT,
    normalized_domain TEXT,
    phone TEXT,
    normalized_phone TEXT,
    email TEXT,
    pinterest TEXT,
    address TEXT,
    keyword TEXT,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'NEW',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_businesses_domain ON businesses(normalized_domain);
CREATE INDEX IF NOT EXISTS idx_businesses_phone ON businesses(normalized_phone);
CREATE INDEX IF NOT EXISTS idx_businesses_name ON businesses(normalized_name);

CREATE TABLE IF NOT EXISTS processing_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id INTEGER,
    keyword TEXT,
    location TEXT,
    stage TEXT NOT NULL,
    error_message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL;")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- searches (drive --resume) ----

    def get_search_status(self, keyword: str, location: str) -> Optional[str]:
        row = self.connection.execute(
            "SELECT status FROM searches WHERE keyword = ? AND location = ?", (keyword, location)
        ).fetchone()
        return row["status"] if row else None

    def start_search(self, keyword: str, location: str) -> None:
        now = _now()
        self.connection.execute(
            """
            INSERT INTO searches (keyword, location, status, created_at, updated_at)
            VALUES (?, ?, 'IN_PROGRESS', ?, ?)
            ON CONFLICT(keyword, location) DO UPDATE SET status = 'IN_PROGRESS', updated_at = excluded.updated_at
            """,
            (keyword, location, now, now),
        )
        self.connection.commit()

    def complete_search(self, keyword: str, location: str) -> None:
        self.connection.execute(
            "UPDATE searches SET status = 'COMPLETE', updated_at = ? WHERE keyword = ? AND location = ?",
            (_now(), keyword, location),
        )
        self.connection.commit()

    # ---- businesses (drive deduplication + merging) ----

    def find_matching_business(
        self, normalized_domain: str, normalized_phone: str, normalized_name: str
    ) -> Optional[sqlite3.Row]:
        """Domain is the strongest identifier, then phone, then name as a
        last resort. Returns the first match found, or None."""
        if normalized_domain:
            row = self.connection.execute(
                "SELECT * FROM businesses WHERE normalized_domain = ? LIMIT 1", (normalized_domain,)
            ).fetchone()
            if row:
                return row
        if normalized_phone:
            row = self.connection.execute(
                "SELECT * FROM businesses WHERE normalized_phone = ? LIMIT 1", (normalized_phone,)
            ).fetchone()
            if row:
                return row
        if normalized_name:
            row = self.connection.execute(
                "SELECT * FROM businesses WHERE normalized_name = ? LIMIT 1", (normalized_name,)
            ).fetchone()
            if row:
                return row
        return None

    def insert_business(self, fields: dict) -> int:
        now = _now()
        cursor = self.connection.execute(
            """
            INSERT INTO businesses (
                company_name, normalized_name, website, normalized_domain,
                phone, normalized_phone, email, pinterest, address,
                keyword, location, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fields["company_name"], fields.get("normalized_name", ""), fields.get("website", ""),
                fields.get("normalized_domain", ""), fields.get("phone", ""), fields.get("normalized_phone", ""),
                fields.get("email", ""), fields.get("pinterest", ""), fields.get("address", ""),
                fields.get("keyword", ""), fields.get("location", ""), fields.get("status", "NEW"), now, now,
            ),
        )
        self.connection.commit()
        return cursor.lastrowid

    def update_business(self, business_id: int, fields: dict) -> None:
        if not fields:
            return
        fields = dict(fields)
        fields["updated_at"] = _now()
        columns = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [business_id]
        self.connection.execute(f"UPDATE businesses SET {columns} WHERE id = ?", values)
        self.connection.commit()

    def get_business(self, business_id: int) -> Optional[sqlite3.Row]:
        return self.connection.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()

    def get_export_rows(self) -> list[sqlite3.Row]:
        """Rows for the Excel export, in first-discovered order."""
        return self.connection.execute(
            "SELECT company_name, website, phone, email, pinterest FROM businesses "
            "WHERE company_name IS NOT NULL AND company_name != '' ORDER BY id ASC"
        ).fetchall()

    def count_businesses(self) -> int:
        return self.connection.execute("SELECT COUNT(*) AS c FROM businesses").fetchone()["c"]

    # ---- errors ----

    def log_error(
        self, stage: str, message: str, keyword: str = "", location: str = "", business_id: Optional[int] = None
    ) -> None:
        self.connection.execute(
            "INSERT INTO processing_errors (business_id, keyword, location, stage, error_message, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (business_id, keyword, location, stage, message, _now()),
        )
        self.connection.commit()
