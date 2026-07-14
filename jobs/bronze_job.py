from grocery_index.bronze import run_bronze
from grocery_index.config import PipelineConfig

config = PipelineConfig()
run_bronze(spark, config.source_csv_path, config.bronze_table)  # noqa: F821

