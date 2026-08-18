from datetime import date

import pytest

from grocery_index.gold import build_gold
from grocery_index.taxonomy import BasketRule


def test_gold_calculates_only_consecutive_month_change(spark):
    rows = [
        (date(2026, 1, 1), "Ontario", "Milk, 2 litres", 5.0, "dollars"),
        (date(2026, 2, 1), "Ontario", "Milk, 2 litres", 5.5, "dollars"),
        (date(2026, 4, 1), "Ontario", "Milk, 2 litres", 6.0, "dollars"),  # skips March
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    result = build_gold(spark.createDataFrame(rows, columns)).orderBy("SnapshotDate").collect()

    assert len(result) == 3
    # Month 1: no previous month
    assert result[0].PreviousMonthPrice is None
    assert result[0].MoM_AbsoluteChange is None
    assert result[0].MoM_PercentageChange is None

    # Month 2: valid consecutive month (Jan -> Feb)
    assert result[1].PreviousMonthPrice == pytest.approx(5.0)
    assert result[1].MoM_AbsoluteChange == pytest.approx(0.5)
    assert result[1].MoM_PercentageChange == pytest.approx(10.0)

    # Month 3: non-consecutive month (Feb -> Apr, skipped Mar)
    assert result[2].PreviousMonthPrice is None
    assert result[2].MoM_AbsoluteChange is None
    assert result[2].MoM_PercentageChange is None


def test_gold_preserves_product_and_unit_grain(spark):
    rows = [
        (date(2026, 1, 1), "Canada", "Beef stewing cuts, per kilogram", 18.0, "dollars"),
        (date(2026, 1, 1), "Canada", "Beef striploin, per kilogram", 25.0, "dollars"),
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    result = build_gold(spark.createDataFrame(rows, columns)).collect()

    assert {row.ProductName for row in result} == {row[2] for row in rows}
    assert {row.BasketCategory for row in result} == {"Beef"}
    assert all(len(row.GoldRecordId) == 64 for row in result)


def test_gold_taxonomy_avoids_false_substring_matching(spark):
    custom_taxonomy = (
        BasketRule(1, "Bacon", r"(?i)\bbacon\b"),
        BasketRule(2, "Butter", r"(?i)\bbutter\b(?!.*tarts)"),
        BasketRule(3, "Chicken", r"(?i)\bchicken\b"),
    )
    rows = [
        (date(2026, 1, 1), "Canada", "Butter tarts, 6 pack", 4.99, "dollars"),  # should be excluded
        (date(2026, 1, 1), "Canada", "Salted butter, 454 grams", 5.99, "dollars"),  # Butter
        (date(2026, 1, 1), "Canada", "Chicken breast, per kg", 14.50, "dollars"),  # Chicken
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    result = build_gold(spark.createDataFrame(rows, columns), taxonomy=custom_taxonomy).collect()

    categories = {row.BasketCategory for row in result}
    assert "Butter" in categories
    assert "Chicken" in categories
    assert len(result) == 2  # Butter tarts excluded


def test_gold_raises_on_missing_required_columns(spark):
    rows = [(date(2026, 1, 1), "Canada")]
    df = spark.createDataFrame(rows, ["SnapshotDate", "Geography"])

    with pytest.raises(ValueError, match="Missing required columns"):
        build_gold(df)
