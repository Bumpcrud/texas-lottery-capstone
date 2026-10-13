"""
Validation of the proposed County x Month x Game Category aggregation.

This script reviews coverage of the aggregated dataset, identifies groups
with very few active retailers, checks county labels for unusable geography,
and examines negative net sales before the final cleaning step.
"""

from pathlib import Path
import polars as pl

# ============================================================
# 1. PROJECT PATHS AND AGGREGATED SOURCE
# ============================================================
PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"

DATA_FILE = OUTPUT_DIR / "county_month_game.parquet"

df = pl.read_parquet(DATA_FILE)

print("Aggregated dataset rows:", df.height)
print("Aggregated dataset columns:", df.width)
print("File loaded successfully:", DATA_FILE.exists())

# ============================================================
# 2. CHECK AGGREGATION COVERAGE
# ============================================================

# Compare observed County x Month x Game Category combinations
# with the full set of combinations possible in the aggregated data.
counties = df["Retailer Location County"].n_unique()
months = df["Month Ending Date Parsed"].n_unique()
categories = df["Game Category"].n_unique()

possible_combinations = counties * months * categories
observed_combinations = df.height
missing_combinations = possible_combinations - observed_combinations
coverage_pct = observed_combinations / possible_combinations * 100

print("\n=== AGGREGATION COVERAGE ===\n")
print("Counties:", counties)
print("Months:", months)
print("Game categories:", categories)
print("Possible combinations:", possible_combinations)
print("Observed combinations:", observed_combinations)
print("Missing combinations:", missing_combinations)
print(f"Coverage: {coverage_pct:.2f}%")

# ============================================================
# 3. REVIEW SMALL RETAILER GROUPS
# ============================================================

# Review groups with two or fewer active retailers to see whether
# the proposed analytical grain creates many very small observations.
small_groups = (
    df.filter(pl.col("active_retailers") <= 2)
    .sort(
        [
            "active_retailers",
            "Retailer Location County",
            "Month Ending Date Parsed",
            "Game Category",
        ]
    )
)

print("\n=== GROUPS WITH 2 OR FEWER ACTIVE RETAILERS ===\n")
print("Count:", small_groups.height)
print(small_groups.head(20))

small_groups.write_csv(
    OUTPUT_DIR / "small_retailer_groups.csv"
)

# ============================================================
# 4. REVIEW NEGATIVE NET SALES
# ============================================================

# Identify aggregate groups with negative net sales so they can
# be investigated against the original accounting fields.
negative_sales = (
    df.filter(pl.col("net_sales") < 0)
    .sort("net_sales")
)

print("\n=== NEGATIVE NET SALES GROUPS ===\n")
print(negative_sales)

negative_sales.write_csv(
    OUTPUT_DIR / "negative_net_sales_groups.csv"
)

# ============================================================
# 5. CHECK COUNTY LABELS
# ============================================================

# Inspect county labels that may represent unknown or invalid geography.
county_summary = (
    df.group_by("Retailer Location County")
    .agg(
        pl.len().alias("observation_count"),
        pl.col("net_sales").sum().alias("total_net_sales"),
    )
    .sort("observation_count", descending=True)
)

print("\n=== COUNTY SUMMARY ===\n")
print("Unique county labels:", county_summary.height)

unknown_counties = county_summary.filter(
    pl.col("Retailer Location County")
    .str.to_lowercase()
    .str.contains("unknown|null|missing|unassigned")
)

print("\n=== POSSIBLE UNKNOWN COUNTY LABELS ===\n")
print(unknown_counties)

unknown_counties.write_csv(
    OUTPUT_DIR / "unknown_county_labels.csv"
)

# ============================================================
# 6. COMPARE SMALL GROUPS BY GAME CATEGORY
# ============================================================

# Determine whether sparse groups are concentrated in certain game categories.
small_group_by_category = (
    df.with_columns(
        (pl.col("active_retailers") <= 2).alias("small_group")
    )
    .group_by("Game Category")
    .agg(
        pl.len().alias("total_groups"),
        pl.col("small_group").sum().alias("groups_with_2_or_fewer_retailers"),
    )
    .with_columns(
        (
            pl.col("groups_with_2_or_fewer_retailers")
            / pl.col("total_groups")
            * 100
        ).alias("small_group_pct")
    )
    .sort("small_group_pct", descending=True)
)

print("\n=== SMALL GROUPS BY GAME CATEGORY ===\n")
print(small_group_by_category)

small_group_by_category.write_csv(
    OUTPUT_DIR / "small_groups_by_category.csv"
)

# ============================================================
# 7. DISPLAY DETAILS FOR NEGATIVE SALES GROUPS
# ============================================================

# Display the group size, retailer count, gross sales, and net sales
# for each negative observation identified above.
print("\n=== DETAILED NEGATIVE NET SALES ===\n")

negative_detail = (
    df.filter(pl.col("net_sales") < 0)
    .select(
        [
            "Retailer Location County",
            "Month Ending Date Parsed",
            "Game Category",
            "raw_row_count",
            "active_retailers",
            "gross_sales",
            "net_sales",
        ]
    )
    .sort("net_sales")
)

print(negative_detail)

