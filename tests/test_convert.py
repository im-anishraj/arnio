"""Tests for pandas conversion."""

from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

import arnio as ar
from arnio.convert import _to_binding_safe


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


class TestFromRecords:
    def test_list_of_dicts(self):
        frame = ar.ArFrame.from_records(
            [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]
        )
        assert frame.shape == (2, 2)
        assert frame.columns == ["id", "name"]

    def test_list_of_lists(self):
        frame = ar.ArFrame.from_records(
            [[1, "alice"], [2, "bob"]], columns=["id", "name"]
        )
        assert frame.shape == (2, 2)
        assert frame.columns == ["id", "name"]

    def test_list_of_tuples(self):
        frame = ar.ArFrame.from_records(
            [(1, "alice"), (2, "bob")], columns=["id", "name"]
        )
        assert frame.shape == (2, 2)

    def test_missing_key_fills_none(self):
        frame = ar.ArFrame.from_records([{"a": 1}, {"a": 2, "b": 99}])
        assert frame.shape == (2, 2)
        df = ar.to_pandas(frame)
        assert pd.isna(df["b"].iloc[0])

    def test_top_level_reexport(self):
        frame = ar.from_records([{"x": 1}])
        assert frame.shape == (1, 1)

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            ar.ArFrame.from_records([])

    def test_sequences_without_columns_raises(self):
        with pytest.raises(ValueError, match="columns must be provided"):
            ar.ArFrame.from_records([[1, 2]])

    def test_column_count_mismatch_raises(self):
        with pytest.raises(ValueError, match="row 1"):
            ar.ArFrame.from_records([[1, 2], [3, 4, 5]], columns=["a", "b"])

    def test_nested_value_raises(self):
        with pytest.raises(TypeError, match="nested"):
            ar.ArFrame.from_records([{"a": [1, 2]}])

    def test_mixed_types_raises(self):
        with pytest.raises(TypeError):
            ar.ArFrame.from_records([{"a": 1}, [1, 2]])


