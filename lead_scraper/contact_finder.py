"""Shared regex-based extraction of a published owner name, email, and Pinterest
link from a page's HTML.

This never guesses or fabricates a contact detail (e.g. no
first.last@domain.com pattern guessing) -- fields stay blank when nothing
is publicly published on the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PINTEREST_RE = re.compile(r"https?://(?:www\.)?pinterest\.[a-z.]+/[A-Za-z0-9_./-]+", re.IGNORECASE)
TITLE_KEYWORDS = ("founder", "owner", "ceo", "president", "managing director")
TITLE_PATTERN = "|".join(TITLE_KEYWORDS)

_NAME_BEFORE_TITLE = re.compile(rf"([A-Z][a-z]+(?:\s[A-Z][a-z]+){{1,2}})\s*[,\-|]\s*(?:{TITLE_PATTERN})", re.IGNORECASE)
_TITLE_BEFORE_NAME = re.compile(rf"(?:{TITLE_PATTERN})\s*[:\-]\s*([A-Z][a-z]+(?:\s[A-Z][a-z]+){{1,2}})", re.IGNORECASE)
_TITLE_LINE = re.compile(rf".{{0,60}}(?:{TITLE_PATTERN}).{{0,60}}", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Contact:
    email: str = ""
    owner_name: str = ""
    pinterest: str = ""

    @property
    def complete(self) -> bool:
        return bool(self.email and self.owner_name and self.pinterest)

    def merge(self, other: "Contact") -> "Contact":
        """Fill in any still-blank fields from `other`; return self for chaining."""
        self.email = self.email or other.email
        self.owner_name = self.owner_name or other.owner_name
        self.pinterest = self.pinterest or other.pinterest
        return self


def find_owner_name(html: str) -> str:
    """Look for a line like 'Jane Smith, Founder & CEO' or 'Founder: Jane Smith'."""
    flat_text = " ".join(_TAG_RE.sub(" ", html).split())
    for line in _TITLE_LINE.findall(flat_text):
        match = _NAME_BEFORE_TITLE.search(line) or _TITLE_BEFORE_NAME.search(line)
        if match:
            return match.group(1).strip()
    return ""


def extract_contact(html: str) -> Contact:
    email_match = EMAIL_RE.search(html)
    pinterest_match = PINTEREST_RE.search(html)
    return Contact(
        email=email_match.group(0) if email_match else "",
        pinterest=pinterest_match.group(0) if pinterest_match else "",
        owner_name=find_owner_name(html),
    )
