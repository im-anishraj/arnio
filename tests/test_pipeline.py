"""Tests for the pipeline function."""

import importlib
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from inspect import Signature

import pandas as pd
import pytest

import arnio as ar
from arnio.exceptions import PipelineSerializationError
from arnio.pipeline import load_pipeline, save_pipeline

pipeline_module = importlib.import_module("arnio.pipeline")


@pytest.fixture(autouse=True)
def restore_python_step_registry():
    """Restore custom pipeline steps after each test.

    Tests may register temporary custom steps. This fixture prevents those
    registrations from leaking into other tests while preserving any steps
    that were already registered before the test started.
    """
    with pipeline_module._REGISTRY_LOCK:
        original_registry = dict(pipeline_module._PYTHON_STEP_REGISTRY)
        original_aliases = dict(pipeline_module._DEPRECATED_STEP_ALIASES)

    yield

    with pipeline_module._REGISTRY_LOCK:
        pipeline_module._PYTHON_STEP_REGISTRY.clear()
        pipeline_module._PYTHON_STEP_REGISTRY.update(original_registry)
        pipeline_module._DEPRECATED_STEP_ALIASES.clear()
        pipeline_module._DEPRECATED_STEP_ALIASES.update(original_aliases)


class TestPipeline:
    def test_single_step(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("drop_nulls",),
            ],
        )
        assert result.shape[0] < frame.shape[0]

    def test_multi_step(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)
        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "lower"}),
            ],
        )
        df = ar.to_pandas(result)
        assert df["name"].iloc[0] == "alice"

    def test_full_pipeline(self, csv_with_nulls):
        frame = ar.read_csv(csv_with_nulls)
        result = ar.pipeline(
            frame,
            [
                ("drop_nulls",),
                ("strip_whitespace",),
                ("drop_duplicates",),
            ],
        )
        assert isinstance(result, ar.ArFrame)
        assert result.shape[0] <= frame.shape[0]

    def test_pipeline_with_kwargs(self, csv_with_duplicates):
        frame = ar.read_csv(csv_with_duplicates)
        result = ar.pipeline(
            frame,
            [
                ("drop_duplicates", {"keep": "last"}),
            ],
        )
        assert result.shape[0] == 3

    def test_pipeline_drop_constant_columns(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "constant": [1, 1, 1],
                    "value": [1, 2, 1],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("drop_constant_columns",),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df.columns) == ["value"]
        assert list(df["value"]) == [1, 2, 1]

    def test_pipeline_clip_numeric(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "value": [-5, 2, 10],
                    "label": ["a", "b", "c"],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("clip_numeric", {"lower": 0, "upper": 5}),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df["value"]) == [0, 2, 5]
        assert list(df["label"]) == ["a", "b", "c"]

    def test_pipeline_mapping_shorthand(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"age": "float64"}),
                ("rename_columns", {"age": "years"}),
            ],
        )

        assert result.dtypes["years"] == "float64"
        assert "age" not in result.columns

    def test_pipeline_cast_types_shorthand_rejects_reserved_kwargs(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "age": ["1", "2"],
                }
            )
        )

        with pytest.raises(
            ValueError,
            match="cast_types shorthand mapping cannot be mixed",
        ):
            ar.pipeline(
                frame,
                [
                    (
                        "cast_types",
                        {
                            "age": "int64",
                            "errors": "coerce",
                        },
                    ),
                ],
            )

    def test_pipeline_mapping_keyword_form(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"mapping": {"age": "float64"}}),
                ("rename_columns", {"mapping": {"age": "years"}}),
            ],
        )

        assert result.dtypes["years"] == "float64"
        assert "age" not in result.columns

    def test_pipeline_validate_columns_exist(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("validate_columns_exist", {"columns": ["name", "age"]}),
                ("strip_whitespace", {"subset": ["name"]}),
            ],
        )

        assert result.shape == frame.shape

    def test_pipeline_validate_columns_exist_allows_empty_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [("validate_columns_exist", {"columns": []})])

        assert result is frame

    def test_pipeline_validate_columns_exist_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns"):
            ar.pipeline(
                frame,
                [("validate_columns_exist", {"columns": ["missing"]})],
            )

    def test_pipeline_subset_step_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(KeyError, match="Missing columns for strip_whitespace"):
            ar.pipeline(
                frame,
                [("strip_whitespace", {"subset": ["missing"]})],
            )

    def test_empty_pipeline(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [])
        assert result.shape == frame.shape

    @pytest.mark.parametrize("invalid_frame", ["not-frame", None])
    def test_pipeline_rejects_invalid_frame_with_empty_steps(self, invalid_frame):
        with pytest.raises(TypeError, match="frame must be an ArFrame"):
            ar.pipeline(invalid_frame, [])

    def test_pipeline_rejects_invalid_frame_before_non_empty_steps(self):
        with pytest.raises(TypeError, match="frame must be an ArFrame"):
            ar.pipeline("not-frame", [("strip_whitespace",)])

    def test_pipeline_dry_run_returns_original_frame(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
            ],
            dry_run=True,
        )

        assert result is frame

    def test_pipeline_dry_run_validates_unknown_steps(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ar.UnknownStepError):
            ar.pipeline(
                frame,
                [
                    ("missing_step",),
                ],
                dry_run=True,
            )

    def test_pipeline_dry_run_validates_invalid_kwargs(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Expected a dict"):
            ar.pipeline(
                frame,
                [
                    ("drop_nulls", "subset=name"),
                ],
                dry_run=True,
            )

    def test_pipeline_return_metadata_disabled_by_default(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
            ],
        )

        assert isinstance(result, ar.ArFrame)

    def test_pipeline_return_metadata_includes_step_timings(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result, metadata = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("normalize_case", {"case_type": "lower"}),
            ],
            return_metadata=True,
        )

        assert isinstance(result, ar.ArFrame)
        assert list(metadata.keys()) == [
            "applied_steps",
            "row_counts",
            "step_timings",
            "execution_summary",
        ]
        assert metadata["applied_steps"] == ["strip_whitespace", "normalize_case"]
        assert len(metadata["row_counts"]) == 2
        assert metadata["row_counts"][0]["step"] == "strip_whitespace"
        assert metadata["row_counts"][0]["before"] == frame.shape[0]
        assert metadata["row_counts"][0]["after"] == result.shape[0]
        assert len(metadata["step_timings"]) == 2
        assert metadata["step_timings"][0]["step"] == "strip_whitespace"
        assert metadata["step_timings"][1]["step"] == "normalize_case"
        assert all(item["seconds"] >= 0 for item in metadata["step_timings"])

    def test_pipeline_return_metadata_handles_python_steps(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        def add_marker(df, value="ok"):
            df["marker"] = value
            return df

        ar.register_step("timed_python_step", add_marker)

        result, metadata = ar.pipeline(
            frame,
            [
                ("timed_python_step", {"value": "done"}),
            ],
            return_metadata=True,
        )

        df = ar.to_pandas(result)
        assert set(df["marker"]) == {"done"}
        assert metadata["applied_steps"] == ["timed_python_step"]
        assert metadata["row_counts"] == [
            {
                "step": "timed_python_step",
                "before": frame.shape[0],
                "after": result.shape[0],
                "dry_run": False,
            }
        ]
        assert len(metadata["step_timings"]) == 1
        assert metadata["step_timings"][0]["step"] == "timed_python_step"
        assert metadata["step_timings"][0]["seconds"] >= 0

    def test_register_python_step(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        def add_marker(df, value="ok"):
            df["marker"] = value
            return df

        ar.register_step("test_add_marker", add_marker)

        result = ar.pipeline(
            frame,
            [
                ("test_add_marker", {"value": "done"}),
            ],
        )

        df = ar.to_pandas(result)
        assert "marker" in df.columns
        assert set(df["marker"]) == {"done"}

    def test_unregister_missing_step(self):
        with pytest.raises(ar.UnknownStepError):
            ar.unregister_step("missing_step")

    def test_unregister_builtin_python_step(self):
        for step_name in [
            "standardize_missing_tokens",
            "filter_rows",
            "replace_values",
        ]:
            with pytest.raises(ValueError):
                ar.unregister_step(step_name)

    def test_unregister_custom_step(self):
        def custom_step(df):
            return df

        ar.register_step("temporary_step", custom_step)

        ar.unregister_step("temporary_step")

        with pytest.raises(ar.UnknownStepError):
            ar.pipeline(
                ar.from_pandas(pd.DataFrame({"a": [1]})),
                [("temporary_step",)],
            )

    def test_pipeline_passes_context_to_opt_in_python_steps(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        seen = {}

        def capture_context(df, context=None):
            seen["context"] = context
            df["step_seen"] = context.step_name
            return df

        ar.register_step("context_capture_step", capture_context)

        result = ar.pipeline(
            frame,
            [
                ("strip_whitespace",),
                ("context_capture_step",),
            ],
            dry_run=True,
        )

        context = seen["context"]
        assert isinstance(context, ar.PipelineContext)
        assert context.step_name == "context_capture_step"
        assert context.step_index == 1
        assert context.total_steps == 2
        assert context.dry_run is True
        assert isinstance(result, ar.ArFrame)

    def test_pipeline_does_not_require_context_for_existing_python_steps(
        self, sample_csv
    ):
        frame = ar.read_csv(sample_csv)

        def legacy_step(df, value="ok"):
            df["marker"] = value
            return df

        ar.register_step("legacy_context_free_step", legacy_step)

        result = ar.pipeline(
            frame,
            [
                ("legacy_context_free_step", {"value": "done"}),
            ],
        )

        df = ar.to_pandas(result)
        assert set(df["marker"]) == {"done"}

    def test_pipeline_preserves_explicit_context_kwarg_for_python_steps(
        self, sample_csv
    ):
        frame = ar.read_csv(sample_csv)
        seen = {}

        def capture_context(df, context=None):
            seen["context"] = context
            df["context_marker"] = str(context)
            return df

        ar.register_step("explicit_context_step", capture_context)
        explicit_context = {"source": "caller"}

        result = ar.pipeline(
            frame,
            [
                ("explicit_context_step", {"context": explicit_context}),
            ],
        )

        df = ar.to_pandas(result)

        assert seen["context"] is explicit_context
        assert set(df["context_marker"]) == {str(explicit_context)}

    def test_concurrent_step_registration(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        def make_step(column_name):
            def step(df):
                df[column_name] = column_name
                return df

            return step

        step_count = 25
        step_names = [f"concurrent_step_{i}" for i in range(step_count)]

        def register(name):
            ar.register_step(name, make_step(name))

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(register, step_names))

        result = ar.pipeline(frame, [(name,) for name in step_names])
        df = ar.to_pandas(result)

        for name in step_names:
            assert name in df.columns
            assert set(df[name]) == {name}

    def test_pipeline_uses_stable_registry_snapshot_during_execution(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        started = threading.Event()
        continue_step = threading.Event()

        def blocking_step(df):
            started.set()
            continue_step.wait(timeout=5)
            df["blocking_step_done"] = True
            return df

        def late_step(df):
            df["late_step_done"] = True
            return df

        ar.register_step("blocking_snapshot_step", blocking_step)

        errors = []

        def run_pipeline():
            try:
                ar.pipeline(
                    frame,
                    [
                        ("blocking_snapshot_step",),
                        ("late_snapshot_step",),
                    ],
                )
            except Exception as exc:
                errors.append(exc)

        thread = threading.Thread(target=run_pipeline)
        thread.start()

        assert not started.is_set()

        ar.register_step("late_snapshot_step", late_step)

        continue_step.set()
        thread.join(timeout=5)

        assert len(errors) == 1
        assert isinstance(errors[0], ar.UnknownStepError)
        assert "late_snapshot_step" in str(errors[0])

    def test_invalid_step_name(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("nonexistent_op",)])
            assert False, "Should have raised UnknownStepError"
        except ar.UnknownStepError as e:
            assert "Unknown pipeline step" in str(e)

    def test_invalid_step_format(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("a", "b", "c")])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid step format" in str(e)

    def test_invalid_step_kwargs(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        try:
            ar.pipeline(frame, [("drop_nulls", "subset=name")])
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Expected a dict" in str(e)

    def test_pipeline_make_column_names_unique(self, csv_with_duplicate_columns):
        # Construct a frame with duplicate column names using the C++ bindings
        from arnio._core import (
            _Column as _CColumn,
        )
        from arnio._core import (
            _DType as _CDType,
        )
        from arnio._core import (
            _Frame as _CFrame,
        )

        c1 = _CColumn("col", _CDType.STRING)
        c1.push_back("1")
        c1.push_back("4")

        c2 = _CColumn("col", _CDType.STRING)
        c2.push_back("2")
        c2.push_back("5")

        c3 = _CColumn("age", _CDType.INT64)
        c3.push_back(3)
        c3.push_back(6)

        cpp_frame = _CFrame()
        cpp_frame.add_column(c1)
        cpp_frame.add_column(c2)
        cpp_frame.add_column(c3)

        frame = ar.ArFrame(cpp_frame)

        result = ar.pipeline(frame, [("make_column_names_unique",)])

        assert result.columns == ["col", "col_1", "age"]

    def test_pipeline_make_column_names_unique_already_unique(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.pipeline(frame, [("make_column_names_unique",)])

        assert result.columns == frame.columns
    def test_pipeline_rejects_empty_step(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.pipeline(
            frame,
            [
                (
                    "combine_columns",
                    {
                        "columns": ["first", "last"],
                        "output_column": "full_name",
                        "separator": " ",
                    },
                ),
            ],
        )

        df = ar.to_pandas(result)
        assert df["full_name"].tolist() == ["Ada Lovelace", "Grace Hopper"]
        assert "first" in result.columns

    def test_combine_columns_step_can_drop_original_columns(self, tmp_path):
        path = tmp_path / "names.csv"
        path.write_text("first,last\nAda,Lovelace\n")
        frame = ar.read_csv(path)

        result = ar.pipeline(
            frame,
            [
                (
                    "combine_columns",
                    {
                        "columns": ["first", "last"],
                        "output_column": "full_name",
                        "separator": " ",
                        "drop_original": True,
                    },
                ),
            ],
        )

        assert result.columns == ["full_name"]
        assert ar.to_pandas(result)["full_name"].iloc[0] == "Ada Lovelace"

    def test_combine_columns_rejects_empty_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

    result = ar.filter_rows(frame, column="age", op=">", value=25)

    result_df = ar.to_pandas(result)

    assert list(result_df["age"]) == [30, 40]


def test_round_numeric_columns_pipeline():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"price": [10.555, 20.123]})
    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("round_numeric_columns", {"subset": ["price"], "decimals": 2})]
    )

    result_df = ar.to_pandas(result)
    assert list(result_df["price"]) == [10.56, 20.12]


def test_safe_divide_columns_pipeline():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"revenue": [100.0, 200.0, 0.0], "cost": [50.0, 0.0, 30.0]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "safe_divide_columns",
                {
                    "numerator": "revenue",
                    "denominator": "cost",
                    "output_column": "ratio",
                },
            )
        ],
    )

    result_df = ar.to_pandas(result)
    assert result_df["ratio"].iloc[0] == 2.0
    assert result_df["ratio"].iloc[1] == 0.0  # division by zero → fill_value
    assert result_df["ratio"].iloc[2] == 0.0  # zero numerator


