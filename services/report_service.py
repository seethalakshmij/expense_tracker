"""
services/report_service.py

Report generation service for the Home Expense Tracker.

Responsibilities
----------------
- Provide read-only aggregated views of income and expense data.
- All methods execute SELECT-only queries — no data is ever modified.
"""

from __future__ import annotations

from database.database import DatabaseManager


class ReportService:
    """
    Service layer for generating financial reports.

    All methods are read-only; they never INSERT, UPDATE, or DELETE any row.

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
    # Income reports
    # ------------------------------------------------------------------

    def monthly_income(self, year: int) -> list[dict]:
        """
        Return total income grouped by month and source for *year*.

        Parameters
        ----------
        year : int
            The calendar year to filter on (e.g. 2025).

        Returns
        -------
        list[dict]
            Each dict has keys: ``month`` (str "01"–"12"),
            ``source`` (str), ``total`` (float).
            Ordered by month then source.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT
                    strftime('%m', income_date) AS month,
                    source,
                    ROUND(SUM(amount), 2)       AS total
                FROM income
                WHERE strftime('%Y', income_date) = ?
                GROUP BY month, source
                ORDER BY month, source;
                """,
                (str(year),),
            )
            rows = cursor.fetchall()

        return [
            {
                "month": row["month"],
                "source": row["source"],
                "total": row["total"],
            }
            for row in rows
        ]

    def income_by_source(self, start: str, end: str) -> list[dict]:
        """
        Return total income grouped by source between *start* and *end* (inclusive).

        Parameters
        ----------
        start : str
            Start date in YYYY-MM-DD format.
        end : str
            End date in YYYY-MM-DD format.

        Returns
        -------
        list[dict]
            Each dict has keys: ``source`` (str), ``total`` (float).
            Ordered by total descending.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT
                    source,
                    ROUND(SUM(amount), 2) AS total
                FROM income
                WHERE income_date BETWEEN ? AND ?
                GROUP BY source
                ORDER BY total DESC;
                """,
                (start, end),
            )
            rows = cursor.fetchall()

        return [
            {
                "source": row["source"],
                "total": row["total"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Expense reports
    # ------------------------------------------------------------------

    def monthly_expenses(self, year: int) -> list[dict]:
        """
        Return total expenses grouped by month for *year*.

        Parameters
        ----------
        year : int
            The calendar year to filter on.

        Returns
        -------
        list[dict]
            Each dict has keys: ``month`` (str "01"–"12"),
            ``total`` (float).
            Ordered by month ascending.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT
                    strftime('%m', expense_date) AS month,
                    ROUND(SUM(amount), 2)        AS total
                FROM expenses
                WHERE strftime('%Y', expense_date) = ?
                GROUP BY month
                ORDER BY month;
                """,
                (str(year),),
            )
            rows = cursor.fetchall()

        return [
            {
                "month": row["month"],
                "total": row["total"],
            }
            for row in rows
        ]

    def expenses_by_category(
        self, year: int, month: int | None = None
    ) -> list[dict]:
        """
        Return total expenses grouped by category name.

        Parameters
        ----------
        year : int
            The calendar year to filter on.
        month : int or None
            If provided, restrict results to this calendar month (1–12).
            If None, all months in *year* are included.

        Returns
        -------
        list[dict]
            Each dict has keys: ``category`` (str), ``total`` (float).
            Ordered by total descending.
        """
        if month is not None:
            month_str = f"{month:02d}"
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        ec.category_name              AS category,
                        ROUND(SUM(e.amount), 2)       AS total
                    FROM expenses e
                    JOIN expense_categories ec ON ec.id = e.category_id
                    WHERE strftime('%Y', e.expense_date) = ?
                      AND strftime('%m', e.expense_date) = ?
                    GROUP BY ec.category_name
                    ORDER BY total DESC;
                    """,
                    (str(year), month_str),
                )
                rows = cursor.fetchall()
        else:
            with self.db.transaction() as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        ec.category_name              AS category,
                        ROUND(SUM(e.amount), 2)       AS total
                    FROM expenses e
                    JOIN expense_categories ec ON ec.id = e.category_id
                    WHERE strftime('%Y', e.expense_date) = ?
                    GROUP BY ec.category_name
                    ORDER BY total DESC;
                    """,
                    (str(year),),
                )
                rows = cursor.fetchall()

        return [
            {
                "category": row["category"],
                "total": row["total"],
            }
            for row in rows
        ]

    def expenses_by_member(self, start: str, end: str) -> list[dict]:
        """
        Return total expenses grouped by the member who paid (``paid_by``).

        Parameters
        ----------
        start : str
            Start date in YYYY-MM-DD format.
        end : str
            End date in YYYY-MM-DD format.

        Returns
        -------
        list[dict]
            Each dict has keys: ``member`` (str), ``total`` (float).
            Ordered by total descending.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT
                    paid_by                   AS member,
                    ROUND(SUM(amount), 2)     AS total
                FROM expenses
                WHERE expense_date BETWEEN ? AND ?
                GROUP BY paid_by
                ORDER BY total DESC;
                """,
                (start, end),
            )
            rows = cursor.fetchall()

        return [
            {
                "member": row["member"],
                "total": row["total"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Account reports
    # ------------------------------------------------------------------

    def account_balances(self) -> list[dict]:
        """
        Return the current balance for every account.

        Returns
        -------
        list[dict]
            Each dict has keys: ``account_name`` (str),
            ``opening_balance`` (float), ``current_balance`` (float).
            Ordered by id ascending.
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT
                    account_name,
                    opening_balance,
                    current_balance
                FROM accounts
                ORDER BY id ASC;
                """
            )
            rows = cursor.fetchall()

        return [
            {
                "account_name": row["account_name"],
                "opening_balance": row["opening_balance"],
                "current_balance": row["current_balance"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Savings / summary reports
    # ------------------------------------------------------------------

    def monthly_savings(self, year: int) -> list[dict]:
        """
        Return income, expenses, and net savings per month for *year*.

        Months with either income or expenses (or both) are included.

        Parameters
        ----------
        year : int
            The calendar year to analyse.

        Returns
        -------
        list[dict]
            Each dict has keys: ``month`` (str "01"–"12"),
            ``income`` (float), ``expenses`` (float), ``savings`` (float).
            Ordered by month ascending.
        """
        year_str = str(year)

        with self.db.transaction() as conn:
            # Monthly income totals
            cursor = conn.execute(
                """
                SELECT
                    strftime('%m', income_date) AS month,
                    ROUND(SUM(amount), 2)       AS total
                FROM income
                WHERE strftime('%Y', income_date) = ?
                GROUP BY month;
                """,
                (year_str,),
            )
            income_rows = cursor.fetchall()

            # Monthly expense totals
            cursor = conn.execute(
                """
                SELECT
                    strftime('%m', expense_date) AS month,
                    ROUND(SUM(amount), 2)        AS total
                FROM expenses
                WHERE strftime('%Y', expense_date) = ?
                GROUP BY month;
                """,
                (year_str,),
            )
            expense_rows = cursor.fetchall()

        income_map: dict[str, float] = {
            row["month"]: row["total"] for row in income_rows
        }
        expense_map: dict[str, float] = {
            row["month"]: row["total"] for row in expense_rows
        }

        all_months = sorted(set(income_map) | set(expense_map))

        result: list[dict] = []
        for month in all_months:
            inc = income_map.get(month, 0.0)
            exp = expense_map.get(month, 0.0)
            result.append(
                {
                    "month": month,
                    "income": inc,
                    "expenses": exp,
                    "savings": round(inc - exp, 2),
                }
            )

        return result

    def yearly_summary(self, year: int) -> dict:
        """
        Return aggregated totals for income, expenses, and net savings for *year*.

        Parameters
        ----------
        year : int
            The calendar year to summarise.

        Returns
        -------
        dict
            Keys: ``year`` (int), ``total_income`` (float),
            ``total_expenses`` (float), ``net_savings`` (float).
        """
        year_str = str(year)

        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT ROUND(COALESCE(SUM(amount), 0.0), 2) AS total
                FROM income
                WHERE strftime('%Y', income_date) = ?;
                """,
                (year_str,),
            )
            income_row = cursor.fetchone()
            total_income: float = income_row["total"] if income_row else 0.0

            cursor = conn.execute(
                """
                SELECT ROUND(COALESCE(SUM(amount), 0.0), 2) AS total
                FROM expenses
                WHERE strftime('%Y', expense_date) = ?;
                """,
                (year_str,),
            )
            expense_row = cursor.fetchone()
            total_expenses: float = expense_row["total"] if expense_row else 0.0

        return {
            "year": year,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_savings": round(total_income - total_expenses, 2),
        }
