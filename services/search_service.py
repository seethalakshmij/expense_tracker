"""
services/search_service.py

Search service for the Home Expense Tracker.

Responsibilities
----------------
- Accept a flexible filter dict and return a unified list of income and
  expense records that match all supplied criteria.
- Resolve date presets ("Daily", "Weekly", "Monthly", "Yearly") to
  concrete start/end date strings.
- Build parameterised SQL dynamically — values are never interpolated
  directly into the query string.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

from database.database import DatabaseManager
from utils.constants import (
    FILTER_DAILY,
    FILTER_MONTHLY,
    FILTER_WEEKLY,
    FILTER_YEARLY,
)


class SearchService:
    """
    Service layer for cross-table search operations.

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
    # Public API
    # ------------------------------------------------------------------

    def search(self, filters: dict) -> list[dict]:
        """
        Return records matching all supplied *filters*.

        Accepted filter keys
        --------------------
        date_preset : str
            One of "Daily", "Weekly", "Monthly", "Yearly".  Resolved to
            concrete start/end dates based on today.
        start_date : str
            Explicit start date in YYYY-MM-DD format.
        end_date : str
            Explicit end date in YYYY-MM-DD format.
        category_id : int
            Filter expenses by this category id (ignored for income).
        keyword : str
            Case-insensitive LIKE match against the description field.
        member : str
            ``paid_by`` (expenses) or ``received_by`` (income).
        account_id : int
            Filter both tables by this account id.
        source : str
            Filter income by source (ignored for expenses).
        record_type : str
            "income", "expense", or "all" (default).

        Returns
        -------
        list[dict]
            Each dict has keys: ``id``, ``date``, ``amount``, ``type``
            ("Income" or "Expense"), ``category_or_source``, ``member``,
            ``account_name``, ``description``.
            Results are ordered by date descending.
        """
        # --- resolve date range -------------------------------------
        start_date, end_date = self._resolve_dates(filters)

        record_type: str = filters.get("record_type", "all").lower()

        rows: list[dict] = []

        if record_type in ("income", "all"):
            rows.extend(
                self._query_income(filters, start_date, end_date)
            )

        if record_type in ("expense", "all"):
            rows.extend(
                self._query_expenses(filters, start_date, end_date)
            )

        # Sort combined results by date descending
        rows.sort(key=lambda r: r["date"], reverse=True)

        return rows

    # ------------------------------------------------------------------
    # Date-preset resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_dates(
        filters: dict,
    ) -> tuple[str | None, str | None]:
        """
        Determine the effective start and end dates from *filters*.

        Explicit ``start_date`` / ``end_date`` keys take priority over
        ``date_preset``.  Returns ``(None, None)`` when no date constraint
        is supplied.

        Returns
        -------
        tuple[str | None, str | None]
            ``(start_date, end_date)`` as YYYY-MM-DD strings, or None.
        """
        # Explicit dates take priority
        start_date: str | None = filters.get("start_date")
        end_date: str | None = filters.get("end_date")

        if start_date or end_date:
            return start_date, end_date

        preset: str | None = filters.get("date_preset")
        if not preset:
            return None, None

        today: date = date.today()

        if preset == FILTER_DAILY:
            today_str = today.strftime("%Y-%m-%d")
            return today_str, today_str

        if preset == FILTER_WEEKLY:
            # ISO week: Monday = 0, Sunday = 6
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            return monday.strftime("%Y-%m-%d"), sunday.strftime("%Y-%m-%d")

        if preset == FILTER_MONTHLY:
            first_day = today.replace(day=1)
            last_day_num = monthrange(today.year, today.month)[1]
            last_day = today.replace(day=last_day_num)
            return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")

        if preset == FILTER_YEARLY:
            first_day = date(today.year, 1, 1)
            last_day = date(today.year, 12, 31)
            return first_day.strftime("%Y-%m-%d"), last_day.strftime("%Y-%m-%d")

        return None, None

    # ------------------------------------------------------------------
    # Income query builder
    # ------------------------------------------------------------------

    def _query_income(
        self,
        filters: dict,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict]:
        """
        Build and execute a parameterised SELECT on the income table.

        Parameters
        ----------
        filters : dict
            The original filter dict from :meth:`search`.
        start_date : str or None
            Resolved start date.
        end_date : str or None
            Resolved end date.

        Returns
        -------
        list[dict]
            Matching income rows as dicts.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if start_date:
            conditions.append("i.income_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("i.income_date <= ?")
            params.append(end_date)

        keyword: str | None = filters.get("keyword")
        if keyword:
            conditions.append("i.description LIKE ? COLLATE NOCASE")
            params.append(f"%{keyword}%")

        member: str | None = filters.get("member")
        if member:
            conditions.append("i.received_by = ?")
            params.append(member)

        account_id: int | None = filters.get("account_id")
        if account_id is not None:
            conditions.append("i.account_id = ?")
            params.append(account_id)

        source: str | None = filters.get("source")
        if source:
            conditions.append("i.source = ?")
            params.append(source)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT
                i.id,
                i.income_date   AS date,
                i.amount,
                'Income'        AS type,
                i.source        AS category_or_source,
                i.received_by   AS member,
                a.account_name,
                i.description
            FROM income i
            JOIN accounts a ON a.id = i.account_id
            {where_clause}
            ORDER BY i.income_date DESC;
        """

        with self.db.transaction() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "date": row["date"],
                "amount": row["amount"],
                "type": row["type"],
                "category_or_source": row["category_or_source"],
                "member": row["member"],
                "account_name": row["account_name"],
                "description": row["description"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Expense query builder
    # ------------------------------------------------------------------

    def _query_expenses(
        self,
        filters: dict,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict]:
        """
        Build and execute a parameterised SELECT on the expenses table.

        Parameters
        ----------
        filters : dict
            The original filter dict from :meth:`search`.
        start_date : str or None
            Resolved start date.
        end_date : str or None
            Resolved end date.

        Returns
        -------
        list[dict]
            Matching expense rows as dicts.
        """
        conditions: list[str] = []
        params: list[Any] = []

        if start_date:
            conditions.append("e.expense_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("e.expense_date <= ?")
            params.append(end_date)

        category_id: int | None = filters.get("category_id")
        if category_id is not None:
            conditions.append("e.category_id = ?")
            params.append(category_id)

        keyword: str | None = filters.get("keyword")
        if keyword:
            conditions.append("e.description LIKE ? COLLATE NOCASE")
            params.append(f"%{keyword}%")

        member: str | None = filters.get("member")
        if member:
            conditions.append("e.paid_by = ?")
            params.append(member)

        account_id: int | None = filters.get("account_id")
        if account_id is not None:
            conditions.append("e.account_id = ?")
            params.append(account_id)

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        sql = f"""
            SELECT
                e.id,
                e.expense_date      AS date,
                e.amount,
                'Expense'           AS type,
                ec.category_name    AS category_or_source,
                e.paid_by           AS member,
                a.account_name,
                e.description
            FROM expenses e
            JOIN expense_categories ec ON ec.id = e.category_id
            JOIN accounts a            ON a.id  = e.account_id
            {where_clause}
            ORDER BY e.expense_date DESC;
        """

        with self.db.transaction() as conn:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "date": row["date"],
                "amount": row["amount"],
                "type": row["type"],
                "category_or_source": row["category_or_source"],
                "member": row["member"],
                "account_name": row["account_name"],
                "description": row["description"],
            }
            for row in rows
        ]