def test_pipeline_combine_columns():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"first": ["Alice", "Bob"], "last": ["Smith", "Jones"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "combine_columns",
                {
                    "subset": ["first", "last"],
                    "separator": " ",
                    "output_column": "full_name",
                },
            )
        ],
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["full_name"]) == ["Alice Smith", "Bob Jones"]


def test_replace_values_simple():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"status": ["active", "inactive", "active"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "replace_values",
                {"mapping": {"active": "A", "inactive": "I"}, "column": "status"},
            )
        ],
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["status"]) == ["A", "I", "A"]


def test_replace_values_none():
    import numpy as np
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"status": ["active", None, np.nan, "inactive"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "replace_values",
                {
                    "mapping": {None: "MISSING", "active": "A", "inactive": "I"},
                    "column": "status",
                },
            )
        ],
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["status"]) == ["A", "MISSING", "MISSING", "I"]


def test_replace_values_no_column():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame(
        {
            "status": ["active", None, "inactive"],
            "flag": [None, "active", "inactive"],
        }
    )

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            (
                "replace_values",
                {"mapping": {None: "MISSING", "active": "A", "inactive": "I"}},
            ),
        ],
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["status"]) == ["A", "MISSING", "I"]
    assert list(result_df["flag"]) == ["MISSING", "A", "I"]


