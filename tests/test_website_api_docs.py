"""Website API reference drift checks.

Extends the existing suite with targeted regression coverage for the six
public I/O functions whose signatures drifted on website/api.html.

Each new test extracts only the specific function's signature row from the
HTML before asserting, so a token present in another function's row cannot
mask drift in the target function.

Fixes #2174
"""

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Helpers shared by existing and new tests
# ---------------------------------------------------------------------------


def _public_exports() -> list[str]:
    tree = ast.parse((REPO_ROOT / "arnio" / "__init__.py").read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                return [
                    item.value
                    for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                ]
    raise AssertionError("arnio.__all__ not found")


def _api_html() -> str:
    return (REPO_ROOT / "website" / "api.html").read_text()


def _signature_row(fn_name: str, html: str) -> str:
    """Return the text of the single .api-func-header element whose content
    starts with *fn_name*.  Raises AssertionError if not found."""
    # Match the content between the opening and closing tag of api-func-header
    # that begins with the target function name.
    pattern = re.compile(
        r'class="api-func-header">(' + re.escape(fn_name) + r".*?)</div>",
        re.DOTALL,
    )
    m = pattern.search(html)
    assert m, f"No api-func-header row found for {fn_name!r} in website/api.html"
    return m.group(1)


def _io_params(fn_name: str) -> tuple[list[str], dict[str, str]]:
    """Return (param_names, defaults) for *fn_name* from arnio/io.py.

    Parsed via ``ast`` so no C++ extension import is required.
    String defaults are rendered with double quotes to match the HTML.
    """
    tree = ast.parse((REPO_ROOT / "arnio" / "io.py").read_text())
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == fn_name):
            continue
        args = node.args
        all_params = [a.arg for a in args.args] + [a.arg for a in args.kwonlyargs]

        def _dq(node) -> str:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return f'"{node.value}"'
            return ast.unparse(node)

        defaults: dict[str, str] = {}
        for arg, d in zip(reversed(args.args), reversed(args.defaults)):
            defaults[arg.arg] = _dq(d)
        for arg, d in zip(args.kwonlyargs, args.kw_defaults):
            if d is not None:
                defaults[arg.arg] = _dq(d)

        return all_params, defaults

    raise AssertionError(f"Function {fn_name!r} not found in arnio/io.py")


def _check(fn_name: str, row: str, params: list[str], defaults: dict[str, str]) -> None:
    """Assert *params* names and *defaults* tokens appear in *row*."""
    missing = [p for p in params if p not in row]
    assert (
        missing == []
    ), f"{fn_name}: parameter(s) absent from its api-func-header row: {missing}"
    for param, value in defaults.items():
        token = f"{param}={value}"
        assert (
            token in row
        ), f"{fn_name}: expected token '{token}' not found in its api-func-header row"


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


def test_website_api_reference_mentions_public_exports():
    api_html = _api_html()
    missing = [name for name in _public_exports() if name not in api_html]
    assert missing == []


def test_website_profile_signature_matches_current_options():
    api_html = _api_html()
    assert "top_n=5" not in api_html
    assert "approx_top_values_min_unique=1000" in api_html
    assert "approx_top_values_min_ratio=0.2" in api_html
    assert "approx_top_values_sample_size=2000" in api_html


# ---------------------------------------------------------------------------
# New: targeted drift checks for the six stale I/O signatures (#2174)
# Each test extracts only that function's own signature row before asserting.
# ---------------------------------------------------------------------------


def test_read_csv_signature_matches_website():
    """read_csv: required params present in its own row; delimiter=None not ','."""
    row = _signature_row("read_csv", _api_html())
    _check(
        "read_csv",
        row,
        params=[
            "delimiter",
            "trim_headers",
            "thousands_separator",
            "null_values",
            "mode",
        ],
        defaults={
            "delimiter": "None",
            "mode": '"strict"',
            "encoding_errors": '"strict"',
            "on_bad_lines": '"error"',
        },
    )


def test_read_csv_chunked_signature_matches_website():
    """read_csv_chunked: required params present in its own row."""
    row = _signature_row("read_csv_chunked", _api_html())
    _check(
        "read_csv_chunked",
        row,
        params=[
            "dtype",
            "usecols",
            "nrows",
            "skip_rows",
            "skiprows",
            "trim_headers",
            "thousands_separator",
            "null_values",
            "mode",
        ],
        defaults={
            "delimiter": "None",
            "skip_rows": "0",
            "mode": '"strict"',
            "on_bad_lines": '"error"',
        },
    )


def test_scan_csv_signature_matches_website():
    """scan_csv: required params present in its own row."""
    row = _signature_row("scan_csv", _api_html())
    _check(
        "scan_csv",
        row,
        params=[
            "thousands_separator",
            "sample_size",
            "null_values",
            "mode",
            "on_bad_lines",
        ],
        defaults={
            "delimiter": "None",
            "mode": '"strict"',
            "on_bad_lines": '"error"',
            "encoding_errors": '"strict"',
        },
    )


