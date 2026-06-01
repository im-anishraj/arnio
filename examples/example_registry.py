"""Canonical metadata for runnable Python scripts under examples/."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleEntry:
    """Shared metadata consumed by check_env and smoke tests."""

    path: str
    deps: tuple[str, ...] = ()
    cwd: str = "."
    smoke_deps: tuple[str, ...] | None = None

    @property
    def deps_for_smoke(self) -> tuple[str, ...]:
        """Dependency set used by subprocess smoke tests."""
        if self.smoke_deps is None:
            return self.deps
        return self.smoke_deps


# Single source of truth for runnable examples and optional dependencies.
# deps are used by examples/check_env.py.
# smoke_deps is an optional override for tests/test_examples_smoke.py.
EXAMPLE_ENTRIES: tuple[ExampleEntry, ...] = (
    ExampleEntry("basic_usage.py", smoke_deps=("pandas",)),
    ExampleEntry("custom_step.py", deps=("pandas",)),
    ExampleEntry("auto_clean_tutorial.py", deps=("pandas",)),
    ExampleEntry("arnio_with_pandas.py", deps=("pandas",)),
    ExampleEntry(
        "arnio_with_numpy.py", deps=("numpy",), smoke_deps=("numpy", "pandas")
    ),
    ExampleEntry("arnio_with_duckdb.py", deps=("duckdb", "pandas")),
    ExampleEntry("arnio_with_sklearn.py", deps=("sklearn", "pandas")),
    ExampleEntry("sklearn_pipeline.py", deps=("sklearn", "pandas")),
    ExampleEntry("arnio_with_jsonl.py", deps=("pandas",)),
    ExampleEntry("arnio_with_arrow.py", deps=("pandas", "pyarrow")),
    ExampleEntry("arnio_chunk_reading.py", deps=("pandas",)),
    ExampleEntry("schema_validation.py", deps=("pandas",)),
    ExampleEntry("sales/recipe.py", deps=("pandas",), cwd="examples/sales"),
    ExampleEntry("customers/recipe.py", deps=("pandas",), cwd="examples/customers"),
    ExampleEntry("survey/recipe.py", deps=("pandas",), cwd="examples/survey"),
    ExampleEntry("logs/recipe.py", deps=("pandas",), cwd="examples/logs"),
    ExampleEntry("finance/recipe.py", deps=("pandas",), cwd="examples/finance"),
)

# Scripts intentionally excluded from subprocess smoke (with maintainer reason).
EXCLUDED_EXAMPLES: dict[str, str] = {
    "check_env.py": "Dashboard utility; behavior covered by tests/test_check_env.py.",
    "example_registry.py": "Shared metadata module consumed by check_env and tests.",
    "custom_step_with_tests.py": (
        "Pytest example module; intended to be run via pytest, not subprocess smoke."
    ),
}


def check_env_examples() -> dict[str, list[str]]:
    """Return the check_env dashboard view: path -> dependency list."""
    return {entry.path: list(entry.deps) for entry in EXAMPLE_ENTRIES}
