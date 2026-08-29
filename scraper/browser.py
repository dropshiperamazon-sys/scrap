"""Manages the Playwright browser lifecycle: startup, page creation, crash
recovery, and clean shutdown.

No anti-detection or CAPTCHA-bypass logic lives here or anywhere else in
this project -- if a page appears blocked, callers are expected to log it
and move on rather than trying to evade the block.
"""

from __future__ import annotations

import logging

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


class BrowserManager:
    def __init__(self, headless: bool, logger: logging.Logger):
        self.headless = headless
        self.logger = logger
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context()
        self.logger.info(f"Browser started (headless={self.headless}).")

    def _is_alive(self) -> bool:
        try:
            return self._browser is not None and self._browser.is_connected()
        except Exception:
            return False

    def _ensure_alive(self) -> None:
        """Restart the browser/context if a previous crash tore it down."""
        if self._is_alive():
            if self._context is None:
                self._context = self._browser.new_context()
            return
        self.logger.warning("Browser appears to have crashed or never started; (re)starting it.")
        self.close()
        self.start()

    def safe_new_page(self) -> Page:
        """Get a fresh page, recovering from a crashed browser/context first."""
        self._ensure_alive()
        return self._context.new_page()

    def close_page(self, page: Page | None) -> None:
        if page is None:
            return
        try:
            page.close()
        except Exception:
            pass

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._browser = None
        self._playwright = None

    def __enter__(self) -> "BrowserManager":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
        self.logger.info("Browser closed.")
