# Texas Lottery Capstone

This repository contains Python code used for the Data Collection,
Cleaning, and Preprocessing stage of my DS 785 capstone project,
"Modeling Geographic and Temporal Patterns in Texas Lottery Sales."

## Data Source

The project uses the Texas Lottery Sales by Fiscal Month/Year, Game and
Retailer dataset from the Texas Open Data Portal.

The source CSV contains approximately 51.9 million rows and is not
included in this repository because of its size.

## Code Organization

### 01_profile_data.py

Profiles the raw dataset, converts date and financial fields, creates
summary outputs, and aggregates the source data to
County x Month x Game Category.

### 02_validate_aggregation.py

Evaluates aggregation coverage, small retailer groups, county labels,
and unusual negative net sales observations.

### 03_prepare_analytical_data.py

Removes records without usable county geography, validates analytical
keys, and creates the cleaned dataset used for later analysis.

### 04_investigate_negative_sales.py

Reviews negative net sales observations using the original ticket
adjustment, cancellation, and return fields.

## Software

Python 3  
Polars
