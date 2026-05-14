# Arnio API Reference

Your CSV hits C++ before Python even wakes up.

**Arnio** is a compiled C++ data cleaning engine that slots in _before_ pandas. It parses, infers types, strips whitespace, deduplicates, and normalizes — all natively, in columnar memory — then hands you a pristine `DataFrame`.

## Installation

```bash
pip install arnio
```

## Quick Start

```python
import arnio as ar

# Read a CSV file
frame = ar.read_csv("data.csv")

# Profile data quality
report = ar.profile(frame)
print(report.summary())

# Clean automatically
clean = ar.auto_clean(frame)

# Convert to pandas
import pandas as pd
df = ar.to_pandas(clean)
```

## Module Overview

| Module | Description |
|--------|-------------|
| [`arnio.io`](api/io.md) | CSV reading and schema scanning |
| [`arnio.cleaning`](api/cleaning.md) | Data cleaning operations |
| [`arnio.convert`](api/convert.md) | Pandas ↔ ArFrame conversion |
| [`arnio.pipeline`](api/pipeline.md) | Chained cleaning pipelines |
| [`arnio.schema`](api/schema.md) | Data contracts and validation |
| [`arnio.quality`](api/quality.md) | Data quality profiling and auto-cleaning |
| [`arnio.exceptions`](api/exceptions.md) | Custom exception classes |
