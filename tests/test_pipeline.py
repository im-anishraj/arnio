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

    def test_pipeline_dry_run_validates_builtin_step_arguments(self):
        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", None],
                }
            )
        )

        with pytest.raises(KeyError, match="missing"):
            ar.pipeline(
                frame,
                [
                    ("strip_whitespace", {"subset": ["missing"]}),
                ],
                dry_run=True,
            )

    def test_pipeline_dry_run_mapping_shorthand_does_not_mutate(self):
        original = pd.DataFrame(
            {
                "transaction_id": ["t001", "t002"],
            }
        )
        frame = ar.from_pandas(original)

        result = ar.pipeline(
            frame,
            [
                (
                    "rename_columns",
                    {
                        "transaction_id": "TRANSACTION_ID",
                    },
                ),
            ],
            dry_run=True,
        )

        output = ar.to_pandas(result)

        pd.testing.assert_frame_equal(
            output,
            original,
            check_dtype=False,
        )

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

    def test_pipeline_drop_empty_columns(self, tmp_path):
        csv_path = tmp_path / "pipeline_drop_empty_columns.csv"
        csv_path.write_text(
            'all_null,all_blank,value\n,"",1\n,"   ",2\n',
            encoding="utf-8",
        )
        frame = ar.read_csv(csv_path)

        result = ar.pipeline(
            frame,
            [
                ("drop_empty_columns",),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df.columns) == ["value"]
        assert list(df["value"]) == [1, 2]

    def test_pipeline_trim_column_names(self):
        import pandas as pd

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    " name ": ["Alice"],
                    " age ": [30],
                }
            )
        )

        result = ar.pipeline(
            frame,
            [
                ("trim_column_names",),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df.columns) == ["name", "age"]

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

    def test_pipeline_standardize_missing_tokens(self):
        frame = ar.from_pandas(pd.DataFrame({"value": [1, 2, "N/A"]}))

        result = ar.pipeline(
            frame,
            [
                ("standardize_missing_tokens",),
            ],
        )
        df = ar.to_pandas(result)

        assert pd.isna(df["value"].iloc[2])

    def test_pipeline_supports_namespaced_builtin_steps(self, csv_with_whitespace):
        frame = ar.read_csv(csv_with_whitespace)

        result = ar.pipeline(
            frame,
            [
                ("builtin:strip_whitespace",),
            ],
        )
        df = ar.to_pandas(result)

        assert df["name"].iloc[0] == "Alice"

    def test_pipeline_warns_for_deprecated_builtin_step_alias(
        self,
        csv_with_whitespace,
    ):
        pipeline_module._register_deprecated_step_alias(
            "trim_whitespace",
            "strip_whitespace",
        )
        frame = ar.read_csv(csv_with_whitespace)

        with pytest.warns(
            DeprecationWarning,
            match="trim_whitespace.*strip_whitespace",
        ):
            result = ar.pipeline(
                frame,
                [
                    ("trim_whitespace",),
                ],
            )

        df = ar.to_pandas(result)

        assert df["name"].iloc[0] == "Alice"

    def test_pipeline_supports_namespaced_custom_steps_with_builtin_basename(self):
        def custom_drop_nulls(df):
            df["marker"] = "custom"
            return df

        ar.register_step("team:drop_nulls", custom_drop_nulls)
        frame = ar.from_pandas(pd.DataFrame({"value": [1, None]}))

        result = ar.pipeline(
            frame,
            [
                ("team:drop_nulls",),
            ],
        )
        df = ar.to_pandas(result)

        assert list(df["marker"]) == ["custom", "custom"]
        assert df["value"].isna().sum() == 1

    def test_register_deprecated_step_alias_rejects_unknown_target(self):
        with pytest.raises(ar.UnknownStepError, match="missing_step"):
            pipeline_module._register_deprecated_step_alias(
                "legacy_step",
                "missing_step",
            )

    def test_register_deprecated_step_alias_rejects_registered_name_conflict(self):
        with pytest.raises(ValueError, match="already registered"):
            pipeline_module._register_deprecated_step_alias(
                "drop_nulls",
                "strip_whitespace",
            )

    def test_register_step_rejects_reserved_deprecated_alias_name(self):
        pipeline_module._register_deprecated_step_alias(
            "legacy_strip",
            "strip_whitespace",
        )

        def custom_step(df):
            return df

        with pytest.raises(ValueError, match="deprecated pipeline step alias"):
            ar.register_step("legacy_strip", custom_step)

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


    def test_split_column_step(self, tmp_path):
        path = tmp_path / "names.csv"
        path.write_text("name\nAda Lovelace\nGrace Hopper\n")
        frame = ar.read_csv(path)

        result = ar.pipeline(
            frame,
            [
                (
                    "split_column",
                    {
                        "column": "name",
                        "into": ["first", "last"],
                        "sep": " ",
                        "drop": True,
                    },
                ),
            ],
        )

        df = ar.to_pandas(result)
        assert "name" not in df.columns
        assert df["first"].tolist() == ["Ada", "Grace"]
        assert df["last"].tolist() == ["Lovelace", "Hopper"]

    def test_split_column_rejects_existing_output_column(self, tmp_path):
        path = tmp_path / "names.csv"
        path.write_text("name,first\nAda Lovelace,Ada\n")
        frame = ar.read_csv(path)

        try:
            ar.pipeline(
                frame,
                [("split_column", {"column": "name", "into": ["first"], "sep": " "})],
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Output column already exists" in str(e)

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

    def test_pipeline_rejects_empty_step(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Invalid step format"):
            ar.pipeline(frame, [()])

    def test_pipeline_rejects_string_step(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Invalid step format"):
            ar.pipeline(frame, ["drop_nulls"])

    def test_pipeline_rejects_non_tuple_step(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Invalid step format"):
            ar.pipeline(frame, [123])

    def test_pipeline_dry_run_metadata_preserves_original_row_counts(self):

        frame = ar.from_pandas(
            pd.DataFrame(
                {
                    "name": ["Alice", None, "Bob"],
                }
            )
        )

        result, metadata = ar.pipeline(
            frame,
            [("drop_nulls",)],
            dry_run=True,
            return_metadata=True,
        )

        assert result.shape[0] == 3

        row_counts = metadata["row_counts"]

        assert row_counts[0]["before"] == 3
        assert row_counts[0]["after"] == 3
        assert row_counts[0]["dry_run"] is True

    def test_register_step_invalid_name_type(self):
        """Raise ValueError when name is not a string."""
        with pytest.raises(
            ValueError, match="parameter 'name' must be a non-empty string"
        ):
            ar.register_step(123, lambda df: df)

    def test_register_step_empty_name(self):
        """Raise ValueError when name is empty string."""
        with pytest.raises(
            ValueError, match="parameter 'name' must be a non-empty string"
        ):
            ar.register_step("", lambda df: df)

    def test_register_step_non_callable_fn(self):
        """Raise TypeError when fn is not callable."""
        with pytest.raises(TypeError, match="parameter 'fn' must be a callable object"):
            ar.register_step("bad_step", 123)

    def test_register_step_non_bool_overwrite(self):
        """Raise TypeError when overwrite is not a bool."""
        with pytest.raises(TypeError, match="parameter 'overwrite' must be a bool"):
            ar.register_step("some_step", lambda df: df, overwrite="yes")

    def test_unregister_step_invalid_name_type(self):
        """Raise TypeError when name is not a string."""
        with pytest.raises(TypeError, match="parameter 'name' must be a string"):
            ar.unregister_step(["bad_step"])

    def test_unregister_step_empty_name(self):
        """Raise ValueError when name is empty string."""
        with pytest.raises(
            ValueError, match="parameter 'name' must be a non-empty string"
        ):
            ar.unregister_step("")

    def test_pipeline_filter_rows_non_string_column_raises_type_error(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))
        with pytest.raises(TypeError, match="column must be a non-empty string"):
            ar.pipeline(
                frame, [("filter_rows", {"column": 123, "op": "==", "value": 1})]
            )

    def test_pipeline_filter_rows_non_string_op_raises_type_error(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        with pytest.raises(TypeError, match="op must be a string"):
            ar.pipeline(
                frame, [("filter_rows", {"column": "x", "op": ["=="], "value": 1})]
            )


class TestPipelineDryRunIntermediateFrame:
    """Regression tests for dry_run validating against intermediate frame."""

    def test_dry_run_rename_then_validate(self):
        frame = ar.from_pandas(pd.DataFrame({"old_name": [" Alice "]}))
        result = ar.pipeline(
            frame,
            [
                ("rename_columns", {"old_name": "name"}),
                ("validate_columns_exist", {"columns": ["name"]}),
            ],
            dry_run=True,
        )
        assert result is frame
        assert "old_name" in ar.to_pandas(result).columns

    def test_dry_run_drop_then_validate_column_gone(self):
        frame = ar.from_pandas(pd.DataFrame({"keep_me": [1], "drop_me": [2]}))
        result = ar.pipeline(
            frame,
            [
                ("drop_columns", {"columns": ["drop_me"]}),
                ("validate_columns_exist", {"columns": ["keep_me"]}),
            ],
            dry_run=True,
        )
        assert result is frame

    def test_dry_run_drop_then_validate_missing_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"keep_me": [1], "drop_me": [2]}))
        with pytest.raises(KeyError, match="Missing columns"):
            ar.pipeline(
                frame,
                [
                    ("drop_columns", {"columns": ["keep_me"]}),
                    ("validate_columns_exist", {"columns": ["keep_me"]}),
                ],
                dry_run=True,
            )

    def test_dry_run_rename_then_validate_missing_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"old_name": [" Alice "]}))
        with pytest.raises(KeyError, match="Missing columns"):
            ar.pipeline(
                frame,
                [
                    ("rename_columns", {"old_name": "name"}),
                    ("validate_columns_exist", {"columns": ["old_name"]}),
                ],
                dry_run=True,
            )

    def test_dry_run_select_then_validate(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1], "y": [2], "z": [3]}))
        result = ar.pipeline(
            frame,
            [
                ("select_columns", {"columns": ["x", "y"]}),
                ("validate_columns_exist", {"columns": ["x", "y"]}),
            ],
            dry_run=True,
        )
        assert result is frame

    def test_dry_run_select_then_validate_dropped_raises(self):
        frame = ar.from_pandas(pd.DataFrame({"x": [1], "y": [2], "z": [3]}))
        with pytest.raises(KeyError, match="Missing columns"):
            ar.pipeline(
                frame,
                [
                    ("select_columns", {"columns": ["x", "y"]}),
                    ("validate_columns_exist", {"columns": ["z"]}),
                ],
                dry_run=True,
            )

    def test_dry_run_and_real_consistency(self):
        frame = ar.from_pandas(
            pd.DataFrame({"old_name": [" Alice "], "extra": [" Bob "]})
        )
        dry_result = ar.pipeline(
            frame,
            [
                ("rename_columns", {"old_name": "name"}),
                ("drop_columns", {"columns": ["extra"]}),
                ("strip_whitespace",),
            ],
            dry_run=True,
        )
        real_result = ar.pipeline(
            frame,
            [
                ("rename_columns", {"old_name": "name"}),
                ("drop_columns", {"columns": ["extra"]}),
                ("strip_whitespace",),
            ],
            dry_run=False,
        )
        assert dry_result is frame
        assert "name" in ar.to_pandas(real_result).columns
        assert "old_name" not in ar.to_pandas(real_result).columns
        assert "extra" not in ar.to_pandas(real_result).columns

    def test_dry_run_does_not_mutate_original(self):
        original = pd.DataFrame({"delete_me": [1, 2], "keep": [3, 4]})
        frame = ar.from_pandas(original.copy())
        ar.pipeline(
            frame,
            [
                ("drop_columns", {"columns": ["delete_me"]}),
                ("validate_columns_exist", {"columns": ["keep"]}),
            ],
            dry_run=True,
        )
        pd.testing.assert_frame_equal(ar.to_pandas(frame), original, check_dtype=False)

    def test_dry_run_python_step_advances_intermediate_frame(self):
        def add_column_step(df):
            df["added"] = "present"
            return df

        ar.register_step("test_dry_add_column", add_column_step)
        frame = ar.from_pandas(pd.DataFrame({"x": [1]}))
        ar.pipeline(
            frame,
            [
                ("test_dry_add_column",),
                ("validate_columns_exist", {"columns": ["added"]}),
            ],
            dry_run=True,
        )

    def test_dry_run_transform_then_validate_column_content_type(self):
        frame = ar.from_pandas(pd.DataFrame({"age_str": ["10", "20", "30"]}))
        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"age_str": "int64"}),
                ("validate_columns_exist", {"columns": ["age_str"]}),
            ],
            dry_run=True,
        )
        assert result is frame

    def test_dry_run_rename_with_mapping_shorthand_then_validate(self):
        frame = ar.from_pandas(pd.DataFrame({"old": [1], "other": [2]}))
        result = ar.pipeline(
            frame,
            [
                ("rename_columns", {"old": "new"}),
                ("validate_columns_exist", {"columns": ["new"]}),
            ],
            dry_run=True,
        )
        assert result is frame

    def test_dry_run_metadata_still_uses_original_rows(self):
        frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", None, "Bob", None]}))
        original_rows = frame.shape[0]
        _, meta = ar.pipeline(
            frame,
            [("drop_nulls",), ("validate_columns_exist", {"columns": ["name"]})],
            dry_run=True,
            return_metadata=True,
        )
        for entry in meta["row_counts"]:
            assert entry["after"] == original_rows
            assert entry["dry_run"] is True


