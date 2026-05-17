"""Tests for pandas conversion."""

import numpy as np
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

    def test_copy_option_returns_equivalent_dataframe(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        zero_copy = ar.to_pandas(frame)
        defensive = ar.to_pandas(frame, copy=True)

        pd.testing.assert_frame_equal(defensive, zero_copy)
        assert defensive is not zero_copy

    def test_copy_option_rejects_non_bool(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(TypeError, match="copy must be a bool"):
            ar.to_pandas(frame, copy="yes")

    def test_copy_option_preserves_null_masks(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)

        df = ar.to_pandas(frame, copy=True)

        assert df.isna().any().any()

    def test_copy_option_isolates_integer_buffers(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        zero_copy = ar.to_pandas(frame)
        defensive = ar.to_pandas(frame, copy=True)
        original_age = zero_copy.loc[0, "age"]

        assert not np.shares_memory(
            zero_copy["age"].to_numpy(copy=False),
            defensive["age"].to_numpy(copy=False),
        )

        defensive.loc[0, "age"] = 99

        assert zero_copy.loc[0, "age"] == original_age
        assert ar.to_pandas(frame).loc[0, "age"] == original_age

    def test_copy_option_isolates_float_buffers(self, tmp_path):
        csv_path = tmp_path / "floats.csv"
        csv_path.write_text("score\n1.5\n2.5\n3.5\n")
        frame = ar.read_csv(csv_path)

        zero_copy = ar.to_pandas(frame)
        defensive = ar.to_pandas(frame, copy=True)

        assert not np.shares_memory(
            zero_copy["score"].to_numpy(copy=False),
            defensive["score"].to_numpy(copy=False),
        )

        defensive.loc[0, "score"] = 99.5

        assert zero_copy.loc[0, "score"] == 1.5
        assert ar.to_pandas(frame).loc[0, "score"] == 1.5

    def test_boolean_conversion_is_already_isolated(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        first = ar.to_pandas(frame)
        second = ar.to_pandas(frame)

        assert not np.shares_memory(
            first["active"].to_numpy(copy=False),
            second["active"].to_numpy(copy=False),
        )

        second.loc[0, "active"] = False

        assert first.loc[0, "active"] is np.True_
        assert ar.to_pandas(frame).loc[0, "active"] is np.True_

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

    def test_nullable_boolean_roundtrip(self):
        df = pd.DataFrame(
            {
                "active": pd.Series(
                    [True, False, pd.NA],
                    dtype="boolean",
                )
            }
        )

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert str(result["active"].dtype) == "boolean"
        assert list(result["active"]) == [True, False, pd.NA]

    def test_nullable_string_roundtrip(self):
        df = pd.DataFrame(
            {
                "name": pd.Series(
                    ["Alice", pd.NA, "Bob"],
                    dtype="string",
                )
            }
        )
        result = ar.to_pandas(ar.from_pandas(df))

        assert str(result["name"].dtype) == "string"

        pd.testing.assert_series_equal(
            result["name"],
            df["name"],
        )

    def test_nullable_float_roundtrip(self):
        df = pd.DataFrame(
            {
                "score": pd.Series(
                    [1.5, pd.NA, 3.7],
                    dtype="Float64",
                )
            }
        )

        result = ar.to_pandas(ar.from_pandas(df))

        assert str(result["score"].dtype) == "float64"
        assert result["score"].tolist()[0] == 1.5
        assert pd.isna(result["score"].tolist()[1])
        assert result["score"].tolist()[2] == 3.7

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

    def test_dataframe_index_is_dropped(self):
        """pandas index is not preserved during from_pandas conversion."""
        df = pd.DataFrame({"a": [1, 2, 3]}, index=["x", "y", "z"])
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert isinstance(result.index, pd.RangeIndex)


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
