# Architecture Decision Records (ADRs)

This document records the foundational architectural and design decisions made in the **Grocery Intelligence Index (GII)** Lakehouse pipeline.

---

## ADR 001: Medallion Lakehouse Architecture on Delta Lake

### Status
**Accepted**

### Context
We needed a reliable, testable, and scalable architecture to ingest raw Statistics Canada monthly grocery price surveys (Table 18-10-0245-01), standardize schema and data types, enforce data quality gates, and serve curated price change metrics to downstream BI consumers.

### Decision
We adopted the **Medallion Architecture** pattern using Delta Lake storage:
1. **Bronze (Raw Ingestion)**: Ingests source CSV records preserving original column names without schema inference, sanitizing UTF-8 BOM headers, and appending audit lineage metadata (`ingestion_timestamp`, `source_file_name`, `_batch_id`).
2. **Silver (Cleansed & Validated)**: Types, trims, standardizes dates (`yyyy-MM`), generates deterministic surrogate keys (`RecordId` via SHA-256), and partitions malformed/duplicate rows into a **Quarantine Dead-Letter Table**.
3. **Gold (Curated Analytical Serving)**: Applies basket taxonomy categorization, performs month-over-month (MoM) window analytics, and exports optimized single-partition extracts for reporting.

---

## ADR 002: Window Functions vs. Self-Joins for Month-over-Month (MoM) Analytics

### Status
**Accepted**

### Context
Calculating month-over-month price changes requires pairing the current month's record with the immediately preceding calendar month's record for the exact same product and unit grain across 9+ years of historical data (2017–2026).

### Decision
We implemented PySpark Window specifications (`Window.partitionBy(*grain).orderBy("SnapshotDate")`) combined with `F.lag()` and strict calendar interval validation (`months_between(current, previous) == 1`).

### Rationale & Alternatives
- **Self-Joins**: Performing `df.join(df, on=[... and add_months(date, 1)])` introduces shuffle overhead, handles missing prior months poorly, and risks cartesian explosions if keys contain unhandled duplicates.
- **Window + Lag**: Executes as a single shuffle-and-sort pass over the partition grain, providing $O(N \log N)$ performance and making it trivial to validate that the lagged month is strictly the consecutive calendar month ($N - 1$). If a month is missing from the survey, `PreviousMonthPrice` remains `null` rather than generating a spurious 0% change.

---

## ADR 003: Quarantine & Dead-Letter Routing vs. Hard Failures in Silver

### Status
**Accepted**

### Context
In real-world data feeds, survey data or external vendor CSVs occasionally contain anomalous rows (e.g. negative prices, malformed dates, duplicate transmissions). Crashing the entire batch delays SLAs for valid records, while silently dropping records loses critical audit trails.

### Decision
We implemented a **Quarantine / Dead-Letter Lakehouse Pattern** in `grocery_index.quality`:
- Valid rows passing all quality constraints are promoted to `workspace.silver.grocery_prices`.
- Invalid or duplicate rows are routed to `workspace.silver.grocery_prices_quarantine` annotated with a descriptive `quarantine_reason` (`NULL_SNAPSHOT_DATE`, `NON_POSITIVE_PRICE`, `DUPLICATE_BUSINESS_KEY`).

---

## ADR 004: Decoupled Business Logic & Databricks Asset Bundles (DABs)

### Status
**Accepted**

### Context
Data pipelines often suffer from "notebook sprawl," where mission-critical business logic is trapped inside untestable Databricks notebooks, making CI/CD, unit testing, and local development impossible.

### Decision
- All transformation logic, schema definitions, and quality rules are packaged as a modular, pure-Python package in `src/grocery_index/`.
- Databricks notebooks (`notebooks/`) and workflow tasks (`jobs/`) act purely as **thin orchestration wrappers** invoking the tested package.
- Infrastructure and multi-environment deployment (`dev`, `prod`) are managed as code via **Databricks Asset Bundles (`databricks.yml`)**.

---

## ADR 005: Engine Selection Trade-off (PySpark vs. DuckDB/dbt)

### Status
**Accepted**

### Context
The monthly StatCan price survey (~138,000 rows, ~18MB) is compact enough to run in single-node engines like DuckDB, Polars, or dbt in milliseconds. Why deploy an Apache Spark / Delta Lake pipeline on Databricks?

### Decision
1. **Enterprise Platform Alignment**: The architecture is designed to integrate into enterprise Lakehouse ecosystems leveraging **Unity Catalog**, centralized access control, lineage graphs, and Delta Lake table formats.
2. **Horizontal Scale-Out Path**: While the public StatCan survey is compact, the identical Medallion codebase and windowing algorithms are architected to scale horizontally to multi-gigabyte/terabyte point-of-sale (POS) barcode scanner feeds from major grocery retail chains without code refactoring.
3. **Local Developer Ergonomics**: To eliminate cloud compute lock-in, the codebase provides a local runner (`python -m grocery_index.cli run --env local`) and local PySpark fixtures for zero-cost developer testing.

---

## ADR 006: Decoupled Taxonomy Mapping & Regex Boundary Protection

### Status
**Accepted**

### Context
Deriving grocery basket categories via basic substring matching (e.g. `product.contains("chicken")`) creates classification errors (e.g., matching `"Chicken-flavored beef broth"` as `Chicken` or `"Butter tarts"` as `Butter`).

### Decision
We decoupled basket taxonomy into a dedicated module (`src/grocery_index/taxonomy.py`) with prioritized regex rules and word boundary enforcement (`\b`). Rules are evaluated in priority order to guarantee deterministic classification.

---

## ADR 007: Serving Tier Architecture & Pre-Aggregated Gold Extract

### Status
**Accepted**

### Context
Downstream business intelligence and executive dashboard consumers require low-latency, interactive exploration without incurring persistent Databricks cluster spin-up latency or cloud warehouse compute costs.

### Decision
1. **Pre-Aggregated Serving Extract**: The Gold pipeline stage generates an analytical dataset (`data/export/grocery_index_extract.csv`) containing pre-computed MoM percentage changes and surrogate keys.
2. **Serverless UI Deployment**: An interactive Python application (`streamlit_app.py`) is deployed to Streamlit Community Cloud, providing instantaneous sub-second query latency and zero persistent server idle costs.
3. **Dual Consumption Patterns**: Enterprise BI tools (PowerBI, Tableau) query Delta Lake tables directly via Databricks SQL Warehouses, while the public interactive application consumes the curated extract.
