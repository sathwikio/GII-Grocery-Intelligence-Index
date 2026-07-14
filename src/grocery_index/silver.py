from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from grocery_index.quality import (
    assert_no_violations,
    duplicate_business_keys,
    require_columns,
    silver_violations,
)

REQUIRED_BRONZE_COLUMNS = {
    "REF_DATE",
    "GEO",
    "Products",
    "VALUE",
    "UOM",
    "ingestion_timestamp",
}


def build_silver(bronze_df: DataFrame, geographies: tuple[str, ...]) -> DataFrame:
    require_columns(bronze_df, REQUIRED_BRONZE_COLUMNS)
    return (
        bronze_df.filter(F.lower(F.trim(F.col("GEO"))).isin(*geographies))
        .select(
            F.to_date("REF_DATE", "yyyy-MM").alias("SnapshotDate"),
            F.trim("GEO").alias("Geography"),
            F.trim("Products").alias("ProductName"),
            F.col("VALUE").cast("double").alias("AveragePrice"),
            F.trim("UOM").alias("UOM"),
            "ingestion_timestamp",
        )
    )


def run_silver(spark, source_table: str, target_table: str, geographies: tuple[str, ...]) -> None:
    silver_df = build_silver(spark.read.table(source_table), geographies)
    assert_no_violations(silver_violations(silver_df), "invalid silver records")
    assert_no_violations(duplicate_business_keys(silver_df), "duplicate silver business keys")
    silver_df.write.format("delta").mode("overwrite").saveAsTable(target_table)

