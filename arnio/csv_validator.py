
import csv


def detect_csv_issues(file_path):

    issues = []

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            newline=""
        ) as csv_file:

            reader = csv.reader(csv_file)

            expected_fields = None

            for row_number, row in enumerate(reader, start=1):

                field_count = len(row)

                if expected_fields is None:

                    expected_fields = field_count

                elif field_count != expected_fields:

                    issues.append(
                        {
                            "row": row_number,
                            "issue_type": "inconsistent_columns",
                            "expected_fields": expected_fields,
                            "actual_fields": field_count,
                            "message": (
                                f"Expected {expected_fields} "
                                f"columns but found {field_count}"
                            ),
                        }
                    )

    except FileNotFoundError:

        issues.append(
            {
                "row": None,
                "issue_type": "missing_file",
                "message": "CSV file not found",
            }
        )

    except UnicodeDecodeError:

        issues.append(
            {
                "row": None,
                "issue_type": "encoding_error",
                "message": "Unable to decode CSV file as UTF-8",
            }
        )

    except csv.Error as error:

        issues.append(
            {
                "row": None,
                "issue_type": "malformed_row",
                "message": str(error),
            }
        )

    return issues
