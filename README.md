# Grocery Intelligence Index

![Databricks](https://img.shields.io/badge/Platform-Databricks-EF3E2E?style=for-the-badge&logo=databricks&logoColor=white)
![PySpark](https://img.shields.io/badge/Engine-PySpark-FDEE21?style=for-the-badge&logo=apache-spark&logoColor=black)
![Delta Lake](https://img.shields.io/badge/Storage-Delta%20Lake-00A3E0?style=for-the-badge)
![Tableau](https://img.shields.io/badge/Output-Tableau%20Ready-E97627?style=for-the-badge&logo=tableau&logoColor=white)

The **Grocery Intelligence Index** is a Databricks data engineering project that transforms raw grocery price data into a curated analytics layer for tracking grocery price movement over time.

It uses a Bronze-Silver-Gold medallion architecture to move data from raw ingestion to cleaned, analysis-ready Delta tables and a Tableau-ready CSV extract.

## Project Snapshot

| Area | Details |
| --- | --- |
| Domain | Grocery price analytics |
| Time window | 2023-2026 analysis period |
| Platform | Databricks |
| Processing | Spark / PySpark |
| Storage | Delta tables with Unity Catalog |
| Output | Gold analytics table and Tableau-ready CSV |
| Architecture | Bronze, Silver, Gold medallion pipeline |

## Why This Project Matters

Grocery prices change quickly, and raw public datasets are rarely ready for analysis right away. This project turns source-level price records into a clean grocery basket dataset that can support:

- month-over-month price trend analysis
- product-level grocery basket comparisons
- Canada and Ontario grocery price reporting
- dashboard-ready extracts for Tableau Public
- reproducible data engineering workflows in Databricks

## Architecture

```text
Raw CSV
   |
   v
Bronze Layer
Raw ingestion + lineage metadata
   |
   v
Silver Layer
Cleaning + typing + geographic filtering
   |
   v
Gold Layer
Core basket analytics + MoM price movement
   |
   v
Tableau Extract
Dashboard-ready CSV output
```

## Medallion Pipeline

### Bronze: Raw Ingestion

The Bronze notebook ingests the source CSV into Databricks and preserves the raw structure of the data.

Key steps:

- reads the source CSV from a Databricks volume
- loads fields as strings for a stable landing layer
- adds ingestion metadata such as timestamp and source file name
- writes the result to `workspace.bronze.grocery_prices`

### Silver: Cleaned Data

The Silver notebook standardizes the raw records into a cleaner analytical shape.

Key steps:

- reads from the Bronze Delta table
- filters records to Canada and Ontario
- parses `REF_DATE` into `SnapshotDate`
- trims product names into `ProductName`
- casts price values into `AveragePrice`
- removes records with missing dates or price values
- writes the result to `workspace.silver.grocery_prices`

### Gold: Analytics Layer

The Gold notebook creates the final grocery basket dataset for reporting and visualization.

The basket currently focuses on:

```text
Milk, Eggs, Bread, Butter, Chicken, Bananas, Potatoes, Beef, Coffee, Bacon
```

Key steps:

- reads from the Silver Delta table
- filters to the core grocery basket
- calculates previous-month price with a Spark window function
- calculates month-over-month percentage change
- writes the result to `workspace.gold.grocery_prices`
- exports a Tableau-ready CSV extract

## Repository Structure

```text
.
|-- Bronze/
|   `-- 01_bronze_grocery_prices.ipynb
|-- Silver/
|   `-- 02_silver_grocery_prices.ipynb
|-- Gold/
|   `-- 03_gold_grocery_prices.ipynb
|-- LICENSE
`-- README.md
```

## Data Model

The final Gold layer includes the main fields needed for grocery price trend analysis:

| Column | Description |
| --- | --- |
| `SnapshotDate` | Monthly date associated with the grocery price record |
| `Geography` | Geographic scope, such as Canada or Ontario |
| `ProductName` | Grocery item or product category |
| `AveragePrice` | Current average price |
| `PreviousMonthPrice` | Previous month's average price for the same product and geography |
| `MoM_PercentageChange` | Month-over-month percentage price change |

## Source and Output Paths

Expected source CSV:

```text
/Volumes/workspace/bronze/v_gii_raw_landing/18100245.csv
```

Final Gold table:

```text
workspace.gold.grocery_prices
```

Tableau-ready export:

```text
/Volumes/workspace/gold/gold_output/toronto_grocery_index_extract
```

## How to Run

Run the notebooks in order:

1. `Bronze/01_bronze_grocery_prices.ipynb`
2. `Silver/02_silver_grocery_prices.ipynb`
3. `Gold/03_gold_grocery_prices.ipynb`

Each notebook depends on the Delta table created by the previous layer.

## Tech Stack

- Databricks
- PySpark
- Spark SQL functions
- Delta Lake
- Unity Catalog
- Databricks Volumes
- Tableau Public export workflow

## Portfolio Highlights

This project demonstrates:

- medallion architecture design
- raw-to-curated data pipeline development
- Delta table creation in Databricks
- data cleaning and type standardization with PySpark
- analytical window functions for time-series price movement
- dashboard-ready data export
- clear separation between ingestion, transformation, and analytics layers

## Future Enhancements

- add data quality checks for schema drift and missing values
- parameterize source paths, table names, and date ranges
- add automated workflow orchestration in Databricks Jobs
- expand the grocery basket with more product categories
- publish a Tableau dashboard connected to the Gold extract

## Summary

The Grocery Intelligence Index shows how a compact data pipeline can still follow production-style engineering practices. It transforms grocery price data from raw CSV input into a polished, analytics-ready dataset for tracking price movement across a focused basket of everyday grocery items.
