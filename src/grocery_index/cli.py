from __future__ import annotations

import argparse
import sys
import time

from grocery_index.bronze import run_bronze
from grocery_index.config import PipelineConfig
from grocery_index.gold import run_gold
from grocery_index.logging import get_logger
from grocery_index.silver import run_silver

logger = get_logger("grocery_index.cli")


def get_spark_session(app_name: str = "GroceryIntelligenceIndex-CLI"):
    """Initializes or retrieves an active SparkSession with Delta Lake support."""
    try:
        from pyspark.sql import SparkSession

        builder = (
            SparkSession.builder.appName(app_name)
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
            .config("spark.ui.enabled", "false")
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.driver.bindAddress", "127.0.0.1")
        )
        try:
            from delta import configure_spark_with_delta_pip

            builder = configure_spark_with_delta_pip(builder)
        except ImportError:
            pass

        return builder.getOrCreate()
    except Exception as exc:
        logger.error("Failed to initialize SparkSession: %s", exc)
        raise


def run_pipeline(
    env: str = "local",
    stage: str = "all",
    config_override: PipelineConfig | None = None,
) -> None:
    """Executes the pipeline stages according to the specified environment."""
    config = config_override or PipelineConfig.from_env(env)  # type: ignore
    spark = get_spark_session(f"GII-Pipeline-{config.environment}")

    start_time = time.time()
    print("=" * 70)
    print(f"🚀 Grocery Intelligence Index Pipeline | Environment: [{config.environment.upper()}]")
    print("=" * 70)
    print(f"• Source Path:       {config.source_csv_path}")
    print(f"• Bronze Table/Path: {config.bronze_table}")
    print(f"• Silver Table/Path: {config.silver_table}")
    print(f"• Gold Table/Path:   {config.gold_table}")
    print(f"• Target Geographies: {', '.join(config.geographies)}")
    print("=" * 70)

    try:
        if stage in ("all", "bronze"):
            print("\n[1/3] Ingesting raw dataset into Bronze...")
            run_bronze(spark, config.source_csv_path, config.bronze_table)
            print("  ✓ Bronze stage completed.")

        if stage in ("all", "silver"):
            print("\n[2/3] Validating, cleansing, and promoting to Silver...")
            run_silver(
                spark,
                config.bronze_table,
                config.silver_table,
                config.geographies,
                quarantine_table=config.silver_quarantine_table,
            )
            print("  ✓ Silver stage completed.")

        if stage in ("all", "gold"):
            print("\n[3/3] Categorizing baskets and computing MoM metrics in Gold...")
            run_gold(spark, config.silver_table, config.gold_table, config.export_path)
            print("  ✓ Gold stage completed.")

        total_elapsed = time.time() - start_time
        print("\n" + "=" * 70)
        print(f"🎉 Pipeline successfully finished in {total_elapsed:.2f} seconds.")
        print("=" * 70)
    except Exception as exc:
        print(f"\n❌ Pipeline execution failed: {exc}", file=sys.stderr)
        raise


def main() -> None:
    """Command-line entrypoint for the Grocery Intelligence Index."""
    parser = argparse.ArgumentParser(
        description="Grocery Intelligence Index (GII) - Lakehouse Pipeline Runner"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    run_parser = subparsers.add_parser("run", help="Run the Lakehouse pipeline")
    run_parser.add_argument(
        "--env",
        choices=["local", "dev", "prod"],
        default="local",
        help="Target environment (default: local)",
    )
    run_parser.add_argument(
        "--stage",
        choices=["all", "bronze", "silver", "gold"],
        default="all",
        help="Pipeline stage to execute (default: all)",
    )

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        env = getattr(args, "env", "local")
        stage = getattr(args, "stage", "all")
        run_pipeline(env=env, stage=stage)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
