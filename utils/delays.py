"""Randomized pacing between batches.

This exists purely for reasonable pacing and resource management. It is
NOT a mechanism to defeat CAPTCHA, anti-bot protection, or rate limits --
if a source blocks automation, the scraper/web_search stages log it and
move on rather than waiting it out or attempting to bypass it.
"""

from __future__ import annotations

import logging
import random
import time


def wait_between_batches(min_seconds: int, max_seconds: int, logger: logging.Logger) -> None:
    if max_seconds <= 0:
        return
    low, high = sorted((min_seconds, max_seconds))
    delay = random.uniform(low, high) if high > low else float(low)
    minutes = delay / 60
    logger.info(f"Batch complete. Waiting {minutes:.1f} minutes before the next batch.")
    print(f"Waiting approximately {minutes:.1f} minutes...")
    time.sleep(delay)
