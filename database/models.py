"""
database/models.py

Data models used throughout the Home Expense Tracker application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------

@dataclass(slots=True)
class Account:
    """
    Represents a bank account.
    """

    id: Optional[int] = None
    account_name: str = ""
    opening_balance: float = 0.0
    current_balance: float = 0.0
    created_at: Optional[str] = None


# ---------------------------------------------------------------------
# Expense Category
# ---------------------------------------------------------------------

@dataclass(slots=True)
class ExpenseCategory:
    """
    Represents an expense category.
    """

    id: Optional[int] = None
    category_name: str = ""


# ---------------------------------------------------------------------
# Income
# ---------------------------------------------------------------------

@dataclass(slots=True)
class Income:
    """
    Represents an income transaction.
    """

    id: Optional[int] = None

    income_date: str = ""

    amount: float = 0.0

    source: str = ""

    received_by: str = ""

    account_id: int = 0

    description: str = ""

    created_at: Optional[str] = None


# ---------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------

@dataclass(slots=True)
class Expense:
    """
    Represents an expense transaction.
    """

    id: Optional[int] = None

    expense_date: str = ""

    amount: float = 0.0

    category_id: int = 0

    description: str = ""

    paid_by: str = ""

    account_id: int = 0

    payment_method: str = ""

    notes: str = ""

    created_at: Optional[str] = None