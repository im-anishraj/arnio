# arnio

**Fast CSV loading and cleaning for Python, powered by C++.**

arnio handles the slowest, most repetitive part of working with tabular data: reading a raw CSV file, cleaning it up, and getting it into a DataFrame. The parsing and cleaning run in C++ through pybind11. The output is a standard pandas DataFrame.

<p align="center">
  <img src="intro.gif" alt="arnio demo" width="700">
</p>

```bash
pip install arnio
```

```python
import arnio as ar

# Load and clean in three lines
frame = ar.read_csv("customers.csv")

clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("drop_nulls",),
    ("drop_duplicates",),
])

df = ar.to_pandas(clean)
```

> Requires Python 3.9+. Wheels available for Linux, macOS, and Windows. Source builds require a C++17 compiler.

---

## How arnio is different

- **CSV parsing runs in C++, not Python.** On large files, `ar.read_csv()` uses measurably less time and memory than `pd.read_csv`.

- **Cleaning is built in, not bolted on.** `ar.pipeline()` takes a list of named steps and runs them in sequence. No scattered method chains, no copy-paste between notebooks.

- **Preview before you load.** `ar.scan_csv("file.csv")` returns column names and inferred types by sampling the file -- no full load required.

- **Exact memory tracking.** `frame.memory_usage()` returns real byte counts from C++. No estimation, no `deep=True`.

- **Pandas is the output, not the engine.** arnio reads and cleans your data natively, then hands you a DataFrame when you're ready.

---

## Performance

Benchmark: 1M-row CSV, 12 columns, mixed types.

| Tool   | Load time | Peak memory |
|--------|-----------|-------------|
| pandas | ~4.2s     | ~620 MB     |
| arnio  | ~2.1s     | ~380 MB     |

Approximately 2x faster CSV ingestion and 40% lower peak memory on large files.

*Measured on an M2 MacBook Pro, Python 3.11. Your results will vary. Benchmark with your own data.*

---

## pandas vs arnio

**pandas**

```python
import pandas as pd

df = pd.read_csv("sales.csv")

str_cols = df.select_dtypes(include="object").columns
df[str_cols] = df[str_cols].apply(lambda c: c.str.strip())

df = df.dropna()
df = df.drop_duplicates()
```

**arnio**

```python
import arnio as ar

frame = ar.read_csv("sales.csv")

clean = ar.pipeline(frame, [
    ("strip_whitespace",),
    ("drop_nulls",),
    ("drop_duplicates",),
])

df = ar.to_pandas(clean)
```

Same result. Less code. Each step is explicit. The pipeline runs in C++.

---

## When to use arnio

Use arnio when your bottleneck is **loading and cleaning CSVs** -- large files, messy columns, repeated preprocessing across projects.

Use pandas when you need **analysis** -- groupby, merge, pivot, time-series, plotting. arnio produces DataFrames; everything downstream stays the same.

arnio replaces the first steps of your notebook. It does that part faster and with less code. Everything after that is still pandas.

---

## Roadmap

arnio is actively in development. The core CSV reader and basic cleaning primitives are the current focus. Planned work includes:

- [x] C++ CSV parser core
- [x] Basic cleaning API (`drop_nulls`, `strip_whitespace`, `normalize_columns`)
- [x] pandas DataFrame output
- [ ] Streaming / chunked reads for very large files
- [ ] Type inference and automatic dtype casting
- [ ] Encoding detection and normalization
- [ ] Schema validation and column contracts
- [ ] Parallel parsing across CPU cores
- [ ] CLI tool (`arnio clean data.csv --output clean.csv`)
- [ ] Async-friendly API for use in async pipelines

Feedback on priorities is welcome — open a [GitHub Discussion](https://github.com/yourusername/arnio/discussions) to share what matters most to you.

---

## Contributing

Contributions are welcome and genuinely appreciated. arnio is early-stage, which means there's real space to shape how it grows.

**To get started:**

```bash
git clone https://github.com/yourusername/arnio.git
cd arnio
pip install -e ".[dev]"
```

Before submitting a pull request:

- Run the test suite: `pytest tests/`
- Follow the existing code style (enforced via `ruff`)
- Keep PRs focused — one concern per pull request
- Open an issue first for significant changes so the direction can be discussed

There's a [CONTRIBUTING.md](CONTRIBUTING.md) with more detail on the development setup, C++ build process, and testing approach.

---

## License

arnio is released under the [MIT License](LICENSE).

---

*Built to make Python data work feel faster and cleaner — one CSV at a time.*
