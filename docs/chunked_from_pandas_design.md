# Design: Chunked `from_pandas()` Conversion

## Current Memory Behavior

`from_pandas()` converts each column via `.tolist()`, materializing the entire
column as a Python list before passing it to the C++ layer. This causes a peak
allocation proportional to the full frame size.

### Measured Peak Allocations (tracemalloc)

| Row Count | Peak Memory (MB) |
|-----------|-----------------|
| 10,000    | 0.93            |
| 100,000   | 8.71            |
| 1,000,000 | 88.77           |

### Per-Column Hotspot (100k rows)

| Column    | Peak (MB) |
|-----------|-----------|
| col_int   | 4.13      |
| col_float | 3.82      |
| col_bool  | 1.53      |
| col_str   | 1.53      |

Numeric columns (int, float) are the primary allocation hotspot.

## Proposed Public API

```python
ar.from_pandas(df, chunk_size=None)
```

- `chunk_size=None` current behavior, no change.
- `chunk_size=N` splits DataFrame into row batches of N, converts each
  independently, then concatenates.

## Limitations

- Index is reset and ignored per chunk.
- Nullable dtypes (`Int64`, `Float64`, `boolean`) supported via existing routing.
- Mixed-type columns raise the same errors as today.
- No parallelism in v1 sequential chunk processing only.

## First PR Scope

Design and measurement only:
- Benchmark script (`benchmarks/benchmark_from_pandas_memory.py`)
- This design document
- No public API change

## Follow-up Implementation Plan

1. Add `chunk_size` parameter to `from_pandas()` in `arnio/convert.py`.
2. Implement row slicing and per-chunk conversion.
3. Add concatenation of ArFrame chunks.
4. Tests: normal chunked, chunk_size > frame, single-row chunks, empty frame.
5. Benchmark comparison: chunked vs non-chunked peak memory.