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


def test_negative_int_inference(tmp_path):
    csv_file = tmp_path / "neg.csv"
    csv_file.write_text("a\n-123\n-456\n-789\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "int64"
    vals = df["a"]
    assert vals == [-123, -456, -789]


def test_explicit_positive_float(tmp_path):
    csv_file = tmp_path / "pos_float.csv"
    csv_file.write_text("a\n+1.5\n+2.75\n+3.0\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "float64"
    vals = df["a"]
    assert vals == [1.5, 2.75, 3.0]


def test_large_int_in_range(tmp_path):
    csv_file = tmp_path / "large_int.csv"
    csv_file.write_text("a\n2147483648\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "int64"


def test_overflow_int_falls_back_to_float(tmp_path):
    csv_file = tmp_path / "overflow_int.csv"
    csv_file.write_text("a\n999999999999999999999999999\n")

    df = read_csv(str(csv_file))

    # Overflow integers are not coerced to float; preserve the token as string.
    assert df.dtypes["a"] == "string"


def test_numeric_with_leading_zeros_is_string(tmp_path):
    csv_file = tmp_path / "leading_zero.csv"
    csv_file.write_text("a\n0123\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "string"


def test_negative_float_inference(tmp_path):
    csv_file = tmp_path / "neg_float.csv"
    csv_file.write_text("a\n-1.5\n-2.75\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "float64"
    vals = df["a"]
    assert vals == [-1.5, -2.75]


def test_mixed_int_float_promotes_to_float(tmp_path):
    csv_file = tmp_path / "mixed.csv"
    csv_file.write_text("a\n123\n4.5\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "float64"


def test_scientific_notation_float(tmp_path):
    csv_file = tmp_path / "sci.csv"
    csv_file.write_text("a\n1.5e3\n-2.5e-2\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "float64"
    vals = df["a"]
    assert vals[0] == 1500.0
    assert abs(vals[1] - (-0.025)) < 1e-12


def test_hex_int_is_string(tmp_path):
    csv_file = tmp_path / "hex.csv"
    csv_file.write_text("a\n0xFF\n0x1A\n")

    df = read_csv(str(csv_file))

    assert df.dtypes["a"] == "string"
