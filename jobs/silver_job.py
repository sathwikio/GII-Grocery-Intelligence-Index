from grocery_index.config import PipelineConfig
from grocery_index.silver import run_silver

config = PipelineConfig.from_env()
run_silver(
    spark,  # noqa: F821
    config.bronze_table,
    config.silver_table,
    config.geographies,
    quarantine_table=config.silver_quarantine_table,
)
