"""Configuration for the Messy Spreadsheet Rescue demo."""

SEED = 2026
N_ORDERS = 5000

DATE_START = "2025-01-01"
DATE_END = "2026-05-31"

CATEGORIES = [
    "Electronics",
    "Office Supplies",
    "Furniture",
    "Cleaning",
    "Food & Beverage",
    "Safety Equipment",
]

REGIONS = ["VA", "NC", "MD", "DC", "SC"]

MISSING_TOKENS = ["", "N/A", "n/a", "NULL", "null", "-", "na", "  "]

# disease rates (fraction of affected rows/cells)
RATE_EXACT_DUPES = 0.02
RATE_NEAR_DUPES = 0.01
RATE_DECIMAL_SHIFT = 0.005
RATE_NEGATIVE_QTY = 0.006
RATE_BLANK_DATE = 0.01
RATE_MISSING_CELLS = 0.03
