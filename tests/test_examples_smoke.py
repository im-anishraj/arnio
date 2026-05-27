"""Integration tests to ensure all Python example scripts run successfully."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

# Check if the C++ extension is compiled
try:
    import arnio._core  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

REPO_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


@dataclass(frozen=True)
class ExampleSpec:
    """Runnable example under examples/ with optional deps and working directory."""

    path: str
    deps: tuple[str, ...] = ()
    cwd: str = "."


# Explicit allowlist of CI-safe examples, optional dependencies, and run directory.
# cwd is relative to REPO_ROOT (repo root for top-level scripts; subdirs for recipes).
EXAMPLE_SPECS: tuple[ExampleSpec, ...] = (
    ExampleSpec("basic_usage.py", deps=("pandas",)),
    ExampleSpec("custom_step.py", deps=("pandas",)),
    ExampleSpec("auto_clean_tutorial.py", deps=("pandas",)),
    ExampleSpec("arnio_with_pandas.py", deps=("pandas",)),
    ExampleSpec("arnio_with_numpy.py", deps=("numpy", "pandas")),
    ExampleSpec("arnio_with_duckdb.py", deps=("duckdb", "pandas")),
    ExampleSpec("arnio_with_sklearn.py", deps=("sklearn", "pandas")),
    ExampleSpec("sklearn_pipeline.py", deps=("sklearn", "pandas")),
    ExampleSpec("arnio_with_jsonl.py", deps=("pandas",)),
    ExampleSpec("arnio_with_arrow.py", deps=("pandas", "pyarrow")),
    ExampleSpec("arnio_chunk_reading.py", deps=("pandas",)),
    ExampleSpec("schema_validation.py", deps=("pandas",)),
    ExampleSpec("sales/recipe.py", deps=("pandas",), cwd="examples/sales"),
    ExampleSpec("customers/recipe.py", deps=("pandas",), cwd="examples/customers"),
    ExampleSpec("survey/recipe.py", deps=("pandas",), cwd="examples/survey"),
    ExampleSpec("logs/recipe.py", deps=("pandas",), cwd="examples/logs"),
    ExampleSpec("finance/recipe.py", deps=("pandas",), cwd="examples/finance"),
)

# Scripts intentionally excluded from subprocess smoke (with reason for maintainers).
EXCLUDED_EXAMPLES: dict[str, str] = {
    "check_env.py": ("Dashboard utility; behavior covered by tests/test_check_env.py."),
}


def _discover_example_scripts() -> set[str]:
    """Return relative paths of all .py files under examples/."""
    if not EXAMPLES_DIR.exists():
        return set()
    return {
        path.relative_to(EXAMPLES_DIR).as_posix() for path in EXAMPLES_DIR.rglob("*.py")
    }


def get_example_specs() -> list[ExampleSpec]:
    """Return allowlisted specs whose script files exist."""
    specs: list[ExampleSpec] = []
    for spec in EXAMPLE_SPECS:
        if (EXAMPLES_DIR / spec.path).exists():
            specs.append(spec)
    return specs


def _subprocess_env() -> dict[str, str]:
    """Ensure subprocesses can import the in-tree arnio package (editable or not)."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(REPO_ROOT) if not existing else f"{REPO_ROOT}{os.pathsep}{existing}"
    )
    return env


def has_dependencies(deps: tuple[str, ...]) -> bool:
    """Check if all required dependencies are installed."""
    for dep in deps:
        try:
            if importlib.util.find_spec(dep) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


def test_all_example_scripts_are_accounted_for() -> None:
    """Fail when a new examples/**/*.py is not allowlisted or explicitly excluded."""
    discovered = _discover_example_scripts()
    allowlisted = {spec.path for spec in EXAMPLE_SPECS}
    excluded = set(EXCLUDED_EXAMPLES)
    missing = discovered - allowlisted - excluded
    extra = allowlisted - discovered
    assert not missing, (
        "New example script(s) missing from EXAMPLE_SPECS or EXCLUDED_EXAMPLES: "
        f"{sorted(missing)}"
    )
    assert not extra, (
        "EXAMPLE_SPECS lists script(s) that do not exist: " f"{sorted(extra)}"
    )


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("spec", get_example_specs(), ids=lambda s: s.path)
def test_example_script_runs_successfully(spec: ExampleSpec) -> None:
    """Run an example python script and verify that it exits with code 0."""
    script_path = EXAMPLES_DIR / spec.path
    if not has_dependencies(spec.deps):
        pytest.skip(
            f"Skipping {spec.path} due to missing optional dependencies: {list(spec.deps)}"
        )

    run_cwd = REPO_ROOT / spec.cwd
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(run_cwd),
            env=_subprocess_env(),
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(
            f"Example {spec.path} timed out after 30 seconds.\nOutput so far:\n{e.stdout}"
        )

    assert result.returncode == 0, (
        f"Example {spec.path} failed with return code {result.returncode}.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )
