from datetime import date

import pytest

from grocery_index.gold import build_gold


def test_gold_calculates_only_consecutive_month_change(spark):
    rows = [
        (date(2026, 1, 1), "Ontario", "Milk, 2 litres", 5.0, "dollars"),
        (date(2026, 2, 1), "Ontario", "Milk, 2 litres", 5.5, "dollars"),
        (date(2026, 4, 1), "Ontario", "Milk, 2 litres", 6.0, "dollars"),
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    result = build_gold(spark.createDataFrame(rows, columns)).orderBy("SnapshotDate").collect()

    assert result[0].PreviousMonthPrice is None
    assert result[0].MoM_PercentageChange is None
    assert result[1].PreviousMonthPrice == pytest.approx(5.0)
    assert result[1].MoM_PercentageChange == pytest.approx(10.0)
    assert result[2].PreviousMonthPrice is None
    assert result[2].MoM_PercentageChange is None


def test_gold_keeps_product_and_unit_grain(spark):
    rows = [
        (date(2026, 1, 1), "Canada", "Beef stewing cuts, per kilogram", 18.0, "dollars"),
        (date(2026, 1, 1), "Canada", "Beef striploin, per kilogram", 25.0, "dollars"),
    ]
    columns = ["SnapshotDate", "Geography", "ProductName", "AveragePrice", "UOM"]
    result = build_gold(spark.createDataFrame(rows, columns)).collect()
    assert {row.ProductName for row in result} == {row[2] for row in rows}
    assert {row.BasketCategory for row in result} == {"Beef"}

