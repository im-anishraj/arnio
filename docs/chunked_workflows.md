# Chunked / Streaming Workflows

**Target audience:** Users who need to validate or clean very large CSV files (hundreds of MB to
hundreds of GB) without loading the entire dataset into memory at once.

---

## Table of contents

- [Why chunked mode?](#why-chunked-mode)
- [read\_csv\_chunked — API reference](#read_csv_chunked--api-reference)
- [row\_index convention across chunks](#row_index-convention-across-chunks)
- [Supported pipeline steps for chunked mode](#supported-pipeline-steps-for-chunked-mode)
- [Example A — Chunked schema validation with aggregated summary](#example-a--chunked-schema-validation-with-aggregated-summary)
- [Example B — Chunked cleanup using only streaming-safe steps](#example-b--chunked-cleanup-using-only-streaming-safe-steps)
- [What does NOT work in chunked mode — and why](#what-does-not-work-in-chunked-mode--and-why)
- [Reconciling row\_index values in CI and data-quality logs](#reconciling-row_index-values-in-ci-and-data-quality-logs)

---

## Why chunked mode?

`ar.read_csv()` materialises the full file into an `ArFrame` before any work begins.  For files
that fit comfortably in RAM this is always the right choice: the C++ backend is fast and the
full-frame pipeline, profiler, and validator all work without restriction.

When a file is too large to fit in memory you have two options:

| Option | When to use |
|---|---|
| `ar.scan_csv()` | You only need the inferred schema (column names + types). No row data is loaded. |
| `ar.read_csv_chunked()` | You need to inspect, validate, or clean the actual row data without loading everything at once. |

`scan_csv` is documented in the [API reference](https://arnio.vercel.app/api.html#scan_csv).
This page focuses on `read_csv_chunked`.

---

## `read_csv_chunked` — API reference

```python
arnio.read_csv_chunked(
    path,
    *,
    chunksize=10_000,
    delimiter=None,
    has_header=True,
    usecols=None,
    dtype=None,
    nrows=None,
    skip_rows=0,
    skiprows=None,
    trim_headers=True,
    decimal_separator=".",
    thousands_separator=None,
    null_values=None,
    mode="strict",
    encoding="utf-8",
    on_bad_lines="error",
)
```

Returns a **lazy iterator** of `ArFrame` objects.  Each yielded frame contains at most
`chunksize` rows.  The header is consumed once; every chunk shares the same column names
and inferred types.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | `str \| os.PathLike` | — | Path to the CSV file. |
| `chunksize` | `int` | `10_000` | Maximum rows per yielded `ArFrame`. The last chunk may be smaller. |
| `delimiter` | `str \| None` | `None` | Column delimiter. `None` auto-detects from the file (tries `,`, `;`, `\t`, `\|`). |
| `has_header` | `bool` | `True` | Whether the first row is a header. |
| `usecols` | `list[str] \| None` | `None` | Subset of columns to load. |
| `dtype` | `dict[str, str] \| None` | `None` | Force specific types for named columns instead of inferring them (e.g. `{"id": "string"}`). |
| `nrows` | `int \| None` | `None` | Stop after reading this many rows in total across all chunks. `None` reads to end-of-file. |
| `skip_rows` | `int` | `0` | Number of data rows to skip after the header. |
| `skiprows` | `int \| None` | `None` | Optional alias for `skip_rows`. When provided, takes precedence over `skip_rows`. |
| `trim_headers` | `bool` | `True` | Strip leading and trailing whitespace from column header names. |
| `decimal_separator` | `str` | `"."` | Decimal point character. Use `","` for European-style CSVs. |
| `thousands_separator` | `str \| None` | `None` | Thousands grouping character (e.g. `","`). Stripped before numeric parsing. |
| `null_values` | `list[str] \| None` | `None` | Additional strings to treat as null (e.g. `["N/A", "–", "none"]`). Always combined with the built-in set. |
| `mode` | `str` | `"strict"` | `"strict"` rejects rows with extra fields and raises on bad lines; `"permissive"` also rejects extra fields but pads missing trailing fields with nulls. |
| `encoding` | `str` | `"utf-8"` | File encoding. Non-UTF-8 input is transcoded before the C++ parser runs. |
| `on_bad_lines` | `"error" \| "warn" \| "skip"` | `"error"` | Action taken for rows classified as bad by the selected mode. |

The iterator is consumed once; re-iteration requires a new call to `read_csv_chunked`.

---

## `row_index` convention across chunks

Every `ValidationIssue` returned by `ar.validate()` carries a `.row_index` field.
**`row_index` is always 1-based and always local to the chunk that was validated.**

```
File row 1   → chunk 0, row_index 1
File row 2   → chunk 0, row_index 2
...
File row 10000  → chunk 0, row_index 10000   (chunksize=10_000)
File row 10001  → chunk 1, row_index 1       ← resets to 1
File row 10002  → chunk 1, row_index 2
```

To convert a local `row_index` to its global file row number use:

```python
global_row = chunk_number * chunksize + issue.row_index
```

`chunk_number` is 0-based (the first chunk is chunk 0).  Example A below demonstrates this
pattern in practice.

> **Why not global row indices by default?**  Producing global row indices would require the
> C++ reader to track absolute file position across chunk boundaries and expose that state to
> Python.  Keeping indices local to each chunk keeps the reader stateless and allows chunks to
> be processed concurrently in the future.  Use the formula above to reconstruct global
> positions whenever you need them.

---

## Supported pipeline steps for chunked mode

A **row-safe** step is one that operates on each row independently.  It never needs to see
adjacent rows or the full column to produce a correct result.  Row-safe steps can be applied
safely inside a chunked loop.

A **requires-global-view** step is one whose correctness depends on the full dataset being
present.  Applying it per chunk produces silently wrong results.

A **schema-changing** step alters column names or types.  It is safe per chunk but the same
mapping must be applied to every chunk consistently.

| Step | Category | Safe in chunked loop? | Notes |
|---|---|---|---|
| `strip_whitespace` | Row-safe | ✅ Yes | Operates on individual cell strings. |
| `normalize_case` | Row-safe | ✅ Yes | Operates on individual cell strings. |
| `fill_nulls` | Row-safe | ✅ Yes | Fills per-cell with a scalar value. |
| `cast_types` | Schema-changing | ✅ Yes | Apply the same mapping to every chunk. |
| `rename_columns` | Schema-changing | ✅ Yes | Apply the same mapping to every chunk. |
| `drop_nulls` | Row-safe | ✅ Yes | Drops rows whose specified columns are null. Cross-chunk row counts differ; this is expected and fine. |
| `drop_duplicates` | Requires global view | ❌ No | Can only detect duplicates within a single chunk. Rows that are duplicates of each other across chunk boundaries will not be removed. |
| `auto_clean(mode="safe")` | Row-safe | ✅ Yes | Only applies `strip_whitespace` internally. |
| `auto_clean(mode="strict")` | Requires global view | ❌ No | Includes `drop_duplicates` internally. |
| `suggest_cleaning` / `profile` | Requires global view | ⚠️ Partial | Profiling a single chunk gives locally-accurate statistics only. Aggregate manually if you need file-level metrics. See the note below. |

### `profile` and `suggest_cleaning` in chunked mode

`ar.profile()` returns accurate statistics for the frame it receives.  When you call it inside
a chunked loop each report reflects only that chunk.  File-level metrics such as
`duplicate_ratio` or `null_count` will be underestimates unless you aggregate them yourself.

For large-file quality monitoring the recommended pattern is to profile each chunk, collect the
per-chunk `DataQualityReport` objects, and combine the counts you care about:

```python
total_rows = 0
total_nulls = 0

for chunk in ar.read_csv_chunked("big.csv", chunksize=50_000):
    report = ar.profile(chunk)
    total_rows += report.row_count
    for col_profile in report.columns.values():
        total_nulls += col_profile.null_count
```

---

## Example A — Chunked schema validation with aggregated summary

This example streams a large CSV, validates each chunk against a fixed schema, and aggregates
all `ValidationIssue` objects into a single summary with **global row numbers**.

```python
"""
example_a_chunked_validation.py
--------------------------------
Stream-validates a large CSV against a schema and prints a consolidated
summary.  Runs in constant memory regardless of file size.
"""

import arnio as ar

# ── Schema ────────────────────────────────────────────────────────────────────
# Define the contract once.  The same schema is reused for every chunk.
schema = ar.Schema(
    {
        "user_id":   ar.Int64(nullable=False, unique=False),
        "email":     ar.Email(nullable=False),
        "age":       ar.Int64(nullable=True, min=0, max=130),
        "country":   ar.String(nullable=False, min_length=2, max_length=2),
        "revenue":   ar.Float64(nullable=True, min=0.0),
    }
)

CHUNKSIZE = 50_000
all_issues = []   # list of dicts — kept small because only issues are stored
total_rows = 0

# ── Stream ────────────────────────────────────────────────────────────────────
for chunk_number, chunk in enumerate(
    ar.read_csv_chunked(
        "users_large.csv",
        chunksize=CHUNKSIZE,
        on_bad_lines="warn",
    )
):
    result = ar.validate(chunk, schema)
    total_rows += len(chunk)

    for issue in result.issues:
        # Convert the local (per-chunk) row_index to a global file row number.
        # row_index is 1-based; chunk_number is 0-based.
        global_row = chunk_number * CHUNKSIZE + issue.row_index

        all_issues.append(
            {
                "global_row": global_row,
                "column":     issue.column,
                "rule":       issue.rule,
                "message":    issue.message,
                "value":      issue.value,
            }
        )

# ── Summary ───────────────────────────────────────────────────────────────────
passed = len(all_issues) == 0

print(f"Rows validated : {total_rows:,}")
print(f"Total issues   : {len(all_issues):,}")
print(f"Passed         : {passed}")

if not passed:
    # Show the first ten issues
    print("\nFirst 10 issues:")
    for issue in all_issues[:10]:
        print(
            f"  row {issue['global_row']:>8,}  "
            f"column={issue['column']!r:20}  "
            f"rule={issue['rule']!r:20}  "
            f"{issue['message']}"
        )

    # Optional: export all issues to a pandas DataFrame for further analysis
    import pandas as pd
    issues_df = pd.DataFrame(all_issues)
    issues_df.to_csv("validation_issues.csv", index=False)
    print(f"\nFull issue log written to validation_issues.csv")
```

**Expected output (example):**

```
Rows validated : 2,500,000
Total issues   :       347
Passed         : False

First 10 issues:
       row      1,042  column='email'               rule='email_format'       Invalid email address: 'not-an-email'
       row      3,871  column='age'                 rule='max'                Value 999 exceeds maximum 130
       ...
```

---

## Example B — Chunked cleanup using only streaming-safe steps

This example streams a large CSV, applies a **row-safe** pipeline to each chunk, and writes the
cleaned chunks out to a new CSV file.  Only steps from the "Row-safe" and "Schema-changing"
categories are used.

```python
"""
example_b_chunked_cleanup.py
-----------------------------
Cleans a large CSV in a constant-memory loop and writes cleaned chunks
to an output file.  Uses only streaming-safe pipeline steps.
"""

import csv
import arnio as ar

INPUT_PATH  = "orders_raw.csv"
OUTPUT_PATH = "orders_clean.csv"
CHUNKSIZE   = 25_000

# ── Pipeline steps ────────────────────────────────────────────────────────────
# All steps below are row-safe: each row is transformed independently.
#
# DO NOT include drop_duplicates here — it cannot detect cross-chunk duplicates
# and will silently miss them.  Deduplicate after the full file is loaded into
# a database or after converting to Parquet and using a query engine.
STEPS = [
    ("strip_whitespace",),
    ("normalize_case", {"subset": ["status", "country"], "case_type": "lower"}),
    ("fill_nulls",     {"value": 0.0, "subset": ["discount", "tax"]}),
    ("drop_nulls",     {"subset": ["order_id", "customer_email"]}),
    ("cast_types",     {"order_id": "int64", "amount": "float64"}),
]

rows_in  = 0
rows_out = 0
header_written = False

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as out_file:
    writer = None  # initialised after the first chunk so we know the column names

    for chunk in ar.read_csv_chunked(
        INPUT_PATH,
        chunksize=CHUNKSIZE,
        on_bad_lines="warn",
    ):
        rows_in += len(chunk)

        # Apply the row-safe pipeline
        clean_chunk = ar.pipeline(chunk, STEPS)
        rows_out   += len(clean_chunk)

        # Convert to pandas for CSV output (zero-copy for numeric columns)
        df = ar.to_pandas(clean_chunk)

        if not header_written:
            writer = csv.DictWriter(out_file, fieldnames=df.columns.tolist())
            writer.writeheader()
            header_written = True

        writer.writerows(df.to_dict("records"))

print(f"Rows read    : {rows_in:,}")
print(f"Rows written : {rows_out:,}")
print(f"Rows dropped : {rows_in - rows_out:,}  (null in order_id or customer_email)")
print(f"Output       : {OUTPUT_PATH}")
```

**Expected output (example):**

```
Rows read    : 1,800,000
Rows written : 1,796,412
Rows dropped :     3,588  (null in order_id or customer_email)
Output       : orders_clean.csv
```

> **Tip — writing to Parquet instead of CSV:**  Replace the `csv` writer block with
> `ar.write_parquet(clean_chunk, ...)` if your downstream tool accepts Parquet.  Parquet's
> columnar encoding compresses streaming output significantly better than CSV.

---

## What does NOT work in chunked mode — and why

### `drop_duplicates`

```python
# ❌ This silently misses cross-chunk duplicates
for chunk in ar.read_csv_chunked("big.csv"):
    clean = ar.pipeline(chunk, [("drop_duplicates",)])
```

`drop_duplicates` can only compare rows that are in memory at the same time.  A row in chunk 0
and a duplicate of it in chunk 3 will both survive because the two chunks are never in memory
simultaneously.

**Alternatives:**

- Load into DuckDB (`ar.to_arrow` + `duckdb.arrow`) and run `SELECT DISTINCT`.
- Load into a database with a `UNIQUE` constraint and let the insert fail on duplicates.
- If the file fits in RAM after cleaning, materialise it: `frame = ar.read_csv("big.csv")`.

### `unique=True` schema field

```python
schema = ar.Schema({"id": ar.Int64(nullable=False, unique=True)})

# ❌ This only checks uniqueness within each chunk
for chunk in ar.read_csv_chunked("big.csv"):
    result = ar.validate(chunk, schema)
```

A `unique=True` rule is evaluated against the chunk being validated.  An `id` that is globally
duplicated but appears in two different chunks will pass validation in both chunks.

**Alternative:** Validate uniqueness after loading into a query engine, or collect all `id`
values across chunks and check for duplicates yourself.

### `auto_clean(mode="strict")`

`strict` mode calls `drop_duplicates` internally.  Use `mode="safe"` in chunked loops.

### `profile` for file-level statistics

Per-chunk `DataQualityReport` objects reflect chunk-level statistics only.  Fields like
`duplicate_ratio`, `null_count`, and `unique_ratio` must be aggregated manually across all
chunks if you need file-level values.

---

## Reconciling `row_index` values in CI and data-quality logs

When you log or store validation issues from a chunked run, always record both the `chunk_number`
and the `global_row` (computed as shown in Example A).  This makes issues traceable back to the
original file regardless of `chunksize`.

**Recommended log schema for CI:**

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique identifier for this validation run (timestamp, git SHA, etc.). |
| `source_file` | string | Path or URI of the input CSV. |
| `chunksize` | int | `chunksize` used in this run. |
| `chunk_number` | int | 0-based chunk index. |
| `local_row` | int | `issue.row_index` — 1-based, local to the chunk. |
| `global_row` | int | `chunk_number * chunksize + local_row`. |
| `column` | string | Column name where the issue was detected. |
| `rule` | string | Rule name (e.g. `"email_format"`, `"max"`). |
| `message` | string | Human-readable description. |
| `value` | any | The offending cell value. |

Storing `chunksize` alongside `global_row` lets you re-derive `local_row` later
(`local_row = global_row - chunk_number * chunksize`) and also means the log remains
interpretable if `chunksize` changes between runs.

**Quick CI gate pattern:**

```python
import sys
import arnio as ar

schema = ar.Schema({ ... })
issue_count = 0

for chunk_number, chunk in enumerate(ar.read_csv_chunked("pipeline_input.csv")):
    result = ar.validate(chunk, schema)
    issue_count += result.issue_count

    if issue_count > 0:
        print(f"[FAIL] chunk {chunk_number}: {result.issue_count} issue(s)")
        for issue in result.issues[:5]:
            global_row = chunk_number * 10_000 + issue.row_index
            print(f"  row {global_row}: {issue.column} — {issue.message}")

if issue_count > 0:
    print(f"\nValidation failed: {issue_count} total issue(s).")
    sys.exit(1)

print("Validation passed.")
```

---
