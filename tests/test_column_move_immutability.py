"""Immutability regression tests for the move-unmodified-columns optimization.

strip_whitespace and normalize_case now move unmodified columns out of an
internal frame clone instead of deep-copying them.  These tests verify that
the source frame is never mutated through shared storage and that the
optimization produces identical results to the previous deep-copy path.
"""

from __future__ import annotations

import pandas as pd

import arnio as ar


class TestStripWhitespaceImmutability:
    """Source frame must be unchanged after strip_whitespace."""

    def test_source_string_columns_unchanged(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {"name": ["  Alice  ", "  Bob  "], "city": ["  NYC  ", "  LA  "]}
            )
        )
        original_names = ar.to_pandas(frame)["name"].tolist()
        original_cities = ar.to_pandas(frame)["city"].tolist()

        ar.strip_whitespace(frame)

        assert ar.to_pandas(frame)["name"].tolist() == original_names
        assert ar.to_pandas(frame)["city"].tolist() == original_cities

    def test_source_numeric_columns_unchanged(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["  Alice  "], "score": [42], "ratio": [3.14]})
        )
        original_score = ar.to_pandas(frame)["score"].tolist()
        original_ratio = ar.to_pandas(frame)["ratio"].tolist()

        ar.strip_whitespace(frame)

        assert ar.to_pandas(frame)["score"].tolist() == original_score
        assert ar.to_pandas(frame)["ratio"].tolist() == original_ratio

    def test_result_is_new_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["  Alice  "]}))
        result = ar.strip_whitespace(frame)
        # Result must be a different object
        assert result is not frame

    def test_result_string_columns_are_trimmed(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["  Alice  ", "  Bob  "], "score": [1, 2]})
        )
        result = ar.strip_whitespace(frame)
        df = ar.to_pandas(result)
        assert df["name"].tolist() == ["Alice", "Bob"]

    def test_result_numeric_columns_unchanged(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["  Alice  "], "score": [99], "ratio": [1.5]})
        )
        result = ar.strip_whitespace(frame)
        df = ar.to_pandas(result)
        assert df["score"].tolist() == [99]
        assert df["ratio"].tolist() == [1.5]

    def test_multiple_calls_on_same_frame_consistent(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["  Alice  ", "  Bob  "], "score": [1, 2]})
        )
        result1 = ar.strip_whitespace(frame)
        result2 = ar.strip_whitespace(frame)
        df1 = ar.to_pandas(result1)
        df2 = ar.to_pandas(result2)
        assert df1["name"].tolist() == df2["name"].tolist()
        assert df1["score"].tolist() == df2["score"].tolist()

    def test_wide_frame_unmodified_columns_preserved(self):
        """20-column frame: only 2 string cols modified, 18 int cols untouched."""
        import numpy as np

        rng = np.random.default_rng(0)
        n = 1000
        df = pd.DataFrame(
            {
                "name": [f"  user_{i}  " for i in range(n)],
                "city": [f"  city_{i}  " for i in range(n)],
                **{
                    f"col_{i}": rng.integers(0, 100, size=n).tolist() for i in range(18)
                },
            }
        )
        frame = ar.from_pandas(df)
        original_col0 = ar.to_pandas(frame)["col_0"].tolist()

        result = ar.strip_whitespace(frame)

        # Source unchanged
        assert ar.to_pandas(frame)["col_0"].tolist() == original_col0
        # Result string cols trimmed
        assert ar.to_pandas(result)["name"].iloc[0] == "user_0"
        # Result numeric cols identical
        assert ar.to_pandas(result)["col_0"].tolist() == original_col0


class TestNormalizeCaseImmutability:
    """Source frame must be unchanged after normalize_case."""

    def test_source_string_columns_unchanged(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"]}))
        original = ar.to_pandas(frame)["name"].tolist()

        ar.normalize_case(frame, case_type="lower")

        assert ar.to_pandas(frame)["name"].tolist() == original

    def test_source_numeric_columns_unchanged(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice"], "score": [42], "ratio": [3.14]})
        )
        original_score = ar.to_pandas(frame)["score"].tolist()

        ar.normalize_case(frame, case_type="upper")

        assert ar.to_pandas(frame)["score"].tolist() == original_score

    def test_result_is_new_frame(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice"]}))
        result = ar.normalize_case(frame, case_type="lower")
        assert result is not frame

    def test_result_string_columns_lowercased(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice", "BOB"], "score": [1, 2]})
        )
        result = ar.normalize_case(frame, case_type="lower")
        df = ar.to_pandas(result)
        assert df["name"].tolist() == ["alice", "bob"]

    def test_result_numeric_columns_unchanged(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice"], "score": [99], "ratio": [1.5]})
        )
        result = ar.normalize_case(frame, case_type="upper")
        df = ar.to_pandas(result)
        assert df["score"].tolist() == [99]
        assert df["ratio"].tolist() == [1.5]

    def test_multiple_calls_on_same_frame_consistent(self):
        frame = ar.from_pandas(
            pd.DataFrame({"name": ["Alice", "BOB"], "score": [1, 2]})
        )
        result1 = ar.normalize_case(frame, case_type="lower")
        result2 = ar.normalize_case(frame, case_type="lower")
        assert (
            ar.to_pandas(result1)["name"].tolist()
            == ar.to_pandas(result2)["name"].tolist()
        )

    def test_pipeline_does_not_mutate_source(self):
        """5-step pipeline must not mutate the original frame."""
        import numpy as np

        rng = np.random.default_rng(1)
        n = 500
        df = pd.DataFrame(
            {
                "name": [f"  User_{i}  " for i in range(n)],
                "city": [f"  City_{i}  " for i in range(n)],
                **{
                    f"col_{i}": rng.integers(0, 100, size=n).tolist() for i in range(18)
                },
            }
        )
        frame = ar.from_pandas(df)
        original_name_0 = ar.to_pandas(frame)["name"].iloc[0]
        original_col0 = ar.to_pandas(frame)["col_0"].tolist()

        ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "lower"}),
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "upper"}),
                ("strip_whitespace",),
            ],
        )

        # Source frame must be completely unchanged
        assert ar.to_pandas(frame)["name"].iloc[0] == original_name_0
        assert ar.to_pandas(frame)["col_0"].tolist() == original_col0
