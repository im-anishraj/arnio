"""Integration tests to ensure all Python example scripts run successfully."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from examples.example_registry import EXAMPLE_ENTRIES, EXCLUDED_EXAMPLES, ExampleEntry

# Check if the C++ extension is compiled
try:
    import arnio._core  # noqa: F401

    HAS_CORE = True
except ImportError:
    HAS_CORE = False

REPO_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"


def _discover_example_scripts() -> set[str]:
    """Return relative paths of all .py files under examples/."""
    if not EXAMPLES_DIR.exists():
        return set()
    return {
        path.relative_to(EXAMPLES_DIR).as_posix() for path in EXAMPLES_DIR.rglob("*.py")
    }


def get_example_specs() -> list[ExampleEntry]:
    """Return allowlisted specs whose script files exist."""
    specs: list[ExampleEntry] = []
    for spec in EXAMPLE_ENTRIES:
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


def test_example_entries_preserve_smoke_dependency_overrides() -> None:
    by_path = {entry.path: entry for entry in EXAMPLE_ENTRIES}
    assert by_path["basic_usage.py"].deps_for_smoke == ("pandas",)
    assert by_path["basic_usage.py"].deps == ()
    assert by_path["arnio_with_numpy.py"].deps_for_smoke == ("numpy", "pandas")
    assert by_path["arnio_with_numpy.py"].deps == ("numpy",)


def test_all_example_scripts_are_accounted_for() -> None:
    """Fail when a new examples/**/*.py is not allowlisted or explicitly excluded."""
    if not EXAMPLES_DIR.exists():
        pytest.skip("examples/ directory is not present in this test environment.")

    discovered = _discover_example_scripts()
    allowlisted = {spec.path for spec in EXAMPLE_ENTRIES}
    excluded = set(EXCLUDED_EXAMPLES)
    missing = discovered - allowlisted - excluded
    extra = allowlisted - discovered
    assert not missing, (
        "New example script(s) missing from EXAMPLE_ENTRIES or EXCLUDED_EXAMPLES: "
        f"{sorted(missing)}"
    )
    assert not extra, (
        "EXAMPLE_ENTRIES lists script(s) that do not exist: " f"{sorted(extra)}"
    )


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
@pytest.mark.parametrize("spec", get_example_specs(), ids=lambda s: s.path)
def test_example_script_runs_successfully(spec: ExampleEntry) -> None:
    """Run an example python script and verify that it exits with code 0."""
    script_path = EXAMPLES_DIR / spec.path
    deps = spec.deps_for_smoke
    if not has_dependencies(deps):
        pytest.skip(
            f"Skipping {spec.path} due to missing optional dependencies: {list(deps)}"
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


@pytest.mark.skipif(not HAS_CORE, reason="Arnio C++ extension is not compiled.")
def test_pytest_example_custom_step_with_tests() -> None:
    """Run the pytest-oriented custom step example via pytest subprocess."""
    script = EXAMPLES_DIR / "custom_step_with_tests.py"
    if not script.exists():
        pytest.skip("custom_step_with_tests.py not present in examples/.")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(script), "-q"],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
        timeout=60,
    )
    assert result.returncode == 0, (
        f"custom_step_with_tests.py failed.\n"
        f"Stdout:\n{result.stdout}\n"
        f"Stderr:\n{result.stderr}"
    )
