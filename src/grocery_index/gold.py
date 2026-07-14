from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from grocery_index.quality import require_columns

BASKET_CATEGORIES = (
    "Milk",
    "Eggs",
    "Bread",
    "Butter",
    "Chicken",
    "Bananas",
    "Potatoes",
    "Beef",
    "Coffee",
    "Bacon",
)

REQUIRED_SILVER_COLUMNS = {
    "SnapshotDate",
    "Geography",
    "ProductName",
    "AveragePrice",
    "UOM",
}


def _basket_category() -> F.Column:
    product = F.lower(F.col("ProductName"))
    expression = None
    for category in BASKET_CATEGORIES:
        condition = product.contains(category.lower())
        expression = F.when(condition, F.lit(category)) if expression is None else expression.when(
            condition, F.lit(category)
        )
    return expression


def build_gold(silver_df: DataFrame) -> DataFrame:
    require_columns(silver_df, REQUIRED_SILVER_COLUMNS)
    basket_df = silver_df.withColumn("BasketCategory", _basket_category()).filter(
        F.col("BasketCategory").isNotNull()
    )

    grain = ["Geography", "BasketCategory", "ProductName", "UOM"]
    window = Window.partitionBy(*grain).orderBy("SnapshotDate")
    enriched = (
        basket_df.withColumn("PreviousSnapshotDate", F.lag("SnapshotDate").over(window))
        .withColumn("CandidatePreviousPrice", F.lag("AveragePrice").over(window))
        .withColumn(
            "PreviousMonthPrice",
            F.when(
                (F.months_between("SnapshotDate", "PreviousSnapshotDate") == 1)
                & (F.col("CandidatePreviousPrice") > 0),
                F.col("CandidatePreviousPrice"),
            ),
        )
        .withColumn(
            "MoM_PercentageChange",
            F.round(
                (
                    (F.col("AveragePrice") - F.col("PreviousMonthPrice"))
                    / F.col("PreviousMonthPrice")
                )
                * 100,
                2,
            ),
        )
    )

    return enriched.select(
        "SnapshotDate",
        "Geography",
        "BasketCategory",
        "ProductName",
        "UOM",
        "AveragePrice",
        "PreviousMonthPrice",
        "MoM_PercentageChange",
    )


def run_gold(spark, source_table: str, target_table: str, export_path: str) -> None:
    gold_df = build_gold(spark.read.table(source_table))
    gold_df.write.format("delta").mode("overwrite").saveAsTable(target_table)
    gold_df.coalesce(1).write.format("csv").option("header", "true").mode("overwrite").save(
        export_path
    )

