"""
arnio.cli
---------
First-party command-line interface for arnio.

Entry point: ``arnio`` (registered in pyproject.toml).

Commands
--------
    arnio scan  --input FILE [--format json|text]

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
from typing import NoReturn

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _exit_error(message: str, code: int = 1) -> NoReturn:
    """Print an actionable error message to stderr and exit with *code*."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


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
    import os

    path = args.input
    if not os.path.exists(path):
        _exit_error(f"input file not found: {path!r}")
    if not os.path.isfile(path):
        _exit_error(f"input path is not a file: {path!r}")

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
            print("\u2500" * len(header))
            for col, dtype in ordered.items():
                print(f"{col:<{col_w}}{dtype}")

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
