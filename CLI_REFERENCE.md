# CLI Reference and Roadmap

This document covers the current command-line workflows and
planned CLI goals for Arnio contributors and users.

## Development Commands

```bash
# Install in development mode with all dev dependencies
make install

# Run the full test suite with coverage
make test

# Run linter and formatter checks
make lint

# Run benchmarks against pandas
make benchmark
```

## Common Python Workflow Examples

```python
import arnio as ar

# Load a CSV file through C++
frame = ar.read_csv("data.csv")

# Run a cleaning pipeline
clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("normalize_case", {"case_type": "lower"}),
    ("drop_nulls",),
    ("drop_duplicates",),
])

# Profile your dataset
report = ar.profile(frame)
print(report.summary())

# Get cleaning suggestions
suggestions = ar.suggest_cleaning(frame)
print(suggestions)

# Auto clean safely
clean = ar.auto_clean(frame, mode="safe")

# Auto clean strictly (includes deduplication)
clean = ar.auto_clean(frame, mode="strict")

# Convert to pandas
df = ar.to_pandas(clean)
```

## CLI Roadmap

| Focus Area | Status |
|-----------|--------|
| CSV parsing and cleaning | 🔨 Current |
| Data quality and schema validation | 🔨 Current |
| Chunked and streaming processing | 📋 Near Term |
| Native CSV writers | 📋 Near Term |
| Parallel column processing | 💭 Long Term |
| SIMD string operations | 💭 Long Term |
| JSON Lines and Parquet support | 💭 Long Term |

> Full roadmap: [ROADMAP.md](ROADMAP.md)

## Related Docs

- `ROADMAP.md` — full version roadmap
- `ARCHITECTURE.md` — system architecture
- `GSSOC_GUIDE.md` — contributor onboarding guide
- `README.md` — quickstart and examples
