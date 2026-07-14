from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    source_csv_path: str = "/Volumes/workspace/bronze/v_gii_raw_landing/18100245.csv"
    bronze_table: str = "workspace.bronze.grocery_prices"
    silver_table: str = "workspace.silver.grocery_prices"
    gold_table: str = "workspace.gold.grocery_prices"
    export_path: str = "/Volumes/workspace/gold/gold_output/grocery_index_extract"
    geographies: tuple[str, ...] = ("canada", "ontario")

