from __future__ import annotations

from typing import NamedTuple

from pyspark.sql import Column
from pyspark.sql import functions as F


class BasketRule(NamedTuple):
    """Taxonomy rule defining priority, category name, and matching regex pattern."""

    priority: int
    category: str
    pattern: str  # Regex pattern (case-insensitive)


# Configurable Basket Taxonomy Rules (ordered by priority to eliminate false matches)
DEFAULT_BASKET_TAXONOMY: tuple[BasketRule, ...] = (
    BasketRule(1, "Bacon", r"(?i)\bbacon\b"),
    BasketRule(2, "Butter", r"(?i)^(?!.*peanut).*?\bbutter\b"),
    BasketRule(3, "Eggs", r"(?i)\beggs?\b"),
    BasketRule(4, "Milk", r"(?i)\bmilk\b(?!.*chocolate\s+bar)"),
    BasketRule(5, "Chicken", r"(?i)\bchicken\b"),
    BasketRule(6, "Beef", r"(?i)\bbeef\b"),
    BasketRule(7, "Bananas", r"(?i)\bbananas?\b"),
    BasketRule(8, "Potatoes", r"(?i)^(?!.*french).*?\bpotatoes?\b"),
    BasketRule(9, "Coffee", r"(?i)\bcoffee\b"),
    BasketRule(10, "Bread", r"(?i)^(?!.*crackers).*?\bbread\b"),
)

BASKET_CATEGORIES: tuple[str, ...] = tuple(rule.category for rule in DEFAULT_BASKET_TAXONOMY)


def get_basket_category_expression(
    taxonomy: tuple[BasketRule, ...] = DEFAULT_BASKET_TAXONOMY,
    product_col: str = "ProductName",
) -> Column:
    """Builds a SQL CASE expression applying prioritized regex pattern matching across products."""
    product = F.col(product_col)
    expression: Column | None = None

    sorted_rules = sorted(taxonomy, key=lambda r: r.priority)

    for rule in sorted_rules:
        condition = product.rlike(rule.pattern)
        expression = (
            F.when(condition, F.lit(rule.category))
            if expression is None
            else expression.when(condition, F.lit(rule.category))
        )

    return expression if expression is not None else F.lit(None)
