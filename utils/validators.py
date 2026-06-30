"""
utils/validators.py

Validation utilities for the Home Expense Tracker.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from utils.constants import (
    BANK_ACCOUNTS,
    DATE_FORMAT,
    EXPENSE_MEMBERS,
    FAMILY_MEMBERS,
    INCOME_SOURCES,
    PAYMENT_METHODS,
)


class ValidationError(Exception):
    """Raised when validation fails."""


def validate_required(value: str, field_name: str) -> None:
    """
    Validate that a required field is not empty.
    """
    if not value or not value.strip():
        raise ValidationError(f"{field_name} is required.")


def validate_amount(amount: float) -> None:
    """
    Validate that the amount is greater than zero.
    """
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")


def validate_date(date_string: str) -> None:
    """
    Validate date format.
    """
    try:
        datetime.strptime(date_string, DATE_FORMAT)
    except ValueError as exc:
        raise ValidationError(
            f"Date must be in the format {DATE_FORMAT}."
        ) from exc


def validate_bank_account(account_name: str) -> None:
    """
    Validate bank account.
    """
    if account_name not in BANK_ACCOUNTS:
        raise ValidationError("Invalid bank account selected.")


def validate_income_source(source: str) -> None:
    """
    Validate income source.
    """
    if source not in INCOME_SOURCES:
        raise ValidationError("Invalid income source.")


def validate_expense_member(member: str) -> None:
    """
    Validate member paying the expense.
    """
    if member not in EXPENSE_MEMBERS:
        raise ValidationError(
            "Expense can only be paid by Mom, Me or Sister."
        )


def validate_family_member(member: str) -> None:
    """
    Validate family member.
    """
    if member not in FAMILY_MEMBERS:
        raise ValidationError("Invalid family member.")


def validate_payment_method(method: str) -> None:
    """
    Validate payment method.
    """
    if method not in PAYMENT_METHODS:
        raise ValidationError("Invalid payment method.")


def validate_text_length(
    value: Optional[str],
    max_length: int,
    field_name: str,
) -> None:
    """
    Validate maximum text length.
    """
    if value is None:
        return

    if len(value) > max_length:
        raise ValidationError(
            f"{field_name} cannot exceed {max_length} characters."
        )


def sanitize_text(value: str) -> str:
    """
    Remove leading and trailing whitespace.
    """
    return value.strip()


def validate_positive_integer(
    value: int,
    field_name: str,
) -> None:
    """
    Validate a positive integer.
    """
    if value <= 0:
        raise ValidationError(
            f"{field_name} must be greater than zero."
        )