def test_read_jsonl_signature_matches_website():
    """read_jsonl: encoding and encoding_errors in its own row."""
    row = _signature_row("read_jsonl", _api_html())
    _check(
        "read_jsonl",
        row,
        params=["encoding", "encoding_errors"],
        defaults={
            "encoding": '"utf-8"',
            "encoding_errors": '"strict"',
        },
    )


def test_read_jsonl_chunked_signature_matches_website():
    """read_jsonl_chunked: chunk size plus decoding controls in its own row."""
    row = _signature_row("read_jsonl_chunked", _api_html())
    _check(
        "read_jsonl_chunked",
        row,
        params=["chunksize", "encoding", "encoding_errors"],
        defaults={
            "chunksize": "10000",
            "encoding": '"utf-8"',
            "encoding_errors": '"strict"',
        },
    )


def test_write_parquet_signature_matches_website():
    """write_parquet: compression='snappy' and preserve_attrs in its own row."""
    row = _signature_row("write_parquet", _api_html())
    _check(
        "write_parquet",
        row,
        params=["compression", "preserve_attrs"],
        defaults={
            "compression": '"snappy"',
            "preserve_attrs": "True",
        },
    )


def test_sniff_delimiter_signature_matches_website():
    """sniff_delimiter: sample_size present in its own row."""
    row = _signature_row("sniff_delimiter", _api_html())
    _check(
        "sniff_delimiter",
        row,
        params=["sample_size"],
        defaults={
            "sample_size": "2048",
        },
    )


# ---------------------------------------------------------------------------
# New: badge check for unreleased APIs (#2368)
# ---------------------------------------------------------------------------


def test_website_marks_unreleased_apis():
    # v1.19.0 exports from git
    v1_19_0_exports = {
        "ArFrame",
        "ColumnSummary",
        "read_csv",
        "read_csv_chunked",
        "read_jsonl",
        "write_csv",
        "write_parquet",
        "scan_csv",
        "sniff_delimiter",
        "drop_nulls",
        "drop_columns",
        "select_columns",
        "keep_rows_with_nulls",
        "fill_nulls",
        "validate_columns_exist",
        "filter_rows",
        "replace_values",
        "normalize_whitespace",
        "drop_duplicates",
        "drop_constant_columns",
        "drop_empty_columns",
        "clean_column_names",
        "clip_numeric",
        "winsorize_outliers",
        "coalesce_columns",
        "combine_columns",
        "drop_columns_matching",
        "strip_whitespace",
        "parse_bool_strings",
        "normalize_case",
        "rename_columns",
        "round_numeric_columns",
        "cast_types",
        "clean",
        "safe_divide_columns",
        "trim_column_names",
        "standardize_missing_tokens",
        "to_pandas",
        "to_arrow",
        "from_pandas",
        "from_records",
        "from_dict",
        "ArnioPandasAccessor",
        "register_duckdb",
        "pipeline",
        "register_step",
        "unregister_step",
        "get_builtin_step_signatures",
        "list_steps",
        "PipelineContext",
        "reset_steps",
        "profile",
        "compare_profiles",
        "check_quality_gates",
        "suggest_cleaning",
        "auto_clean",
        "ColumnProfile",
        "DataQualityReport",
        "CleanStepRecord",
        "CleanExplanation",
        "ProfileComparison",
        "QualityGateIssue",
        "QualityGateResult",
        "Schema",
        "SchemaDiff",
        "SchemaDiffEntry",
        "Field",
        "ValidationIssue",
        "ValidationResult",
        "validate",
        "diff_schema",
        "Int64",
        "Float64",
        "String",
        "CountryCode",
        "CurrencyCode",
        "LanguageCode",
        "TimeZone",
        "Bool",
        "Email",
        "URL",
        "PhoneNumber",
        "DateTime",
        "UnknownStepError",
        "ArnioError",
        "CsvReadError",
        "JsonlReadError",
        "TypeCastError",
        "PipelineStepError",
        "SchemaValidationError",
        "normalize_unicode",
        "Regex",
        "Custom",
        "register_validator",
        "Date",
        "schema_to_dict",
        "schema_to_yaml",
    }

    current_exports = set(_public_exports())
    unreleased_apis = current_exports - v1_19_0_exports

    api_html = _api_html()

    for api in unreleased_apis:
        # Not every API is individually documented. Only test those that appear in api.html
        if api in api_html:
            # Check that the API name is closely followed by the unreleased badge or enclosed in a block with it.
            # We allow up to 150 characters between the api name and the badge.
            pattern = re.compile(
                re.escape(api) + r'.{0,150}?<span[^>]*class="[^"]*badge-unreleased',
                re.IGNORECASE | re.DOTALL,
            )
            assert pattern.search(
                api_html
            ), f"Unreleased API {api!r} appears in website/api.html but lacks a badge-unreleased"
