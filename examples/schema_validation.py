"""
Schema Validation Tutorial for Arnio
------------------------------------
This script shows an end-to-end schema validation workflow:
- define a Schema with typed fields
- validate intentionally mixed-quality data
- inspect ValidationResult summaries and markdown output
"""

import arnio as ar
import pandas as pd


def main():
    frame = ar.from_pandas(
        pd.DataFrame(
            [
                {
                    "user_id": 101,
                    "email": "alice@example.com",
                    "age": 31,
                    "signup_date": "2026-05-01T09:30:00",
                    "country": "IN",
                    "is_active": True,
                },
                {
                    "user_id": 101,
                    "email": "broken-email",
                    "age": -4,
                    "signup_date": "not-a-date",
                    "country": None,
                    "is_active": "yes",
                },
                {
                    "user_id": None,
                    "email": "charlie@example.com",
                    "age": 22,
                    "signup_date": "2026-05-03T12:15:00",
                    "country": "USA",
                    "is_active": False,
                },
            ]
        )
    )

    schema = ar.Schema(
        {
            "user_id": ar.Int64(nullable=False),
            "email": ar.Email(nullable=False),
            "age": ar.Int64(nullable=False, min=0),
            "signup_date": ar.DateTime(nullable=False, format="%Y-%m-%dT%H:%M:%S"),
            "country": ar.CountryCode(nullable=True),
            "is_active": ar.Bool(nullable=False),
        },
        unique=["user_id"],
        strict=True,
    )

    result = ar.validate(frame, schema)

    print("Validation passed:", result.passed)
    print("Issue count:", result.issue_count)
    print("\nIssues by rule:")
    print(result.summary()["issues_by_rule"])
    print("\nValidation report:")
    print(result.to_markdown(max_issues=10))


if __name__ == "__main__":
    main()
