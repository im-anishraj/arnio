"""Website API reference drift checks.

Extends the existing suite with targeted regression coverage for the six
public I/O functions whose signatures drifted on website/api.html.

Fixes #2174
"""

import ast
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
            # HTML signatures use double-quoted string literals; ast.unparse
            # uses single quotes, so normalise for a direct substring search.
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


def _check(
    fn_name: str, html: str, params: list[str], defaults: dict[str, str]
) -> None:
    """Assert *params* names and *defaults* tokens appear in *html*."""
    missing = [p for p in params if p not in html]
    assert (
        missing == []
    ), f"{fn_name}: parameter(s) absent from website/api.html: {missing}"
    for param, value in defaults.items():
        token = f"{param}={value}"
        assert (
            token in html
        ), f"{fn_name}: expected token '{token}' not found in website/api.html"


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
# ---------------------------------------------------------------------------


def test_read_csv_signature_matches_website():
    """read_csv: required params present; delimiter=None not hardcoded as ','."""
    html = _api_html()
    _check(
        "read_csv",
        html,
        params=[
            "delimiter",
            "trim_headers",
            "thousands_separator",
            "null_values",
            "mode",
        ],
        defaults={
            "delimiter": "None",  # website previously showed delimiter=","
            "mode": '"strict"',
            "encoding_errors": '"strict"',
            "on_bad_lines": '"error"',
        },
    )


def test_read_csv_chunked_signature_matches_website():
    """read_csv_chunked: required params present and key defaults correct."""
    html = _api_html()
    _check(
        "read_csv_chunked",
        html,
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
    """scan_csv: required params present and key defaults correct."""
    html = _api_html()
    _check(
        "scan_csv",
        html,
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
    """read_jsonl: encoding and encoding_errors must be documented."""
    html = _api_html()
    _check(
        "read_jsonl",
        html,
        params=["encoding", "encoding_errors"],
        defaults={
            "encoding": '"utf-8"',
            "encoding_errors": '"strict"',
        },
    )


def test_write_parquet_signature_matches_website():
    """write_parquet: compression default must be 'snappy', not None."""
    html = _api_html()
    _check(
        "write_parquet",
        html,
        params=["compression", "preserve_attrs"],
        defaults={
            "compression": '"snappy"',  # website previously showed compression=None
            "preserve_attrs": "True",
        },
    )


def test_sniff_delimiter_signature_matches_website():
    """sniff_delimiter: sample_size must be documented."""
    html = _api_html()
    _check(
        "sniff_delimiter",
        html,
        params=["sample_size"],
        defaults={
            "sample_size": "2048",
        },
    )