def test_get_builtin_step_signatures_returns_normalized_signatures():
    signatures = ar.get_builtin_step_signatures()

    assert isinstance(signatures, dict)
    assert "drop_nulls" in signatures
    assert isinstance(signatures["drop_nulls"], Signature)
    assert "frame" not in signatures["drop_nulls"].parameters
    assert list(signatures["drop_nulls"].parameters) == ["subset"]


def test_get_builtin_step_signatures_includes_builtin_python_steps_only():
    def custom_step(df, threshold=1):
        return df

    ar.register_step("custom_signature_probe", custom_step)

    signatures = ar.get_builtin_step_signatures()

    assert "filter_rows" in signatures
    assert "replace_values" in signatures
    assert "custom_signature_probe" not in signatures


def test_filter_rows_greater_than():

    df = pd.DataFrame({"age": [20, 30, 40]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "age", "op": ">", "value": 25})]
    )

    result_df = ar.to_pandas(result)

    assert len(result_df) == 2
    assert list(result_df["age"]) == [30, 40]


def test_filter_rows_equal_string():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"name": ["Alice", "Bob", "Alice"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "name", "op": "==", "value": "Alice"})]
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["name"]) == ["Alice", "Alice"]


def test_filter_rows_bool():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"active": [True, False, True]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame, [("filter_rows", {"column": "active", "op": "==", "value": True})]
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["active"]) == [True, True]


