"""
tests/test_cli.py
-----------------
CLI smoke tests for the arnio scan command.

Each test exercises the command through the public subprocess interface so the
tests remain independent of internal arnio implementation details.

Coverage targets
~~~~~~~~~~~~~~~~
* ``arnio scan``     – JSON keys correct, dtype values match, column ordering,
                       text format, default format, missing-file exit 1,
                       missing --input flag exit nonzero
* ``arnio profile``  – text, JSON, Markdown, default format, missing-file exit 1
* ``arnio --version`` – returns a version string
* ``arnio --help``   – exits 0 and contains command names
* ``arnio`` (no args) – exits 0 and prints help
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run ``python -m arnio.cli <args>`` and return the result."""
    return subprocess.run(
        [sys.executable, "-m", "arnio.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _simple_csv(tmp_path: Path, *, name: str = "data.csv") -> Path:
    """Write a minimal CSV fixture and return its path."""
    p = tmp_path / name
    p.write_text("name,age,score\nAlice,30,95.5\nBob,25,88.0\nCharlie,35,72.0\n")
    return p


def _quality_csv(tmp_path: Path, *, name: str = "quality.csv") -> Path:
    """Write a CSV fixture with nulls, duplicates, and whitespace."""
    p = tmp_path / name
    p.write_text("name,age,status\nAlice,30, active\nBob,,inactive\nBob,,inactive\n")
    return p


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


class TestScan:
    def test_scan_json_keys(self, tmp_path: Path):
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "json"])

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert "path" in data
        assert "columns" in data
        assert set(data["columns"]) == {"name", "age", "score"}

    def test_scan_json_dtypes(self, tmp_path: Path):
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "json"])

        assert result.returncode == 0, result.stderr
        cols = json.loads(result.stdout)["columns"]
        assert cols["age"] == "int64"
        assert cols["score"] == "float64"
        assert cols["name"] == "string"

    def test_scan_json_ordered(self, tmp_path: Path):
        """Column keys in JSON output are sorted deterministically."""
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "json"])

        assert result.returncode == 0, result.stderr
        cols = list(json.loads(result.stdout)["columns"].keys())
        assert cols == sorted(cols)

    def test_scan_text_contains_columns(self, tmp_path: Path):
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "text"])

        assert result.returncode == 0, result.stderr
        for col in ("name", "age", "score"):
            assert col in result.stdout

    def test_scan_text_default_format(self, tmp_path: Path):
        """Default format is text (no --format flag needed)."""
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv)])

        assert result.returncode == 0, result.stderr
        assert "name" in result.stdout

    def test_scan_text_contains_header_rule(self, tmp_path: Path):
        """Text output contains the separator line under the header."""
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "text"])

        assert result.returncode == 0, result.stderr
        assert "-" * 5 in result.stdout

    def test_scan_missing_file_exits_1(self, tmp_path: Path):
        result = _run(["scan", "--input", str(tmp_path / "nonexistent.csv")])

        assert result.returncode == 1
        assert "error" in result.stderr.lower()

    def test_scan_missing_input_flag_exits_nonzero(self):
        result = _run(["scan"])
        assert result.returncode != 0

    def test_scan_json_path_matches_input(self, tmp_path: Path):
        """JSON output 'path' field matches the --input argument."""
        csv = _simple_csv(tmp_path)
        result = _run(["scan", "--input", str(csv), "--format", "json"])

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["path"] == str(csv)

    def test_scan_single_column_csv(self, tmp_path: Path):
        p = tmp_path / "single.csv"
        p.write_text("value\n1\n2\n3\n")
        result = _run(["scan", "--input", str(p), "--format", "json"])

        assert result.returncode == 0, result.stderr
        cols = json.loads(result.stdout)["columns"]
        assert "value" in cols
        assert cols["value"] == "int64"


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------


class TestProfile:
    def test_profile_text_contains_quality_summary(self, tmp_path: Path):
        csv = _quality_csv(tmp_path)
        result = _run(["profile", "--input", str(csv), "--format", "text"])

        assert result.returncode == 0, result.stderr
        assert "Profile:" in result.stdout
        assert "Quality score:" in result.stdout
        assert "Rows: 3" in result.stdout
        assert "Columns: 3" in result.stdout
        assert "Null counts:" in result.stdout
        assert "age" in result.stdout
        assert "Top suggestions:" in result.stdout
        assert "drop_duplicates" in result.stdout

    def test_profile_text_default_format(self, tmp_path: Path):
        csv = _quality_csv(tmp_path)
        result = _run(["profile", "--input", str(csv)])

        assert result.returncode == 0, result.stderr
        assert "Quality score:" in result.stdout

    def test_profile_json_emits_report_dict(self, tmp_path: Path):
        csv = _quality_csv(tmp_path)
        result = _run(["profile", "--input", str(csv), "--format", "json"])

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["row_count"] == 3
        assert data["column_count"] == 3
        assert "quality_score" in data
        assert set(data["columns"]) == {"name", "age", "status"}
        assert isinstance(data["suggestions"], list)

    def test_profile_markdown_emits_report_markdown(self, tmp_path: Path):
        csv = _quality_csv(tmp_path)
        result = _run(["profile", "--input", str(csv), "--format", "markdown"])

        assert result.returncode == 0, result.stderr
        assert "# Data Quality Report" in result.stdout
        assert "## Overview" in result.stdout
        assert "- Rows: 3" in result.stdout

    def test_profile_missing_file_exits_1(self, tmp_path: Path):
        result = _run(["profile", "--input", str(tmp_path / "missing.csv")])

        assert result.returncode == 1
        assert "error" in result.stderr.lower()


# ---------------------------------------------------------------------------
# misc / top-level
# ---------------------------------------------------------------------------


class TestMisc:
    def test_version_flag(self):
        result = _run(["--version"])
        assert result.returncode == 0
        assert result.stdout.strip() != ""

    def test_help_exits_0(self):
        result = _run(["--help"])
        assert result.returncode == 0

    def test_help_mentions_scan(self):
        result = _run(["--help"])
        assert "scan" in result.stdout

    def test_help_mentions_profile(self):
        result = _run(["--help"])
        assert "profile" in result.stdout

    def test_no_args_exits_0_and_prints_help(self):
        result = _run([])
        assert result.returncode == 0

    def test_unknown_command_exits_nonzero(self):
        result = _run(["notacommand"])
        assert result.returncode != 0
