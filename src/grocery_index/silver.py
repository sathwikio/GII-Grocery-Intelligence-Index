from __future__ import annotations

from typing import TYPE_CHECKING

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from grocery_index.logging import get_logger, log_stage_execution
from grocery_index.quality import (
    require_columns,
    split_valid_and_quarantine,
)

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = get_logger("grocery_index.silver")

REQUIRED_BRONZE_COLUMNS = {
    "REF_DATE",
    "GEO",
    "Products",
    "VALUE",
    "UOM",
    "ingestion_timestamp",
}


def build_silver_raw(bronze_df: DataFrame, geographies: tuple[str, ...]) -> DataFrame:
    """Parses, types, and filters Bronze records for the target geographies."""
    require_columns(bronze_df, REQUIRED_BRONZE_COLUMNS)

    # Standardize and filter by allowed geography
    allowed_geos = [g.strip().lower() for g in geographies]
    filtered_df = bronze_df.filter(F.lower(F.trim(F.col("GEO"))).isin(*allowed_geos))

    has_batch_id = "_batch_id" in bronze_df.columns

    base_select = [
        F.to_date("REF_DATE", "yyyy-MM").alias("SnapshotDate"),
        F.trim("GEO").alias("Geography"),
        F.trim("Products").alias("ProductName"),
        F.col("VALUE").cast("double").alias("AveragePrice"),
        F.trim("UOM").alias("UOM"),
        F.col("ingestion_timestamp"),
    ]

    if has_batch_id:
        base_select.append(F.col("_batch_id"))

    typed_df = filtered_df.select(*base_select)

    # Generate deterministic surrogate key (SHA-256 hash of business grain)
    surrogate_key_expr = F.sha2(
        F.concat_ws(
            "||",
            F.coalesce(F.date_format("SnapshotDate", "yyyy-MM-dd"), F.lit("")),
            F.coalesce(F.col("Geography"), F.lit("")),
            F.coalesce(F.col("ProductName"), F.lit("")),
            F.coalesce(F.col("UOM"), F.lit("")),
        ),
        256,
    ).alias("RecordId")

    return typed_df.withColumn("RecordId", surrogate_key_expr).withColumn(
        "_processed_at", F.current_timestamp()
    )


def build_silver(bronze_df: DataFrame, geographies: tuple[str, ...]) -> DataFrame:
    """Builds clean Silver dataset, rejecting and filtering out any malformed rows."""
    raw_silver = build_silver_raw(bronze_df, geographies)
    valid_df, _ = split_valid_and_quarantine(raw_silver)
    return valid_df


def run_silver(
    spark: SparkSession,
    source_table: str,
    target_table: str,
    geographies: tuple[str, ...],
    quarantine_table: str | None = None,
    mode: str = "overwrite",
) -> tuple[DataFrame, DataFrame]:
    """Executes the Silver transformation pipeline with data quality quarantine routing."""
    with log_stage_execution("silver", logger=logger) as ctx:
        source_df = (
            spark.read.format("delta").load(source_table)
            if ("/" in source_table or source_table.startswith("."))
            else spark.read.table(source_table)
        )

        raw_silver = build_silver_raw(source_df, geographies)
        valid_df, quarantine_df = split_valid_and_quarantine(raw_silver)

        valid_count = valid_df.count()
        quarantine_count = quarantine_df.count()
        ctx["records_processed"] = valid_count

        logger.info(
            "Silver validation complete: %d valid records, %d quarantined records",
            valid_count,
            quarantine_count,
        )

        # Persist valid records
        valid_writer = valid_df.write.format("delta").mode(mode)
        if "/" in target_table or target_table.startswith("."):
            valid_writer.save(target_table)
        else:
            valid_writer.saveAsTable(target_table)

        # Persist quarantine records if table/path configured
        if quarantine_table and quarantine_count > 0:
            logger.warning(
                "Writing %d records to Silver Quarantine table '%s'",
                quarantine_count,
                quarantine_table,
            )
            q_writer = quarantine_df.write.format("delta").mode("append")
            if "/" in quarantine_table or quarantine_table.startswith("."):
                q_writer.save(quarantine_table)
            else:
                q_writer.saveAsTable(quarantine_table)

        return valid_df, quarantine_df
