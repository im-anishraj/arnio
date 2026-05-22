import pandas as pd
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


def test_on_bad_lines_warn_truncates_and_pads(self, tmp_path):
    csv_path = tmp_path / "warn.csv"

    csv_path.write_text("name,age\n" "Alice,30\n" "Bob,25,extra\n" "Charlie\n")

    frame = ar.read_csv(
        csv_path,
        mode="permissive",
        on_bad_lines="warn",
    )

    df = ar.to_pandas(frame)

    assert frame.shape == (3, 2)

    assert df["name"].iloc[1] == "Bob"
    assert df["age"].iloc[1] == 25

    assert pd.isna(df["age"].iloc[2])


def test_on_bad_lines_skip_drops_rows(self, tmp_path):
    csv_path = tmp_path / "skip.csv"

    csv_path.write_text("name,age\n" "Alice,30\n" "Bob,25,extra\n" "Charlie\n")

    frame = ar.read_csv(
        csv_path,
        mode="permissive",
        on_bad_lines="skip",
    )

    df = ar.to_pandas(frame)

    assert frame.shape == (1, 2)
    assert df["name"].iloc[0] == "Alice"


def test_on_bad_lines_error_raises(self, tmp_path):
    csv_path = tmp_path / "error.csv"

    csv_path.write_text("name,age\n" "Alice,30\n" "Bob,25,extra\n")

    with pytest.raises(RuntimeError, match="expected 2"):
        ar.read_csv(
            csv_path,
            mode="permissive",
            on_bad_lines="error",
        )
