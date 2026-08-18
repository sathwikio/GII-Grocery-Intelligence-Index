from datetime import date, datetime

import pytest

from grocery_index.quality import (
    assert_no_violations,
    require_columns,
    silver_violations,
    split_valid_and_quarantine,
)


def test_require_columns_passes_when_all_present(spark):
    df = spark.createDataFrame([(1, "a")], ["col1", "col2"])
    require_columns(df, ["col1", "col2"])


def test_require_columns_raises_when_columns_missing(spark):
    df = spark.createDataFrame([(1,)], ["col1"])
    with pytest.raises(ValueError, match="Missing required columns: col2, col3"):
        require_columns(df, ["col1", "col2", "col3"])


def test_silver_violations_detects_invalid_values(spark):
    rows = [
        (date(2026, 1, 1), "Ontario", "Milk", 5.0, "dollars"),  # valid
        (None, "Ontario", "Milk", 5.0, "dollars"),  # null date
        (date(2026, 1, 1), None, "Milk", 5.0, "dollars"),  # null geo
        (date(2026, 1, 1), "Ontario", None, 5.0, "dollars"),  # null product
        (date(2026, 1, 1), "Ontario", "Milk", 0.0, "dollars"),  # zero price
        (date(2026, 1, 1), "Ontario", "Milk", -2.5, "dollars"),  # negative price
        (date(2026, 1, 1), "Ontario", "Milk", 5.0, None),  # null uom
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    df = spark.createDataFrame(rows, columns)

    violations = silver_violations(df)
    assert violations.count() == 6


def test_split_valid_and_quarantine_routes_and_deduplicates(spark):
    rows = [
        # Valid record 1
        (date(2026, 1, 1), "Ontario", "Milk", 5.0, "dollars", datetime(2026, 1, 2, 10, 0)),
        # Malformed record (zero price)
        (date(2026, 1, 1), "Ontario", "Bread", 0.0, "dollars", datetime(2026, 1, 2, 10, 0)),
        # Duplicate record 1 (older)
        (date(2026, 1, 1), "Ontario", "Eggs", 4.0, "dollars", datetime(2026, 1, 2, 8, 0)),
        # Duplicate record 2 (newer - should be kept in valid)
        (date(2026, 1, 1), "Ontario", "Eggs", 4.25, "dollars", datetime(2026, 1, 2, 12, 0)),
    ]
    columns = [
        "SnapshotDate",
        "Geography",
        "ProductName",
        "AveragePrice",
        "UOM",
        "ingestion_timestamp",
    ]
    df = spark.createDataFrame(rows, columns)

    valid_df, quarantine_df = split_valid_and_quarantine(df)

    valid_rows = valid_df.collect()
    quarantine_rows = quarantine_df.collect()

    assert len(valid_rows) == 2  # Milk + newer Eggs
    assert len(quarantine_rows) == 2  # Zero-price Bread + older Eggs

    quarantine_reasons = {r.ProductName: r.quarantine_reason for r in quarantine_rows}
    assert quarantine_reasons["Bread"] == "NON_POSITIVE_PRICE"
    assert quarantine_reasons["Eggs"] == "DUPLICATE_BUSINESS_KEY"


def test_assert_no_violations_raises_on_non_empty_df(spark):
    df = spark.createDataFrame([(1,)], ["id"])
    with pytest.raises(ValueError, match="Data-quality check failed: sample_check"):
        assert_no_violations(df, "sample_check")
