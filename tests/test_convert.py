"""Tests for pandas conversion."""

import pandas as pd

import arnio as ar


class TestToPandas:
    def test_basic_conversion(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        df = ar.to_pandas(frame)
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (3, 4)
        assert list(df.columns) == ["name", "age", "email", "active"]

    def test_types_preserved(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        df = ar.to_pandas(frame)
        assert pd.api.types.is_integer_dtype(df["age"])

    def test_nulls_converted(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        df = ar.to_pandas(frame)
        assert df.isna().any().any()  # Should have some NaN/NA values

    def test_to_python_list_with_nulls(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", None, "Charlie"],
                    "score": [95, None, 88],
                    "active": [True, None, False],
                },
                dtype=object,
            )
        )

        assert frame._frame.column_by_name("name").to_python_list() == [
            "Alice",
            None,
            "Charlie",
        ]
        assert frame._frame.column_by_name("score").to_python_list() == [95, None, 88]
        assert frame._frame.column_by_name("active").to_python_list() == [
            True,
            None,
            False,
        ]


class TestFromPandas:
    def test_basic_roundtrip(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        df = ar.to_pandas(frame)
        frame2 = ar.from_pandas(df)
        assert isinstance(frame2, ar.ArFrame)
        assert frame2.shape == frame.shape
        assert frame2.columns == frame.columns

    def test_from_constructed_df(self):
        df = pd.DataFrame(
            {
                "x": [1, 2, 3],
                "y": [1.5, 2.5, 3.5],
                "z": ["a", "b", "c"],
            }
        )
        frame = ar.from_pandas(df)
        assert frame.shape == (3, 3)
        assert "x" in frame.columns
        assert "y" in frame.columns
        assert "z" in frame.columns

    def test_roundtrip_values(self):
        df = pd.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "score": [95.5, 87.0],
            }
        )
        frame = ar.from_pandas(df)
        df2 = ar.to_pandas(frame)
        assert list(df2["name"]) == ["Alice", "Bob"]
        assert list(df2["score"]) == [95.5, 87.0]

    def test_from_pandas_nested_data(self):
        import pytest

        df_list = pd.DataFrame({"a": [[1, 2], [3, 4]]})
        with pytest.raises(TypeError, match="Unsupported nested/complex type"):
            ar.from_pandas(df_list)

        df_dict = pd.DataFrame({"a": [{"x": 1}, {"y": 2}]})
        with pytest.raises(TypeError, match="Unsupported nested/complex type"):
            ar.from_pandas(df_dict)

    def test_from_pandas_mixed_object_column(self):
        df = pd.DataFrame({"a": [1, "x", 3]}, dtype=object)
        frame = ar.from_pandas(df)
        df2 = ar.to_pandas(frame)

        assert list(df2["a"]) == ["1", "x", "3"]

    def test_from_pandas_unsupported_scalar_object_column(self):
        timestamp = pd.Timestamp("2026-05-14 12:30:00")
        frame = ar.from_pandas(pd.DataFrame({"created_at": [timestamp]}))

        assert frame._frame.column_by_name("created_at").to_python_list() == [
            str(timestamp)
        ]
