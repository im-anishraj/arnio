"""Tests for pandas conversion."""

import pandas as pd
import pytest

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

    def test_nullable_int64_roundtrip_mixed_values(self):
        df = pd.DataFrame({"id": pd.Series([1, pd.NA, 3], dtype=pd.Int64Dtype())})

        result = ar.to_pandas(ar.from_pandas(df))

        pd.testing.assert_series_equal(result["id"], df["id"])

    def test_nullable_int64_roundtrip_all_nulls(self):
        df = pd.DataFrame({"id": pd.Series([pd.NA, pd.NA], dtype=pd.Int64Dtype())})

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert frame.dtypes["id"] == "int64"
        assert str(result["id"].dtype) == "Int64"
        assert result["id"].isna().tolist() == [True, True]

    def test_nullable_int64_roundtrip_without_nulls(self):
        df = pd.DataFrame({"id": pd.Series([1, 2, 3], dtype=pd.Int64Dtype())})

        result = ar.to_pandas(ar.from_pandas(df))

        pd.testing.assert_series_equal(result["id"], df["id"])

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

        df_list = pd.DataFrame({"a": [[1, 2], [3, 4]]})
        with pytest.raises(
            TypeError, match="Column 'a' contains unsupported nested value"
        ):
            ar.from_pandas(df_list)

        df_dict = pd.DataFrame({"a": [{"x": 1}, {"y": 2}]})
        with pytest.raises(
            TypeError, match="Column 'a' contains unsupported nested value"
        ):
            ar.from_pandas(df_dict)

    def test_from_pandas_mixed_object_column(self):
        df = pd.DataFrame({"a": [1, "x", 3]}, dtype=object)
        frame = ar.from_pandas(df)
        df2 = ar.to_pandas(frame)

        assert list(df2["a"]) == ["1", "x", "3"]

    def test_from_pandas_mixed_object_column_with_nested_value(self):

        df = pd.DataFrame({"mixed": [1, "hello", {"a": 1}]}, dtype=object)

        with pytest.raises(
            TypeError,
            match="Column 'mixed' contains unsupported nested value",
        ):
            ar.from_pandas(df)

    def test_from_pandas_unsupported_scalar_object_column(self):
        timestamp = pd.Timestamp("2026-05-14 12:30:00")
        frame = ar.from_pandas(pd.DataFrame({"created_at": [timestamp]}))

        assert frame._frame.column_by_name("created_at").to_python_list() == [
            str(timestamp)
        ]

    def test_from_pandas_preserves_column_order(self):
        df = pd.DataFrame(
            {
                "name": ["Alice"],
                "age": [20],
                "city": ["Delhi"],
            }
        )

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert list(result.columns) == ["name", "age", "city"]

    def test_cleaning_preserves_column_order(self):
        df = pd.DataFrame(
            {
                "name": [" Alice "],
                "age": [20],
                "city": ["Delhi"],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.strip_whitespace(frame)
        result_df = ar.to_pandas(result)

        assert list(result_df.columns) == ["name", "age", "city"]

    def test_pipeline_preserves_column_order(self):
        df = pd.DataFrame(
            {
                "name": [" Alice "],
                "age": [20],
                "city": ["Delhi"],
            }
        )

        frame = ar.from_pandas(df)

        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "lower"}),
            ],
        )

        result_df = ar.to_pandas(result)

        assert list(result_df.columns) == ["name", "age", "city"]

    def test_bool_null_mask_roundtrip(self):
        df = pd.DataFrame(
            {
                "flag": pd.Series(
                    [True, False, pd.NA],
                    dtype="boolean",
                )
            }
        )

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert list(result["flag"]) == [True, False, pd.NA]


class TestAttrsPreservation:
    def test_attrs_roundtrip(self):
        """attrs set on input DataFrame survive from_pandas -> to_pandas."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.attrs = {"source": "test_db", "version": 2}
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert result.attrs == {"source": "test_db", "version": 2}

    def test_empty_attrs_roundtrip(self):
        """Empty attrs stay empty — no pollution."""
        df = pd.DataFrame({"x": [1, 2, 3]})
        df.attrs = {}
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert result.attrs == {}

    def test_attrs_not_shared(self):
        """Mutating result.attrs must not affect the ArFrame's stored attrs."""
        df = pd.DataFrame({"x": [1, 2]})
        df.attrs = {"key": "original"}
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        result.attrs["key"] = "mutated"
        # original frame attrs must be untouched
        assert frame._attrs["key"] == "original"

    def test_attrs_through_pipeline(self):
        """attrs survive a direct round-trip — pipeline frames are out of scope."""
        df = pd.DataFrame({"name": [" Alice ", " Bob "]})
        df.attrs = {"owner": "data_team"}
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert result.attrs.get("owner") == "data_team"

    def test_read_csv_has_no_attrs(self, sample_csv):
        """ArFrames from read_csv start with empty attrs — no junk metadata."""
        frame = ar.read_csv(sample_csv)
        result = ar.to_pandas(frame)
        assert result.attrs == {}

    def test_nested_mutable_attrs_are_deep_copied(self):
        """Nested mutable values in attrs are deep-copied, not shared."""
        df = pd.DataFrame({"x": [1, 2]})
        df.attrs = {"meta": {"version": 1, "tags": ["a", "b"]}}
        frame = ar.from_pandas(df)
        # mutate the original nested object
        df.attrs["meta"]["tags"].append("c")
        result = ar.to_pandas(frame)
        # stored copy must be unaffected
        assert result.attrs["meta"]["tags"] == ["a", "b"]