class TestFromPandas:
    def test_column_order_preserved_with_non_alphabetical_mixed_dtypes(self):
        df = pd.DataFrame(
            {
                "z_name": ["Alice", "Bob"],
                "a_score": [95.5, 88.0],
                "m_active": [True, False],
                "b_id": [1, 2],
            }
        )

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert frame.columns == ["z_name", "a_score", "m_active", "b_id"]
        assert list(result.columns) == ["z_name", "a_score", "m_active", "b_id"]

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

    def test_string_dtype_roundtrip_with_missing_value(self):
        df = pd.DataFrame(
            {
                "name": pd.Series(
                    ["a", pd.NA],
                    dtype=pd.StringDtype(),
                )
            }
        )

        result = ar.to_pandas(ar.from_pandas(df))

        assert str(result["name"].dtype) == "string"
        assert list(result["name"]) == ["a", pd.NA]

    def test_string_dtype_roundtrip_all_nulls(self):
        df = pd.DataFrame(
            {
                "name": pd.Series(
                    [pd.NA, pd.NA],
                    dtype=pd.StringDtype(),
                )
            }
        )

        result = ar.to_pandas(ar.from_pandas(df))

        assert str(result["name"].dtype) == "string"
        assert result["name"].isna().tolist() == [True, True]

    def test_plain_object_string_column_behavior_unchanged(self):
        df = pd.DataFrame({"name": ["a", "b"]}, dtype=object)

        result = ar.to_pandas(ar.from_pandas(df))

        assert list(result["name"]) == ["a", "b"]
        assert str(result["name"].dtype) == "string"

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
        """datetime64 columns now raise a clear TypeError with a fix hint."""
        timestamp = pd.Timestamp("2026-05-14 12:30:00")
        df = pd.DataFrame({"created_at": [timestamp]})
        with pytest.raises(TypeError, match="Column 'created_at'"):
            ar.from_pandas(df)

    def test_from_pandas_object_timestamp_raises_clear_error(self):
        df = pd.DataFrame(
            {
                "created_at": pd.Series(
                    [pd.Timestamp("2026-05-14 12:30:00")], dtype=object
                )
            }
        )

        with pytest.raises(TypeError, match="Column 'created_at'") as exc_info:
            ar.from_pandas(df)

        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_timedelta_raises_clear_error(self):
        df = pd.DataFrame(
            {"duration": pd.Series([pd.Timedelta("2 days")], dtype=object)}
        )

        with pytest.raises(TypeError, match="Column 'duration'") as exc_info:
            ar.from_pandas(df)

        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_complex_raises_clear_error(self):
        df = pd.DataFrame({"signal": pd.Series([1 + 2j], dtype=object)})

        with pytest.raises(TypeError, match="Column 'signal'") as exc_info:
            ar.from_pandas(df)

        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_numpy_complex_raises_clear_error(self):
        df = pd.DataFrame({"signal": pd.Series([np.complex64(1 + 2j)], dtype=object)})

        with pytest.raises(TypeError, match="Column 'signal'") as exc_info:
            ar.from_pandas(df)

        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_custom_class_raises_clear_error(self):
        class Token:
            def __str__(self):
                return "TOKEN"

        df = pd.DataFrame({"x": pd.Series([Token()], dtype=object)})
        with pytest.raises(
            TypeError, match="Column 'x' contains unsupported scalar value"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_bytes_raises_clear_error(self):
        df = pd.DataFrame({"x": pd.Series([b"abc"], dtype=object)})
        with pytest.raises(
            TypeError, match="Column 'x' contains unsupported scalar value"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_object_datetime_date_and_time_raise_clear_error(self):
        import datetime as dt

        df_date = pd.DataFrame({"x": pd.Series([dt.date(2026, 5, 29)], dtype=object)})
        with pytest.raises(
            TypeError, match="Column 'x' contains unsupported scalar value"
        ):
            ar.from_pandas(df_date)

        df_time = pd.DataFrame({"x": pd.Series([dt.time(12, 30)], dtype=object)})
        with pytest.raises(
            TypeError, match="Column 'x' contains unsupported scalar value"
        ):
            ar.from_pandas(df_time)

    def test_from_pandas_object_pandas_period_raises_clear_error(self):
        df = pd.DataFrame({"x": pd.Series([pd.Period("2026-05")], dtype=object)})
        with pytest.raises(
            TypeError, match="Column 'x' contains unsupported scalar value"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)

    def test_from_pandas_native_datetime64_raises_clear_error(self):
        """Native datetime64 columns should raise a clear TypeError with a fix hint."""
        df = pd.DataFrame({"timestamp": pd.date_range("2026-05-20", periods=3)})
        with pytest.raises(
            TypeError, match="Column 'timestamp' has unsupported dtype 'datetime64"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)
        assert ".astype(str)" in str(exc_info.value)

    def test_from_pandas_native_timedelta64_raises_clear_error(self):
        """Native timedelta64 columns should raise a clear TypeError with a fix hint."""
        df = pd.DataFrame({"duration": pd.to_timedelta(["1 days", "2 days"])})
        with pytest.raises(
            TypeError, match="Column 'duration' has unsupported dtype 'timedelta"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)
        assert ".dt.total_seconds()" in str(exc_info.value)

    def test_from_pandas_native_category_raises_clear_error(self):
        """Native category columns should raise a clear TypeError with a fix hint."""
        df = pd.DataFrame(
            {"category_col": pd.Series(["a", "b", "a"], dtype="category")}
        )
        with pytest.raises(
            TypeError, match="Column 'category_col' has unsupported dtype 'category'"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)
        assert ".astype(str)" in str(exc_info.value)

    def test_from_pandas_native_complex_raises_clear_error(self):
        """Native complex columns should raise a clear TypeError with a fix hint."""
        df = pd.DataFrame({"signal": pd.Series([1 + 2j, 3 + 4j], dtype=complex)})
        with pytest.raises(
            TypeError, match="Column 'signal' has unsupported dtype 'complex128'"
        ) as exc_info:
            ar.from_pandas(df)
        assert "Fix:" in str(exc_info.value)
        assert ".apply(str)" in str(exc_info.value)

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

    def test_datetime_raises_clear_error(self):
        df = pd.DataFrame({"created_at": pd.to_datetime(["2021-01-01", "2022-06-15"])})
        with pytest.raises(TypeError, match="Column 'created_at'"):
            ar.from_pandas(df)

    def test_timedelta_raises_clear_error(self):
        df = pd.DataFrame({"duration": pd.to_timedelta(["1 days", "2 days"])})
        with pytest.raises(TypeError, match="Column 'duration'"):
            ar.from_pandas(df)

    def test_categorical_raises_clear_error(self):
        df = pd.DataFrame({"status": pd.Categorical(["active", "inactive", "active"])})
        with pytest.raises(TypeError, match="Column 'status'"):
            ar.from_pandas(df)

    def test_complex_raises_clear_error(self):
        df = pd.DataFrame({"signal": np.array([1 + 2j, 3 + 4j, 5 + 6j])})
        with pytest.raises(TypeError, match="Column 'signal'"):
            ar.from_pandas(df)

    def test_error_message_contains_fix_hint_datetime(self):
        df = pd.DataFrame({"ts": pd.to_datetime(["2023-01-01"])})
        with pytest.raises(TypeError, match="Fix:"):
            ar.from_pandas(df)

    def test_error_message_contains_fix_hint_timedelta(self):
        df = pd.DataFrame({"td": pd.to_timedelta(["3 days"])})
        with pytest.raises(TypeError, match="Fix:"):
            ar.from_pandas(df)

    def test_error_message_contains_fix_hint_category(self):
        df = pd.DataFrame({"cat": pd.Categorical(["a", "b"])})
        with pytest.raises(TypeError, match="Fix:"):
            ar.from_pandas(df)

    def test_error_message_contains_fix_hint_complex(self):
        df = pd.DataFrame({"cx": np.array([1 + 1j])})
        with pytest.raises(TypeError, match="Fix:"):
            ar.from_pandas(df)

    def test_mixed_valid_and_invalid_raises_on_bad_column(self):
        df = pd.DataFrame(
            {
                "name": ["Alice", "Bob"],
                "joined": pd.to_datetime(["2020-01-01", "2021-06-01"]),
            }
        )
        with pytest.raises(TypeError, match="Column 'joined'"):
            ar.from_pandas(df)

    def test_duplicate_single_label_raises(self):
        df = pd.DataFrame([[1, 2]], columns=["id", "id"])
        with pytest.raises(ValueError, match="duplicate column labels") as exc_info:
            ar.from_pandas(df)
        assert "id" in str(exc_info.value)

    def test_duplicate_multiple_labels_raises(self):
        df = pd.DataFrame([[1, 2, 3, 4]], columns=["a", "b", "a", "b"])
        with pytest.raises(ValueError, match="duplicate column labels") as exc_info:
            ar.from_pandas(df)
        assert "a" in str(exc_info.value)
        assert "b" in str(exc_info.value)

    def test_unique_labels_converts_cleanly(self):
        df = pd.DataFrame({"x": [1], "y": [2]})
        frame = ar.from_pandas(df)
        assert frame.columns == ["x", "y"]

    def test_unique_non_string_labels_convert_cleanly(self):
        df = pd.DataFrame([[1, 2]], columns=[0, 1])
        frame = ar.from_pandas(df)
        assert frame.columns == ["0", "1"]

    def test_duplicate_non_string_labels_raises(self):
        df = pd.DataFrame([[1, 2, 3]], columns=[0, 1, 0])
        with pytest.raises(ValueError, match="duplicate column labels") as exc_info:
            ar.from_pandas(df)
        assert "0" in str(exc_info.value)

    def test_stringified_integer_label_collision_raises(self):
        df = pd.DataFrame([[1, 2]], columns=[1, "1"])
        with pytest.raises(ValueError, match="string conversion") as exc_info:
            ar.from_pandas(df)

        message = str(exc_info.value)
        assert "'1'" in message
        assert "1" in message

    def test_stringified_bool_label_collision_raises(self):
        df = pd.DataFrame([[1, 2]], columns=[True, "True"])
        with pytest.raises(ValueError, match="string conversion") as exc_info:
            ar.from_pandas(df)

        message = str(exc_info.value)
        assert "True" in message

    def test_from_pandas_all_null_float64_extension(self):
        df = pd.DataFrame({"score": pd.Series([pd.NA, pd.NA, pd.NA], dtype="Float64")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert len(result) == 3
        assert result["score"].isna().all()
        assert str(result["score"].dtype) == "float64"

    def test_from_pandas_mixed_null_float64_extension(self):
        df = pd.DataFrame({"score": pd.Series([1.5, pd.NA, 3.7], dtype="Float64")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert str(result["score"].dtype) == "float64"
        assert result["score"].iloc[0] == 1.5
        assert pd.isna(result["score"].iloc[1])
        assert result["score"].iloc[2] == 3.7

    def test_from_pandas_all_null_boolean_extension(self):
        df = pd.DataFrame({"active": pd.Series([pd.NA, pd.NA, pd.NA], dtype="boolean")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert len(result) == 3
        assert result["active"].isna().all()
        assert str(result["active"].dtype) == "boolean"

    def test_from_pandas_all_null_string_extension(self):
        df = pd.DataFrame({"name": pd.Series([pd.NA, pd.NA, pd.NA], dtype="string")})
        result = ar.to_pandas(ar.from_pandas(df))
        assert len(result) == 3
        assert result["name"].isna().all()
        assert str(result["name"].dtype) == "string"

    def test_empty_column_dataframe_preserves_row_count(self):
        df = pd.DataFrame(index=range(3))

        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)

        assert frame.shape == (3, 0)
        assert result.shape == (3, 0)
        assert result.index.tolist() == [0, 1, 2]

    def test_zero_column_frame_survives_repeated_roundtrip(self):
        df = pd.DataFrame(index=range(2))

        frame = ar.from_pandas(df)
        roundtripped = ar.from_pandas(ar.to_pandas(frame))

        assert roundtripped.shape == (2, 0)

    def test_from_dict_mismatched_column_lengths(self):
        with pytest.raises(
            ValueError,
            match="from_dict\\(\\) column lengths differ",
        ) as exc_info:
            ar.from_dict(
                {
                    "id": [1, 2, 3],
                    "name": ["a", "b"],
                }
            )

        message = str(exc_info.value)

        assert "id=3" in message
        assert "name=2" in message

    def test_from_dict_equal_length_columns(self):
        frame = ar.from_dict(
            {
                "id": [1, 2],
                "name": ["a", "b"],
            }
        )

        result = ar.to_pandas(frame)

        assert result.shape == (2, 2)
        assert list(result.columns) == ["id", "name"]

    def test_from_dict_rejects_scalar_value(self):
        with pytest.raises(
            TypeError,
            match="Column 'a' must be a sequence of values",
        ):
            ar.from_dict({"a": 1})

    def test_from_dict_rejects_mixed_scalar_and_list(self):
        with pytest.raises(
            TypeError,
            match="Column 'b' must be a sequence of values",
        ):
            ar.from_dict(
                {
                    "a": [1, 2],
                    "b": 3,
                }
            )

    def test_from_dict_accepts_tuple_values(self):
        frame = ar.from_dict(
            {
                "a": (1, 2),
                "b": ("x", "y"),
            }
        )

        result = ar.to_pandas(frame)

        assert result.shape == (2, 2)

    def test_from_dict_rejects_string_value(self):
        with pytest.raises(
            TypeError,
            match="Column 'a' must be a sequence of values",
        ):
            ar.from_dict({"a": "abc"})

    def test_from_dict_rejects_bytes_value(self):
        with pytest.raises(
            TypeError,
            match="Column 'a' must be a sequence of values",
        ):
            ar.from_dict({"a": b"abc"})


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
        assert frame._attrs["key"] == "original"


class TestDecimalConversion:
    """Test support for Python Decimal objects in financial datasets."""

    def test_decimal_normal_conversion(self):
        """Normal financial value conversion."""
        dec_val = Decimal("123.45")
        assert _to_binding_safe(dec_val) == "123.45"
        assert isinstance(_to_binding_safe(dec_val), str)

    def test_decimal_edge_cases(self):
        """Zero and negative values."""
        assert _to_binding_safe(Decimal("0.00")) == "0.00"
        assert _to_binding_safe(Decimal("-0.01")) == "-0.01"
        assert _to_binding_safe(Decimal("999.999")) == "999.999"

    def test_decimal_precision_loss_awareness(self):
        """Large precision decimal is perfectly preserved as string."""
        large_dec = Decimal("1.234567890123456789")
        result = _to_binding_safe(large_dec)
        assert result == "1.234567890123456789"

    def test_invalid_cases_infinity(self):
        """Invalid floating/decimal boundaries like infinity."""
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(float("inf"))

        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(float("-inf"))

    def test_decimal_from_pandas_roundtrip(self):
        """Decimal columns convert to exact strings during from_pandas."""
        df = pd.DataFrame(
            {"price": [Decimal("19.99"), Decimal("29.95"), Decimal("15.50")]}
        )
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        # Result should be preserved as exact strings
        assert list(result["price"]) == ["19.99", "29.95", "15.50"]
        assert result["price"].dtype == "string"

    def test_decimal_with_nulls(self):
        """Decimal columns with null values."""
        df = pd.DataFrame({"amount": [Decimal("100.50"), None, Decimal("50.25")]})
        frame = ar.from_pandas(df)
        result = ar.to_pandas(frame)
        assert result["amount"].iloc[0] == "100.50"
        assert pd.isna(result["amount"].iloc[1])
        assert result["amount"].iloc[2] == "50.25"

    def test_from_pandas_rejects_decimal_infinity(self):
        """from_pandas() must reject Decimal infinity during conversion."""
        df = pd.DataFrame({"value": [Decimal("100.50"), Decimal("Infinity")]})
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            ar.from_pandas(df)

    def test_from_pandas_rejects_decimal_nan(self):
        """from_pandas() must reject Decimal NaN during conversion."""
        df = pd.DataFrame({"value": [Decimal("100.50"), Decimal("NaN")]})
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            ar.from_pandas(df)

    def test_from_pandas_rejects_float_infinity(self):
        """from_pandas() must reject native float infinity during conversion."""
        df = pd.DataFrame({"value": [100.50, float("inf")]})
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            ar.from_pandas(df)

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


class TestToBindingSafeExtras:
    """Additional focused tests for to_binding_safe Decimal/float handling."""

    def test_decimal_infinity_and_nan_raise(self):
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(Decimal("Infinity"))

        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(Decimal("NaN"))

    def test_float_infinite_and_nan_raise(self):
        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(float("inf"))

        with pytest.raises(
            ValueError, match="Invalid financial value: NaN or Infinity."
        ):
            _to_binding_safe(float("nan"))


class TestUInt64BoundaryConversion:
    """Tests for pandas UInt64 and uint64 boundary conversions near signed 64-bit integer limits.

    Links with Fixes #626.
    """

    def test_uint64_within_bounds(self):
        # 9223372036854775807 is the maximum signed 64-bit integer.
        df = pd.DataFrame(
            {
                "col_uint": pd.Series(
                    [0, 12345, 9223372036854775807],
                    dtype="UInt64",
                )
            }
        )
        frame = ar.from_pandas(df)
        assert frame.dtypes["col_uint"] == "int64"

        result = ar.to_pandas(frame)
        assert list(result["col_uint"]) == [0, 12345, 9223372036854775807]

    def test_uint64_out_of_bounds_raises(self):
        # 9223372036854775808 exceeds the maximum signed 64-bit integer.
        df = pd.DataFrame(
            {
                "col_uint": pd.Series(
                    [9223372036854775808],
                    dtype="UInt64",
                )
            }
        )
        with pytest.raises(
            ValueError,
            match="out of bounds for signed 64-bit integer",
        ):
            ar.from_pandas(df)

    def test_numpy_uint64_within_bounds(self):
        df = pd.DataFrame(
            {
                "col_uint": np.array(
                    [0, 9223372036854775807],
                    dtype=np.uint64,
                )
            }
        )
        frame = ar.from_pandas(df)
        assert frame.dtypes["col_uint"] == "int64"

        result = ar.to_pandas(frame)
        assert list(result["col_uint"]) == [0, 9223372036854775807]

    def test_numpy_uint64_out_of_bounds_raises(self):
        df = pd.DataFrame(
            {
                "col_uint": np.array(
                    [9223372036854775808],
                    dtype=np.uint64,
                )
            }
        )
        with pytest.raises(
            ValueError,
            match="out of bounds for signed 64-bit integer",
        ):
            ar.from_pandas(df)


class TestToArrow:
    """Tests for Arrow export."""

    def setup_method(self):
        pytest.importorskip("pyarrow")

    def test_int64_columns(self):
        import pyarrow

        df = pd.DataFrame({"x": pd.Series([1, 2, 3], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.num_columns == 1
        assert table.column_names == ["x"]
        assert table.column(0).type == pyarrow.int64()
        assert table.column(0).to_pylist() == [1, 2, 3]

    def test_float64_columns(self):
        import pyarrow

        df = pd.DataFrame({"y": pd.Series([1.5, 2.5, 3.5], dtype="float64")})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.column(0).type == pyarrow.float64()
        assert table.column(0).to_pylist() == [1.5, 2.5, 3.5]

    def test_bool_columns(self):
        import pyarrow

        df = pd.DataFrame({"z": pd.Series([True, False, True], dtype="bool")})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.column(0).type == pyarrow.bool_()
        assert table.column(0).to_pylist() == [True, False, True]

    def test_nullable_bool_columns(self):
        import pyarrow

        df = pd.DataFrame({"a": pd.Series([True, False, pd.NA], dtype="boolean")})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.column(0).type == pyarrow.bool_()
        assert table.column(0).to_pylist() == [True, False, None]

    def test_string_columns(self):
        import pyarrow

        df = pd.DataFrame({"s": pd.Series(["a", "b", "c"], dtype="string")})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.column(0).type == pyarrow.string()
        assert table.column(0).to_pylist() == ["a", "b", "c"]

    def test_mixed_column_types(self):
        import pyarrow

        df = pd.DataFrame(
            {
                "int_col": pd.Series([1, 2, 3], dtype=pd.Int64Dtype()),
                "float_col": pd.Series([1.5, 2.5, 3.5], dtype="float64"),
                "bool_col": pd.Series([True, False, True], dtype="bool"),
                "str_col": pd.Series(["a", "b", "c"], dtype="string"),
            }
        )
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.num_columns == 4
        assert table.column_names == ["int_col", "float_col", "bool_col", "str_col"]
        assert table.column(0).type == pyarrow.int64()
        assert table.column(1).type == pyarrow.float64()
        assert table.column(2).type == pyarrow.bool_()
        assert table.column(3).type == pyarrow.string()

    def test_roundtrip_to_pandas(self):
        df = pd.DataFrame(
            {
                "x": pd.Series([1, 2, 3], dtype=pd.Int64Dtype()),
                "y": pd.Series([1.5, 2.5, 3.5], dtype="float64"),
                "z": pd.Series([True, False, True], dtype="bool"),
            }
        )
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        result = table.to_pandas()
        for col in df.columns:
            assert list(result[col]) == list(df[col])

    def test_null_handling(self):
        df = pd.DataFrame(
            {
                "int_col": pd.Series([1, pd.NA, 3], dtype=pd.Int64Dtype()),
                "bool_col": pd.Series([True, pd.NA, False], dtype="boolean"),
                "str_col": pd.Series(["a", None, "c"], dtype="string"),
            }
        )
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.column(0).to_pylist() == [1, None, 3]
        assert table.column(1).to_pylist() == [True, None, False]
        assert table.column(2).to_pylist() == ["a", None, "c"]

    def test_empty_frame(self):
        df = pd.DataFrame({"x": pd.Series([], dtype=pd.Int64Dtype())})
        frame = ar.from_pandas(df)
        table = ar.to_arrow(frame)
        assert table.num_rows == 0
        assert table.num_columns == 1

    def test_invalid_frame_type(self):
        with pytest.raises(TypeError, match="to_arrow.*expects an ArFrame"):
            ar.to_arrow("not_a_frame")

    def test_from_csv_roundtrip(self, sample_csv):
        import pyarrow

        frame = ar.read_csv(sample_csv)
        table = ar.to_arrow(frame)
        assert table.num_columns == 4
        assert table.column_names == ["name", "age", "email", "active"]
        assert table.column(0).type == pyarrow.string()
        assert table.column(1).type == pyarrow.int64()
        assert table.column(2).type == pyarrow.string()
        assert table.column(3).type == pyarrow.bool_()
        assert table.num_rows == 3

    def test_csv_nulls_roundtrip(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        table = ar.to_arrow(frame)
        assert table.num_rows == 4
        names = table.column("name").to_pylist()
        assert names == ["Alice", None, "Charlie", "Diana"]
        ages = table.column("age").to_pylist()
        assert ages[0] == 30
        assert ages[1] == 25
        assert ages[2] is None
        assert ages[3] == 28


class TestNullableInt64ObjectConversion:
    """Tests for casting object series containing None/NaN and valid integers to integer types."""

    def test_object_series_with_none_and_integers(self):
        df = pd.DataFrame({"col": [1, None, 3]}, dtype=object)
        frame = ar.from_pandas(df)
        assert frame.dtypes["col"] == "int64"
        result = ar.to_pandas(frame)
        assert str(result["col"].dtype) == "Int64"
        assert list(result["col"]) == [1, pd.NA, 3]

    def test_object_series_with_nan_and_integers(self):
        df = pd.DataFrame({"col": [1, np.nan, 3]}, dtype=object)
        frame = ar.from_pandas(df)
        assert frame.dtypes["col"] == "int64"
        result = ar.to_pandas(frame)
        assert str(result["col"].dtype) == "Int64"
        assert list(result["col"]) == [1, pd.NA, 3]

    def test_object_series_with_pd_na_and_integers(self):
        df = pd.DataFrame({"col": [1, pd.NA, 3]}, dtype=object)
        frame = ar.from_pandas(df)
        assert frame.dtypes["col"] == "int64"
        result = ar.to_pandas(frame)
        assert str(result["col"].dtype) == "Int64"
        assert list(result["col"]) == [1, pd.NA, 3]


class TestCastNullableInt:
    """Tests for casting object series with None/NaN and valid integers."""

    def test_cast_object_series_with_none_and_valid_integers(self):
        """Casting object column with None and integer strings to int64."""
        df = pd.DataFrame({"val": [1, None, 3, "4", None]})
        frame = ar.from_pandas(df)
        result = ar.cast_types(frame, {"val": "int64"}, errors="coerce")
        df_result = ar.to_pandas(result)
        assert result.dtypes["val"] == "int64"
        assert df_result["val"].iloc[0] == 1
        assert pd.isna(df_result["val"].iloc[1])  # type: ignore[arg-type]
        assert df_result["val"].iloc[2] == 3
        assert df_result["val"].iloc[3] == 4
        assert pd.isna(df_result["val"].iloc[4])  # type: ignore[arg-type]

    def test_cast_object_series_with_nan_and_valid_integers(self):
        """Casting object column with float NaN and integer values to int64."""
        df = pd.DataFrame({"val": pd.Series([1, float("nan"), 3, 4], dtype=object)})
        frame = ar.from_pandas(df)
        result = ar.cast_types(frame, {"val": "int64"}, errors="coerce")
        df_result = ar.to_pandas(result)
        assert result.dtypes["val"] == "int64"
        assert df_result["val"].iloc[0] == 1
        assert pd.isna(df_result["val"].iloc[1])  # type: ignore[arg-type]
        assert df_result["val"].iloc[2] == 3
        assert df_result["val"].iloc[3] == 4

    def test_cast_object_series_all_valid_integers_from_object(self):
        """Casting object column with all valid integers to int64."""
        df = pd.DataFrame({"val": ["10", "20", "30"]})
        frame = ar.from_pandas(df)
        result = ar.cast_types(frame, {"val": "int64"})
        df_result = ar.to_pandas(result)
        assert result.dtypes["val"] == "int64"
        assert list(df_result["val"]) == [10, 20, 30]

    def test_cast_object_series_raises_on_invalid(self):
        """Casting object column with invalid string raises TypeCastError."""
        df = pd.DataFrame({"val": [1, 2, "not_a_number"]})
        frame = ar.from_pandas(df)
        with pytest.raises(ar.TypeCastError, match="Cannot cast column 'val'"):
            ar.cast_types(frame, {"val": "int64"})


def test_from_records_rejects_string_columns():
    import pytest

    import arnio as ar

    with pytest.raises(
        TypeError,
        match="columns must be a list or tuple of strings",
    ):
        ar.ArFrame.from_records([[1]], columns="a")


def test_from_records_rejects_bytes_columns():
    import pytest

    import arnio as ar

    with pytest.raises(
        TypeError,
        match="columns must be a list or tuple of strings",
    ):
        ar.ArFrame.from_records([[1]], columns=b"a")


def test_from_records_rejects_non_string_column_entries():
    import pytest

    import arnio as ar

    with pytest.raises(
        TypeError,
        match="columns must contain only strings",
    ):
        ar.ArFrame.from_records([[1]], columns=[1])


def test_from_records_accepts_valid_string_columns_list():
    import arnio as ar

    frame = ar.ArFrame.from_records([[1, 2]], columns=["a", "b"])

    assert frame.columns == ["a", "b"]


def test_from_records_accepts_valid_string_columns_tuple():
    import arnio as ar

    frame = ar.ArFrame.from_records([[1, 2]], columns=("a", "b"))

    assert frame.columns == ["a", "b"]
