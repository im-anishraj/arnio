"""Focused drift checks for API_REFERENCE.md."""

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DOCUMENTED_PUBLIC_APIS = [
    "read_csv_chunked",
    "read_jsonl",
    "read_jsonl_chunked",
    "write_jsonl",
    "read_parquet",
    "write_parquet",
    "from_dict",
    "from_records",
    "to_arrow",
    "from_polars",
    "to_polars",
    "encode_categorical",
]


def _public_exports() -> set[str]:
    tree = ast.parse((REPO_ROOT / "arnio" / "__init__.py").read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                return {
                    item.value
                    for item in node.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                }
    raise AssertionError("arnio.__all__ not found")


def test_api_reference_documents_selected_public_exports():
    """Keep issue #2545's focused API_REFERENCE.md sync from drifting."""
    public_exports = _public_exports()
    api_reference = (REPO_ROOT / "API_REFERENCE.md").read_text(encoding="utf-8")

    missing_exports = [
        name for name in DOCUMENTED_PUBLIC_APIS if name not in public_exports
    ]
    assert missing_exports == []

    missing_index_links = [
        name
        for name in DOCUMENTED_PUBLIC_APIS
        if f"[`{name}`](#{name})" not in api_reference
    ]
    assert missing_index_links == []

    missing_sections = [
        name
        for name in DOCUMENTED_PUBLIC_APIS
        if re.search(rf"^### {re.escape(name)}$", api_reference, re.MULTILINE) is None
    ]
    assert missing_sections == []
