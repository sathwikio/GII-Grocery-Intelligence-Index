from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

EnvironmentType = Literal["local", "dev", "prod"]


@dataclass(frozen=True)
class PipelineConfig:
    """Environment-aware configuration for the Grocery Intelligence Index pipeline."""

    environment: EnvironmentType = "dev"
    source_csv_path: str = "/Volumes/workspace/bronze/v_gii_raw_landing/18100245.csv"
    bronze_table: str = "workspace.bronze.grocery_prices"
    silver_table: str = "workspace.silver.grocery_prices"
    silver_quarantine_table: str = "workspace.silver.grocery_prices_quarantine"
    gold_table: str = "workspace.gold.grocery_prices"
    export_path: str = "/Volumes/workspace/gold/gold_output/grocery_index_extract"
    geographies: tuple[str, ...] = ("canada", "ontario")

    @classmethod
    def from_env(cls, env: EnvironmentType | None = None) -> PipelineConfig:
        """Create configuration based on environment and environment variable overrides."""
        target_env = env or os.getenv("GII_ENV", "dev").lower()  # type: ignore

        if target_env == "local":
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
            raw_path = os.path.join(base_dir, "raw", "18100245.csv")
            sample_path = os.path.join(base_dir, "sample", "statcan_grocery_sample.csv")
            default_source = raw_path if os.path.exists(raw_path) else sample_path

            return cls(
                environment="local",
                source_csv_path=os.getenv("GII_SOURCE_CSV_PATH", default_source),
                bronze_table=os.getenv(
                    "GII_BRONZE_TABLE", os.path.join(base_dir, "delta", "bronze_grocery_prices")
                ),
                silver_table=os.getenv(
                    "GII_SILVER_TABLE", os.path.join(base_dir, "delta", "silver_grocery_prices")
                ),
                silver_quarantine_table=os.getenv(
                    "GII_SILVER_QUARANTINE_TABLE",
                    os.path.join(base_dir, "delta", "silver_quarantine"),
                ),
                gold_table=os.getenv(
                    "GII_GOLD_TABLE", os.path.join(base_dir, "delta", "gold_grocery_prices")
                ),
                export_path=os.getenv(
                    "GII_EXPORT_PATH", os.path.join(base_dir, "export", "grocery_index_extract")
                ),
                geographies=tuple(
                    g.strip().lower()
                    for g in os.getenv("GII_GEOGRAPHIES", "canada,ontario").split(",")
                ),
            )

        if target_env == "prod":
            return cls(
                environment="prod",
                source_csv_path=os.getenv(
                    "GII_SOURCE_CSV_PATH",
                    "/Volumes/prod_catalog/bronze/v_gii_raw_landing/18100245.csv",
                ),
                bronze_table=os.getenv("GII_BRONZE_TABLE", "prod_catalog.bronze.grocery_prices"),
                silver_table=os.getenv("GII_SILVER_TABLE", "prod_catalog.silver.grocery_prices"),
                silver_quarantine_table=os.getenv(
                    "GII_SILVER_QUARANTINE_TABLE",
                    "prod_catalog.silver.grocery_prices_quarantine",
                ),
                gold_table=os.getenv("GII_GOLD_TABLE", "prod_catalog.gold.grocery_prices"),
                export_path=os.getenv(
                    "GII_EXPORT_PATH",
                    "/Volumes/prod_catalog/gold/gold_output/grocery_index_extract",
                ),
                geographies=tuple(
                    g.strip().lower()
                    for g in os.getenv("GII_GEOGRAPHIES", "canada,ontario").split(",")
                ),
            )

        # Default: dev
        return cls(
            environment="dev",
            source_csv_path=os.getenv(
                "GII_SOURCE_CSV_PATH",
                "/Volumes/workspace/bronze/v_gii_raw_landing/18100245.csv",
            ),
            bronze_table=os.getenv("GII_BRONZE_TABLE", "workspace.bronze.grocery_prices"),
            silver_table=os.getenv("GII_SILVER_TABLE", "workspace.silver.grocery_prices"),
            silver_quarantine_table=os.getenv(
                "GII_SILVER_QUARANTINE_TABLE",
                "workspace.silver.grocery_prices_quarantine",
            ),
            gold_table=os.getenv("GII_GOLD_TABLE", "workspace.gold.grocery_prices"),
            export_path=os.getenv(
                "GII_EXPORT_PATH",
                "/Volumes/workspace/gold/gold_output/grocery_index_extract",
            ),
            geographies=tuple(
                g.strip().lower() for g in os.getenv("GII_GEOGRAPHIES", "canada,ontario").split(",")
            ),
        )
