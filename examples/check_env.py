"""Environment validation utility for Arnio examples and benchmarks.

-----------------------------------------------------------------
This script verifies the installation of optional development dependencies and
prints a beautifully formatted status dashboard indicating which example scripts
can be run.
"""

import sys

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
    "pytest": ("pytest", "Required for running the integration and unit test suites."),
    "pyarrow": (
        "pyarrow",
        "Required for Arrow integration examples.",
    ),
}


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
    "arnio_chunk_reading.py": ["pandas"],
    "arnio_with_arrow.py": ["pyarrow", "pandas"],
    "schema_validation.py": [],
}


def check_dependencies():
    """Verify presence of optional dependencies."""
    results = {}
    for lib in DEPENDENCIES:
        try:
            __import__(lib)
            results[lib] = (True, "Installed")
        except ImportError:
            results[lib] = (False, "Not Installed")
    return results


def print_dashboard(results):
    """Print a clean dashboard of the check results."""
    print("=" * 70)
    print(" ARNIO DEVELOPMENT ENVIRONMENT STATUS ")
    print("=" * 70)

    # Check Arnio C++ Core status
    core_available = False
    try:
        import arnio._core  # noqa: F401

        core_status = "Available (C++ Accelerated)"
        core_available = True
    except ImportError:
        core_status = "Not Compiled (Pure-Python Mode)"

    print(f"Arnio Core Module:  {core_status}")
    print(f"Python Version:     {sys.version.split()[0]}")
    print("-" * 70)
    print(f"{'Dependency':<15} | {'Status':<15} | {'Description'}")
    print("-" * 70)

    for lib, (status, _) in results.items():
        package, desc = DEPENDENCIES[lib]
        mark = "[OK]" if status else "[X]"
        print(f"{lib:<15} | {mark:<15} | {desc}")

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
