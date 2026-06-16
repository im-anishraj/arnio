"""Unit tests for auto_clean utility focusing on extreme edge cases."""

import pandas as pd

import arnio as ar


class TestAutoCleanEdgeCases:
    def test_auto_clean_entirely_clean_data(self):
        """auto_clean on perfectly clean data should suggest no mutations and return same content."""
        df = pd.DataFrame(
            {
                "name": ["Alice", "Bob", "Charlie"],
                "age": [30, 25, 35],
                "score": [100.0, 95.0, 98.0],
            }
        )
        frame = ar.from_pandas(df)
        cleaned, explanation = ar.auto_clean(frame, explain=True)

        # Check that it returns an ArFrame
        assert isinstance(cleaned, ar.ArFrame)
        # Perfect data shouldn't need heavy/lossy cleaning mutations
        res_df = ar.to_pandas(cleaned)
        assert res_df.shape == (3, 3)
        assert list(res_df["name"]) == ["Alice", "Bob", "Charlie"]
        # Explanation is a CleanExplanation when explain=True
        assert isinstance(explanation, ar.CleanExplanation)
        assert explanation.steps == []

    def test_auto_clean_entirely_empty_data(self):
        """auto_clean on entirely empty DataFrame (zero rows, zero columns) handles gracefully."""
        df = pd.DataFrame()
        frame = ar.from_pandas(df)

        # Should not crash and return empty frame
        cleaned = ar.auto_clean(frame)
        res_df = ar.to_pandas(cleaned)
        assert res_df.empty
        assert res_df.shape == (0, 0)

    def test_auto_clean_extremely_skewed_outliers(self):
        """auto_clean handles extremely skewed columns with outliers or missing values correctly."""
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "skewed_val": [10.0, 12.0, 11.0, 10000.0, 10.5],
                "mostly_null": [None, None, "val", None, None],
            }
        )
        frame = ar.from_pandas(df)

        # auto_clean should run without errors and produce a valid report
        result = ar.auto_clean(frame, return_report=True)
        if isinstance(result, tuple):
            cleaned, report = result
        else:
            cleaned = result

        assert isinstance(cleaned, ar.ArFrame)
        assert isinstance(report, ar.DataQualityReport)

        # Verify the report detected the skewed and mostly-null columns
        col_names = list(report.columns.keys())
        assert "skewed_val" in col_names
        assert "mostly_null" in col_names

        res_df = ar.to_pandas(cleaned)
        assert len(res_df) == 5