def test_filter_rows_invalid_operator():
    import pandas as pd
    import pytest

    import arnio as ar

    df = pd.DataFrame({"age": [20, 30]})

    frame = ar.from_pandas(df)

    with pytest.raises(ValueError):
        ar.pipeline(
            frame, [("filter_rows", {"column": "age", "op": "invalid", "value": 25})]
        )


def test_filter_rows_direct_api():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"age": [20, 30, 40]})

    frame = ar.from_pandas(df)

    result = ar.filter_rows(frame, column="age", op=">", value=25)

    result_df = ar.to_pandas(result)

    assert list(result_df["age"]) == [30, 40]


def test_filter_rows_pipeline_invalid_comparison_keeps_column_context():
    import pandas as pd
    import pytest

    import arnio as ar

    frame = ar.from_pandas(pd.DataFrame({"name": ["Alice", "Bob"]}))

    with pytest.raises(TypeError, match="filter_rows: cannot compare column 'name'"):
        ar.pipeline(frame, [("filter_rows", {"column": "name", "op": ">", "value": 1})])


def test_round_numeric_columns_pipeline():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"price": [10.555, 20.123]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [("round_numeric_columns", {"subset": ["price"], "decimals": 2})],
    )

    result_df = ar.to_pandas(result)

    assert list(result_df["price"]) == [10.56, 20.12]


