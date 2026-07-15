"""Schema inference — infer a schema from existing data.

``infer_schema(data)`` inspects data to produce a Schema that describes it.
Useful for bootstrapping schemas from existing datasets.
"""

from __future__ import annotations

from typing import Any

from arnio.adapt._detect import resolve_adapter
from arnio.schema._fields import Bool, DateTime, Field, Float, Int, String
from arnio.schema._schema import Schema


def _infer_field(dtype: str, null_count: int, row_count: int) -> Field:
    """Infer a Field type from column dtype and null information."""
    nullable = null_count > 0

    dtype_to_field: dict[str, type[Field]] = {
        "int64": Int,
        "float64": Float,
        "bool": Bool,
        "datetime": DateTime,
    }

    field_cls = dtype_to_field.get(dtype, String)
    return field_cls(nullable=nullable)


def infer_schema(data: Any) -> Schema:
    """Infer a Schema from existing data.

    Inspects each column's dtype and null rate to produce a best-guess
    schema. The result is a starting point — users should refine it
    with domain-specific constraints.

    Args:
        data: Any supported data type (pandas DataFrame, list of dicts, etc.)

    Returns:
        A Schema with one field per column.
    """
    adapter = resolve_adapter(data)
    fields: dict[str, Field] = {}
    row_count = adapter.row_count()

    for col in adapter.column_names():
        dtype = adapter.column_dtype(col)
        null_count = adapter.null_count(col)
        fields[col] = _infer_field(dtype, null_count, row_count)

    return Schema(fields)
