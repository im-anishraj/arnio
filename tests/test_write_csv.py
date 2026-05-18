"""Tests for write_csv functionality."""

from pathlib import Path

import pandas as pd
import pytest

import arnio as ar


class TestWriteCsv:
    def test_basic_write(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        assert Path(out).exists()

    def test_round_trip(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "out.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df1 = ar.to_pandas(frame)
        df2 = ar.to_pandas(frame2)
        pd.testing.assert_frame_equal(df1, df2)

    def test_quotes_escaped(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"name": ['say "hello"', "normal"]}))
        out = str(tmp_path / "quoted.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["name"].iloc[0] == 'say "hello"'

    def test_comma_in_field(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Smith, John", "Jane"]}))
        out = str(tmp_path / "comma.csv")
        ar.write_csv(frame, out)
        frame2 = ar.read_csv(out)
        df = ar.to_pandas(frame2)
        assert df["name"].iloc[0] == "Smith, John"

    def test_write_no_header(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = str(tmp_path / "noheader.csv")
        ar.write_csv(frame, out, write_header=False)
        content = Path(out).read_text()
        assert "name" not in content.splitlines()[0]

    def test_custom_delimiter(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}))
        out = str(tmp_path / "out.tsv")
        ar.write_csv(frame, out, delimiter="\t")
        content = Path(out).read_text()
        assert "\t" in content

    def test_unsupported_extension(self, tmp_path):
        frame = ar.from_pandas(pd.DataFrame({"a": [1]}))
        with pytest.raises(ValueError, match="Unsupported file format"):
            ar.write_csv(frame, str(tmp_path / "out.json"))

    def test_pathlike_input(self, tmp_path, sample_csv):
        frame = ar.read_csv(sample_csv)
        out = tmp_path / "out.csv"
        ar.write_csv(frame, out)
        assert out.exists()