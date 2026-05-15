# Arnio Architecture

Arnio is designed to provide high-performance, memory-efficient data ingestion and cleaning by leveraging C++ while maintaining a seamless, declarative Python API.

This document outlines the core architecture and the boundary between Python and C++.

## 1. The Core Philosophy

Data preprocessing often involves operations that are inherently slow in Python (e.g., string manipulation, repeated passes over data). Arnio solves this by:
1. **Loading data directly into C++ memory structures.**
2. **Performing all cleaning operations natively in C++ without Python GIL contention.**
3. **Translating the final, pristine dataset to a pandas DataFrame via a zero-copy (or near zero-copy) boundary.**

## 2. Python ↔ C++ Boundary

The boundary is managed using [`pybind11`](https://github.com/pybind/pybind11).

The C++ core is compiled into a Python extension module (`_arnio_cpp`). The Python API (in `arnio/`) serves as a lightweight, type-hinted wrapper around this compiled extension.

```mermaid
graph TD
    A[Python User Code] --> B[Arnio Python API]
    B -->|pybind11| C[C++ Core _arnio_cpp]

    subgraph C++ Runtime
        C --> D[CsvReader]
        C --> E[Frame / Column]
        C --> F[Cleaning Primitives]
    end

    F -->|Return| E
    E -->|to_pandas| A
```

## 3. Data Model

Arnio's data model is columnar, strongly resembling Apache Arrow or modern Pandas internals.

### `Column`
A `Column` represents a single 1D array of homogeneous data.
- **Variant Storage**: Data is stored using `std::variant` over strongly-typed `std::vector`s (e.g., `std::vector<int64_t>`, `std::vector<std::string>`).
- **Null Handling**: Nulls are tracked via a separate boolean mask (`std::vector<bool>`), allowing the underlying data vectors to remain dense and cache-friendly.

### `Frame`
A `Frame` is an ordered collection of `Column` objects, representing a 2D dataset.
- The `Frame` maintains an index mapping column names to their respective `Column` objects for `O(1)` access.

## 4. Pipeline Execution

The `pipeline()` function in Python accepts a list of declarative steps.

1. **Step Registry**: Arnio maintains a registry mapping string names (e.g., `"strip_whitespace"`) to function pointers.
2. **C++ Execution**: For natively supported operations, the Python wrapper calls the C++ function directly, passing the `Frame` pointer. The operation modifies the data or returns a new `Frame` entirely within C++.
3. **Python Fallback**: If a step is registered via pure Python (`ar.register_step()`), the `Frame` is temporarily converted to a pandas DataFrame, the Python function executes, and the result is converted back. *(Note: This incurs a conversion penalty and is intended for prototyping or operations not yet supported in C++).*

## 5. Converting to Pandas

The `to_pandas()` function is the most critical boundary. It uses the NumPy C-API (via pybind11's buffer protocol) to expose the underlying C++ `std::vector` memory directly to pandas, avoiding expensive element-by-element copies where possible (zero-copy for numerics and booleans). String columns currently require instantiation of Python `str` objects.


## 6. Data Quality and Schema Validation

Arnio is split into two layers:

- The **C++ layer** handles parsing CSVs, storing data in memory, and cleaning operations such as `drop_nulls()` and `strip_whitespace()`. These execute through pybind11 directly in C++.
- The **Python/pandas layer** handles data quality: profiling, validation, and schema checks.

Each function in the quality layer behaves as follows:
- `profile()` and `validate()` convert an `ArFrame` to pandas for analysis/validation.
- `suggest_cleaning()` can inspect an existing `DataQualityReport` directly, or call `profile()` when given an `ArFrame`.
- `auto_clean()` calls `profile()` first, then applies selected cleaning helpers/pipeline steps to the original frame flow.

### What each function does

1. `profile()`: converts `ArFrame` to a pandas DataFrame internally, then computes per-column statistics including null counts, duplicate rows, data types, and unique value ratios. Returns a `DataQualityReport`.
2. `suggest_cleaning()`: accepts an `ArFrame` or an existing `DataQualityReport`. If given an `ArFrame`, it calls `profile()` first. Returns a list of cleaning steps that can be passed to `pipeline()`.
3. `auto_clean()`: accepts an `ArFrame`, calls `profile()` internally, then applies suggested cleaning steps directly to the original `ArFrame`. Returns a cleaned `ArFrame`.
4. `validate()`: converts `ArFrame` to a pandas DataFrame internally, then evaluates each column against rules defined in a `Schema` including nullability, dtype, range, pattern, and semantic constraints. Returns a `ValidationResult`.

```mermaid
graph TD
    A[ArFrame] -->|or| D[suggest_cleaning]
    A --> B[profile]
    A --> C[auto_clean]
    A --> H[validate]
    B --> E[DataQualityReport]
    E -->|or| D
    D --> F[step list]
    C --> G[cleaned ArFrame]
    H --> I[ValidationResult]
```
