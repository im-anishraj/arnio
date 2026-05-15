import subprocess
import sys


def test_public_lazy_attributes_resolve():
    """Verify that every single public name advertised in __all__ resolves correctly."""
    import arnio

    # This dynamically loops and tests every export—including combine_columns!
    for attribute_name in arnio.__all__:
        if attribute_name == "__version__":
            continue

        assert hasattr(
            arnio, attribute_name
        ), f"Lazy attribute '{attribute_name}' failed to resolve!"


def test_lazy_import_performance_audit():
    """Verify in a clean subprocess that importing arnio does not eagerly load pandas or numpy."""
    code = """
import sys
import arnio

if "pandas" in sys.modules or "numpy" in sys.modules:
    sys.exit(1)
sys.exit(0)
    """
    result = subprocess.run([sys.executable, "-c", code], capture_output=True)
    assert (
        result.returncode == 0
    ), "Regression Error: Heavy dependencies (pandas/numpy) were loaded during 'import arnio'!"
