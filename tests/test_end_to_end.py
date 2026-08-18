import os

from grocery_index.bronze import run_bronze
from grocery_index.gold import run_gold
from grocery_index.silver import run_silver


def test_end_to_end_medallion_pipeline(spark, temp_delta_dir):
    # Setup test paths
    sample_csv = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "data", "sample", "statcan_grocery_sample.csv"
        )
    )
    bronze_dir = os.path.join(temp_delta_dir, "bronze")
    silver_dir = os.path.join(temp_delta_dir, "silver")
    quarantine_dir = os.path.join(temp_delta_dir, "quarantine")
    gold_dir = os.path.join(temp_delta_dir, "gold")
    export_dir = os.path.join(temp_delta_dir, "export")

    # 1. Bronze stage
    bronze_df = run_bronze(spark, sample_csv, bronze_dir)
    assert bronze_df.count() > 0
    assert "_batch_id" in bronze_df.columns
    assert "ingestion_timestamp" in bronze_df.columns

    # 2. Silver stage
    valid_silver, quarantine_silver = run_silver(
        spark,
        bronze_dir,
        silver_dir,
        geographies=("canada", "ontario"),
        quarantine_table=quarantine_dir,
    )
    assert valid_silver.count() > 0
    assert "RecordId" in valid_silver.columns
    # Check that non-target geography (Quebec in sample) was filtered out
    assert valid_silver.filter(valid_silver.Geography == "Quebec").count() == 0

    # 3. Gold stage
    gold_df = run_gold(spark, silver_dir, gold_dir, export_path=export_dir)
    assert gold_df.count() > 0
    assert "GoldRecordId" in gold_df.columns
    assert "MoM_PercentageChange" in gold_df.columns
    assert "BasketCategory" in gold_df.columns

    # Check export directory created
    assert os.path.exists(export_dir)
    export_files = [f for f in os.listdir(export_dir) if f.endswith(".csv")]
    assert len(export_files) == 1
