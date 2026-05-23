"""Tests for the pipeline function."""

import importlib
import threading
from concurrent.futures import ThreadPoolExecutor
from inspect import Signature

import pandas as pd
import pytest

import arnio as ar

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

    def test_pipeline_shorthand_with_column_named_mapping_cast_types(self):
        import pandas as pd

        import arnio as ar

        frame = ar.from_pandas(pd.DataFrame({"mapping": ["1", "2"]}))

        result = ar.pipeline(
            frame,
            [
                ("cast_types", {"mapping": "int64"}),
            ],
        )

        assert result.dtypes["mapping"] == "int64"

    def test_pipeline_shorthand_with_column_named_mapping_rename_columns(self):
        import pandas as pd

        import arnio as ar

        frame = ar.from_pandas(pd.DataFrame({"mapping": [1, 2]}))

        result = ar.pipeline(
            frame,
            [
                ("rename_columns", {"mapping": "new_mapping_col"}),
            ],
        )

        assert "new_mapping_col" in result.columns
        assert "mapping" not in result.columns

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

    def test_pipeline_drop_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(
            frame,
            [
                ("drop_columns", {"columns": ["active"]}),
            ],
        )

        assert result.columns == ["name", "age", "email"]

    def test_pipeline_drop_columns_allows_empty_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [("drop_columns", {"columns": []})])

        assert result is frame

    def test_pipeline_drop_columns_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Columns not found in frame"):
            ar.pipeline(
                frame,
                [("drop_columns", {"columns": ["missing"]})],
            )

    def test_pipeline_select_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        result = ar.pipeline(
            frame,
            [
                ("select_columns", {"columns": ["email", "name"]}),
            ],
        )

        assert result.columns == ["email", "name"]

    def test_pipeline_select_columns_rejects_missing_columns(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Unknown columns"):
            ar.pipeline(
                frame,
                [
                    ("select_columns", {"columns": ["missing"]}),
                ],
            )

    def test_pipeline_select_columns_reject_empty_columns(self, sample_csv):
        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Column selection cannot be empty"):
            ar.pipeline(
                frame,
                [
                    ("select_columns", {"columns": []}),
                ],
            )

    def test_pipeline_select_columns_rejects_duplicates(self, sample_csv):
        import pytest

        frame = ar.read_csv(sample_csv)

        with pytest.raises(ValueError, match="Duplicate column names are not allowed"):
            ar.pipeline(
                frame,
                [
                    ("select_columns", {"columns": ["name", "name"]}),
                ],
            )

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
        assert list(metadata.keys()) == ["applied_steps", "row_counts", "step_timings"]
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
    import pandas as pd

    import arnio as ar

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
