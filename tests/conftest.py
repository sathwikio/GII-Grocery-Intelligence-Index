import shutil
import tempfile

import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """Initializes a local SparkSession configured for unit and integration tests."""
    session = (
        SparkSession.builder.master("local[2]")
        .appName("gii-test-suite")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.default.parallelism", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def temp_delta_dir():
    """Provides a clean temporary directory for isolated Delta/Parquet storage tests."""
    tmp_path = tempfile.mkdtemp(prefix="gii_delta_test_")
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)
