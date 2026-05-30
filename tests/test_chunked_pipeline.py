import pytest

import arnio as ar


def create_dummy_csv(path):
    with open(path, "w") as f:
        f.write("a,b\n")
        for i in range(100):
            if i % 2 == 0:
                f.write(f"{i},\n")
            else:
                f.write(f"{i},{i*2}\n")
    return path


def test_read_csv_chunksize_returns_chunked_frame(tmp_path):
    csv_path = tmp_path / "dummy.csv"
    create_dummy_csv(csv_path)

    chunked = ar.read_csv(str(csv_path), chunksize=10)
    assert type(chunked).__name__ == "ChunkedArFrame"


def test_invalid_chunksize(tmp_path):
    csv_path = tmp_path / "dummy.csv"
    create_dummy_csv(csv_path)

    with pytest.raises(ValueError, match="chunksize must be a positive integer"):
        ar.read_csv(str(csv_path), chunksize=-5)

    with pytest.raises(ValueError, match="chunksize must be a positive integer"):
        ar.read_csv(str(csv_path), chunksize=0)


def test_lazy_pipeline_iteration_and_materialization(tmp_path):
    csv_path = tmp_path / "dummy.csv"
    create_dummy_csv(csv_path)

    chunked = ar.read_csv(str(csv_path), chunksize=25)
    # 100 rows total. Half of them (where i % 2 == 0) have null in column b
    pipelined = ar.pipeline(chunked, [("drop_nulls",)])

    # Should still be chunked
    assert type(pipelined).__name__ == "ChunkedArFrame"

    # Materialize
    df = pipelined.to_pandas()
    # 50 rows should remain
    assert len(df) == 50
    # They should be the odd indices
    assert df["a"].iloc[0] == 1
    assert df["b"].iloc[0] == 2


def test_unsupported_full_pass_steps(tmp_path):
    csv_path = tmp_path / "dummy.csv"
    create_dummy_csv(csv_path)

    chunked = ar.read_csv(str(csv_path), chunksize=10)
    with pytest.raises(
        ValueError,
        match="Step 'drop_duplicates' requires a full pass and cannot be used in a streaming pipeline.",
    ):
        ar.pipeline(chunked, [("drop_duplicates",)])
