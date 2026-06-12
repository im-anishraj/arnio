.PHONY: install test test-quick lint format benchmark doctor clean help

help:  ## Show this help message
	@python -c "import re; [print(f'\033[36m{m[0]:<15}\033[0m {m[1]}') for m in sorted([re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line).groups() for line in open('$(MAKEFILE_LIST)') if re.match(r'^[a-zA-Z_-]+:.*?## .*$$', line)])]"

install: ## Install dependencies and pre-commit
	pip install -e ".[dev]"
	pre-commit install

doctor: ## Check Python dependencies, native core, and local build tools
	python examples/check_env.py

test: ## Run tests with coverage
	pytest tests/ -v --cov=arnio --cov-report=term-missing

test-quick: ## Run tests without coverage (fast, pass/fail only)
	pytest tests/ -v

lint: ## Check linting
	python scripts/check_docs_utf8.py
	black --check --diff .
	ruff check . --extend-exclude "*.ipynb"
	mypy --config-file mypy.ini
	find cpp/ bindings/ -type f \( -name '*.cpp' -o -name '*.h' \) | xargs clang-format --dry-run --Werror

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
	python -c "import shutil, os, glob; [shutil.rmtree(p, ignore_errors=True) for p in ['dist', 'build', '.pytest_cache'] + glob.glob('*.egg-info') + glob.glob('**/__pycache__', recursive=True)]; [os.remove(f) for f in glob.glob('**/*.pyc', recursive=True) + glob.glob('arnio/_arnio_cpp*.pyd') + glob.glob('arnio/_arnio_cpp*.dll')]"
else
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache dist build *.egg-info
	find arnio -name "_arnio_cpp*.so" -delete
	find arnio -name "_arnio_cpp*.dylib" -delete
	find arnio -name "_arnio_cpp*.pyd" -delete
	find arnio -name "_arnio_cpp*.dll" -delete
endif
