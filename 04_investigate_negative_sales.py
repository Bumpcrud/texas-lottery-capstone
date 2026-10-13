"""
Investigate negative net sales identified during validation.

This script returns to the raw Texas Lottery accounting fields for the
County x Month x Game Category groups with negative net sales. It reviews
gross sales, promotional tickets, cancellations, adjustments, returns,
and net sales to determine whether the negative values reflect valid
accounting activity rather than data errors.
"""

from pathlib import Path
import polars as pl

# ============================================================
# 1. PROJECT PATHS AND RAW SOURCE
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

DATA_FILE = DATA_DIR / "Texas_Lottery®_Sales_by_Fiscal_Month_Year,_Game_and_Retailer_20260903.csv"

# Scan the raw CSV lazily so only the needed records and fields
# are processed from the full 16 GB source file.
lf = pl.scan_csv(DATA_FILE)

# ============================================================
# 2. CONVERT ACCOUNTING FIELDS TO NUMERIC VALUES
# ============================================================

# Convert the raw currency fields to numeric values so the
# accounting components can be summed and compared.
numeric_names = {
    "Gross Ticket Sales Amount": "gross_sales",
    "Promotional Tickets Amount": "promotional_tickets",
    "Cancelled Tickets Amount": "cancelled_tickets",
    "Ticket Adjustments Amount": "ticket_adjustments",
    "Ticket Returns Amount": "ticket_returns",
    "Net Ticket Sales Amount": "net_sales",
}

for original, cleaned in numeric_names.items():
    lf = lf.with_columns(
        pl.col(original)
        .str.replace_all(r"[$,]", "")
        .str.replace_all(r"\((.*)\)", "-$1")
        .cast(pl.Float64, strict=False)
        .alias(cleaned)
    )

# ============================================================
# 3. DEFINE NEGATIVE SALES GROUPS TO INVESTIGATE
# ============================================================

# These six groups were identified in the aggregation validation
# step as having negative net sales.
target_groups = [
    ("Upshur", "12/31/2022", "Cash Five®"),
    ("Reagan", "03/31/2021", "Pick 3™"),
    ("Kent", "09/30/2025", "Scratch Tickets"),
    ("Unknown", "06/30/2022", "Scratch Tickets"),
    ("Roberts", "11/30/2023", "Scratch Tickets"),
    ("Kent", "01/31/2026", "Scratch Tickets"),
]

# ============================================================
# 4. FILTER THE RAW DATA TO THE TARGET GROUPS
# ============================================================

# Build filter for the six known groups.
conditions = []

for county, date, category in target_groups:
    conditions.append(
        (pl.col("Retailer Location County") == county)
        & (pl.col("Month Ending Date") == date)
        & (pl.col("Game Category") == category)
    )

filter_expression = conditions[0]

for condition in conditions[1:]:
    filter_expression = filter_expression | condition

# ============================================================
# 5. SUM ACCOUNTING COMPONENTS FOR EACH GROUP
# ============================================================

# Aggregate the raw accounting fields for each target group to
# identify which adjustments, cancellations, or returns explain
# the negative net sales.
negative_components = (
    lf.filter(filter_expression)
    .group_by(
        [
            "Retailer Location County",
            "Month Ending Date",
            "Game Category",
        ]
    )
    .agg(
        pl.len().alias("raw_rows"),
        pl.col("gross_sales").sum().alias("gross_sales"),
        pl.col("promotional_tickets").sum().alias("promotional_tickets"),
        pl.col("cancelled_tickets").sum().alias("cancelled_tickets"),
        pl.col("ticket_adjustments").sum().alias("ticket_adjustments"),
        pl.col("ticket_returns").sum().alias("ticket_returns"),
        pl.col("net_sales").sum().alias("net_sales"),
    )
    .sort("net_sales")
    .collect()
)

print("\n=== NEGATIVE SALES COMPONENT ANALYSIS ===\n")
print(negative_components)

# Save the results for documentation and later reference.
negative_components.write_csv(
    OUTPUT_DIR / "negative_sales_component_analysis.csv"
)

