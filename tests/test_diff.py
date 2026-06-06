"""Tests for arnio DataFrame drift detection (diff_dataframes, DataFrameDiffReport)."""

import pandas as pd
import pytest

from arnio.diff import ColumnDiff, DataFrameDiffReport, diff_dataframes


def test_diff_dataframes_raises_for_non_dataframe_expected():
    with pytest.raises(TypeError, match="expected must be a pandas DataFrame"):
        diff_dataframes("not a df", pd.DataFrame())


def test_diff_dataframes_raises_for_non_dataframe_observed():
    with pytest.raises(TypeError, match="observed must be a pandas DataFrame"):
        diff_dataframes(pd.DataFrame(), 123)


def test_diff_dataframes_raises_for_invalid_null_ratio_threshold_type():
    expected = pd.DataFrame({"a": [1]})
    observed = pd.DataFrame({"a": [1]})
    with pytest.raises(TypeError, match="null_ratio_threshold must be a float"):
        diff_dataframes(expected, observed, null_ratio_threshold="high")


def test_diff_dataframes_raises_for_null_ratio_threshold_out_of_range():
    expected = pd.DataFrame({"a": [1]})
    observed = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="null_ratio_threshold must be between"):
        diff_dataframes(expected, observed, null_ratio_threshold=1.5)


def test_diff_dataframes_identical_frames_is_clean():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    report = diff_dataframes(df, df.copy())
    assert report.is_clean is True
    assert report.has_breaking_changes is False
    assert report.row_count_delta == 0
    assert report.column_diffs == []


def test_diff_dataframes_empty_frames_is_clean():
    df = pd.DataFrame({"a": pd.Series([], dtype="int64")})
    report = diff_dataframes(df, df.copy())
    assert report.is_clean is True


def test_diff_dataframes_detects_removed_column():
    expected = pd.DataFrame({"a": [1], "b": [2]})
    observed = pd.DataFrame({"a": [1]})
    report = diff_dataframes(expected, observed)
    removed = [cd for cd in report.column_diffs if cd.change == "removed"]
    assert len(removed) == 1
    assert removed[0].name == "b"
    assert removed[0].expected_dtype == "int64"


def test_diff_dataframes_detects_added_column():
    expected = pd.DataFrame({"a": [1]})
    observed = pd.DataFrame({"a": [1], "b": [2]})
    report = diff_dataframes(expected, observed)
    added = [cd for cd in report.column_diffs if cd.change == "added"]
    assert len(added) == 1
    assert added[0].name == "b"
    assert added[0].observed_dtype == "int64"


def test_diff_dataframes_detects_multiple_added_and_removed():
    expected = pd.DataFrame({"a": [1], "b": [2]})
    observed = pd.DataFrame({"a": [1], "c": [3], "d": [4]})
    report = diff_dataframes(expected, observed)
    changes = {cd.change for cd in report.column_diffs}
    assert "removed" in changes
    assert "added" in changes


def test_diff_dataframes_detects_dtype_change():
    expected = pd.DataFrame({"age": pd.array([1, 2], dtype="int64")})
    observed = pd.DataFrame({"age": ["one", "two"]})
    report = diff_dataframes(expected, observed)
    dtype_diffs = [cd for cd in report.column_diffs if cd.change == "dtype_changed"]
    assert len(dtype_diffs) == 1
    assert dtype_diffs[0].name == "age"
    assert dtype_diffs[0].expected_dtype == "int64"
    assert dtype_diffs[0].observed_dtype == "string"


def test_diff_dataframes_dtype_change_is_breaking():
    expected = pd.DataFrame({"x": [1.0, 2.0]})
    observed = pd.DataFrame({"x": ["a", "b"]})
    report = diff_dataframes(expected, observed)
    assert report.has_breaking_changes is True


def test_diff_dataframes_detects_null_ratio_change():
    expected = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})
    observed = pd.DataFrame({"a": [1.0, None, None, None]})
    report = diff_dataframes(expected, observed)
    null_diffs = [cd for cd in report.column_diffs if cd.change == "null_ratio_changed"]
    assert len(null_diffs) == 1
    assert null_diffs[0].name == "a"
    assert null_diffs[0].expected_null_ratio == 0.0
    assert null_diffs[0].observed_null_ratio == pytest.approx(0.75)


