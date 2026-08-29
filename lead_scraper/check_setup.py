"""Pre-flight check: confirms Python version, dependencies, and the Playwright
Chromium browser are all in place before you try a real scrape.

Run with:
    python -m lead_scraper.check_setup
"""

from __future__ import annotations

import importlib
import sys

REQUIRED_PACKAGES = ["playwright", "requests", "pandas", "openpyxl"]
MIN_PYTHON = (3, 10)


def _check_python_version() -> tuple[bool, str]:
    ok = sys.version_info >= MIN_PYTHON
    version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    requirement = f"need >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}"
    return ok, f"Python {version_str} ({'OK' if ok else requirement})"


def _check_package(package_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(package_name)
        return True, f"{package_name}: installed"
    except ImportError:
        return False, f"{package_name}: MISSING (run: pip install -r requirements.txt)"


def _check_chromium_installed() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False, "chromium: can't check (playwright not installed)"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return True, "chromium: installed and launches"
    except Exception as exc:
        return False, f"chromium: NOT ready ({exc}). Run: playwright install chromium"


def main() -> int:
    checks = [_check_python_version()]
    checks += [_check_package(package) for package in REQUIRED_PACKAGES]
    checks.append(_check_chromium_installed())

    all_ok = True
    for ok, message in checks:
        print(f"[{'OK' if ok else 'FAIL'}] {message}")
        all_ok = all_ok and ok

    print()
    print("All checks passed - ready to run: python -m lead_scraper.cli scrape" if all_ok else "Fix the FAIL line(s) above before running a real scrape.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
