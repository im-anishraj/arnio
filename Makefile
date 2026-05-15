.PHONY: install test lint format benchmark clean help

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and pre-commit
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests with coverage
	pytest tests/ -v --cov=arnio --cov-report=term-missing

lint: ## Check linting
	ruff check .
	black --check .

format: ## Format code
	black .
	ruff check --fix .

benchmark: ## Run benchmarks
	python benchmarks/generate_data.py
	python benchmarks/benchmark_vs_pandas.py

clean: ## Remove build artifacts
	python -c "import shutil, os, glob; [shutil.rmtree(p, ignore_errors=True) for p in ['dist', 'build', '.pytest_cache'] + glob.glob('*.egg-info') + glob.glob('**/__pycache__', recursive=True)]; [os.remove(f) for f in glob.glob('**/*.pyc', recursive=True)]"