def test_pipeline_normalize_unicode():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame({"text": ["cafe\u0301"]})

    frame = ar.from_pandas(df)

    result = ar.pipeline(
        frame,
        [
            ("normalize_unicode",),
        ],
    )

    result_df = ar.to_pandas(result)

    assert result_df["text"].iloc[0] == "café"


def test_normalize_unicode_invalid_form():
    import pandas as pd
    import pytest

    import arnio as ar

    df = pd.DataFrame({"text": ["cafe\u0301"]})

    frame = ar.from_pandas(df)

    with pytest.raises(ValueError):
        ar.normalize_unicode(frame, form="INVALID")


def test_normalize_unicode_subset():
    import pandas as pd

    import arnio as ar

    df = pd.DataFrame(
        {
            "text": ["cafe\u0301"],
            "other": ["test"],
        }
    )

    frame = ar.from_pandas(df)

    result = ar.normalize_unicode(frame, subset=["text"])

    result_df = ar.to_pandas(result)

    assert result_df["text"].iloc[0] == "café"


def test_normalize_unicode_unknown_subset():
    import pandas as pd
    import pytest

    import arnio as ar

    df = pd.DataFrame({"text": ["cafe\u0301"]})

    frame = ar.from_pandas(df)

    with pytest.raises(KeyError):
        ar.normalize_unicode(frame, subset=["missing"])


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
            ),
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


def test_pipeline_drop_columns_matching():
    df = pd.DataFrame({"temp_a": [1], "temp_b": [2], "keep_c": [3]})
    frame = ar.from_pandas(df)
    result = ar.pipeline(frame, [("drop_columns_matching", {"pattern": "^temp_"})])
    result_df = ar.to_pandas(result)
    assert list(result_df.columns) == ["keep_c"]


def test_pipeline_drop_columns_matching_all_columns():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    frame = ar.from_pandas(df)
    with pytest.raises(ValueError, match="Pattern matches all columns"):
        ar.pipeline(frame, [("drop_columns_matching", {"pattern": ".*"})])


def test_register_step_conflict_raises_value_error():
    def dummy_step(df):
        return df

    with pytest.raises(ValueError, match="conflicts with built-in C\\+\\+ step"):
        ar.register_step("drop_nulls", dummy_step)


