from datetime import date, timedelta
from enum import Enum


class Period(str, Enum):
    today = "today"
    last_week = "last_week"
    last_month = "last_month"
    all_time = "all_time"


_PERIOD_DAYS = {"today": 1, "last_week": 7, "last_month": 30}


def period_since(period: str) -> str | None:
    """Return ISO date string for start of period, or None for all_time."""
    days = _PERIOD_DAYS.get(period)
    if days is None:
        return None
    today = date.today()
    if days == 1:
        return today.isoformat()
    return (today - timedelta(days=days - 1)).isoformat()
