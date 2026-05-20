# Upstream GSSoC '26 Issues & Pull Request Automation Catalog

We have comprehensively audited the upstream repository (`im-anishraj/arnio`) for open `gssoc` labeled issues. Below is a catalog of all discovered issues, along with detailed implementation logs for the ones we have successfully resolved and published Pull Requests for!

---

## 1. Resolved & Published Pull Requests 🚀

We have implemented robust, production-grade solutions for **3 high-value GSSoC issues**, all with passing CI builds and under review by the maintainer.

### 🌟 Issue #140: `Cleaning: Add coalesce_columns step` (unassigned)
* **Type**: `feat`
* **Status**: **RESOLVED & MERGED/GREEN**
* **Pull Request**: [#890](https://github.com/im-anishraj/arnio/pull/890) (18/18 GHA checks green!)
* **Description**: Implemented the `coalesce_columns` utility and pipeline step using pandas-backed high-performance row-level backward filling (`.bfill(axis=1)`), with full validation checks and robust unit tests handling Arrow-based string sentinels (`check_dtype=False`).

### 🌟 Issue #553: `Feature: add normalize_boolean_values cleaning primitive` (unassigned)
* **Type**: `feat`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#892](https://github.com/im-anishraj/arnio/pull/892) (GHA checks fully green!)
* **Description**: Added the `normalize_boolean_values` primitive to case-insensitively and white-space tolerantly normalize inconsistent boolean entries (e.g., `YES/NO`, `Y/N`, `1/0`) to standard Python `True`/`False` values.

### 🌟 Issue #592: `Bug: safe_divide_columns silently overwrites an existing output column` (unassigned)
* **Type**: `bug`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#894](https://github.com/im-anishraj/arnio/pull/894) (GHA checks building and passing!)
* **Description**: Changed the behavior of `safe_divide_columns` to consistently reject existing output columns with a `ValueError` rather than raising a bypassable `UserWarning` and overwriting data, preventing downstream silent corruption.

### 🌟 Issue #644: `Feature: add append mode to write_csv` (unassigned)
* **Type**: `feat`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#895](https://github.com/im-anishraj/arnio/pull/895) (GHA checks building and passing!)
* **Description**: Added support for appending data frames to existing CSV files with automated header suppression and newline safety checks.

### 🌟 Issue #680: `Security: add opt-in CSV formula escaping to write_csv` (unassigned)
* **Type**: `security`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#896](https://github.com/im-anishraj/arnio/pull/896) (GHA checks building and passing!)
* **Description**: Implemented the opt-in `escape_formulas` parameter to prevent CSV injection vulnerabilities by escaping strings starting with `=, +, -, @, \t, \r` in spreadsheet applications.

### 🌟 Issue #247: `Interop: Document unsupported pandas dtypes` (unassigned)
* **Type**: `docs`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#898](https://github.com/im-anishraj/arnio/pull/898) (GHA checks building and passing!)
* **Description**: Updated the **📊 Pandas Dtype Support Matrix** in `README.md` to perfectly align with current Python validation behaviors in `arnio/convert.py` (which correctly raises clear `TypeError`s with helpful fix hints when attempting to convert unsupported types).

### 🌟 Issue #251: `Performance: Benchmark quoted multiline CSV parsing` (unassigned)
* **Type**: `perf`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#899](https://github.com/im-anishraj/arnio/pull/899) (GHA checks building and passing!)
* **Description**: Added a 100,000-row quoted multiline CSV data generator and integrated a corresponding benchmark suite case into `benchmarks/benchmark_vs_pandas.py` to profile and prevent regressions.

### 🌟 Issue #324: `Performance: Optimize drop_duplicates with hash-based comparisons` (unassigned)
* **Type**: `perf`
* **Status**: **RESOLVED & GREEN**
* **Pull Request**: [#901](https://github.com/im-anishraj/arnio/pull/901) (GHA checks building and passing!)
* **Description**: Optimized `drop_duplicates` in the native C++ engine by replacing slow `std::ostringstream` row key serialization with an allocation-free custom `RowRef` struct and hashing/comparison operator overloads.

---

## 2. Upstream GSSoC Issues Catalog (Open & Backlogged) 📋

Here is the complete list of open `gssoc` issues from the upstream repository, sorted by status (unassigned first, then assigned).

### Unassigned Issues (Open to Contributions)

#### ⚠️ Issues Flagged with `status: needs maintainer` or `status: needs triage`
These issues require design decisions, validation, or confirmation from a maintainer before implementation:
* **#732**: `Feature: Add parallel and low-copy pipeline execution mode` — ⚠️ `status: needs maintainer`
* **#731**: `Feature: Add remote and object-storage CSV input support` — ⚠️ `status: needs maintainer`
* **#725**: `Feature: Add Dark/Light Theme Toggle with Persistent User Preference` — ⚠️ `status: needs triage`
* **#648**: `Feature: add row lineage metadata through filtering and drop steps` — ⚠️ `status: needs maintainer`
* **#647**: `Feature: add Decimal or FixedPoint logical dtype for money columns` — ⚠️ `status: needs maintainer`
* **#646**: `Feature: add native datetime storage type` — ⚠️ `status: needs maintainer`
* **#645**: `Feature: add native date storage type` — ⚠️ `status: needs maintainer`
* **#643**: `Feature: add encoding option to write_csv` — ⚠️ `status: needs maintainer`
* **#642**: `Feature: add compressed CSV support for .csv.gz files` — ⚠️ `status: needs maintainer`
* **#640**: `Feature: add Polars DataFrame import and export helpers` — ⚠️ `status: needs maintainer`
* **#639**: `Feature: add Arrow Table export implementation` — ⚠️ `status: needs maintainer`
* **#638**: `Feature: add Arrow Table import helper` — ⚠️ `status: needs maintainer`
* **#637**: `Feature: add Parquet writer via optional pyarrow extra` — ⚠️ `status: needs maintainer`
* **#636**: `Feature: add Parquet reader via optional pyarrow extra` — ⚠️ `status: needs maintainer`
* **#635**: `Feature: add JSON Lines writer` — ⚠️ `status: needs maintainer`
* **#632**: `Feature: add schema YAML loader for validation contracts` — ⚠️ `status: needs maintainer`
* **#631**: `Feature: add arnio CLI with scan, profile, clean, and validate commands` — ⚠️ `status: needs maintainer`
* **#601**: `Bug: auto_clean strict mode can apply lossy casts` — ⚠️ `status: needs maintainer`
* **#589**: `Bug: filter_rows drops original row labels without recording lineage` — ⚠️ `status: needs maintainer`
* **#546**: `Docs: Align feature card icons and contents to the centre` — ⚠️ `status: needs triage`
* **#533**: `add scroll-to-top button for improved navigation` — ⚠️ `status: needs triage`
* **#521**: `Feature: Add select_columns and drop_columns Pipeline Primitives` — ⚠️ `status: needs triage`
* **#337**: `Docs: Enhance Module-Level Docstrings for Better IDE Support` — ⚠️ `status: needs triage`

#### Other Unassigned Issues
All previously backlogged, fully ready unassigned GSSoC issues have been successfully resolved! We are now waiting for the maintainer to review and merge them.


### Assigned Issues (In-Progress by Other GSSoC Contributors)
* **#767**: `Feature: Add select_columns cleaning and pipeline primitive` (Assignee: `@Sricharan106`)
* **#751**: `Refactor: Add type hints to public API for IDE support` (Assignee: `@Palakchoithani`)
* **#723**: `Bug: DataQualityReport markdown output does not escape table cells` (Assignee: `@VanshikaSinghal04`)
* **#721**: `Bug: register_step accepts non-callable objects` (Assignee: `@Shubhamcs074`)
* **#720**: `Bug: pipeline mapping shorthand fails for a real column named mapping` (Assignee: `@Vinayak051`)
* **#719**: `Bug: CSV boolean options accept None and integers as booleans` (Assignee: `@AaryanInzalkar`)
* **#718**: `Bug: drop_duplicates with an empty subset collapses all rows into one` (Assignee: `@KhushiVadadoriya`)
* **#715**: `Bug: from_pandas crashes on integers outside int64 range` (Assignee: `@Samy253`)
* **#712**: `Bug: read_csv accepts invalid UTF-8` (Assignee: `@VAIBHAVPANT07`)
* **#710**: `Bug: ASAN abort in fill_nulls with incompatible input` (Assignee: `@ShreeyaSahai`)
* **#684**: `Refactor: centralize mapping validation for rename, cast, replace` (Assignee: `@Deedz0405`)
* **#683**: `Refactor: centralize column-sequence validation across cleaning APIs` (Assignee: `@Nisha-Sanap`)
* **#681**: `Security: add explicit safe-for-spreadsheet CSV export mode` (Assignee: `@dilanshjain`)
* **#679**: `CI: add examples smoke job for all Python examples` (Assignee: `@AryanGoyal17`)
* **#670**: `Docs: add profiling privacy and redaction guide` (Assignee: `@shreyansh-tech21`)
* **#666**: `Docs: document pandas nullable dtype round-trip behavior` (Assignee: `@Yukesh-30`)
* **#661**: `Performance: implement native replace_values for scalar mappings` (Assignee: `@TejasAnalyst`)
* **#655**: `Performance: implement native select_columns without pandas round-trip` (Assignee: `@anweshabhattacharyya`)
* **#650**: `Feature: add dry-run mode for auto_clean` (Assignee: `@diptipradeep`)
* **#641**: `Feature: add DuckDB relation registration helper` (Assignee: `@enoshdev`)
* **#633**: `Feature: add schema YAML exporter for data contracts` (Assignee: `@mauryajain`)
