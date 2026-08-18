# Operational Runbook & Backfill Strategy

This runbook documents operational procedures, disaster recovery, backfill mechanics, and maintenance policies for the **Grocery Intelligence Index (GII)** Lakehouse pipeline.

---

## 1. Pipeline Execution & Scheduling Cadence

### Production Cadence
* **Trigger Event:** Scheduled monthly execution (aligned with Statistics Canada Table 18-10-0245-01 release on the third Wednesday of each calendar month).
* **Ingestion SLA:** Processing complete within 30 minutes of raw survey drop.
* **Orchestration:** Managed via Databricks Workflows (`resources/grocery_pipeline.job.yml`).

### Cluster & Resource Sizing
For monthly survey volumes (~138,000 cumulative rows, growing ~1,200 rows/month):

| Environment | Mode | Nodes | Worker Type | Driver Type | Memory |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **Local / CI** | Single Process | 1 | Local JVM | Local (`local[2]`) | $\ge$ 4 GB |
| **Dev / Staging** | Single-Node Cluster | 1 | None | `Standard_D4s_v5` (4 cores) | 16 GB |
| **Production** | Auto-scaling Cluster | 1–2 | `Standard_D4s_v5` | `Standard_D4s_v5` | 16 GB |

---

## 2. Backfill & Retroactive Revision Strategy

### Scenario 1: StatCan Publishes a Retroactive Historical Revision
Occasionally, statistical agencies revise price estimates for prior quarters.

**Procedure:**
1. Land the revised CSV into the landing volume:
   ```bash
   cp /landing/18100245_revised.csv /Volumes/prod_catalog/bronze/v_gii_raw_landing/18100245.csv
   ```
2. Re-run the full pipeline:
   ```bash
   databricks bundle run grocery_intelligence_pipeline -t prod
   ```
3. **Idempotency Guarantee:** Because `RecordId` and `GoldRecordId` are deterministic SHA-256 hashes of `(SnapshotDate, Geography, ProductName, UOM)`, the ingestion updates existing records in place and reconstructs consecutive-month window metrics cleanly without duplicate accumulation.

### Scenario 2: Partial Partition Reprocessing
To reprocess a specific date range or geography without re-ingesting raw Bronze data:
```python
from grocery_index.config import PipelineConfig
from grocery_index.silver import run_silver
from grocery_index.gold import run_gold

config = PipelineConfig.from_env("prod")
# Re-execute Silver validation & Gold windowing
run_silver(spark, config.bronze_table, config.silver_table, config.geographies, config.silver_quarantine_table)
run_gold(spark, config.silver_table, config.gold_table, config.export_path)
```

---

## 3. Data Quality Quarantine Remediation

When the Silver quality gate detects malformed or unparseable records, it isolates them in `workspace.silver.grocery_prices_quarantine`.

### Monitoring Quarantined Rows
Run the following SQL diagnostics in Databricks SQL or Spark:
```sql
SELECT 
    quarantine_reason,
    count(*) AS violation_count,
    min(SnapshotDate) AS earliest_violation,
    max(SnapshotDate) AS latest_violation
FROM workspace.silver.grocery_prices_quarantine
GROUP BY quarantine_reason
ORDER BY violation_count DESC;
```

### Common Quarantine Codes & Fix Actions
| Code | Root Cause | Remediation Action |
| :--- | :--- | :--- |
| `NULL_SNAPSHOT_DATE` | Unparseable `REF_DATE` string in survey CSV | Verify StatCan source format hasn't changed from `YYYY-MM`. |
| `NON_POSITIVE_PRICE` | Value was $\le 0.00$ or missing survey entry | Flag to downstream consumers; StatCan suppressed estimate for confidentiality. |
| `DUPLICATE_BUSINESS_KEY` | Multiple price observations for identical product & unit in same month | Pipeline automatically retains newest observation by `ingestion_timestamp`; verify upstream feed deduplication. |

---

## 4. Delta Lake Storage Maintenance

To ensure optimal columnar query performance and prevent transaction log bloat:

```sql
-- 1. Compact small Delta files and optimize layout
OPTIMIZE workspace.gold.grocery_prices
ZORDER BY (SnapshotDate, Geography, BasketCategory);

-- 2. Remove obsolete Delta snapshots older than 7 days
VACUUM workspace.bronze.grocery_prices RETAIN 168 HOURS;
VACUUM workspace.silver.grocery_prices RETAIN 168 HOURS;
VACUUM workspace.gold.grocery_prices RETAIN 168 HOURS;
```
