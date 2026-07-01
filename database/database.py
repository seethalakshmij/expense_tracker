"""
database/database.py

Database manager for the Home Expense Tracker.

Responsibilities
----------------
- Create SQLite connection
- Enable foreign keys
- Enable WAL mode
- Create database schema
- Initialize default data
- Provide transaction support
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


class DatabaseManager:
    """Handles all SQLite database operations."""

    DATABASE_NAME = "expense_tracker.db"

    def __init__(self) -> None:
        self.database_path = Path(__file__).parent / self.DATABASE_NAME
        self._initialize_database()

    # ==========================================================
    # Connection
    # ==========================================================

    def get_connection(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection.

        A fresh connection is returned each time.
        This avoids stale connections and makes the
        application more reliable.
        """

        connection = sqlite3.connect(self.database_path)

        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA foreign_keys = ON;")

        connection.execute("PRAGMA journal_mode = WAL;")

        connection.execute("PRAGMA synchronous = NORMAL;")

        return connection

    # ==========================================================
    # Context Manager
    # ==========================================================

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Execute database operations inside a transaction.

        Automatically commits on success.

        Automatically rolls back on failure.
        """

        connection = self.get_connection()

        try:
            yield connection

            connection.commit()

        except Exception:

            connection.rollback()

            raise

        finally:

            connection.close()

    # ==========================================================
    # Database Initialization
    # ==========================================================

    def _initialize_database(self) -> None:
        """
        Create tables, indexes and default data.
        """

        with self.transaction() as connection:

            cursor = connection.cursor()

            self._create_tables(cursor)

            self._create_indexes(cursor)

            self._insert_default_accounts(cursor)

            self._insert_default_categories(cursor)

    # ==========================================================
    # Table Creation
    # ==========================================================

    def _create_tables(
        self,
        cursor: sqlite3.Cursor,
    ) -> None:
        """
        Create all required tables.

        Implemented in Part 2.
        """
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name     TEXT    NOT NULL UNIQUE,
                opening_balance  REAL    NOT NULL DEFAULT 0.0,
                current_balance  REAL    NOT NULL DEFAULT 0.0,
                created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_categories (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT    NOT NULL UNIQUE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS income (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                income_date TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                source      TEXT    NOT NULL,
                received_by TEXT    NOT NULL,
                account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
                description TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date   TEXT    NOT NULL,
                amount         REAL    NOT NULL,
                category_id    INTEGER NOT NULL REFERENCES expense_categories(id) ON DELETE RESTRICT,
                description    TEXT    NOT NULL DEFAULT '',
                paid_by        TEXT    NOT NULL,
                account_id     INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
                payment_method TEXT    NOT NULL DEFAULT '',
                notes          TEXT    NOT NULL DEFAULT '',
                created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

    # ==========================================================
    # Index Creation
    # ==========================================================

    def _create_indexes(
        self,
        cursor: sqlite3.Cursor,
    ) -> None:
        """
        Create useful indexes.

        Implemented in Part 3.
        """
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_income_account_id  ON income(account_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_income_date        ON income(income_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_income_source      ON income(source);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_income_received_by ON income(received_by);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_account_id  ON expenses(account_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_date        ON expenses(expense_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_category_id ON expenses(category_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_paid_by     ON expenses(paid_by);"
        )

    # ==========================================================
    # Default Accounts
    # ==========================================================

    def _insert_default_accounts(
        self,
        cursor: sqlite3.Cursor,
    ) -> None:
        """
        Insert the four bank accounts.

        Implemented in Part 3.
        """
        from utils.constants import BANK_ACCOUNTS  # noqa: F401 – kept for traceability

        default_accounts = [
            "My Canara Bank Account",
            "Mom's Canara Bank Account",
            "South Indian Bank Account",
            "Indian Bank Account",
        ]

        for account_name in default_accounts:
            cursor.execute(
                """
                INSERT OR IGNORE INTO accounts (account_name, opening_balance, current_balance)
                VALUES (?, 0.0, 0.0);
                """,
                (account_name,),
            )

    # ==========================================================
    # Default Categories
    # ==========================================================

    def _insert_default_categories(
        self,
        cursor: sqlite3.Cursor,
    ) -> None:
        """
        Insert default expense categories.

        Implemented in Part 3.
        """
        from utils.constants import DEFAULT_EXPENSE_CATEGORIES

        for category_name in DEFAULT_EXPENSE_CATEGORIES:
            cursor.execute(
                """
                INSERT OR IGNORE INTO expense_categories (category_name)
                VALUES (?);
                """,
                (category_name,),
            )


# Singleton instance

db = DatabaseManager()