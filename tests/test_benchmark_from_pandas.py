import os
import subprocess
import sys

def test_benchmark_dry_run():
    env = os.environ.copy()
    env["ARNIO_BENCHMARK_DRY_RUN"] = "1"
    result = subprocess.run(
        [sys.executable, "benchmarks/benchmark_from_pandas_memory.py"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr