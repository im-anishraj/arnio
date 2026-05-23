"""schema_export.py – deterministic YAML serialisation for arnio Schema objects.

Public API
----------
schema_to_dict(schema) -> dict
    Convert a Schema (or raw dict produced by ``ar.scan_csv``) to a plain,
    sorted, serialisation-ready dict.

schema_to_yaml(schema, path=None) -> str
    Return the YAML string.  When *path* is given the string is also written
    to that file (UTF-8, trailing newline guaranteed).

Only the Python standard library is required (no PyYAML dependency).
The emitter is intentionally minimal: it covers the types arnio actually
produces (str, int, float, bool, None, list, dict) and raises ``TypeError``
for anything else so the contract stays explicit.
"""

from __future__ import annotations

import pathlib
from typing import Any

from arnio.schema import _field_to_dict

_INDENT = "  "

# Types that arnio's Schema / scan_csv can legitimately produce.
_SCALAR_TYPES = (str, int, float, bool, type(None))


def _emit_scalar(value: Any) -> str:
    """Return a YAML-safe inline representation for a scalar value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        # bool must come before int (bool is a subclass of int in Python).
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:  # NaN
            return ".nan"
        if value == float("inf"):
            return ".inf"
        if value == float("-inf"):
            return "-.inf"
        return repr(value)
    if isinstance(value, str):
        # Quote strings that would be misread as YAML scalars or are empty.
        needs_quoting = (
            not value
            or value.lower() in {"true", "false", "null", "yes", "no", "on", "off"}
            or value[0]
            in (
                '"',
                "'",
                "{",
                "[",
                "|",
                ">",
                "!",
                "&",
                "*",
                "#",
                "?",
                ":",
                "-",
                ",",
                "@",
                "`",
                "%",
                "~",
            )
            or ":" in value
            or "#" in value
            or value != value.strip()
        )
        if needs_quoting:
            # Use double-quote style; escape backslashes and double-quotes.
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value
    raise TypeError(f"Unsupported scalar type: {type(value)!r}")


def _validate_serializable(value: Any) -> None:
    if isinstance(value, _SCALAR_TYPES):
        return

    if isinstance(value, set):
        for item in value:
            _validate_serializable(item)
        return

    if isinstance(value, list):
        for item in value:
            _validate_serializable(item)
        return

    if isinstance(value, dict):
        for item in value.values():
            _validate_serializable(item)
        return

    raise TypeError(f"schema_to_yaml does not support values of type {type(value)!r}.")


def _emit_value(value: Any, depth: int) -> str:
    """Recursively emit *value* at the given indentation *depth*."""
    indent = _INDENT * depth

    if isinstance(value, _SCALAR_TYPES):
        return _emit_scalar(value)

    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for k in sorted(value.keys()):  # deterministic key order
            v = value[k]
            key_str = _emit_scalar(str(k))
            rendered = _emit_value(v, depth + 1)
            if isinstance(v, dict) and v:
                lines.append(f"{indent}{key_str}:\n{rendered}")
            elif isinstance(v, list) and v:
                lines.append(f"{indent}{key_str}:\n{rendered}")
            else:
                lines.append(f"{indent}{key_str}: {rendered}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"
        lines = []
        for item in value:
            rendered = _emit_value(item, depth + 1)
            if isinstance(item, dict) and item:
                # Multi-line mapping under a list bullet.
                first_line, *rest = rendered.split("\n")
                block = "\n".join(
                    [f"{indent}- {first_line}"] + [f"{indent}  {r}" for r in rest]
                )
                lines.append(block)
            elif isinstance(item, list) and item:
                lines.append(f"{indent}-\n{rendered}")
            else:
                lines.append(f"{indent}- {rendered}")
        return "\n".join(lines)

    raise TypeError(
        f"schema_to_yaml does not support values of type {type(value)!r}. "
        "Only str, int, float, bool, None, list, and dict are allowed."
    )


def schema_to_dict(schema: dict | Any) -> dict:
    """Convert *schema* to a plain, sorted, serialisation-ready :class:`dict`.

    Parameters
    ----------
    schema:
        Either the raw ``dict`` returned by ``ar.scan_csv`` / ``ar.Schema``,
        or any object that exposes a ``fields`` attribute (mapping of field
        name → field descriptor) – whichever arnio uses internally.

    Returns
    -------
    dict
        A plain Python dict with only stdlib-serialisable values.

    Raises
    ------
    TypeError
        If *schema* is neither a ``dict`` nor an object with a ``fields``
        attribute.
    """
    if isinstance(schema, dict):
        raw: dict = schema
    elif hasattr(schema, "fields"):
        raw = {}

        if getattr(schema, "rules", None):
            raise ValueError(
                "schema_to_yaml does not support Schema objects with custom rules "
                "because callables are not serializable. "
                "Remove schema.rules before exporting."
            )

        for name, field in schema.fields.items():
            if isinstance(field, dict):
                raw[name] = field
            elif hasattr(field, "dtype"):
                raw[name] = _field_to_dict(field)
            elif hasattr(field, "__dict__"):
                raw[name] = {
                    k: v for k, v in vars(field).items() if not k.startswith("_")
                }
            else:
                raw[name] = str(field)

        if hasattr(schema, "strict"):
            raw["strict"] = schema.strict

        if hasattr(schema, "unique"):
            raw["unique"] = schema.unique
    else:
        raise TypeError(
            f"Expected a dict or an object with a 'fields' attribute, "
            f"got {type(schema)!r}."
        )

    # Normalise: if the dict values are plain strings (e.g. scan_csv output),
    # wrap them so the YAML has a consistent nested structure.
    normalised: dict = {}
    metadata: dict = {}

    for field_name in sorted(raw.keys()):
        value = raw[field_name]

        if field_name in {"strict", "unique"}:
            metadata[field_name] = value
            continue

        if isinstance(value, str):
            normalised[field_name] = {"type": value}

        elif isinstance(value, dict):
            cleaned = {}

            for k, v in sorted(value.items()):
                if isinstance(v, set):
                    cleaned[k] = sorted(v)
                else:
                    cleaned[k] = v

            _validate_serializable(cleaned)

            normalised[field_name] = cleaned

        else:
            normalised[field_name] = value

    result = {"fields": normalised}
    result.update(metadata)

    return result


def schema_to_yaml(
    schema: dict | Any,
    path: str | pathlib.Path | None = None,
) -> str:
    """Serialise *schema* to a YAML string.

    Parameters
    ----------
    schema:
        A ``dict`` (e.g. from ``ar.scan_csv``) or an arnio ``Schema`` object.
    path:
        Optional file path.  When supplied the YAML is written to that file
        (UTF-8 encoding, existing file is overwritten).  The string is always
        returned regardless.

    Returns
    -------
    str
        The YAML representation, always ending with ``\\n``.

    Examples
    --------
    >>> import arnio as ar
    >>> schema = ar.scan_csv("data.csv")
    >>> print(ar.schema_to_yaml(schema))
    fields:
      id:
        type: INT64
      name:
        type: STRING

    >>> ar.schema_to_yaml(schema, path="schema.yaml")   # also write to file
    """
    data = schema_to_dict(schema)
    body = _emit_value(data, depth=0)
    yaml_str = body if body.endswith("\n") else body + "\n"

    if path is not None:
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml_str, encoding="utf-8")

    return yaml_str
