import subprocess
import sys


def test_public_lazy_attributes_resolve():
    """Verify that accessing public attributes resolves correctly via lazy loading."""
    import arnio

    assert arnio.read_csv is not None
    assert arnio.to_pandas is not None
    assert arnio.profile is not None


def test_lazy_import_performance_audit():
    """Verify in a clean subprocess that importing arnio does not eagerly load pandas or numpy."""
    code = """
import sys
import arnio

# If arnio eagerly imports dependencies at runtime, they will appear in sys.modules
if "pandas" in sys.modules or "numpy" in sys.modules:
    sys.exit(1)
sys.exit(0)
    """
    result = subprocess.run([sys.executable, "-c", code], capture_output=True)
    assert (
        result.returncode == 0
    ), "Regression Error: Heavy dependencies (pandas/numpy) were loaded during 'import arnio'!"
