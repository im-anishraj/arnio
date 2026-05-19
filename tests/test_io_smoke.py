import pytest

try:
    import arnio as ar
except Exception:
    pytest.skip(
        "arnio C++ extension not available; skipping IO smoke tests",
        allow_module_level=True,
    )


def test_read_csv_smoke(tmp_path):
    csv_path = tmp_path / "smoke.csv"
    csv_path.write_text("name,age\nAlice,30\nBob,25\n")

    frame = ar.read_csv(str(csv_path))
    assert isinstance(frame, ar.ArFrame)
    assert frame.shape == (2, 2)
    assert list(frame.columns) == ["name", "age"]


def test_from_pandas_smoke():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"x": [1, 2], "y": ["a", "b"]})

    frame = ar.from_pandas(df)
    assert isinstance(frame, ar.ArFrame)

    # round-trip to pandas and compare basic contents
    out = ar.to_pandas(frame)
    assert list(out.columns) == ["x", "y"]
    assert out["x"].tolist() == [1, 2]
    assert out["y"].tolist() == ["a", "b"]
