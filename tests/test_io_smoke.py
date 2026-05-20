import pytest

# Only skip the module when the package or its native extension is missing.
try:
    import arnio as ar
except ImportError:
    pytest.skip("arnio not installed; skipping IO smoke tests", allow_module_level=True)

# If the Python package imports but the native C++ extension isn't built, skip those
# IO smoke tests specifically. This avoids hiding import/runtime errors that
# should surface during CI while still allowing CI to skip these tests when the
# native extension isn't available in the runner.
if getattr(ar, "_arnio_cpp", None) is None:
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
