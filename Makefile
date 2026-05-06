.PHONY: install test lint format benchmark clean

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest tests/ -v --cov=arnio --cov-report=term-missing

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check --fix .

benchmark:
	python benchmarks/generate_data.py
	python benchmarks/benchmark_vs_pandas.py

clean:  ## Remove build artifacts (Linux/macOS only; Windows: delete manually)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache dist build *.egg-info
