.PHONY: help install lint format test test-cov run-local clean

PYTHON ?= python3

help:
	@echo "Grocery Intelligence Index (GII) - Developer Commands:"
	@echo "  make install     - Install package in editable mode with development dependencies"
	@echo "  make lint        - Run Ruff linting checks across src, tests, and jobs"
	@echo "  make format      - Auto-format codebase using Ruff"
	@echo "  make test        - Run PySpark test suite"
	@echo "  make test-cov    - Run PySpark tests with coverage report"
	@echo "  make run-local   - Execute the end-to-end Medallion pipeline locally with sample data"
	@echo "  make clean       - Remove cache, build artifacts, and local delta files"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check src tests jobs

format:
	ruff format src tests jobs

test:
	pytest

test-cov:
	pytest --cov=grocery_index --cov-report=term-missing

run-local:
	$(PYTHON) -m grocery_index.cli run --env local

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov
	rm -rf data/delta data/export
	find . -type d -name "__pycache__" -exec rm -rf {} +
