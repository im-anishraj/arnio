from benchmarks.benchmark_vs_pandas import calculate_regression, load_baseline


def test_calculate_regression():
    regression = calculate_regression(110, 100)
    assert regression == 10


def test_load_baseline_missing_file(monkeypatch):
    monkeypatch.setattr(
        "benchmarks.benchmark_vs_pandas.BASELINE_FILE",
        "missing_baseline.json",
    )

    baseline = load_baseline()

    assert baseline == {}
