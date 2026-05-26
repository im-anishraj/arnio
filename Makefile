.PHONY: install test lint format benchmark clean help

help:  ## Show this help message
	@python -c "import re; [print(f'\033[36m{m[0]:<15}\033[0m {m[1]}') for m in sorted([re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line).groups() for line in open('$(MAKEFILE_LIST)') if re.match(r'^[a-zA-Z_-]+:.*?## .*$$', line)])]"

install: ## Install dependencies and pre-commit
	pip install -e ".[dev]"
	pre-commit install

test: ## Run tests with coverage
	pytest tests/ -v --cov=arnio --cov-report=term-missing
	
test-quick: ## Run tests without coverage for faster iteration
	pytest tests/ -v
	
lint: ## Check linting
	ruff check .
	black --check .

format: ## Format code
	black .
	ruff check --fix .

benchmark: ## Run benchmarks
	python benchmarks/generate_data.py
	python benchmarks/benchmark_vs_pandas.py

benchmark-sparse-nulls: ## Run sparse-null benchmark
	python benchmarks/benchmark_sparse_nulls.py

clean: ## Remove build artifacts
ifeq ($(OS),Windows_NT)
	python -c "import shutil, os, glob; [shutil.rmtree(p, ignore_errors=True) for p in ['dist', 'build', '.pytest_cache'] + glob.glob('*.egg-info') + glob.glob('**/__pycache__', recursive=True)]; [os.remove(f) for f in glob.glob('**/*.pyc', recursive=True)]"
else
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache dist build *.egg-info
endif
