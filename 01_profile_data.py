"""
Initial profiling and aggregation for the Texas Lottery capstone project.

This script reads the raw Texas Lottery sales CSV, standardizes selected
date and financial fields, profiles the source data, creates summary
outputs, and aggregates the raw retailer/game records to the proposed
County x Month x Game Category analytical grain.
"""

from pathlib import Path
import polars as pl

# Project folder structure
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "output"

# Raw dataset
DATA_FILE = DATA_DIR / "Texas_Lottery®_Sales_by_Fiscal_Month_Year,_Game_and_Retailer_20260903.csv"

print("Project directory:", PROJECT_DIR)
print("Data file:", DATA_FILE)
print("File exists:", DATA_FILE.exists())

# Scan the CSV lazily so the entire 16 GB file is not loaded into memory.
lf = pl.scan_csv(DATA_FILE)

# Parse the monthly date field and convert currency formatted sales
# values to numeric fields needed for aggregation and later modeling.
lf = lf.with_columns(
    pl.col("Month Ending Date")
    .str.strptime(pl.Date, "%m/%d/%Y", strict=False)
    .alias("Month Ending Date Parsed"),

    pl.col("Gross Ticket Sales Amount")
    .str.replace_all(r"[$,]", "")
    .str.replace_all(r"\((.*)\)", "-$1")
    .cast(pl.Float64, strict=False)
    .alias("Gross Sales"),

    pl.col("Net Ticket Sales Amount")
    .str.replace_all(r"[$,]", "")
    .str.replace_all(r"\((.*)\)", "-$1")
    .cast(pl.Float64, strict=False)
    .alias("Net Sales"),
)

# Profile the raw dataset for size, date coverage, category counts,
# missing values, parsing failures, and basic sales ranges.
profile = lf.select(
    pl.len().alias("row_count"),

    pl.col("Month Ending Date Parsed").min().alias("min_date"),
    pl.col("Month Ending Date Parsed").max().alias("max_date"),

    pl.col("Fiscal Year").min().alias("min_fiscal_year"),
    pl.col("Fiscal Year").max().alias("max_fiscal_year"),

    pl.col("Calendar Year").min().alias("min_calendar_year"),
    pl.col("Calendar Year").max().alias("max_calendar_year"),

    pl.col("Game Category").n_unique().alias("game_categories"),
    pl.col("Retailer Location County").n_unique().alias("counties"),
    pl.col("Retailer License Number").n_unique().alias("retailers"),

    pl.col("Month Ending Date").null_count().alias("missing_dates"),
    pl.col("Game Category").null_count().alias("missing_game_category"),
    pl.col("Retailer Location County").null_count().alias("missing_county"),
    pl.col("Net Ticket Sales Amount").null_count().alias("missing_net_sales"),

    pl.col("Month Ending Date Parsed").null_count().alias("unparsed_dates"),
    pl.col("Gross Sales").null_count().alias("unparsed_gross_sales"),
    pl.col("Net Sales").null_count().alias("unparsed_net_sales"),

    pl.col("Gross Sales").min().alias("min_gross_sales"),
    pl.col("Gross Sales").max().alias("max_gross_sales"),
    pl.col("Net Sales").min().alias("min_net_sales"),
    pl.col("Net Sales").max().alias("max_net_sales"),
).collect()

print("\n=== TEXAS LOTTERY DATASET PROFILE ===\n")
print(profile)

print("\n=== PROFILE DETAILS ===\n")

for column, value in zip(profile.columns, profile.row(0)):
    print(f"{column}: {value}")

# Summarize row counts by game category.
game_category_summary = (
    lf.group_by("Game Category")
    .agg(
        pl.len().alias("row_count"),
        pl.col("Net Sales").sum().alias("total_net_sales"),
    )
    .sort("row_count", descending=True)
    .collect()
)

print("\n=== GAME CATEGORY SUMMARY ===\n")
print(game_category_summary)

game_category_summary.write_csv(
    OUTPUT_DIR / "game_category_summary.csv"
)

# Summarize row counts by month.
monthly_summary = (
    lf.group_by("Month Ending Date Parsed")
    .agg(
        pl.len().alias("row_count"),
        pl.col("Net Sales").sum().alias("total_net_sales"),
    )
    .sort("Month Ending Date Parsed")
    .collect()
)

print("\n=== MONTHLY SUMMARY ===\n")
print(monthly_summary)

monthly_summary.write_csv(
    OUTPUT_DIR / "monthly_summary.csv"
)

# Aggregate the retailer level source data to the proposed
# County x Month x Game Category analytical grain.
county_month_game = (
    lf.group_by(
        [
            "Retailer Location County",
            "Month Ending Date Parsed",
            "Game Category",
        ]
    )
    .agg(
        pl.len().alias("raw_row_count"),
        pl.col("Retailer License Number").n_unique().alias("active_retailers"),
        pl.col("Gross Sales").sum().alias("gross_sales"),
        pl.col("Net Sales").sum().alias("net_sales"),
    )
    .sort(
        [
            "Month Ending Date Parsed",
            "Retailer Location County",
            "Game Category",
        ]
    )
    .collect()
)

print("\n=== COUNTY x MONTH x GAME CATEGORY ===\n")
print("Aggregated rows:", county_month_game.height)
print(county_month_game.head(10))

# Save the reduced analytical table as Parquet so later scripts can
# avoid repeatedly scanning the 16 GB source CSV.
county_month_game.write_parquet(
    OUTPUT_DIR / "county_month_game.parquet"
)

# Profile the aggregated table to evaluate group size,
# retailer coverage, and unusual negative net sales observations.
aggregation_profile = county_month_game.select(
    pl.len().alias("aggregated_rows"),
    pl.col("raw_row_count").min().alias("min_raw_rows_per_group"),
    pl.col("raw_row_count").median().alias("median_raw_rows_per_group"),
    pl.col("raw_row_count").max().alias("max_raw_rows_per_group"),
    pl.col("active_retailers").min().alias("min_active_retailers"),
    pl.col("active_retailers").median().alias("median_active_retailers"),
    pl.col("active_retailers").max().alias("max_active_retailers"),
    (pl.col("raw_row_count") == 1).sum().alias("groups_with_one_raw_row"),
    (pl.col("active_retailers") == 1).sum().alias("groups_with_one_retailer"),
    (pl.col("net_sales") < 0).sum().alias("groups_with_negative_net_sales"),
)

print("\n=== AGGREGATION PROFILE ===\n")

for column, value in zip(
    aggregation_profile.columns,
    aggregation_profile.row(0),
):
    print(f"{column}: {value}")

