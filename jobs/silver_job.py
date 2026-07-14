from grocery_index.config import PipelineConfig
from grocery_index.silver import run_silver

config = PipelineConfig()
run_silver(spark, config.bronze_table, config.silver_table, config.geographies)  # noqa: F821

