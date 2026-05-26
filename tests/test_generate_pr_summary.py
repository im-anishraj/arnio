from benchmarks.generate_pr_summary import generate_summary


def test_generate_summary_handles_missing_baseline():
    """Should gracefully handle missing baseline data."""

    results = {
        "Case A": {
            "arnio_exec_time": 10.0,
        }
    }

    summary = generate_summary(results, {})

    assert "No comparable baseline data available." in summary


def test_generate_summary_formats_regression_and_improvement():
    """Should format slower/faster benchmark changes correctly."""

    results = {
        "Case A": {
            "arnio_exec_time": 12.0,
        },
        "Case B": {
            "arnio_exec_time": 8.0,
        },
    }

    baseline = {
        "Case A": {
            "arnio_exec_time": 10.0,
        },
        "Case B": {
            "arnio_exec_time": 10.0,
        },
    }

    summary = generate_summary(results, baseline)

    assert "+20.0% slower" in summary
    assert "20.0% faster" in summary


def test_generate_summary_handles_missing_case_baseline():
    """Should show missing baseline rows cleanly."""

    results = {
        "Case A": {
            "arnio_exec_time": 10.0,
        }
    }

    baseline = {}

    summary = generate_summary(results, baseline)

    assert "No comparable baseline data available." in summary
