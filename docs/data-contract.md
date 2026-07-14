# Gold data contract

The Gold table is a monthly price-change dataset. Its grain is one source product and unit of
measure per geography and snapshot month. Basket categories group related source products; they
do not collapse package sizes or product variants.

| Column | Type | Rule |
| --- | --- | --- |
| `SnapshotDate` | date | First day of the source reference month |
| `Geography` | string | Canada or Ontario under the default configuration |
| `BasketCategory` | string | One of the ten configured grocery categories |
| `ProductName` | string | Trimmed source product description |
| `UOM` | string | Source unit of measure; retained as part of the grain |
| `AveragePrice` | double | Positive source price |
| `PreviousMonthPrice` | double, nullable | Price only when the immediately preceding calendar month exists |
| `MoM_PercentageChange` | double, nullable | Percentage change from `PreviousMonthPrice` |

## Quality rules

- Required source columns must exist.
- Dates, geography, product, price, and unit cannot be null in Silver.
- Prices must be positive.
- Silver business keys must be unique.
- Missing calendar months produce null previous-price and percentage-change values.

