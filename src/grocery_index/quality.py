from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


@dataclass(frozen=True)
class QualitySummary:
    """Summary of data quality evaluation metrics."""

    total_records: int
    valid_records: int
    quarantine_records: int
    duplicate_records: int
    is_clean: bool


def require_columns(df: DataFrame, required: Iterable[str]) -> None:
    """Validates that all required columns exist in the DataFrame."""
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def get_validation_condition() -> Column:
    """Returns a Spark boolean Column condition identifying valid Silver records."""
    return (
        F.col("SnapshotDate").isNotNull()
        & F.col("Geography").isNotNull()
        & F.col("ProductName").isNotNull()
        & F.col("UOM").isNotNull()
        & F.col("AveragePrice").isNotNull()
        & (F.col("AveragePrice") > 0.0)
    )


def silver_violations(df: DataFrame) -> DataFrame:
    """Extracts records that fail Silver tier quality validation rules."""
    return df.filter(~get_validation_condition())


def duplicate_business_keys(df: DataFrame) -> DataFrame:
    """Identifies business key combinations that appear more than once."""
    keys = ["SnapshotDate", "Geography", "ProductName", "UOM"]
    return df.groupBy(*keys).count().filter(F.col("count") > 1)


def split_valid_and_quarantine(
    df: DataFrame,
) -> tuple[DataFrame, DataFrame]:
    """Partitions records into valid dataset and quarantined dataset with reason annotations.

    Deduplicates on business keys, preserving the most recent ingestion record if duplicates exist.
    """
    # 1. Flag validation reason
    tagged_df = df.withColumn(
        "quarantine_reason",
        F.when(F.col("SnapshotDate").isNull(), F.lit("NULL_SNAPSHOT_DATE"))
        .when(F.col("Geography").isNull(), F.lit("NULL_GEOGRAPHY"))
        .when(F.col("ProductName").isNull(), F.lit("NULL_PRODUCT_NAME"))
        .when(F.col("UOM").isNull(), F.lit("NULL_UOM"))
        .when(F.col("AveragePrice").isNull(), F.lit("NULL_AVERAGE_PRICE"))
        .when(F.col("AveragePrice") <= 0.0, F.lit("NON_POSITIVE_PRICE"))
        .otherwise(F.lit(None)),
    )

    # 2. Window for business key deduplication (keep latest ingestion_timestamp)
    business_keys = ["SnapshotDate", "Geography", "ProductName", "UOM"]
    window_spec = Window.partitionBy(*business_keys).orderBy(
        F.col("ingestion_timestamp").desc_nulls_last()
    )

    deduped_df = tagged_df.withColumn("row_num", F.row_number().over(window_spec)).withColumn(
        "quarantine_reason",
        F.when(
            F.col("quarantine_reason").isNull() & (F.col("row_num") > 1),
            F.lit("DUPLICATE_BUSINESS_KEY"),
        ).otherwise(F.col("quarantine_reason")),
    )

    valid_df = deduped_df.filter(F.col("quarantine_reason").isNull()).drop(
        "row_num", "quarantine_reason"
    )
    quarantine_df = deduped_df.filter(F.col("quarantine_reason").isNotNull()).drop("row_num")

    return valid_df, quarantine_df


def assert_no_violations(df: DataFrame, name: str) -> None:
    """Raises an error if the violation DataFrame contains any rows."""
    if not df.isEmpty():
        violation_count = df.count()
        raise ValueError(
            f"Data-quality check failed: {name} ({violation_count} violating records found)"
        )
