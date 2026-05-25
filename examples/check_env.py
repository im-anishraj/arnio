"""Environment validation utility for Arnio examples and benchmarks.

-----------------------------------------------------------------
This script verifies the installation of optional development dependencies and
prints a beautifully formatted status dashboard indicating which example scripts
can be run.
"""

from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

# Map import name to (install package name, description)
DEPENDENCIES = {
    "numpy": (
        "numpy",
        "Required for basic array operations and benchmark data generation.",
    ),
    "pandas": (
        "pandas",
        "Required for pandas DataFrame export and conversion examples.",
    ),
    "duckdb": (
        "duckdb",
        "Required for high-performance database integration examples.",
    ),
    "sklearn": (
        "scikit-learn",
        "Required for scikit-learn pipeline integration examples.",
    ),
    "pyarrow": (
        "pyarrow",
        "Required for Arrow export examples (pip install arnio[arrow]).",
    ),
    "pytest": ("pytest", "Required for running the integration and unit test suites."),
}


@dataclass(frozen=True)
class BuildToolCheck:
    """Status for a local build tool required by Arnio's native extension."""

    name: str
    command: str
    available: bool
    detail: str
    required: bool = True


# Map example script name to its list of optional dependency keys
EXAMPLES = {
    "basic_usage.py": [],
    "custom_step.py": ["pandas"],
    "arnio_with_numpy.py": ["numpy"],
    "arnio_with_pandas.py": ["pandas"],
    "arnio_with_duckdb.py": ["duckdb", "pandas"],
    "arnio_with_sklearn.py": ["sklearn", "pandas"],
    "sklearn_pipeline.py": ["sklearn", "pandas"],
    "auto_clean_tutorial.py": ["pandas"],
    "arnio_with_jsonl.py": ["pandas"],
    "arnio_with_arrow.py": ["pandas", "pyarrow"],
    "arnio_chunk_reading.py": ["pandas"],
    "schema_validation.py": ["pandas"],
    "check_env.py": [],
    "sales/recipe.py": ["pandas"],
    "customers/recipe.py": ["pandas"],
    "survey/recipe.py": ["pandas"],
    "logs/recipe.py": ["pandas"],
    "finance/recipe.py": ["pandas"],
}


def check_dependencies():
    """Verify presence of optional dependencies."""
    results = {}
    for lib in DEPENDENCIES:
        try:
            __import__(lib)
            results[lib] = (True, "Installed")
        except ImportError as exc:
            if exc.name and exc.name != lib:
                results[lib] = (False, f"Import failed: missing {exc.name}")
            else:
                results[lib] = (False, f"Not Installed ({lib})")
        except Exception as exc:  # pragma: no cover - defensive diagnostic path
            results[lib] = (False, f"Import failed: {type(exc).__name__}: {exc}")
    return results


def check_build_tools():
    """Check whether source-build tools are visible in the current shell."""
    system = platform.system()
    checks = [
        BuildToolCheck(
            name="CMake",
            command="cmake",
            available=shutil.which("cmake") is not None,
            detail="Required by scikit-build-core to configure the C++ extension.",
        ),
    ]

    if system == "Windows":
        checks.extend(
            [
                BuildToolCheck(
                    name="MSVC compiler",
                    command="cl",
                    available=shutil.which("cl") is not None,
                    detail=(
                        "Install Visual Studio Build Tools with Desktop development "
                        "with C++, then use a Developer Command Prompt."
                    ),
                ),
                BuildToolCheck(
                    name="NMake",
                    command="nmake",
                    available=shutil.which("nmake") is not None,
                    detail=(
                        "CMake may choose NMake on Windows; nmake must be on PATH "
                        "or another generator must be configured."
                    ),
                ),
            ]
        )
    else:
        checks.append(
            BuildToolCheck(
                name="C++ compiler",
                command="c++",
                available=any(
                    shutil.which(command) is not None
                    for command in ("c++", "g++", "clang++")
                ),
                detail="Required to compile Arnio's native C++ extension.",
            )
        )

    return checks


def detect_core_status():
    """Detect the native extension without importing the full arnio package."""
    if "arnio._core" in sys.modules:
        if sys.modules["arnio._core"] is None:
            return "Not Compiled (arnio._core unavailable)", False
        return "Available (C++ Accelerated)", True

    for entry in sys.path:
        package_dir = Path(entry or ".") / "arnio"
        if not package_dir.is_dir():
            continue

        for suffix in EXTENSION_SUFFIXES:
            if (package_dir / f"_arnio_cpp{suffix}").exists():
                return "Available (C++ Accelerated)", True

    return "Not Compiled (_arnio_cpp extension file not found)", False


def print_build_tool_status(build_tools):
    """Print build-tool checks and setup tips."""
    print("Build Toolchain Status:")
    blocked = False
    for check in build_tools:
        mark = "[OK]" if check.available else "[X]"
        required = "required" if check.required else "optional"
        print(f"  - {check.name:<15} {mark:<4} {check.command:<10} ({required})")
        if check.required and not check.available:
            blocked = True
            print(f"    Tip: {check.detail}")

    if blocked:
        print(
            '\n[BUILD BLOCKED] Source installs like `pip install -e ".[dev]"` '
            "may fail until the missing build tools are available."
        )
        if platform.system() == "Windows":
            print(
                "Windows fix: install Visual Studio Build Tools 2022 with the "
                "`Desktop development with C++` workload, then reopen an x64 "
                "Developer Command Prompt and retry."
            )
    else:
        print("\nBuild toolchain looks ready for a local native-extension build.")


def print_dashboard(results, build_tools=None):
    """Print a clean dashboard of the check results."""
    if build_tools is None:
        build_tools = check_build_tools()

    print("=" * 70)
    print(" ARNIO DEVELOPMENT ENVIRONMENT STATUS ")
    print("=" * 70)

    # Check Arnio C++ Core status
    core_status, core_available = detect_core_status()

    print(f"Arnio Core Module:  {core_status}")
    print(f"Python Version:     {sys.version.split()[0]}")
    print(f"Platform:           {platform.platform()}")
    print("-" * 70)
    print(f"{'Dependency':<15} | {'Status':<15} | {'Description'}")
    print("-" * 70)

    for lib, (status, status_str) in results.items():
        package, desc = DEPENDENCIES[lib]
        mark = "[OK]" if status else "[X]"
        print(f"{lib:<15} | {mark:<15} | {desc}")
        if not status:
            print(f"{'':<15} | {'':<15} | {status_str}")

    print("-" * 70)
    print_build_tool_status(build_tools)
    print("-" * 70)

    # Suggest runnable examples based on core status and packages found
    print("Runnable Examples Status:")
    for name, reqs in EXAMPLES.items():
        if not core_available:
            status = "[Missing arnio core]"
        else:
            missing_reqs = [r for r in reqs if not results[r][0]]
            if missing_reqs:
                status = f"[Missing {'/'.join(missing_reqs)}]"
            else:
                status = "[Ready]"
        print(f"  - {name:<26} : {status}")

    missing = []
    for lib, (status, _) in results.items():
        if not status:
            package, _ = DEPENDENCIES[lib]
            missing.append(package)

    if missing:
        print("\n[TIP] To install all missing optional dependencies, run:")
        print(f"  pip install {' '.join(missing)}")
    else:
        print(
            "\nAll optional dependencies are successfully installed! You are ready to go."
        )
    print("=" * 70)


def main():
    results = check_dependencies()
    print_dashboard(results)


if __name__ == "__main__":
    main()
