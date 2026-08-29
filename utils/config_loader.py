"""Loads config.yaml and applies CLI-argument overrides.

Every user-tunable knob (keywords, locations, batch size, delays,
headless mode) lives in config.yaml -- changing a campaign never requires
touching Python code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

DEFAULT_CONFIG: dict = {
    "keywords": [],
    "locations": [],
    "batch_size": 5,
    "min_delay_seconds": 120,
    "max_delay_seconds": 300,
    "require_website": True,
    "find_email": True,
    "find_phone": True,
    "find_pinterest": True,
    "headless": False,
    "output_file": "output/leads.xlsx",
    "database_file": "data/leads.db",
    "log_file": "logs/app.log",
    "max_results_per_query": 40,
}


@dataclass
class AppConfig:
    keywords: list[str]
    locations: list[str]
    batch_size: int
    min_delay_seconds: int
    max_delay_seconds: int
    require_website: bool
    find_email: bool
    find_phone: bool
    find_pinterest: bool
    headless: bool
    output_file: str
    database_file: str
    log_file: str
    max_results_per_query: int

    def combinations(self) -> list[tuple[str, str]]:
        """Keyword x location, keyword-major within each location (matches
        the processing order described in the workflow: all keywords for
        location 1, then all keywords for location 2, etc.)."""
        return [(keyword, location) for location in self.locations for keyword in self.keywords]


def load_config(path: str = "config.yaml") -> dict:
    data = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as config_file:
            loaded = yaml.safe_load(config_file) or {}
        data.update(loaded)
    return data


def build_app_config(raw: dict, overrides: dict | None = None) -> AppConfig:
    merged = dict(raw)
    for key, value in (overrides or {}).items():
        if value is not None:
            merged[key] = value

    return AppConfig(
        keywords=list(merged.get("keywords") or []),
        locations=list(merged.get("locations") or []),
        batch_size=int(merged["batch_size"]),
        min_delay_seconds=int(merged["min_delay_seconds"]),
        max_delay_seconds=int(merged["max_delay_seconds"]),
        require_website=bool(merged["require_website"]),
        find_email=bool(merged["find_email"]),
        find_phone=bool(merged["find_phone"]),
        find_pinterest=bool(merged["find_pinterest"]),
        headless=bool(merged["headless"]),
        output_file=str(merged["output_file"]),
        database_file=str(merged["database_file"]),
        log_file=str(merged["log_file"]),
        max_results_per_query=int(merged.get("max_results_per_query", 40)),
    )