def test_replace_values_direct_api():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"status": ["active", "inactive", "active"]})

    frame = ar.from_pandas(df)

    result = ar.replace_values(
        frame, mapping={"active": "A", "inactive": "I"}, column="status"
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["status"]) == ["A", "I", "A"]


def test_replace_values_missing_column_raises_clear_error():
    import pandas as pd
    import pytest

    import arnio as ar

    frame = ar.from_pandas(pd.DataFrame({"status": ["active", "inactive"]}))

    with pytest.raises(KeyError, match="Column 'missing' not found"):
        ar.pipeline(
            frame,
            [
                (
                    "replace_values",
                    {"mapping": {"active": "A"}, "column": "missing"},
                ),
            ],
        )


def test_replace_values_invalid_mapping_type_raises_clear_error():
    import pandas as pd
    import pytest

    import arnio as ar

    frame = ar.from_pandas(pd.DataFrame({"status": ["active"]}))

    with pytest.raises(TypeError, match="mapping must be a dict-like mapping"):
        ar.replace_values(frame, mapping=[("active", "A")], column="status")


def test_replace_values_empty_mapping_rejected():
    import pandas as pd
    import pytest

    import arnio as ar

    frame = ar.from_pandas(pd.DataFrame({"status": ["active"]}))

    with pytest.raises(ValueError, match="mapping must not be empty"):
        ar.replace_values(frame, mapping={}, column="status")


