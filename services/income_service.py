"""
services/income_service.py

Income management service for the Home Expense Tracker.

Responsibilities
----------------
- Validate and insert income records.
- Enforce the "Dad Transfer" business rule.
- Keep account balances in sync via AccountService.
- Provide retrieval and mutation operations on the income table.
"""

from __future__ import annotations

from typing import Optional

from database.database import DatabaseManager
from database.models import Income
from services.account_service import AccountService
from utils.constants import INCOME_SOURCE_DAD_TRANSFER
from utils.validators import (
    ValidationError,
    validate_amount,
    validate_date,
    validate_income_source,
)

# Prefix automatically added to descriptions when source is "Dad Transfer".
_DAD_TRANSFER_PREFIX = "Income from Dad: "

# Valid values for the received_by field.
_VALID_RECEIVERS = ("Mom", "Me", "Sister")


class IncomeService:
    """
    Service layer for income-related operations.

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

    def _apply_dad_transfer_rule(self, income: Income) -> None:
        """
        Enforce the Dad Transfer business rule in-place on *income*.

        - ``received_by`` is forced to ``"Me"``.
        - If description does not already start with the prefix
          ``"Income from Dad: "``, it is prepended.
        """
        income.received_by = "Me"
        if not income.description.startswith(_DAD_TRANSFER_PREFIX):
            income.description = _DAD_TRANSFER_PREFIX + income.description

    def _validate(self, income: Income) -> None:
        """
        Validate all fields of *income*, raising :class:`ValidationError`
        on the first failing constraint.

        Raises
        ------
        ValidationError
            If any field fails its constraint.
        """
        # Amount
        try:
            validate_amount(income.amount)
        except ValidationError as exc:
            raise ValidationError("amount", str(exc)) from exc

        # Date
        try:
            validate_date(income.income_date)
        except ValidationError as exc:
            raise ValidationError("income_date", str(exc)) from exc

        # Source
        try:
            validate_income_source(income.source)
        except ValidationError as exc:
            raise ValidationError("source", str(exc)) from exc

        # received_by
        if income.received_by not in _VALID_RECEIVERS:
            raise ValidationError(
                "received_by",
                f"received_by must be one of: {', '.join(_VALID_RECEIVERS)}.",
            )

        # account_id must reference an existing account
        if self.account_service.get_account_by_id(income.account_id) is None:
            raise ValidationError(
                "account_id",
                f"No account found with id {income.account_id}.",
            )

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def add_income(self, income: Income) -> int:
        """
        Validate, apply business rules, persist a new income record, and
        update the associated account balance.

        Returns the new row id.
        """
        # Enforce Dad Transfer rule before validation so the mutated
        # values are what get validated and persisted.
        if income.source == INCOME_SOURCE_DAD_TRANSFER:
            self._apply_dad_transfer_rule(income)

        self._validate(income)

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO income
                    (income_date, amount, source, received_by, account_id, description)
                VALUES
                    (?, ?, ?, ?, ?, ?);
                """,
                (
                    income.income_date,
                    income.amount,
                    income.source,
                    income.received_by,
                    income.account_id,
                    income.description,
                ),
            )
            new_id: int = cursor.lastrowid  # type: ignore[assignment]

        # Credit the account after the row is safely committed.
        self.account_service.apply_income(income.account_id, income.amount)

        return new_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all_income(self) -> list[Income]:
        """Return all income records ordered by income_date descending."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, income_date, amount, source, received_by,
                       account_id, description, created_at
                FROM income
                ORDER BY income_date DESC;
                """
            )
            rows = cursor.fetchall()

        return [self._row_to_income(row) for row in rows]

    def get_income_by_id(self, income_id: int) -> Optional[Income]:
        """Return the income record with the given id, or None if not found."""
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT id, income_date, amount, source, received_by,
                       account_id, description, created_at
                FROM income
                WHERE id = ?;
                """,
                (income_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_income(row)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update_income(self, income: Income) -> None:
        """
        Update an existing income record and keep account balances correct.

        Steps:
        1. Fetch the old record.
        2. Call account_service.reverse_income(old.account_id, old.amount).
        3. Call account_service.apply_income(new.account_id, new.amount).
        4. UPDATE the row in DB.

        Raises
        ------
        ValidationError
            If any field fails validation.
        ValueError
            If no record with income.id exists.
        """
        old = self.get_income_by_id(income.id)  # type: ignore[arg-type]
        if old is None:
            raise ValueError(f"No income record found with id {income.id}.")

        # Enforce Dad Transfer rule before validation.
        if income.source == INCOME_SOURCE_DAD_TRANSFER:
            self._apply_dad_transfer_rule(income)

        self._validate(income)

        # Balance reversal: undo the old credit, apply the new one.
        self.account_service.reverse_income(old.account_id, old.amount)
        self.account_service.apply_income(income.account_id, income.amount)

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE income
                SET income_date = ?,
                    amount      = ?,
                    source      = ?,
                    received_by = ?,
                    account_id  = ?,
                    description = ?
                WHERE id = ?;
                """,
                (
                    income.income_date,
                    income.amount,
                    income.source,
                    income.received_by,
                    income.account_id,
                    income.description,
                    income.id,
                ),
            )

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_income(self, income_id: int) -> None:
        """
        Delete an income record and reverse its effect on the account balance.

        Raises
        ------
        ValueError
            If no record with income_id exists.
        """
        old = self.get_income_by_id(income_id)
        if old is None:
            raise ValueError(f"No income record found with id {income_id}.")

        # Reverse the balance before deleting the row.
        self.account_service.reverse_income(old.account_id, old.amount)

        with self.db.transaction() as conn:
            conn.execute(
                "DELETE FROM income WHERE id = ?;",
                (income_id,),
            )

    # ------------------------------------------------------------------
    # Private utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_income(row) -> Income:
        """Convert a sqlite3.Row to an Income dataclass instance."""
        return Income(
            id=row["id"],
            income_date=row["income_date"],
            amount=row["amount"],
            source=row["source"],
            received_by=row["received_by"],
            account_id=row["account_id"],
            description=row["description"],
            created_at=row["created_at"],
        )
