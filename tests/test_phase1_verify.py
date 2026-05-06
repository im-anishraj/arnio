"""Verify Phase 1 implementation (to_pandas, from_pandas, registry)."""
import pandas as pd
import arnio as ar

def test_to_pandas_matches_old_version(sample_csv):
    frame = ar.read_csv(sample_csv)
    df_new = ar.to_pandas(frame)
    # Basic shape and null checks
    assert df_new.shape[0] > 0
    assert "name" in df_new.columns

def test_from_pandas_roundtrip():
    df_original = pd.DataFrame({
        "name": ["Alice", "Bob", None],
        "score": [1.5, 2.5, None],
        "count": [1, 2, 3]
    })
    # Cast count to int64 so it handles nulls in pandas correctly if needed
    df_original["count"] = df_original["count"].astype("Int64")
    
    frame = ar.from_pandas(df_original)
    df_roundtrip = ar.to_pandas(frame)
    
    # Assert equality (ignoring specific pandas dtypes since Int64 vs int64 etc might differ slightly)
    pd.testing.assert_frame_equal(df_original, df_roundtrip, check_dtype=False)

def test_python_step_registry(sample_csv):
    def my_step(df, multiplier=2):
        df = df.copy()
        # the score column might have nulls or be string depending on the CSV, let's assume it's numeric 
        # or we can just modify a known column. Let's add a new column to test.
        df["new_score"] = 999 * multiplier
        return df

    ar.register_step("scale_score", my_step)

    frame = ar.read_csv(sample_csv)
    result = ar.pipeline(frame, [
        ("strip_whitespace",),
        ("scale_score", {"multiplier": 3}),
    ])
    df = ar.to_pandas(result)
    assert "new_score" in df.columns
    assert df["new_score"].iloc[0] == 999 * 3

def test_unknown_step_error(sample_csv):
    frame = ar.read_csv(sample_csv)
    try:
        ar.pipeline(frame, [("nonexistent_step",)])
        assert False, "Should have raised UnknownStepError"
    except ar.UnknownStepError as e:
        assert "Unknown pipeline step" in str(e)
