"""
database/database.py

Handles:
- SQLite database connection
- Database initialization
- Table creation
- Default account creation
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


class DatabaseManager:
    """Manages the SQLite database."""

    DATABASE_NAME = "expense_tracker.db"

    def __init__(self) -> None:
        self.database_path = Path(__file__).parent / self.DATABASE_NAME
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Create a database connection.

        Returns:
            sqlite3.Connection
        """
        if self.connection is None:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON;")

        return self.connection

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize_database(self) -> None:
        """Create all required database tables."""
        conn = self.connect()
        cursor = conn.cursor()

        # ------------------------------------------------------------------
        # Accounts
        # ------------------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT UNIQUE NOT NULL,
                opening_balance REAL NOT NULL DEFAULT 0,
                current_balance REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # ------------------------------------------------------------------
        # Income
        # ------------------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                income_date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                source TEXT NOT NULL,
                received_by TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(account_id)
                    REFERENCES accounts(id)
                    ON DELETE RESTRICT
            );
            """
        )

        # ------------------------------------------------------------------
        # Expense Categories
        # ------------------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expense_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL
            );
            """
        )

        # ------------------------------------------------------------------
        # Expenses
        # ------------------------------------------------------------------
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                category_id INTEGER NOT NULL,
                description TEXT,
                paid_by TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id)
                    REFERENCES expense_categories(id)
                    ON DELETE RESTRICT,
                FOREIGN KEY(account_id)
                    REFERENCES accounts(id)
                    ON DELETE RESTRICT
            );
            """
        )

        conn.commit()

        self._insert_default_accounts()
        self._insert_default_categories()

    def _insert_default_accounts(self) -> None:
        """Insert the four default bank accounts once."""
        conn = self.connect()
        cursor = conn.cursor()

        default_accounts = [
            "My Canara Bank",
            "Mom's Canara Bank",
            "South Indian Bank",
            "Indian Bank",
        ]

        for account in default_accounts:
            cursor.execute(
                """
                INSERT OR IGNORE INTO accounts
                (
                    account_name,
                    opening_balance,
                    current_balance
                )
                VALUES (?, 0, 0);
                """,
                (account,),
            )

        conn.commit()

    def _insert_default_categories(self) -> None:
        """Insert default expense categories."""
        conn = self.connect()
        cursor = conn.cursor()

        categories = [
            "Groceries",
            "Vegetables",
            "Milk",
            "Electricity",
            "Water",
            "Gas",
            "Petrol",
            "Internet",
            "Mobile Recharge",
            "House Rent",
            "Medical",
            "Education",
            "Shopping",
            "Entertainment",
            "Travel",
            "Gifts",
            "Repairs",
            "Miscellaneous",
        ]

        for category in categories:
            cursor.execute(
                """
                INSERT OR IGNORE INTO expense_categories
                (category_name)
                VALUES (?);
                """,
                (category,),
            )

        conn.commit()


# ----------------------------------------------------------------------
# Singleton Database Instance
# ----------------------------------------------------------------------

db = DatabaseManager()


def initialize_database() -> None:
    """
    Initialize the database.

    This function should be called once from main.py.
    """
    db.initialize_database()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")