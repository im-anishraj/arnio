from arnio import read_csv


def test_int_inference_valid(tmp_path):
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text("a\n123\n456\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "int64"


def test_signed_integer_inference(tmp_path):
    csv_file = tmp_path / "signed.csv"
    csv_file.write_text("value\n+123\n+456\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["value"] == "int64"


def test_float_inference_valid(tmp_path):
    csv_file = tmp_path / "float.csv"
    csv_file.write_text("a\n1.5\n2.75\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "float64"


def test_invalid_numeric_falls_back_to_string(tmp_path):
    csv_file = tmp_path / "invalid.csv"
    csv_file.write_text("a\n123abc\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "string"


def test_whitespace_numeric_current_behavior(tmp_path):
    csv_file = tmp_path / "space.csv"
    csv_file.write_text("a\n 123\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "int64"