def test_register_step_success():
    import pandas as pd

    from arnio.pipeline import _PYTHON_STEP_REGISTRY

    def custom_uppercase_step(df, column_name: str):
        df[column_name] = df[column_name].str.upper()
        return df

    step_name = "test_custom_upper_mutation"
    ar.register_step(step_name, custom_uppercase_step)

    assert step_name in _PYTHON_STEP_REGISTRY

    df = pd.DataFrame({"name": ["bar", "boo", "baz"]})
    frame = ar.from_pandas(df)

    result_frame = ar.pipeline(frame, [(step_name, {"column_name": "name"})])

    processed_df = ar.to_pandas(result_frame)
    assert processed_df["name"].tolist() == ["BAR", "BOO", "BAZ"]


def test_register_step_duplicate_custom_raises_value_error():
    def step_v1(df):
        return df

    def step_v2(df):
        return df

    step_name = "test_policy_duplicate_reject"
    ar.register_step(step_name, step_v1)

    with pytest.raises(ValueError, match="already registered as a custom Python step"):
        ar.register_step(step_name, step_v2)


def test_register_step_explicit_overwrite_success():
    import pandas as pd

    def add_one(df):
        df["val"] = df["val"] + 1
        return df

    def add_ten(df):
        df["val"] = df["val"] + 10
        return df

    step_name = "test_policy_overwrite_mutation"

    ar.register_step(step_name, add_one)
    ar.register_step(step_name, add_ten, overwrite=True)

    df = pd.DataFrame({"val": [0]})
    frame = ar.from_pandas(df)
    result = ar.pipeline(frame, [(step_name,)])

    processed_df = ar.to_pandas(result)
    assert processed_df["val"].tolist() == [10]


def test_register_step_overwrite_cannot_bypass_builtin_protection():
    def dummy_step(df):
        return df

    with pytest.raises(ValueError, match="conflicts with built-in C\\+\\+ step"):
        ar.register_step("drop_nulls", dummy_step, overwrite=True)


def test_register_step_rejects_reserved_builtin_namespace():
    def dummy_step(df):
        return df

    with pytest.raises(ValueError, match="reserved for built-in pipeline steps"):
        ar.register_step("builtin:custom_step", dummy_step)


def test_list_steps_includes_builtins_in_deterministic_order():
    steps = ar.list_steps()

    assert steps == sorted(steps)
    assert "drop_nulls" in steps
    assert "strip_whitespace" in steps
    assert "standardize_missing_tokens" in steps


def test_list_steps_includes_registered_custom_steps():
    def custom_step(df):
        return df

    ar.register_step("list_steps_probe", custom_step)

    steps = ar.list_steps()

    assert "list_steps_probe" in steps


def test_reset_steps_removes_custom_registered_steps():
    import pandas as pd

    def custom_step(df, **kwargs):
        return df

    ar.register_step("custom_step", custom_step)

    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1, 2, 3],
            }
        )
    )

    result = ar.pipeline(
        frame,
        [
            ("custom_step",),
        ],
    )

    assert ar.to_pandas(result)["a"].tolist() == [1, 2, 3]

    ar.reset_steps()

    with pytest.raises(ar.UnknownStepError):
        ar.pipeline(
            frame,
            [
                ("custom_step",),
            ],
        )


def test_reset_steps_preserves_builtin_python_steps():
    import pandas as pd

    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "value": [" yes ", " no "],
            }
        )
    )

    ar.reset_steps()

    result = ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
        ],
    )

    cleaned = ar.to_pandas(result)

    assert cleaned["value"].tolist() == ["yes", "no"]


def test_reset_steps_removes_overwritten_custom_steps():
    import pandas as pd

    def first(df, **kwargs):
        return df

    def second(df, **kwargs):
        return df

    ar.register_step("temp_step", first)
    ar.register_step("temp_step", second, overwrite=True)

    ar.reset_steps()

    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "a": [1],
            }
        )
    )

    with pytest.raises(ar.UnknownStepError):
        ar.pipeline(
            frame,
            [
                ("temp_step",),
            ],
        )


def test_pipeline_verbose_disabled_by_default(caplog):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["A", "B"],
            }
        )
    )

    ar.pipeline(
        frame,
        [
            ("drop_nulls",),
        ],
    )

    assert len(caplog.records) == 0


def test_pipeline_verbose_logs_builtin_step(caplog):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": [" A ", " B "],
            }
        )
    )

    caplog.set_level("INFO", logger="arnio")

    ar.pipeline(
        frame,
        [
            ("strip_whitespace",),
        ],
        verbose=True,
    )

    assert any("strip_whitespace" in record.message for record in caplog.records)


def custom_step(df):
    return df


