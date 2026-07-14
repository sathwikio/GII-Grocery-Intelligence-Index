from collections.abc import Iterable

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def require_columns(df: DataFrame, required: Iterable[str]) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def silver_violations(df: DataFrame) -> DataFrame:
    return df.filter(
        F.col("SnapshotDate").isNull()
        | F.col("ProductName").isNull()
        | F.col("AveragePrice").isNull()
        | (F.col("AveragePrice") <= 0)
        | F.col("Geography").isNull()
        | F.col("UOM").isNull()
    )


def duplicate_business_keys(df: DataFrame) -> DataFrame:
    keys = ["SnapshotDate", "Geography", "ProductName", "UOM"]
    return df.groupBy(*keys).count().filter(F.col("count") > 1)


def assert_no_violations(df: DataFrame, name: str) -> None:
    if not df.isEmpty():
        raise ValueError(f"Data-quality check failed: {name}")

