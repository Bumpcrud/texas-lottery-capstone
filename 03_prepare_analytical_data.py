"""
Create the final cleaned analytical dataset.

This script removes observations with unusable county geography,
keeps the excluded records for documentation, checks for duplicate
County x Month x Game Category keys, and saves the cleaned dataset
for later exploratory analysis and modeling.
"""

from pathlib import Path
import polars as pl

# ============================================================
# 1. PROJECT PATHS AND SOURCE FILES
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output"

SOURCE_FILE = OUTPUT_DIR / "county_month_game.parquet"
CLEAN_FILE = OUTPUT_DIR / "county_month_game_clean.parquet"

df = pl.read_parquet(SOURCE_FILE)

print("Source rows:", df.height)

# ============================================================
# 2. REMOVE UNKNOWN GEOGRAPHY
# ============================================================

# Keep unknown geography documented separately, but exclude it
# from the county level analytical dataset.
unknown_geography = df.filter(
    pl.col("Retailer Location County") == "Unknown"
)

unknown_geography.write_csv(
    OUTPUT_DIR / "excluded_unknown_geography.csv"
)

# Sort the retained observations into a consistent order for later analysis.
clean_df = (
    df.filter(
        pl.col("Retailer Location County") != "Unknown"
    )
    .sort(
        [
            "Month Ending Date Parsed",
            "Retailer Location County",
            "Game Category",
        ]
    )
)

# ============================================================
# 3. VALIDATE THE CLEAN ANALYTICAL TABLE
# ============================================================

# Validate that each County x Month x Game Category combination occurs only once.
duplicate_keys = (
    clean_df.select(
        [
            "Retailer Location County",
            "Month Ending Date Parsed",
            "Game Category",
        ]
    )
    .is_duplicated()
    .sum()
)


# Report the final row count, geography coverage, key uniqueness,
# and remaining negative net sales observations.
print("\n=== CLEAN ANALYTICAL DATASET ===\n")
print("Rows retained:", clean_df.height)
print("Rows excluded for unknown county:", unknown_geography.height)
print("Duplicate County x Month x Game Category keys:", duplicate_keys)
print("Counties:", clean_df["Retailer Location County"].n_unique())
print("Months:", clean_df["Month Ending Date Parsed"].n_unique())
print("Game categories:", clean_df["Game Category"].n_unique())
print(
    "Negative net-sales observations:",
    clean_df.filter(pl.col("net_sales") < 0).height,
)

# Save the cleaned analytical dataset for EDA and modeling.
clean_df.write_parquet(CLEAN_FILE)

print("\nSaved cleaned analytical dataset:")
print(CLEAN_FILE)

