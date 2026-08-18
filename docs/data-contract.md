# Data Contract: Grocery Intelligence Index (GII)

**Version:** 1.1.0  
**Domain:** Canadian Retail Pricing & Inflation Intelligence  
**Upstream Provider:** Statistics Canada (Table 18-10-0245-01)  
**Historical Coverage:** January 2017 – Present (114+ continuous monthly survey drops)  
**Storage Format:** Delta Lake on Unity Catalog  

---

## 1. Pipeline SLA & Grain Overview

| Attribute | Specification |
| :--- | :--- |
| **Refresh Frequency** | Monthly (aligned with StatCan survey release schedule) |
| **Historical Range** | `2017-01` to `2026-06` (138,800+ records) |
| **Target Latency** | Within 60 minutes of source landing |
| **Analytical Grain** | `SnapshotDate` $\times$ `Geography` $\times$ `BasketCategory` $\times$ `ProductName` $\times$ `UOM` |
| **Default Geographies** | `Canada`, `Ontario` (all provinces supported) |

---

## 2. Table Schemas

### Silver Tier: `workspace.silver.grocery_prices`
*Cleaned, standardized, and deduplicated price records.*

| Column | Data Type | Nullable | Description / Constraint |
| :--- | :--- | :---: | :--- |
| `RecordId` | `string` | No | SHA-256 deterministic hash surrogate key of business grain |
| `SnapshotDate` | `date` | No | First day of reference month (`yyyy-MM-01`) |
| `Geography` | `string` | No | Trimmed jurisdiction name (`Canada`, `Ontario`) |
| `ProductName` | `string` | No | Trimmed product label from survey source |
| `AveragePrice` | `double` | No | Positive currency amount ($> 0.00$) |
| `UOM` | `string` | No | Unit of measure description (e.g. `Dollars`, `Cents`) |
| `ingestion_timestamp` | `timestamp` | No | Timestamp of Bronze tier ingestion |
| `_batch_id` | `string` | Yes | Unique UUID of the pipeline execution batch |
| `_processed_at` | `timestamp` | No | Timestamp when Silver record was committed |

### Silver Quarantine Tier: `workspace.silver.grocery_prices_quarantine`
*Dead-letter table capturing records failing Silver data quality rules.*

| Column | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `quarantine_reason` | `string` | No | Rejection code (`NULL_SNAPSHOT_DATE`, `NON_POSITIVE_PRICE`, `DUPLICATE_BUSINESS_KEY`) |
| *(All Silver fields)* | - | - | Raw/typed fields preserved for audit and re-ingestion |

### Gold Tier: `workspace.gold.grocery_prices`
*Curated analytical dataset with basket taxonomy and month-over-month price changes.*

| Column | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `GoldRecordId` | `string` | No | SHA-256 hash surrogate key of Gold record grain |
| `SnapshotDate` | `date` | No | First day of reference month (`yyyy-MM-01`) |
| `Geography` | `string` | No | Target geography |
| `BasketCategory` | `string` | No | Standardized basket category (Milk, Eggs, Bread, Butter, Chicken, Bananas, Potatoes, Beef, Coffee, Bacon) |
| `ProductName` | `string` | No | Full product description preserving package variant |
| `UOM` | `string` | No | Retained unit of measure grain |
| `AveragePrice` | `double` | No | Current reference month price |
| `PreviousMonthPrice` | `double` | Yes | Price in the immediately preceding consecutive month ($N - 1$); `null` if gap exists |
| `MoM_AbsoluteChange` | `double` | Yes | `AveragePrice - PreviousMonthPrice` (rounded to 2 decimals) |
| `MoM_PercentageChange` | `double` | Yes | Percentage change from previous consecutive month (rounded to 2 decimals) |

---

## 3. Data Quality Rules & Expectations

| Rule ID | Field / Scope | Assertion | Failure Action |
| :--- | :--- | :--- | :--- |
| `DQ-01` | Landing File | File must be non-empty CSV (BOM sanitized) | Bronze pipeline halts |
| `DQ-02` | Bronze Tier | Required source columns must exist | Bronze schema validation halts |
| `DQ-03` | Silver Tier | `SnapshotDate`, `Geography`, `ProductName`, `UOM` cannot be null | Routed to Quarantine table |
| `DQ-04` | Silver Tier | `AveragePrice > 0.00` | Routed to Quarantine table |
| `DQ-05` | Silver Tier | Business keys `(SnapshotDate, Geography, ProductName, UOM)` must be unique | Deduplicated (latest retained, duplicate quarantined) |
| `DQ-06` | Gold Tier | `PreviousMonthPrice` populated only when $Date - Date_{prev} == 1\text{ month}$ | Set to `null` on calendar gaps |
