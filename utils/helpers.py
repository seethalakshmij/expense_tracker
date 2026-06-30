"""
utils/helpers.py

Common helper functions for the Home Expense Tracker.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from utils.constants import CURRENCY_SYMBOL, DATE_FORMAT


def today() -> str:
    """
    Return today's date as a string.

    Example:
        2026-06-30
    """
    return date.today().strftime(DATE_FORMAT)


def current_timestamp() -> str:
    """
    Return the current timestamp.

    Example:
        2026-06-30 14:35:20
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_currency(amount: float) -> str:
    """
    Format a number as Indian currency.

    Example:
        ₹1,250.75
    """
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def parse_date(date_string: str) -> date:
    """
    Convert a string into a date object.
    """
    return datetime.strptime(date_string, DATE_FORMAT).date()


def format_date(date_obj: date) -> str:
    """
    Convert a date object into a string.
    """
    return date_obj.strftime(DATE_FORMAT)


def safe_float(value: object, default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: object, default: int = 0) -> int:
    """
    Safely convert a value to int.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def month_start() -> str:
    """
    Return the first day of the current month.

    Example:
        2026-06-01
    """
    today_date = date.today()
    return today_date.replace(day=1).strftime(DATE_FORMAT)


def current_year() -> int:
    """
    Return the current year.
    """
    return date.today().year


def current_month() -> int:
    """
    Return the current month.
    """
    return date.today().month


def is_valid_date(date_string: str) -> bool:
    """
    Check whether a date string matches the application's
    standard date format.
    """
    try:
        datetime.strptime(date_string, DATE_FORMAT)
        return True
    except ValueError:
        return False


def none_to_empty(value: Optional[str]) -> str:
    """
    Convert None to an empty string.
    """
    return "" if value is None else value


def round_amount(amount: float) -> float:
    """
    Round monetary values to two decimal places.
    """
    return round(amount, 2)