"""Integration tests to ensure all Python example scripts run successfully."""

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


def get_example_scripts():
    """Locate all runnable python files in the examples directory."""
    if not EXAMPLES_DIR.exists():
        return []
    # Find all .py files directly inside examples/
    scripts = sorted(
        [
            p
            for p in EXAMPLES_DIR.glob("*.py")
            if p.name != "__init__.py" and p.name != "check_env.py"
        ]
    )
    return scripts


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("script_path", get_example_scripts(), ids=lambda p: p.name)
def test_example_script_runs_successfully(script_path):
    """Run an example python script and verify that it exits with code 0."""
    # Run the script in a subprocess using the same python interpreter
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(EXAMPLES_DIR.parent),
    )

    assert result.returncode == 0, (
        f"Example {script_path.name} failed with return code {result.returncode}.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )
