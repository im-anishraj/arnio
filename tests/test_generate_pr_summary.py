import pytest

from benchmarks.generate_pr_summary import (
    BASELINE_FILE,
    OUTPUT_FILE,
    RESULTS_FILE,
    generate_summary,
    parse_args,
)


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


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------


def test_parse_args_defaults():
    """No arguments → defaults match the module-level path constants."""
    args = parse_args([])

    assert args.results == RESULTS_FILE
    assert args.baseline == BASELINE_FILE
    assert args.output == OUTPUT_FILE


def test_parse_args_custom_paths():
    """Custom --results, --baseline, and --output are honoured."""
    args = parse_args(
        [
            "--results",
            "custom_results.json",
            "--baseline",
            "custom_baseline.json",
            "--output",
            "custom_output.md",
        ]
    )

    assert args.results == "custom_results.json"
    assert args.baseline == "custom_baseline.json"
    assert args.output == "custom_output.md"


def test_parse_args_help_exits_successfully(capsys):
    """--help must print usage information and exit with code 0."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--help"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--results" in captured.out
    assert "--baseline" in captured.out
    assert "--output" in captured.out


def test_parse_args_invalid_argument_fails():
    """Unknown arguments must cause argparse to exit with a non-zero code."""
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--unknown-flag"])

    assert exc_info.value.code != 0
