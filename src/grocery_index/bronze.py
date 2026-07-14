from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def add_ingestion_metadata(raw_df: DataFrame, source_file_name: str) -> DataFrame:
    return raw_df.withColumn("ingestion_timestamp", F.current_timestamp()).withColumn(
        "source_file_name", F.lit(source_file_name)
    )


def run_bronze(spark, source_csv_path: str, target_table: str) -> None:
    raw_df = (
        spark.read.format("csv")
        .option("header", "true")
        .option("inferSchema", "false")
        .load(source_csv_path)
    )
    if raw_df.isEmpty():
        raise ValueError("Source CSV file is empty")

    bronze_df = add_ingestion_metadata(raw_df, source_csv_path.rsplit("/", 1)[-1])
    bronze_df.write.format("delta").mode("overwrite").saveAsTable(target_table)

