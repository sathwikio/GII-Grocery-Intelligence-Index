from grocery_index.config import PipelineConfig
from grocery_index.gold import run_gold

config = PipelineConfig()
run_gold(spark, config.silver_table, config.gold_table, config.export_path)  # noqa: F821

