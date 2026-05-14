"""Tests for the pipeline function."""

import arnio as ar


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

    def test_empty_pipeline(self, sample_csv):
        frame = ar.read_csv(sample_csv)
        result = ar.pipeline(frame, [])
        assert result.shape == frame.shape

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

        try:
            ar.pipeline(
                frame,
                [("combine_columns", {"columns": [], "output_column": "combined"})],
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "non-empty" in str(e)
