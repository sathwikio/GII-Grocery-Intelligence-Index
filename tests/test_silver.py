from datetime import datetime

import pytest

from grocery_index.quality import duplicate_business_keys, silver_violations
from grocery_index.silver import build_silver


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


def test_quality_checks_find_invalid_and_duplicate_rows(spark):
    rows = [
        ("2026-01-01", "Ontario", "Milk", 0.0, "dollars"),
        ("2026-01-01", "Ontario", "Milk", 0.0, "dollars"),
    ]
    df = spark.createDataFrame(rows, ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"])
    assert silver_violations(df).count() == 2
    assert duplicate_business_keys(df).count() == 1

