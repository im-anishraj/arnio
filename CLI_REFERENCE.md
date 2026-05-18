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

| Version | Goal | Status |
|---------|------|--------|
| v1.0 | Stable release, PyPI publishing, CI/CD | ✅ Shipped |
| v1.1 | Release hardening, docs, tooling | ✅ Shipped |
| v1.2 | C++ pipeline optimization, hash-based deduplication | 🔨 Active |
| v1.3 | Chunked/streaming processing, Parquet and JSON readers | 📋 Planned |
| v1.4 | Parallel column processing, SIMD string operations | 💭 Exploring |

## Related Docs

- `ROADMAP.md` — full version roadmap
- `ARCHITECTURE.md` — system architecture
- `API_REFERENCE.md` — full API reference
- `GSSOC_GUIDE.md` — contributor onboarding guide
