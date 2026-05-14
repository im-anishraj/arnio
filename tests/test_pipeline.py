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

    def test_combine_columns_step(self, tmp_path):
        path = tmp_path / "names.csv"
        path.write_text("first,last,age\nAda,Lovelace,36\nGrace,Hopper,85\n")
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


def test_pipeline_coalesce_columns():
    import pandas as pd

    import arnio as ar

    frame = ar.from_pandas(
        pd.DataFrame({"primary": [None, "a", None], "backup": ["x", "b", None]})
    )

    result = ar.pipeline(
        frame, [("coalesce_columns", {"columns": ["primary", "backup"], "output_column": "resolved"})]
    )

    resolved = ar.to_pandas(result)["resolved"]
    assert resolved.iloc[0] == "x"
    assert resolved.iloc[1] == "a"
    assert resolved.isna().iloc[2]
