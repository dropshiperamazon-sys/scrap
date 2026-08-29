"""Application-wide logging: everything goes to logs/app.log; only
warnings/errors also echo to the console (routine per-business detail
would otherwise fight with the pretty progress output main.py prints)."""

from __future__ import annotations

import logging
import os


def setup_logging(log_file: str, level: int = logging.INFO) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    logger = logging.getLogger("lead_scraper")
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_business_result(
    logger: logging.Logger,
    keyword: str,
    location: str,
    company_name: str,
    website_found: bool,
    email_found: bool,
    phone_found: bool,
    pinterest_found: bool,
    status: str,
) -> None:
    def found_label(found: bool) -> str:
        return "Found" if found else "Not Found"

    logger.info(
        f"Keyword: {keyword} | Location: {location} | Company: {company_name} | "
        f"Website: {found_label(website_found)} | Email: {found_label(email_found)} | "
        f"Phone: {found_label(phone_found)} | Pinterest: {found_label(pinterest_found)} | "
        f"Status: {status}"
    )