def test_pipeline_verbose_logs_custom_step(caplog):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "x": [1, 2],
            }
        )
    )

    ar.register_step(
        "custom_step",
        custom_step,
        overwrite=True,
    )

    caplog.set_level("INFO", logger="arnio")

    ar.pipeline(
        frame,
        [
            ("custom_step",),
        ],
        verbose=True,
    )

    assert any("custom_step" in record.message for record in caplog.records)


def drop_first_row(df):
    return df.head(1)


def test_pipeline_verbose_logs_row_change(caplog):
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "x": [1, 2, 3],
            }
        )
    )

    ar.register_step(
        "drop_first_row",
        drop_first_row,
        overwrite=True,
    )

    caplog.set_level("INFO", logger="arnio")

    ar.pipeline(
        frame,
        [
            ("drop_first_row",),
        ],
        verbose=True,
    )

    assert any("rows: 3 -> 1" in record.message for record in caplog.records)


def test_pipeline_dry_run_with_metadata_row_counts_unchanged():
    """dry_run=True: row_counts.after must equal row_counts.before."""
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["Alice", None, "Bob", None],
                "age": [25, 30, None, 40],
            }
        )
    )
    original_rows = frame.shape[0]  # 4

    _, meta = ar.pipeline(
        frame,
        [("drop_nulls",), ("strip_whitespace",)],
        dry_run=True,
        return_metadata=True,
    )

    for entry in meta["row_counts"]:
        assert entry["after"] == original_rows, (
            f"Step '{entry['step']}': expected after={original_rows} "
            f"in dry_run, got {entry['after']}"
        )
        assert entry["dry_run"] is True


def test_pipeline_dry_run_with_metadata_step_timings_consistent():
    """dry_run=True: step_timings.seconds must be non-negative with dry_run flag."""
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["Alice", None, "Bob", None],
            }
        )
    )

    _, meta = ar.pipeline(
        frame,
        [("drop_nulls",), ("strip_whitespace",)],
        dry_run=True,
        return_metadata=True,
    )

    for entry in meta["step_timings"]:
        assert entry["seconds"] >= 0
        assert entry["dry_run"] is True


def test_pipeline_dry_run_false_metadata_unchanged():
    """dry_run=False: existing metadata shape must not be affected by the fix."""
    frame = ar.from_pandas(
        pd.DataFrame(
            {
                "name": ["Alice", None, "Bob", None],
            }
        )
    )

    result, meta = ar.pipeline(
        frame,
        [("drop_nulls",)],
        dry_run=False,
        return_metadata=True,
    )

    assert meta["row_counts"][0]["before"] == frame.shape[0]
    assert meta["row_counts"][0]["after"] == result.shape[0]
    assert meta["row_counts"][0]["after"] < frame.shape[0]
    assert meta["step_timings"][0]["seconds"] >= 0
    assert meta["row_counts"][0].get("dry_run") is False


def test_pipeline_return_metadata_non_bool_raises():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="return_metadata"):
        ar.pipeline(frame, [("strip_whitespace",)], return_metadata="yes")


def test_pipeline_dry_run_non_bool_raises():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="dry_run"):
        ar.pipeline(frame, [("strip_whitespace",)], dry_run=1)


def test_pipeline_verbose_non_bool_raises():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    with pytest.raises(TypeError, match="verbose"):
        ar.pipeline(frame, [("strip_whitespace",)], verbose=None)


def test_pipeline_bool_flags_valid():
    frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
    result = ar.pipeline(
        frame,
        [("strip_whitespace",)],
        return_metadata=True,
        dry_run=False,
        verbose=True,
    )
    assert isinstance(result, tuple)


class TestRegisterStepValidation:
    @pytest.fixture(autouse=True)
    def cleanup_registry(self):
        """Ensure the global custom step registry resets after every single test in this class."""
        yield
        from arnio.pipeline import reset_steps

        reset_steps()

    # --- Happy Path ---
    def test_registers_valid_callable(self):
        from arnio.pipeline import list_steps, register_step

        def dummy_clean(df):
            return df

        register_step("custom_dummy_step", dummy_clean)
        assert "custom_dummy_step" in list_steps()

    def test_allows_intentional_overwrite(self):
        from arnio.pipeline import register_step

        def first_step(df):
            return df

        def second_step(df):
            return df

        register_step("overwrite_step", first_step)
        register_step("overwrite_step", second_step, overwrite=True)

    # --- Edge Cases & Parameter Boundaries ---
    def test_rejects_non_callable_objects(self):
        from arnio.pipeline import register_step

        """Verify TypeError is raised immediately for numbers, strings, and instances."""
        with pytest.raises(TypeError, match="must be a callable object"):
            register_step("bad_int", 123)
        with pytest.raises(TypeError, match="must be a callable object"):
            register_step("bad_str", "not_a_callable_function")
        with pytest.raises(TypeError, match="must be a callable object"):
            register_step("bad_dict", {"a": 1})

    def test_rejects_empty_string_names(self):
        from arnio.pipeline import register_step

        def dummy_clean(df):
            return df

        with pytest.raises(ValueError, match="must be a non-empty string"):
            register_step("", dummy_clean)

    def test_rejects_whitespace_only_names(self):
        from arnio.pipeline import register_step

        def dummy_clean(df):
            return df

        with pytest.raises(ValueError, match="must be a non-empty string"):
            register_step("    ", dummy_clean)

    def test_rejects_invalid_name_types(self):
        from arnio.pipeline import register_step

        def dummy_clean(df):
            return df

        with pytest.raises(ValueError, match="must be a non-empty string"):
            register_step(None, dummy_clean)  # type: ignore
        with pytest.raises(ValueError, match="must be a non-empty string"):
            register_step(42, dummy_clean)  # type: ignore