def test_replace_values_mapping_value_to_none():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"status": ["active", "inactive"]})
    frame = ar.from_pandas(df)

    result = ar.replace_values(
        frame,
        mapping={"inactive": None},
        column="status",
    )

    result_df = ar.to_pandas(result)
    assert pd.isna(result_df["status"].iloc[1])


def test_replace_values_direct_pandas_does_not_mutate_input():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"status": ["active", "inactive"]})

    out = ar.replace_values(df, mapping={"active": "A"}, column="status")

    # original should be untouched
    assert list(df["status"]) == ["active", "inactive"]
    # output should be replaced
    assert list(out["status"]) == ["A", "inactive"]


def test_register_step_validates_callable():
    """Test that register_step raises TypeError immediately for non-callables."""
    import pytest

    from arnio.pipeline import register_step

    with pytest.raises(TypeError, match="expected a callable"):
        register_step("bad", 123)


def test_register_step_validates_name():
    """Test that register_step raises ValueError for invalid names."""
    import pytest

    from arnio.pipeline import register_step

    for invalid_name in ["", "   ", None]:
        with pytest.raises(ValueError, match="Expected a non-empty string"):
            register_step(invalid_name, lambda x: x)


def test_register_step_execution_flow():
    """Test that a valid registered custom step executes cleanly in the pipeline."""
    import pandas as pd

    from arnio.convert import from_pandas, to_pandas
    from arnio.pipeline import pipeline, register_step

    def custom_add_col(df: pd.DataFrame) -> pd.DataFrame:
        df["verified"] = True
        return df

    register_step("custom_add_col_step", custom_add_col)

    initial_df = pd.DataFrame({"id": [1, 2]})
    frame = from_pandas(initial_df)

    result_frame = pipeline(frame, [("custom_add_col_step",)])

    final_df = to_pandas(result_frame)
    assert "verified" in final_df.columns
    assert final_df["verified"].all()
