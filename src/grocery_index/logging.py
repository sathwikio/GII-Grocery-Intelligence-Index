from __future__ import annotations

import logging
import sys
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


def get_logger(name: str = "grocery_index") -> logging.Logger:
    """Configures and returns a structured logger for pipeline tracking."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


@contextmanager
def log_stage_execution(
    stage_name: str,
    logger: logging.Logger | None = None,
    extra_context: dict[str, Any] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Context manager to measure and log execution duration and metadata for pipeline stages."""
    log = logger or get_logger()
    run_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    context: dict[str, Any] = {"run_id": run_id, "stage": stage_name, "records_processed": None}
    if extra_context:
        context.update(extra_context)

    log.info(">>> Starting stage [%s] (run_id=%s)", stage_name, run_id)
    try:
        yield context
        elapsed = time.time() - start_time
        records_str = (
            f", records={context['records_processed']}"
            if context.get("records_processed") is not None
            else ""
        )
        log.info(
            "<<< Completed stage [%s] (run_id=%s, duration=%.2fs%s)",
            stage_name,
            run_id,
            elapsed,
            records_str,
        )
    except Exception as exc:
        elapsed = time.time() - start_time
        log.error(
            "!!! Failed stage [%s] (run_id=%s, duration=%.2fs) - Error: %s",
            stage_name,
            run_id,
            elapsed,
            exc,
            exc_info=True,
        )
        raise