class TestPipelineStepContainerValidation:
    @pytest.fixture
    def frame(self, sample_csv):
        return ar.read_csv(sample_csv)

    @pytest.mark.parametrize(
        "invalid_steps",
        [None, "drop_nulls", b"drop_nulls", {"drop_nulls": {}}, ("drop_nulls",)],
    )
    def test_pipeline_rejects_invalid_step_containers(self, frame, invalid_steps):
        with pytest.raises(TypeError):
            ar.pipeline(frame, invalid_steps)

    def test_pipeline_rejects_bare_step_tuple_with_helpful_message(self, frame):
        with pytest.raises(TypeError, match=r"\[\(\'drop_nulls\',\)\]"):
            ar.pipeline(frame, ("drop_nulls",))

    def test_pipeline_accepts_valid_step_container(self, frame):
        result = ar.pipeline(frame, [("strip_whitespace",)])
        assert isinstance(result, ar.ArFrame)


class TestExecutionSummary:
    def test_execution_summary_present_in_metadata(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        _, metadata = ar.pipeline(
            frame,
            [("drop_nulls",)],
            return_metadata=True,
        )
        assert "execution_summary" in metadata

    def test_execution_summary_total_runtime_is_float(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        _, metadata = ar.pipeline(
            frame,
            [("drop_nulls",)],
            return_metadata=True,
        )
        assert isinstance(metadata["execution_summary"]["total_runtime_ms"], float)

    def test_execution_summary_steps_count_matches(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        _, metadata = ar.pipeline(
            frame,
            [("drop_nulls",), ("strip_whitespace",)],
            return_metadata=True,
        )
        assert len(metadata["execution_summary"]["steps"]) == 2

    def test_execution_summary_step_fields(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        _, metadata = ar.pipeline(
            frame,
            [("drop_nulls",)],
            return_metadata=True,
        )
        step = metadata["execution_summary"]["steps"][0]
        assert step["name"] == "drop_nulls"
        assert step["status"] == "success"
        assert isinstance(step["runtime_ms"], float)
        assert isinstance(step["rows_before"], int)
        assert isinstance(step["rows_after"], int)
        assert isinstance(step["rows_affected"], int)
        assert isinstance(step["columns_before"], int)
        assert isinstance(step["columns_after"], int)

    def test_execution_summary_only_contains_successful_steps(self):
        def bad_step(df):
            raise ValueError("boom")

        ar.register_step("bad_step_summary", bad_step)
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2]}))
        with pytest.raises(Exception):
            ar.pipeline(
                frame,
                [("drop_nulls",), ("bad_step_summary",)],
                return_metadata=True,
            )
        ar.unregister_step("bad_step_summary")

        frame2 = ar.from_pandas(pd.DataFrame({"a": [1, None, 2]}))
        _, metadata = ar.pipeline(
            frame2,
            [("drop_nulls",), ("strip_whitespace",)],
            return_metadata=True,
        )
        assert all(
            s["status"] == "success" for s in metadata["execution_summary"]["steps"]
        )
        assert len(metadata["execution_summary"]["steps"]) == 2

    def test_execution_summary_dry_run_rows_unchanged(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        _, metadata = ar.pipeline(
            frame,
            [("drop_nulls",)],
            return_metadata=True,
            dry_run=True,
        )
        step = metadata["execution_summary"]["steps"][0]
        assert step["rows_before"] == step["rows_after"]
        assert step["rows_affected"] == 0

    def test_execution_summary_python_step(self):
        def add_col(df):
            df["x"] = 1
            return df

        ar.register_step("es_python_step", add_col)
        frame = ar.from_pandas(pd.DataFrame({"a": [1, 2, 3]}))
        _, metadata = ar.pipeline(
            frame,
            [("es_python_step",)],
            return_metadata=True,
        )
        ar.unregister_step("es_python_step")
        step = metadata["execution_summary"]["steps"][0]
        assert step["name"] == "es_python_step"
        assert step["status"] == "success"


def test_pipeline_serialization_errors():
    with pytest.raises(PipelineSerializationError, match="File not found"):
        load_pipeline("non_existent_file.json")


def test_malformed_pipeline_structures():
    with tempfile.TemporaryDirectory() as tmpdirname:
        dict_path = os.path.join(tmpdirname, "dict.json")
        with open(dict_path, "w") as f:
            f.write('{"this_is_a_dictionary_not_a_list": true}')
        with pytest.raises(
            PipelineSerializationError, match="Pipeline steps must be a list"
        ):
            load_pipeline(dict_path)

        empty_path = os.path.join(tmpdirname, "empty.json")
        with open(empty_path, "w") as f:
            f.write("")
        with pytest.raises(PipelineSerializationError, match="file is empty"):
            load_pipeline(empty_path)

        bad_step_path = os.path.join(tmpdirname, "bad_step.json")
        with open(bad_step_path, "w") as f:
            f.write('[["drop_nulls", "not_a_dictionary_kwargs"]]')
        with pytest.raises(
            PipelineSerializationError,
            match="The second element of a step must be a dictionary",
        ):
            load_pipeline(bad_step_path)


def test_roundtrip_kwargs_determinism():
    original_steps = [
        ("cast_types", {"mapping": {"score": "float64", "age": "int64"}}),
        ("rename_columns", {"mapping": {"old_name": "new_name", "a": "b"}}),
    ]
    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "kwargs_job.json")
        save_pipeline(original_steps, filepath)
        loaded_steps = load_pipeline(filepath)
        assert loaded_steps == original_steps


def test_unknown_step_serialization():
    steps = [("this_step_does_not_exist", {"foo": "bar"})]
    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "unknown_step.json")
        save_pipeline(steps, filepath)
        loaded_steps = load_pipeline(filepath)
        assert loaded_steps == steps


def test_pipeline_execution_roundtrip():
    """Verify that a loaded pipeline can be directly executed against an ArFrame."""
    import pandas as pd

    import arnio as ar

    # 1. Create a dummy frame with whitespace and a null
    df = pd.DataFrame({"name": [" Alice ", "Bob", None]})
    frame = ar.from_pandas(df)

    # 2. Define the steps
    steps = [
        ("drop_nulls",),
        ("strip_whitespace", {"subset": ["name"]}),
    ]

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "execution_job.json")

        # 3. Save and load the pipeline
        ar.save_pipeline(steps, filepath)
        loaded_steps = ar.load_pipeline(filepath)

        # 4. Execute the loaded pipeline
        result = ar.pipeline(frame, loaded_steps)
        result_df = ar.to_pandas(result)

        # 5. Assert the cleaning actually happened
        assert len(result_df) == 2
        assert result_df["name"].iloc[0] == "Alice"


def test_yaml_pipeline_serialization_roundtrip():
    """Verify that a pipeline can be saved to and loaded from a YAML file."""
    import pytest

    pytest.importorskip("yaml")
    import os
    import tempfile

    import arnio as ar

    steps = [
        ("drop_nulls",),
        ("strip_whitespace", {"subset": ["name"]}),
    ]

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "pipeline.yaml")

        # Save and load the pipeline
        ar.save_pipeline(steps, filepath)
        loaded_steps = ar.load_pipeline(filepath)

        # Assert the loaded steps match the original steps
        assert steps == loaded_steps


def test_save_pipeline_atomic_failure():
    """Verify that an existing file is unchanged after a serialization error."""
    import os
    import tempfile

    import arnio as ar
    from arnio.exceptions import PipelineSerializationError

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "pipeline.json")

        # Create a valid pre-existing file
        with open(filepath, "w") as f:
            f.write('["original_content"]')

        # Attempt to save a pipeline with an unserializable object (a function)
        invalid_steps = [("drop_nulls", {"func": lambda x: x})]

        try:
            ar.save_pipeline(invalid_steps, filepath)
        except PipelineSerializationError:
            pass

        # Assert the original file was completely untouched
        with open(filepath) as f:
            assert f.read() == '["original_content"]'


def test_save_pipeline_validation():
    """Verify that malformed steps are rejected without creating a file."""
    import os
    import tempfile

    import arnio as ar
    from arnio.exceptions import PipelineSerializationError

    with tempfile.TemporaryDirectory() as tmpdirname:
        filepath = os.path.join(tmpdirname, "pipeline.json")

        # Attempt to save a malformed structure
        malformed_steps = [[], ("drop_nulls", "not-a-dict")]

        try:
            ar.save_pipeline(malformed_steps, filepath)
        except PipelineSerializationError:
            pass

        # Assert the bad structure was caught and no file was ever created
        assert not os.path.exists(filepath)
