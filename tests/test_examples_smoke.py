"""Integration tests to ensure all Python example scripts run successfully."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# Check if the C++ extension is compiled
try:
    import arnio._core  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

# Explicit allowlist of CI-safe examples and their optional dependencies
CI_SAFE_EXAMPLES = {
    "basic_usage.py": ["pandas"],
    "custom_step.py": ["pandas"],
    "auto_clean_tutorial.py": ["pandas"],
    "arnio_with_pandas.py": ["pandas"],
    "arnio_with_numpy.py": ["numpy", "pandas"],
    "arnio_with_duckdb.py": ["duckdb", "pandas"],
    "arnio_with_sklearn.py": ["sklearn", "pandas"],
    "sklearn_pipeline.py": ["sklearn", "pandas"],
    "arnio_with_jsonl.py": ["pandas"],
}


def get_example_scripts():
    """Locate all runnable python files in the examples directory that are CI-safe."""
    if not EXAMPLES_DIR.exists():
        return []
    
    scripts = []
    for name in sorted(CI_SAFE_EXAMPLES.keys()):
        script_path = EXAMPLES_DIR / name
        if script_path.exists():
            scripts.append(script_path)
    return scripts


def has_dependencies(deps):
    """Check if all required dependencies are installed."""
    for dep in deps:
        try:
            if importlib.util.find_spec(dep) is None:
                return False
        except (ImportError, ValueError):
            return False
    return True


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("script_path", get_example_scripts(), ids=lambda p: p.name)
def test_example_script_runs_successfully(script_path):
    """Run an example python script and verify that it exits with code 0."""
    # Check if optional dependencies are missing
    required_deps = CI_SAFE_EXAMPLES.get(script_path.name, [])
    if not has_dependencies(required_deps):
        pytest.skip(f"Skipping {script_path.name} due to missing optional dependencies: {required_deps}")

    # Run the script in a subprocess using the same python interpreter with a timeout
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(EXAMPLES_DIR.parent),
            timeout=15,  # Add timeout to prevent hangs in CI
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"Example {script_path.name} timed out after 15 seconds.\nOutput so far:\n{e.stdout}")

    assert result.returncode == 0, (
        f"Example {script_path.name} failed with return code {result.returncode}.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )

