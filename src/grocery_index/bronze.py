from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from grocery_index.logging import get_logger, log_stage_execution

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = get_logger("grocery_index.bronze")


def sanitize_column_names(df: DataFrame) -> DataFrame:
    """Removes UTF-8 BOM characters and leading/trailing whitespace from column names."""
    renamed_df = df
    for col_name in df.columns:
        clean_name = col_name.lstrip("\ufeff").strip()
        if clean_name != col_name:
            renamed_df = renamed_df.withColumnRenamed(col_name, clean_name)
    return renamed_df


def add_ingestion_metadata(
    raw_df: DataFrame, source_file_name: str, batch_id: str | None = None
) -> DataFrame:
    """Enriches raw data with audit tracking columns for lineage and observability."""
    assigned_batch_id = batch_id or str(uuid.uuid4())
    cleaned_df = sanitize_column_names(raw_df)
    return (
        cleaned_df.withColumn("ingestion_timestamp", F.current_timestamp())
        .withColumn("source_file_name", F.lit(source_file_name))
        .withColumn("_batch_id", F.lit(assigned_batch_id))
    )


def read_raw_csv(spark: SparkSession, source_csv_path: str) -> DataFrame:
    """Reads landing CSV dataset into PySpark with explicit header and string types."""
    if not os.path.exists(source_csv_path) and not source_csv_path.startswith(
        ("dbfs:", "s3:", "abfss:", "wasbs:", "/Volumes")
    ):
        raise FileNotFoundError(f"Source CSV path does not exist: {source_csv_path}")

    raw_df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "false")
        .option("encoding", "UTF-8")
        .load(source_csv_path)
    )

    if raw_df.isEmpty():
        raise ValueError(f"Source CSV file is empty: {source_csv_path}")

    return sanitize_column_names(raw_df)


def run_bronze(
    spark: SparkSession,
    source_csv_path: str,
    target_table: str,
    mode: str = "overwrite",
) -> DataFrame:
    """Ingests raw CSV data into the Bronze Delta tier with lineage metadata."""
    with log_stage_execution("bronze", logger=logger) as ctx:
        source_name = source_csv_path.rsplit("/", 1)[-1]
        raw_df = read_raw_csv(spark, source_csv_path)
        bronze_df = add_ingestion_metadata(raw_df, source_name, batch_id=ctx["run_id"])

        count = bronze_df.count()
        ctx["records_processed"] = count
        logger.info("Landing %d raw records into Bronze table '%s'", count, target_table)

        try:
            writer = bronze_df.write.format("delta").mode(mode)
            if "/" in target_table or target_table.startswith("."):
                writer.save(target_table)
            else:
                writer.saveAsTable(target_table)
        except Exception:
            writer = bronze_df.write.format("parquet").mode(mode)
            if "/" in target_table or target_table.startswith("."):
                writer.save(target_table)
            else:
                writer.saveAsTable(target_table)

        return bronze_df
