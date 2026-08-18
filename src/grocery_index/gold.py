from __future__ import annotations

from typing import TYPE_CHECKING

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from grocery_index.logging import get_logger, log_stage_execution
from grocery_index.quality import require_columns
from grocery_index.taxonomy import (
    BASKET_CATEGORIES,
    DEFAULT_BASKET_TAXONOMY,
    BasketRule,
    get_basket_category_expression,
)

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = get_logger("grocery_index.gold")

REQUIRED_SILVER_COLUMNS = {
    "SnapshotDate",
    "Geography",
    "ProductName",
    "AveragePrice",
    "UOM",
}


def build_gold(
    silver_df: DataFrame,
    taxonomy: tuple[BasketRule, ...] = DEFAULT_BASKET_TAXONOMY,
) -> DataFrame:
    """Enriches Silver grocery data with basket taxonomy and valid MoM price metrics."""
    require_columns(silver_df, REQUIRED_SILVER_COLUMNS)

    # 1. Match products to taxonomy rules
    category_expr = get_basket_category_expression(taxonomy, product_col="ProductName")
    basket_df = silver_df.withColumn("BasketCategory", category_expr).filter(
        F.col("BasketCategory").isNotNull()
    )

    # 2. Define the analytical time-series grain
    grain = ["Geography", "BasketCategory", "ProductName", "UOM"]
    window = Window.partitionBy(*grain).orderBy("SnapshotDate")

    # 3. Consecutive calendar-month validation window calculation
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
            "MoM_AbsoluteChange",
            F.when(
                F.col("PreviousMonthPrice").isNotNull(),
                F.round(F.col("AveragePrice") - F.col("PreviousMonthPrice"), 2),
            ),
        )
        .withColumn(
            "MoM_PercentageChange",
            F.when(
                F.col("PreviousMonthPrice").isNotNull(),
                F.round(
                    (
                        (F.col("AveragePrice") - F.col("PreviousMonthPrice"))
                        / F.col("PreviousMonthPrice")
                    )
                    * 100,
                    2,
                ),
            ),
        )
    )

    # 4. Generate deterministic Gold Surrogate Key
    gold_id_expr = F.sha2(
        F.concat_ws(
            "||",
            F.date_format("SnapshotDate", "yyyy-MM-dd"),
            F.col("Geography"),
            F.col("BasketCategory"),
            F.col("ProductName"),
            F.col("UOM"),
        ),
        256,
    ).alias("GoldRecordId")

    return (
        enriched.withColumn("GoldRecordId", gold_id_expr)
        .select(
            "GoldRecordId",
            "SnapshotDate",
            "Geography",
            "BasketCategory",
            "ProductName",
            "UOM",
            "AveragePrice",
            "PreviousMonthPrice",
            "MoM_AbsoluteChange",
            "MoM_PercentageChange",
        )
        .orderBy("Geography", "BasketCategory", "ProductName", "SnapshotDate")
    )


def run_gold(
    spark: SparkSession,
    source_table: str,
    target_table: str,
    export_path: str | None = None,
    mode: str = "overwrite",
) -> DataFrame:
    """Executes Gold analytical aggregation, Delta table persistence, and optional BI extraction."""
    with log_stage_execution("gold", logger=logger) as ctx:
        source_df = (
            spark.read.format("delta").load(source_table)
            if ("/" in source_table or source_table.startswith("."))
            else spark.read.table(source_table)
        )

        gold_df = build_gold(source_df)
        count = gold_df.count()
        ctx["records_processed"] = count

        logger.info("Writing %d records to Gold Delta table '%s'", count, target_table)

        writer = gold_df.write.format("delta").mode(mode)
        if "/" in target_table or target_table.startswith("."):
            writer.save(target_table)
        else:
            writer.saveAsTable(target_table)

        if export_path:
            logger.info("Exporting single-partition BI extract to '%s'", export_path)
            gold_df.coalesce(1).write.format("csv").option("header", "true").mode("overwrite").save(
                export_path
            )

        return gold_df


__all__ = ["BASKET_CATEGORIES", "build_gold", "run_gold"]
