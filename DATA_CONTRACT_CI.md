# Data contract CI workflow (copy-paste example)

Arnio includes schema inference (`ar.scan_csv`) and row-level validation (`ar.Schema` / `ar.validate`), but it does **not** yet ship a first-class `arnio validate` CLI command.

This document provides an **inert**, copy-paste GitHub Actions workflow example you can add to *your* repository to block schema drift and/or invalid rows in pull requests.

> **Scope note:** This file is documentation-only. It intentionally does **not** add an active workflow under `.github/workflows/` in Arnio itself.

---

## Quickstart: validate a CSV in CI

### 1) Add a contract directory to your repo

Create:

- `contracts/example.schema.json` (schema drift contract for `ar.scan_csv`)
- `contracts/schema.py` (row-level validation rules for `ar.validate`)

Example `contracts/example.schema.json`:

```json
{
  "user_id": "int64",
  "email": "string",
  "is_active": "bool",
  "revenue": "float64"
}
```

> The `example.schema.json` format matches the **current** lowercase dtype output of `ar.scan_csv(...)`, e.g. `{"name": "string", "age": "int64"}`.

Example `contracts/schema.py`:

```python
import arnio as ar

SCHEMA = ar.Schema(
    {
        "user_id": ar.Int64(nullable=False, unique=True),
        "email": ar.Email(nullable=False),
        "is_active": ar.Bool(nullable=False),
        "revenue": ar.Float64(nullable=True, min=0),
    },
    strict=True,  # fail if extra columns appear
)
```

### 2) Add the workflow (copy-paste)

Create `.github/workflows/data-contract.yml` in **your** repo:

```yaml
name: Data contract (Arnio)

on:
  pull_request:
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install arnio
        run: |
          python -m pip install --upgrade pip
          python -m pip install arnio

      - name: Validate CSV(s)
        run: |
          python - <<'PY'
          from __future__ import annotations

          import json
          import os
          import sys
          from pathlib import Path

          import arnio as ar

          # Update these paths for your repo:
          DATA_FILES = [Path("data/example.csv")]
          EXPECTED_SCAN_SCHEMA = Path("contracts/example.schema.json")
          SCHEMA_PY = Path("contracts/schema.py")

          def write_summary(md: str) -> None:
            path = os.environ.get("GITHUB_STEP_SUMMARY")
            if not path:
              return
            Path(path).write_text(md, encoding="utf-8")

          def md_escape(s: str) -> str:
            # Minimal escaping for markdown table cells
            return str(s).replace("|", "\\|").replace("\n", " ")

          # Load row-level schema from contracts/schema.py (no extra deps, no CLI required)
          ns: dict[str, object] = {}
          exec(SCHEMA_PY.read_text(encoding="utf-8"), ns)
          schema = ns["SCHEMA"]

          expected = json.loads(EXPECTED_SCAN_SCHEMA.read_text(encoding="utf-8"))

          failures: list[str] = []
          summary_lines: list[str] = []

          summary_lines.append("## Data contract results")
          summary_lines.append("")

          for data_path in DATA_FILES:
            summary_lines.append(f"### `{data_path}`")
            summary_lines.append("")

            # 1) Schema drift check (fast): compare scan_csv output to expected dtype map
            observed = ar.scan_csv(data_path)
            drift = []
            for col, expected_dtype in expected.items():
              observed_dtype = observed.get(col)
              if observed_dtype is None:
                continue  # handled in missing_cols below
              if observed_dtype != expected_dtype:
                drift.append((col, expected_dtype, observed_dtype))

            extra_cols = sorted(set(observed) - set(expected))
            missing_cols = sorted(set(expected) - set(observed))

            if drift or extra_cols or missing_cols:
              failures.append(f"Schema drift: {data_path}")
              summary_lines.append("**❌ Schema drift detected**")
              summary_lines.append("")
              summary_lines.append("| Column | Expected | Observed |")
              summary_lines.append("|---|---:|---:|")
              for col, exp, obs in drift:
                summary_lines.append(
                  f"| `{md_escape(col)}` | `{md_escape(exp)}` | `{md_escape(obs)}` |"
                )
              for col in missing_cols:
                summary_lines.append(f"| `{md_escape(col)}` | `{md_escape(expected[col])}` | `MISSING` |")
              for col in extra_cols:
                summary_lines.append(f"| `{md_escape(col)}` | `—` | `{md_escape(observed[col])}` |")
              summary_lines.append("")
            else:
              summary_lines.append("**✅ Schema drift check passed**")
              summary_lines.append("")

            # 2) Row-level validation (actionable): produces rule + row + value context
            frame = ar.read_csv(data_path)
            result = ar.validate(frame, schema)

            if result.passed:
              summary_lines.append("**✅ Row-level validation passed**")
              summary_lines.append("")
              continue

            failures.append(f"Row validation: {data_path}")
            summary_lines.append("**❌ Row-level validation failed**")
            summary_lines.append("")
            summary_lines.append("| Column | Rule | Row | Value | Message |")
            summary_lines.append("|---|---|---:|---|---|")
            for issue in result.issues[:50]:
              summary_lines.append(
                "| {col} | `{rule}` | {row} | `{value}` | {msg} |".format(
                  col=f"`{md_escape(issue.column)}`" if issue.column else "`—`",
                  rule=md_escape(issue.rule),
                  row=issue.row_index if issue.row_index is not None else "—",
                  value=md_escape(issue.value) if issue.value is not None else "—",
                  msg=md_escape(issue.message),
                )
              )
            if len(result.issues) > 50:
              summary_lines.append("")
              summary_lines.append(f"_Truncated: showing first 50 of {len(result.issues)} issues._")
            summary_lines.append("")

          write_summary("\n".join(summary_lines) + "\n")

          if failures:
            print("Data contract failed:")
            for f in failures:
              print("-", f)
            sys.exit(1)
          print("Data contract passed.")
          PY
```

---

## Example outputs

### Passing output (PR summary)

```text
## Data contract results

### `data/example.csv`
✅ Schema drift check passed
✅ Row-level validation passed
```

### Failing output (PR summary)

```text
## Data contract results

### `data/example.csv`
❌ Schema drift detected
| Column | Expected | Observed |
| user_id | int64 | string |

❌ Row-level validation failed
| Column | Rule | Row | Value | Message |
| email | email | 12 | not-an-email | Invalid email format |
```

---

## Future compatibility: `arnio validate` CLI

When a first-class CLI lands (e.g. `arnio validate --schema contracts/schema.json data/*.csv`),
the workflow above can be simplified to a one-liner.

The current example intentionally mirrors what that CLI would do internally:

- Load a schema file / schema definition
- Validate one or more CSVs
- Emit a markdown summary
- Exit non-zero on failure

