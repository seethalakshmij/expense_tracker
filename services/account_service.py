"""
services/account_service.py

Account management service for the Home Expense Tracker.

Responsibilities
----------------
- Retrieve all accounts or a single account by id.
- Update an account's opening balance and recalculate current_balance.
- Apply and reverse income/expense amounts on an account's current_balance,
  each mutation wrapped in a database transaction that rolls back on failure.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from database.database import DatabaseManager
from database.models import Account


class AccountService:
    """
    Service layer for account-related operations.

    Attributes
    ----------
    db : DatabaseManager
        The shared database manager injected at construction time.
    """

    def __init__(self, db: DatabaseManager) -> None:
        """
        Initialise the service with a DatabaseManager instance.

        Parameters
        ----------
        db : DatabaseManager
            The database manager used to obtain connections and transactions.
        """
        self.db = db

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_all_accounts(self) -> list[Account]:
        """
        Return all accounts ordered by id ascending.

        Returns
        -------
        list[Account]
            A list of Account dataclass instances (may be empty if the
            accounts table has not been seeded yet).
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT id, account_name, opening_balance, current_balance, created_at "
                "FROM accounts "
                "ORDER BY id ASC;"
            )
            rows = cursor.fetchall()

        return [
            Account(
                id=row["id"],
                account_name=row["account_name"],
                opening_balance=row["opening_balance"],
                current_balance=row["current_balance"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """
        Return the account with the given id, or None if not found.

        Parameters
        ----------
        account_id : int
            The primary-key id of the account to look up.

        Returns
        -------
        Account or None
            The matching Account instance, or None if no row exists.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT id, account_name, opening_balance, current_balance, created_at "
                "FROM accounts "
                "WHERE id = ?;",
                (account_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return Account(
            id=row["id"],
            account_name=row["account_name"],
            opening_balance=row["opening_balance"],
            current_balance=row["current_balance"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Opening-balance update
    # ------------------------------------------------------------------

    def update_opening_balance(
        self, account_id: int, new_opening: float
    ) -> None:
        """
        Persist a new opening balance and recalculate current_balance from scratch.

        current_balance = new_opening_balance + SUM(income) − SUM(expenses)

        Parameters
        ----------
        account_id : int
            The id of the account to update.
        new_opening : float
            The new opening balance value.
        """
        with self.db.transaction() as conn:
            # Persist the new opening balance first.
            conn.execute(
                "UPDATE accounts SET opening_balance = ? WHERE id = ?;",
                (new_opening, account_id),
            )
            cursor = conn.cursor()
            self._recalculate_balance(cursor, account_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _recalculate_balance(
        self, cursor: sqlite3.Cursor, account_id: int
    ) -> None:
        """
        Recalculate and persist current_balance for an account.

        current_balance = opening_balance + SUM(income) − SUM(expenses)

        This method must be called within an active transaction; it does NOT
        open its own transaction.

        Parameters
        ----------
        cursor : sqlite3.Cursor
            An active cursor belonging to the current transaction.
        account_id : int
            The id of the account whose balance should be recalculated.
        """
        cursor.execute(
            "SELECT opening_balance FROM accounts WHERE id = ?;",
            (account_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Account with id {account_id} does not exist.")

        opening: float = row["opening_balance"] if isinstance(row, sqlite3.Row) else row[0]

        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0.0) FROM income WHERE account_id = ?;",
            (account_id,),
        )
        income_row = cursor.fetchone()
        total_income: float = income_row[0] if income_row else 0.0

        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0.0) FROM expenses WHERE account_id = ?;",
            (account_id,),
        )
        expense_row = cursor.fetchone()
        total_expenses: float = expense_row[0] if expense_row else 0.0

        new_balance = opening + total_income - total_expenses

        cursor.execute(
            "UPDATE accounts SET current_balance = ? WHERE id = ?;",
            (new_balance, account_id),
        )

    # ------------------------------------------------------------------
    # Balance mutation helpers (used by IncomeService / ExpenseService)
    # ------------------------------------------------------------------

    def apply_income(self, account_id: int, amount: float) -> None:
        """
        Increment the account's current_balance by *amount*.

        Opens its own transaction; rolls back automatically on failure.

        Parameters
        ----------
        account_id : int
            The id of the account to credit.
        amount : float
            The positive income amount to add.
        """
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE accounts "
                "SET current_balance = current_balance + ? "
                "WHERE id = ?;",
                (amount, account_id),
            )

    def reverse_income(self, account_id: int, amount: float) -> None:
        """
        Decrement the account's current_balance by *amount*.

        Used when an income record is deleted or edited (undo the prior credit).
        Opens its own transaction; rolls back automatically on failure.

        Parameters
        ----------
        account_id : int
            The id of the account to debit.
        amount : float
            The positive income amount to subtract.
        """
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE accounts "
                "SET current_balance = current_balance - ? "
                "WHERE id = ?;",
                (amount, account_id),
            )

    def apply_expense(self, account_id: int, amount: float) -> None:
        """
        Decrement the account's current_balance by *amount*.

        Opens its own transaction; rolls back automatically on failure.

        Parameters
        ----------
        account_id : int
            The id of the account to debit.
        amount : float
            The positive expense amount to subtract.
        """
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE accounts "
                "SET current_balance = current_balance - ? "
                "WHERE id = ?;",
                (amount, account_id),
            )

    def reverse_expense(self, account_id: int, amount: float) -> None:
        """
        Increment the account's current_balance by *amount*.

        Used when an expense record is deleted or edited (undo the prior debit).
        Opens its own transaction; rolls back automatically on failure.

        Parameters
        ----------
        account_id : int
            The id of the account to credit.
        amount : float
            The positive expense amount to add back.
        """
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE accounts "
                "SET current_balance = current_balance + ? "
                "WHERE id = ?;",
                (amount, account_id),
            )
