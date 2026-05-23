
import csv
import chardet


def detect_csv_issues(file_path):

    issues = []

    with open(file_path, "rb") as f:
        raw_data = f.read()

    detected = chardet.detect(raw_data)
    encoding = detected["encoding"]

    if encoding is None:
        encoding = "utf-8"
        issues.append("Could not detect encoding")

    try:
        text = raw_data.decode(encoding)

    except UnicodeDecodeError:

        issues.append("Encoding issue detected")

        text = raw_data.decode(
            "utf-8",
            errors="replace"
        )

    lines = text.splitlines()

    delimiter = ","

    expected_columns = None

    for i, line in enumerate(lines, start=1):

        if line.count('"') % 2 != 0:

            issues.append(
                f"Line {i}: unmatched quotes"
            )

        reader = csv.reader(
            [line],
            delimiter=delimiter
        )

        row = next(reader)

        columns = len(row)

        if expected_columns is None:

            expected_columns = columns

        elif columns != expected_columns:

            issues.append(
                f"Line {i}: expected {expected_columns} columns but found {columns}"
            )

    return {
        "encoding": encoding,
        "issues": issues
    }
