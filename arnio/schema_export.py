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
import re
from typing import Any

from arnio.schema import _field_to_dict

_INDENT = "  "

# Types that arnio's Schema / scan_csv can legitimately produce.
_SCALAR_TYPES = (str, int, float, bool, type(None))

# YAML 1.1 parsers resolve bare scalars matching date/datetime patterns to
# timestamp objects.  Any string matching this pattern must be quoted so it
# survives a round-trip as a string.
# Covers: YYYY-MM-DD, YYYY-MM-DDZ, YYYY-MM-DDThh:mm[:ss][...], YYYY-MM-DD hh:mm[:ss][...]
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?.*|Z)?$")


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
        looks_numeric = False
        try:
            float(value)
            looks_numeric = True
        except ValueError:
            pass

        # Quote strings that would be misread as YAML scalars or are empty.
        needs_quoting = (
            not value
            or looks_numeric
            or value.lower() in {"true", "false", "null", "yes", "no", "on", "off"}
            or any(c in value for c in ("\n", "\r"))
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
            # YAML 1.1 resolves date/datetime-looking scalars to timestamp
            # objects.  Quote them so string semantics are preserved on
            # round-trip.
            or bool(_DATE_RE.match(value))
        )
        if needs_quoting:
            # Use double-quote style; escape backslashes and double-quotes.
            escaped = (
                value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\r", "\\r")
            )
            return f'"{escaped}"'
        return value
    raise TypeError(f"Unsupported scalar type: {type(value)!r}")


# Validate nested container values recursively.
def _validate_serializable(value: Any) -> None:
    """Validate recursively that a value can be serialized."""

    if isinstance(value, _SCALAR_TYPES):
        return

    if isinstance(value, list):
        for item in value:
            _validate_serializable(item)
        return

    if isinstance(value, set):
        for item in value:
            _validate_serializable(item)
        return

    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError("schema dict keys must be strings")

            _validate_serializable(v)

        return

    raise TypeError(
        f"schema_to_yaml does not support values of type "
        f"{type(value)!r}. Only str, int, float, bool, "
        "None, list, and dict are allowed."
    )


# added normalize_serializable function
def _normalize_serializable(value: Any) -> Any:
    """Recursively normalize serialization-safe values.

    - dict keys are sorted deterministically
    - sets are converted into sorted lists
    - lists are normalized recursively
    - unsupported values raise TypeError
    """
    _validate_serializable(value)

    if isinstance(value, dict):
        return {k: _normalize_serializable(v) for k, v in sorted(value.items())}
    # Convert sets into deterministic sorted lists since YAML
    # emission only supports list-like serialized output.
    if isinstance(value, set):
        return sorted(_normalize_serializable(v) for v in value)

    if isinstance(value, list):
        return [_normalize_serializable(v) for v in value]

    return value


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
        Also supports ArFrame objects and lists of ColumnSummary.

    Returns
    -------
    dict
        A plain Python dict with only stdlib-serialisable values.

    Raises
    ------
    TypeError
        If *schema* is not of a supported type.
    """
    # ── ArFrame path ────────────────────────────────────────────────────────
    if hasattr(schema, "schema_summary"):
        schema = schema.schema_summary

    # ── List of ColumnSummary path ──────────────────────────────────────────
    if isinstance(schema, list):
        normalised_list = {}
        for entry in schema:
            if hasattr(entry, "name") and hasattr(entry, "dtype"):
                name = entry.name
                normalised_list[name] = {
                    "type": str(entry.dtype).upper(),
                }
                if hasattr(entry, "nullable"):
                    normalised_list[name]["nullable"] = entry.nullable
            elif isinstance(entry, dict) and "name" in entry and "dtype" in entry:
                name = entry["name"]
                normalised_list[name] = {
                    "type": str(entry["dtype"]).upper(),
                }
                if "nullable" in entry:
                    normalised_list[name]["nullable"] = entry["nullable"]
            else:
                raise TypeError(f"Unsupported list item type: {type(entry)!r}")
        return {"fields": normalised_list}

    # ── Schema object path ──────────────────────────────────────────────────
    if hasattr(schema, "fields"):
        if getattr(schema, "rules", None):
            raise ValueError(
                "schema_to_yaml does not support Schema objects with custom rules "
                "because callables are not serializable. "
                "Remove schema.rules before exporting."
            )

        normalised: dict = {}
        for name, field in schema.fields.items():
            if isinstance(field, dict):
                raw_field = field
            elif hasattr(field, "dtype"):
                raw_field = _field_to_dict(field)
            elif hasattr(field, "__dict__"):
                raw_field = {
                    k: v for k, v in vars(field).items() if not k.startswith("_")
                }
            else:
                raw_field = str(field)

            if isinstance(raw_field, str):
                normalised[name] = {"type": raw_field}
            elif isinstance(raw_field, dict):
                normalised[name] = _normalize_serializable(raw_field)
            else:
                normalised[name] = raw_field

        # Build result cleanly — metadata never touches the fields namespace
        result = {"fields": dict(sorted(normalised.items()))}
        if hasattr(schema, "strict"):
            result["strict"] = schema.strict
        if hasattr(schema, "unique"):
            result["unique"] = schema.unique

        return result

    # ── Raw dict path ────────────────────────────────────────────────────────
    if isinstance(schema, dict):
        # Detect explicit structured input:
        # {"fields": {...}, "strict": ..., "unique": ...}
        if "fields" in schema and isinstance(schema["fields"], dict):
            raw_fields = schema["fields"]
            metadata = {k: v for k, v in schema.items() if k != "fields"}
        else:
            # Flat scan_csv-style dict:
            # all keys are field names
            raw_fields = schema
            metadata = {}

        normalised = {}

        for field_name in sorted(raw_fields.keys()):
            value = raw_fields[field_name]

            # Recursively normalize nested containers
            # into serialization-safe deterministic values.
            if isinstance(value, str):
                normalised[field_name] = {"type": value}
            else:
                normalised[field_name] = _normalize_serializable(value)

        result = {"fields": normalised}
        result.update(metadata)

        return result

    raise TypeError(
        f"Expected a dict, an ArFrame, or an object with a 'fields' attribute, "
        f"got {type(schema)!r}."
    )


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
