"""
app/utils/date_utils.py
Date parsing and formatting helpers for report fields.
"""

from datetime import date, datetime
from typing import Optional


def today_display() -> str:
    """Return today's date in report display format: 'March 18, 2026'"""
    return date.today().strftime("%B %d, %Y")


def today_filename() -> str:
    """Return today's date as a filename-safe string: '2026-03-18'"""
    return date.today().strftime("%Y-%m-%d")


def parse_display_date(date_str: str) -> Optional[date]:
    """
    Attempt to parse a human-entered date string into a date object.
    Tries multiple common formats.
    Returns None if unparseable.
    """
    if not date_str:
        return None

    formats = [
        "%B %d, %Y",     # March 18, 2026
        "%B %Y",          # March 2026
        "%m/%d/%Y",       # 03/18/2026
        "%m-%d-%Y",       # 03-18-2026
        "%Y-%m-%d",       # 2026-03-18
        "%b %d, %Y",     # Mar 18, 2026
        "%b. %d, %Y",    # Mar. 18, 2026
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue

    return None


def format_report_date(date_str: str) -> str:
    """
    Normalize a date string to report display format.
    Returns the original string unchanged if parsing fails.
    """
    parsed = parse_display_date(date_str)
    if parsed:
        return parsed.strftime("%B %d, %Y")
    return date_str


def year_of(date_str: str) -> str:
    """Extract year string from a date string, or empty string."""
    parsed = parse_display_date(date_str)
    return str(parsed.year) if parsed else ""
