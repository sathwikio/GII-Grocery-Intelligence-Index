from datetime import datetime

import pytest

from grocery_index.silver import build_silver, build_silver_raw


def test_silver_types_filters_and_trims(spark):
    rows = [
        ("2026-01", " Ontario ", " Milk, 2 litres ", "6.49", " dollars ", datetime(2026, 1, 2)),
        ("2026-01", "Quebec", "Milk, 2 litres", "6.39", "dollars", datetime(2026, 1, 2)),
    ]
    columns = ["REF_DATE", "GEO", "Products", "VALUE", "UOM", "ingestion_timestamp"]
    result = build_silver(spark.createDataFrame(rows, columns), ("canada", "ontario")).collect()

    assert len(result) == 1
    assert result[0].ProductName == "Milk, 2 litres"
    assert result[0].AveragePrice == pytest.approx(6.49)
    assert result[0].UOM == "dollars"
    assert result[0].Geography == "Ontario"
    assert result[0].RecordId is not None
    assert len(result[0].RecordId) == 64  # SHA-256 length


def test_silver_surrogate_key_is_deterministic(spark):
    rows = [
        ("2026-01", "Canada", "Bananas, per kilogram", "1.79", "dollars", datetime(2026, 1, 1)),
        ("2026-01", "Canada", "Bananas, per kilogram", "1.79", "dollars", datetime(2026, 1, 1)),
    ]
    columns = ["REF_DATE", "GEO", "Products", "VALUE", "UOM", "ingestion_timestamp"]
    df = build_silver_raw(spark.createDataFrame(rows, columns), ("canada",))
    record_ids = [row.RecordId for row in df.collect()]

    assert len(record_ids) == 2
    assert record_ids[0] == record_ids[1]


def test_silver_raises_on_missing_required_columns(spark):
    rows = [("2026-01", "Ontario")]
    df = spark.createDataFrame(rows, ["REF_DATE", "GEO"])

    with pytest.raises(ValueError, match="Missing required columns"):
        build_silver(df, ("ontario",))
