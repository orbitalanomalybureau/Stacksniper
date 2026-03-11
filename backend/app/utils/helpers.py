from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_current_nfl_week() -> Tuple[int, int]:
    """Estimate current NFL season and week based on date.

    Returns (season, week) tuple.
    """
    now = utc_now()
    # NFL regular season typically starts first Thursday of September
    year = now.year
    # Rough approximation; in production use NFL API for accuracy
    if now.month < 3:
        season = year - 1
    elif now.month >= 9:
        season = year
    else:
        season = year  # Offseason, default to upcoming

    # Placeholder week calculation
    week = 1
    return season, week
