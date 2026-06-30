"""
utils/constants.py

Application-wide constants for the Home Expense Tracker.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------

APP_NAME = "Home Expense Tracker"
APP_VERSION = "1.0.0"

DATE_FORMAT = "%Y-%m-%d"

# ---------------------------------------------------------------------
# Family Members
# ---------------------------------------------------------------------

MOM = "Mom"
DAD = "Dad"
ME = "Me"
SISTER = "Sister"

FAMILY_MEMBERS = [
    MOM,
    DAD,
    ME,
    SISTER,
]

EXPENSE_MEMBERS = [
    MOM,
    ME,
    SISTER,
]

# ---------------------------------------------------------------------
# Bank Accounts
# ---------------------------------------------------------------------

MY_CANARA = "My Canara Bank"
MOM_CANARA = "Mom's Canara Bank"
SOUTH_INDIAN = "South Indian Bank"
INDIAN_BANK = "Indian Bank"

BANK_ACCOUNTS = [
    MY_CANARA,
    MOM_CANARA,
    SOUTH_INDIAN,
    INDIAN_BANK,
]

# ---------------------------------------------------------------------
# Income Sources
# ---------------------------------------------------------------------

INCOME_SOURCE_MOM_SALARY = "Mom Salary"
INCOME_SOURCE_DAD_TRANSFER = "Dad Transfer"
INCOME_SOURCE_REFUND = "Refund"
INCOME_SOURCE_GIFT = "Gift"
INCOME_SOURCE_INTEREST = "Interest"
INCOME_SOURCE_OTHER = "Other"

INCOME_SOURCES = [
    INCOME_SOURCE_MOM_SALARY,
    INCOME_SOURCE_DAD_TRANSFER,
    INCOME_SOURCE_REFUND,
    INCOME_SOURCE_GIFT,
    INCOME_SOURCE_INTEREST,
    INCOME_SOURCE_OTHER,
]

# ---------------------------------------------------------------------
# Expense Categories
# ---------------------------------------------------------------------

DEFAULT_EXPENSE_CATEGORIES = [
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

# ---------------------------------------------------------------------
# Payment Methods
# ---------------------------------------------------------------------

PAYMENT_METHODS = [
    "Cash",
    "UPI",
    "Debit Card",
    "Credit Card",
    "Net Banking",
    "Cheque",
    "Other",
]

# ---------------------------------------------------------------------
# Report Filters
# ---------------------------------------------------------------------

FILTER_DAILY = "Daily"
FILTER_WEEKLY = "Weekly"
FILTER_MONTHLY = "Monthly"
FILTER_YEARLY = "Yearly"
FILTER_CUSTOM = "Custom"

REPORT_FILTERS = [
    FILTER_DAILY,
    FILTER_WEEKLY,
    FILTER_MONTHLY,
    FILTER_YEARLY,
    FILTER_CUSTOM,
]

# ---------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------

CSV_EXTENSION = ".csv"

# ---------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------

BACKUP_FOLDER = "backups"

# ---------------------------------------------------------------------
# Export Folder
# ---------------------------------------------------------------------

EXPORT_FOLDER = "exports"

# ---------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------

CURRENCY_SYMBOL = "₹"

# ---------------------------------------------------------------------
# SQLite Table Names
# ---------------------------------------------------------------------

TABLE_ACCOUNTS = "accounts"
TABLE_INCOME = "income"
TABLE_EXPENSES = "expenses"
TABLE_CATEGORIES = "expense_categories"