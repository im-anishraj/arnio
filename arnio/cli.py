"""
arnio.cli
---------
First-party command-line interface for arnio.

Entry point: ``arnio`` (registered in pyproject.toml).

Commands
--------
    arnio scan  --input FILE [--format json|text]
    arnio profile --input FILE [--format text|json|markdown]

Exit codes
----------
    0   success
    1   user error (bad args, missing file)
    2   unexpected internal error

Heavy dependencies (the C++ core) are imported lazily inside each command
handler so that ``arnio --help`` stays fast.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exit_error(message: str, code: int = 1) -> NoReturn:
    """Print an actionable error message to stderr and exit with *code*."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def _validate_input_file(path: str) -> None:
    """Validate that *path* points to a readable input file."""
    import os

    if not os.path.exists(path):
        _exit_error(f"input file not found: {path!r}")
    if not os.path.isfile(path):
        _exit_error(f"input path is not a file: {path!r}")


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


def _cmd_scan(args: argparse.Namespace) -> int:
    """Run ``arnio scan``.

    Calls :func:`arnio.scan_csv` which infers column types **without** loading
    the full dataset into memory.

    JSON output (``--format json``)::

        {
          "path": "data.csv",
          "columns": {"age": "int64", "name": "string", "score": "float64"}
        }

    Text output (``--format text``, default)::

        Scan: data.csv
        column          type
        ────────────────────
        age             int64
        name            string
        score           float64
    """
    path = args.input
    _validate_input_file(path)

    try:
        import arnio as ar  # lazy import keeps --help fast
    except ImportError as exc:  # pragma: no cover
        _exit_error(f"arnio package not importable: {exc}")

    try:
        schema: dict[str, str] = ar.scan_csv(path)
    except Exception as exc:
        _exit_error(f"scan failed for {path!r}: {exc}")

    # Stable ordering so output is deterministic and CI-friendly.
    ordered = dict(sorted(schema.items()))

    if args.format == "json":
        print(json.dumps({"path": path, "columns": ordered}, indent=2))
    else:
        print(f"Scan: {path}")
        if not ordered:
            print("  (no columns found)")
        else:
            col_w = max(len(c) for c in ordered) + 2
            header = f"{'column':<{col_w}}type"
            print(header)
            print("-" * len(header))
            for col, dtype in ordered.items():
                print(f"{col:<{col_w}}{dtype}")

    return 0


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------


def _format_suggestion(suggestion: Any) -> str:
    """Format a cleaning suggestion for compact CLI text output."""
    if hasattr(suggestion, "step"):
        step = suggestion.step
        kwargs = suggestion.kwargs
    else:
        step = suggestion[0]
        kwargs = suggestion[1]
    confidence = getattr(suggestion, "confidence_score", None)

    suffix = ""
    if confidence is not None:
        suffix = f" (confidence {confidence:.2f})"

    return f"{step}{suffix}: {json.dumps(kwargs, sort_keys=True, default=str)}"


def _format_profile_text(path: str, report: Any, *, max_suggestions: int = 5) -> str:
    """Return a readable text summary for ``arnio profile``."""
    lines = [
        f"Profile: {path}",
        f"Quality score: {report.quality_score:.2f}",
        f"Rows: {report.row_count}",
        f"Columns: {report.column_count}",
        f"Duplicate rows: {report.duplicate_rows} ({report.duplicate_ratio:.2%})",
        "",
        "Null counts:",
    ]

    if report.columns:
        name_width = max(len(str(name)) for name in report.columns) + 2
        header = f"{'column':<{name_width}}nulls  null_ratio"
        lines.append(header)
        lines.append("-" * len(header))
        for name in sorted(report.columns):
            column = report.columns[name]
            lines.append(
                f"{name:<{name_width}}{column.null_count:<7}{column.null_ratio:.2%}"
            )
    else:
        lines.append("  (no columns found)")

    lines.extend(["", "Top suggestions:"])
    suggestions = list(report.suggestions[:max_suggestions])
    if suggestions:
        for index, suggestion in enumerate(suggestions, start=1):
            lines.append(f"{index}. {_format_suggestion(suggestion)}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


def _cmd_profile(args: argparse.Namespace) -> int:
    """Run ``arnio profile`` and print a data-quality report."""
    path = args.input
    _validate_input_file(path)

    try:
        import arnio as ar  # lazy import keeps --help fast
    except ImportError as exc:  # pragma: no cover
        _exit_error(f"arnio package not importable: {exc}")

    try:
        frame = ar.read_csv(path)
        report = ar.profile(frame)
    except Exception as exc:
        _exit_error(f"profile failed for {path!r}: {exc}")

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    elif args.format == "markdown":
        print(report.to_markdown())
    else:
        print(_format_profile_text(path, report))

    return 0


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arnio",
        description="arnio \u2013 fast CSV processing and data cleaning companion for pandas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print arnio version and exit",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ---- scan ---------------------------------------------------------------
    p_scan = sub.add_parser(
        "scan",
        help="infer column types without loading data into memory",
        description=(
            "Quickly infer column names and types from a CSV file. "
            "No data is loaded into memory."
        ),
    )
    p_scan.add_argument(
        "--input", required=True, metavar="FILE", help="path to input CSV file"
    )
    p_scan.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )

    # ---- profile ------------------------------------------------------------
    p_profile = sub.add_parser(
        "profile",
        help="generate a data quality report for a CSV file",
        description=(
            "Load a CSV file and print a data quality report with row counts, "
            "null counts, quality score, duplicates, and cleaning suggestions."
        ),
    )
    p_profile.add_argument(
        "--input", required=True, metavar="FILE", help="path to input CSV file"
    )
    p_profile.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="output format (default: text)",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """CLI entry point registered in pyproject.toml."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        try:
            import arnio as ar  # lazy import

            print(ar.__version__)
        except ImportError:  # pragma: no cover
            print("unknown")
        return

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    _HANDLERS = {
        "scan": _cmd_scan,
        "profile": _cmd_profile,
    }

    handler = _HANDLERS.get(args.command)
    if handler is None:  # pragma: no cover – argparse prevents this
        _exit_error(f"unknown command: {args.command!r}", code=2)

    try:
        exit_code = handler(args)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        _exit_error(f"unexpected error: {exc}", code=2)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