def test_diff_dataframes_null_ratio_threshold_suppresses_small_change():
    expected = pd.DataFrame({"a": [1, 2, None, None]})
    observed = pd.DataFrame({"a": [1, None, None, None]})
    report = diff_dataframes(expected, observed, null_ratio_threshold=0.3)
    null_diffs = [cd for cd in report.column_diffs if cd.change == "null_ratio_changed"]
    assert len(null_diffs) == 0


def test_diff_dataframes_null_ratio_no_change_when_equal():
    expected = pd.DataFrame({"a": [1, None, 3]})
    observed = pd.DataFrame({"a": [2, None, 4]})
    report = diff_dataframes(expected, observed)
    assert report.is_clean is True


def test_diff_dataframes_row_count_delta_positive():
    expected = pd.DataFrame({"a": [1, 2]})
    observed = pd.DataFrame({"a": [1, 2, 3, 4]})
    report = diff_dataframes(expected, observed)
    assert report.row_count_delta == 2
    assert report.is_clean is False


def test_diff_dataframes_row_count_delta_negative():
    expected = pd.DataFrame({"a": [1, 2, 3]})
    observed = pd.DataFrame({"a": [1]})
    report = diff_dataframes(expected, observed)
    assert report.row_count_delta == -2


def test_diff_dataframes_row_count_delta_zero_is_not_breaking():
    expected = pd.DataFrame({"a": [1, 2]})
    observed = pd.DataFrame({"a": [3, 4]})
    report = diff_dataframes(expected, observed)
    assert report.row_count_delta == 0
    assert report.has_breaking_changes is False


def test_report_has_breaking_changes_for_removed_column():
    diffs = [ColumnDiff(name="x", change="removed", expected_dtype="int64")]
    report = DataFrameDiffReport(
        expected_row_count=2, observed_row_count=2, column_diffs=diffs
    )
    assert report.has_breaking_changes is True


def test_report_has_breaking_changes_false_for_added_column():
    diffs = [ColumnDiff(name="x", change="added", observed_dtype="int64")]
    report = DataFrameDiffReport(
        expected_row_count=2, observed_row_count=2, column_diffs=diffs
    )
    assert report.has_breaking_changes is False


def test_report_is_clean_false_when_diffs_present():
    diffs = [ColumnDiff(name="x", change="added", observed_dtype="string")]
    report = DataFrameDiffReport(
        expected_row_count=1, observed_row_count=1, column_diffs=diffs
    )
    assert report.is_clean is False


def test_report_summary_keys():
    df1 = pd.DataFrame({"a": [1, 2]})
    df2 = pd.DataFrame({"a": [1, 2, 3]})
    report = diff_dataframes(df1, df2)
    s = report.summary()
    assert isinstance(s, str)
    assert "status" in s
    assert "rows" in s
    assert "breaking_changes" in s


def test_report_to_dict_structure():
    df1 = pd.DataFrame({"a": [1]})
    df2 = pd.DataFrame({"b": [2]})
    report = diff_dataframes(df1, df2)
    d = report.to_dict()
    assert "is_clean" in d
    assert "has_breaking_changes" in d
    assert "column_diffs" in d
    assert isinstance(d["column_diffs"], list)


def test_report_to_markdown_clean():
    df = pd.DataFrame({"a": [1, 2]})
    report = diff_dataframes(df, df.copy())
    md = report.to_markdown()
    assert "clean" in md
    assert "no" in md  # has_breaking_changes: no!


def test_report_to_markdown_with_diffs():
    expected = pd.DataFrame({"a": [1], "b": [2]})
    observed = pd.DataFrame({"a": [1], "c": [3]})
    report = diff_dataframes(expected, observed)
    md = report.to_markdown()
    assert "drifted" in md
    assert "removed" in md
    assert "added" in md
    assert "| Column |" in md


def test_report_raises_for_negative_row_count():
    with pytest.raises(ValueError):
        DataFrameDiffReport(expected_row_count=-1, observed_row_count=0)


def test_report_raises_for_non_int_row_count():
    with pytest.raises(TypeError):
        DataFrameDiffReport(expected_row_count="ten", observed_row_count=0)


def test_report_raises_for_non_list_column_diffs():
    with pytest.raises(TypeError):
        DataFrameDiffReport(
            expected_row_count=0, observed_row_count=0, column_diffs="bad"
        )


def test_report_raises_for_invalid_column_diff_item():
    with pytest.raises(TypeError):
        DataFrameDiffReport(
            expected_row_count=0,
            observed_row_count=0,
            column_diffs=["not a ColumnDiff"],
        )
