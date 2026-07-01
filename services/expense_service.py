"""
services/expense_service.py

Expense management service for the Home Expense Tracker.

Responsibilities
----------------
- Validate and insert expense records.
- Auto-create expense categories on demand (case-insensitive).
- Keep account balances in sync via AccountService.
- Provide retrieval and mutation operations on the expenses table.
"""

from __future__ import annotations

from typing import Optional

from database.database import DatabaseManager
from database.models import Expense, ExpenseCategory
from services.account_service import AccountService
from utils.validators import (
    ValidationError,
    validate_amount,
    validate_date,
    validate_expense_member,
    validate_text_length,
)

# Maximum length for a category name.
_CATEGORY_NAME_MAX_LEN = 100


class ExpenseService:
    """
    Service layer for expense-related operations.

    Attributes
    ----------
    db : DatabaseManager
        The shared database manager injected at construction time.
    account_service : AccountService
        Used to validate accounts and mutate account balances.
    """

    def __init__(
        self,
        db: DatabaseManager,
        account_service: AccountService,
    ) -> None:
        """
        Initialise the service with a DatabaseManager and AccountService.

        Parameters
        ----------
        db : DatabaseManager
            The database manager used to obtain connections and transactions.
        account_service : AccountService
            The account service used for balance mutations.
        """
        self.db = db
        self.account_service = account_service

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate(self, expense: Expense) -> None:
        """
        Validate all fields of *expense*, raising :class:`ValidationError`
        on the first failing constraint.

        Raises
        ------
        ValidationError
            If any field fails its constraint.
        """
        # Amount must be > 0
        validate_amount(expense.amount)

        # Date must be a valid YYYY-MM-DD string
        validate_date(expense.expense_date)

        # paid_by must be Mom, Me, or Sister
        validate_expense_member(expense.paid_by)

        # account_id must reference an existing account
        if self.account_service.get_account_by_id(expense.account_id) is None:
            raise ValidationError(
                f"No account found with id {expense.account_id}."
            )

    # ------------------------------------------------------------------
    # Category management
    # ------------------------------------------------------------------

    def get_or_create_category(self, name: str) -> int:
        """
        Return the id of the category whose name matches *name*
        (case-insensitive), creating it if it does not yet exist.

        Parameters
        ----------
        name : str
            The category name to look up or create.

        Returns
        -------
        int
            The id of the found or newly created category.

        Raises
        ------
        ValidationError
            If *name* exceeds 100 characters.
        """
        validate_text_length(name, _CATEGORY_NAME_MAX_LEN, "Category name")

        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT id FROM expense_categories "
                "WHERE LOWER(category_name) = LOWER(?);",
                (name,),
            )
            row = cursor.fetchone()

            if row is not None:
                return row["id"]

            cursor = conn.execute(
                "INSERT INTO expense_categories (category_name) VALUES (?);",
                (name,),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def get_all_categories(self) -> list[ExpenseCategory]:
        """
        Return all expense categories ordered by name ascending.

        Returns
        -------
        list[ExpenseCategory]
            A list of ExpenseCategory dataclass instances.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "SELECT id, category_name "
                "FROM expense_categories "
                "ORDER BY category_name ASC;"
            )
            rows = cursor.fetchall()

        return [
            ExpenseCategory(id=row["id"], category_name=row["category_name"])
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def add_expense(self, expense: Expense) -> int:
        """
        Validate, auto-create category if needed, persist a new expense
        record, and update the associated account balance.

        Parameters
        ----------
        expense : Expense
            The expense to persist.  ``category_id`` may be 0 / unset;
            if a category lookup is needed, call
            :meth:`get_or_create_category` before passing the object in.

        Returns
        -------
        int
            The newly assigned row id.

        Raises
        ------
        ValidationError
            If any field fails its constraint.
        """
        self._validate(expense)

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses
                    (expense_date, amount, category_id, description,
                     paid_by, account_id, payment_method, notes)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    expense.expense_date,
                    expense.amount,
                    expense.category_id,
                    expense.description,
                    expense.paid_by,
                    expense.account_id,
                    expense.payment_method,
                    expense.notes,
                ),
            )
            new_id: int = cursor.lastrowid  # type: ignore[assignment]

        # Debit the account after the row is safely committed.
        self.account_service.apply_expense(expense.account_id, expense.amount)

        return new_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all_expenses(self) -> list[Expense]:
        """Return all expense records ordered by expense_date descending."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, expense_date, amount, category_id, description,
                       paid_by, account_id, payment_method, notes, created_at
                FROM expenses
                ORDER BY expense_date DESC;
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_expense(row) for row in rows]

    def get_expense_by_id(self, expense_id: int) -> Optional[Expense]:
        """
        Return the expense record with the given id, or None if not found.

        Parameters
        ----------
        expense_id : int
            The primary-key id of the expense to look up.

        Returns
        -------
        Expense or None
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, expense_date, amount, category_id, description,
                       paid_by, account_id, payment_method, notes, created_at
                FROM expenses
                WHERE id = ?;
                """,
                (expense_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_expense(row)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_expense(self, expense: Expense) -> None:
        """
        Update an existing expense record and keep account balances correct.

        Steps:

        1. Fetch the old record.
        2. Validate the new values.
        3. Reverse the old balance debit via ``account_service.reverse_expense``.
        4. Apply the new balance debit via ``account_service.apply_expense``.
        5. UPDATE the row in the database.

        Parameters
        ----------
        expense : Expense
            The expense with updated field values.  ``expense.id`` must
            reference an existing row.

        Raises
        ------
        ValidationError
            If any field fails validation.
        ValueError
            If no record with ``expense.id`` exists.
        """
        old = self.get_expense_by_id(expense.id)  # type: ignore[arg-type]
        if old is None:
            raise ValueError(f"No expense record found with id {expense.id}.")

        self._validate(expense)

        # Balance correction: undo the old debit, apply the new one.
        self.account_service.reverse_expense(old.account_id, old.amount)
        self.account_service.apply_expense(expense.account_id, expense.amount)

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE expenses
                SET expense_date   = ?,
                    amount         = ?,
                    category_id    = ?,
                    description    = ?,
                    paid_by        = ?,
                    account_id     = ?,
                    payment_method = ?,
                    notes          = ?
                WHERE id = ?;
                """,
                (
                    expense.expense_date,
                    expense.amount,
                    expense.category_id,
                    expense.description,
                    expense.paid_by,
                    expense.account_id,
                    expense.payment_method,
                    expense.notes,
                    expense.id,
                ),
            )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_expense(self, expense_id: int) -> None:
        """
        Delete an expense record and reverse its effect on the account balance.

        Parameters
        ----------
        expense_id : int
            The id of the expense to delete.

        Raises
        ------
        ValueError
            If no record with *expense_id* exists.
        """
        old = self.get_expense_by_id(expense_id)
        if old is None:
            raise ValueError(f"No expense record found with id {expense_id}.")

        # Reverse the balance debit before deleting the row.
        self.account_service.reverse_expense(old.account_id, old.amount)

        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM expenses WHERE id = ?;",
                (expense_id,),
            )

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_expense(row) -> Expense:
        """Convert a sqlite3.Row to an Expense dataclass instance."""
        return Expense(
            id=row["id"],
            expense_date=row["expense_date"],
            amount=row["amount"],
            category_id=row["category_id"],
            description=row["description"],
            paid_by=row["paid_by"],
            account_id=row["account_id"],
            payment_method=row["payment_method"],
            notes=row["notes"],
            created_at=row["created_at"],
        )
