import pandas as pd

import arnio as ar


def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# -------------------------------------------------------------------
# MAIN EDGE CASE DATASET
# -------------------------------------------------------------------

df = pd.DataFrame(
    {
        "active": [
            "YES",
            " no ",
            "True",
            "FALSE",
            "1",
            "0",
            "y",
            "N",
            "YeS",
            "FaLsE",
            "maybe",
            "unknown",
            "",
            "   ",
            None,
            123,
            True,
            False,
            "TrUe",
            "fAlSe",
            "YES ",
            " NO",
        ],
        "other": [
            "keep",
            "these",
            "values",
            "untouched",
            "in",
            "subset",
            "testing",
            "only",
            "for",
            "verification",
            "foo",
            "bar",
            "",
            None,
            "baz",
            999,
            True,
            False,
            "TRUE",
            "FALSE",
            " yes ",
            " no ",
        ],
    },
    dtype=object,
)

print_section("ORIGINAL DATAFRAME")
print(df)

frame = ar.from_pandas(df)

# -------------------------------------------------------------------
# DIRECT PUBLIC API TEST
# -------------------------------------------------------------------

parsed = ar.parse_bool_strings(frame)

parsed_df = ar.to_pandas(parsed)

print_section("DIRECT API RESULT")

print(parsed_df)

print("\nACTIVE COLUMN VALUES:")
print(parsed_df["active"].tolist())

print("\nACTIVE COLUMN TYPES:")
for value in parsed_df["active"]:
    print(repr(value), type(value))

# -------------------------------------------------------------------
# VERIFY ORIGINAL INPUT NOT MUTATED
# -------------------------------------------------------------------

print_section("ORIGINAL DATAFRAME AFTER CALL")

print(df)

# -------------------------------------------------------------------
# PIPELINE TEST
# -------------------------------------------------------------------

pipeline_result = ar.pipeline(
    frame,
    [
        ("parse_bool_strings",),
    ],
)

pipeline_df = ar.to_pandas(pipeline_result)

print_section("PIPELINE RESULT")

print(pipeline_df)

# -------------------------------------------------------------------
# SUBSET TEST
# -------------------------------------------------------------------

subset_result = ar.parse_bool_strings(
    frame,
    subset=["active"],
)

subset_df = ar.to_pandas(subset_result)

print_section("SUBSET TEST")

print(subset_df)

print("\nOTHER COLUMN TYPES (should remain unchanged):")

for value in subset_df["other"]:
    print(repr(value), type(value))

# -------------------------------------------------------------------
# CUSTOM TRUE/FALSE VALUES
# -------------------------------------------------------------------

custom_df = pd.DataFrame(
    {
        "status": [
            "enabled",
            "disabled",
            " ENABLED ",
            " DISABLED ",
            "maybe",
            None,
        ]
    },
    dtype=object,
)

custom_frame = ar.from_pandas(custom_df)

custom_result = ar.parse_bool_strings(
    custom_frame,
    true_values={"enabled"},
    false_values={"disabled"},
)

custom_cleaned = ar.to_pandas(custom_result)

print_section("CUSTOM TRUE/FALSE VALUES")

print(custom_cleaned)

print("\nCUSTOM COLUMN TYPES:")

for value in custom_cleaned["status"]:
    print(repr(value), type(value))

# -------------------------------------------------------------------
# ALREADY BOOLEAN VALUES
# -------------------------------------------------------------------

bool_df = pd.DataFrame(
    {
        "flag": [
            True,
            False,
            "True",
            "False",
            "YES",
            "NO",
        ]
    },
    dtype=object,
)

bool_frame = ar.from_pandas(bool_df)

bool_result = ar.parse_bool_strings(bool_frame)

bool_cleaned = ar.to_pandas(bool_result)

print_section("ALREADY BOOLEAN VALUES")

print(bool_cleaned)

print("\nBOOLEAN COLUMN TYPES:")

for value in bool_cleaned["flag"]:
    print(repr(value), type(value))

# -------------------------------------------------------------------
# PURE BOOLEAN-LIKE STRINGS
# -------------------------------------------------------------------

pure_df = pd.DataFrame(
    {
        "active": [
            "YES",
            "NO",
            "true",
            "false",
            "1",
            "0",
            "y",
            "n",
        ]
    }
)

pure_frame = ar.from_pandas(pure_df)

pure_result = ar.parse_bool_strings(pure_frame)

pure_cleaned = ar.to_pandas(pure_result)

print_section("PURE BOOLEAN-LIKE STRINGS")

print(pure_cleaned)

print("\nPURE TYPES:")

for value in pure_cleaned["active"]:
    print(repr(value), type(value))