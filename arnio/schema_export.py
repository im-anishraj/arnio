"""schema_export.py – deterministic YAML serialisation for arnio Schema objects.

Public API
----------
schema_to_dict(schema) -> dict
    Convert a Schema (or raw dict produced by ``ar.scan_csv``) to a plain,
    sorted, serialisation-ready dict.

schema_to_yaml(schema, path=None) -> str
    Return the YAML string.  When *path* is given the string is also written
    to that file (UTF-8, trailing newline guaranteed).

schema_from_yaml(source) -> Schema
    Load a Schema from a YAML file path or raw YAML string.  This is the
    inverse of ``schema_to_yaml`` and reuses the existing ``Schema.from_json``
    validation path so field contracts are enforced identically.

Only the Python standard library is required (no PyYAML dependency) for the
emit path.  ``schema_from_yaml`` requires PyYAML (already listed as a project
dependency in ``pyproject.toml``).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib
import re
import warnings
from typing import Any

from arnio.schema import Schema, _field_to_dict

_INDENT = "  "

# Matches ISO date and datetime strings that YAML 1.1 resolves as timestamps.
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?.*)?$")

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
            or bool(_DATE_RE.match(value))
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
    - tuples are converted into lists
    - lists are normalized recursively
    - unsupported values raise TypeError
    """
    # Normalize tuples to lists before validation so that tuple fields
    # (e.g. required_if=("col", "val"), unique=("id",)) survive export.
    if isinstance(value, tuple):
        return [_normalize_serializable(v) for v in value]

    _validate_serializable(value)

    if isinstance(value, dict):
        return {k: _normalize_serializable(v) for k, v in sorted(value.items())}
    # Convert sets into deterministic sorted lists since YAML
    # emission only supports list-like serialized output.
    # Use a type-and-repr key so mixed-type sets (e.g. {1, "1"})
    # sort deterministically instead of raising TypeError.
    if isinstance(value, set):
        return sorted((_normalize_serializable(v) for v in value), key=lambda v: (type(v).__name__, repr(v)))

    if isinstance(value, list):
        return [_normalize_serializable(v) for v in value]

    return value


def _serializable_sort_key(value: Any) -> tuple[str, str]:
    return (type(value).__name__, repr(value))


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

        raw_fields = schema.fields
        _validate_schema_field_names(raw_fields)

        normalised: dict = {}
        for name, field in raw_fields.items():
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

        _validate_schema_field_names(raw_fields)
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

        # Validate and normalize structured metadata before merging.
        # Keys must be strings; values must be serialization-safe.
        for meta_key, meta_val in metadata.items():
            if not isinstance(meta_key, str):
                raise TypeError(
                    f"schema metadata keys must be strings, got {type(meta_key)!r}"
                )
            result[meta_key] = _normalize_serializable(meta_val)

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
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError("path must be a string or os.PathLike")
        if isinstance(path, str) and not path.strip():
            raise ValueError("path must not be empty")
        target = pathlib.Path(path)
        if target.is_dir():
            raise ValueError("path must point to a file, not a directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml_str, encoding="utf-8")

    return yaml_str


def _normalize_yaml_payload(obj: Any) -> Any:
    """Recursively convert YAML-native types to JSON-safe equivalents.

    ``yaml.safe_load`` may produce ``datetime.date`` or ``datetime.datetime``
    objects for timestamp-looking values (e.g. ``datetime_min: 2024-01-01``).
    These are not JSON-serialisable by default, so we convert them to ISO
    strings here before handing off to ``Schema.from_json``.  All other
    types supported by ``_ALLOWED_FIELD_KEYS`` are already JSON-native.
    """
    if isinstance(obj, dict):
        return {k: _normalize_yaml_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_yaml_payload(item) for item in obj]
    if isinstance(obj, _dt.datetime):
        return obj.isoformat()
    if isinstance(obj, _dt.date):
        return obj.isoformat()
    return obj


def schema_from_yaml(source: str | os.PathLike) -> Schema:
    """Load a Schema from a YAML file path or raw YAML string.

    This is the inverse of :func:`schema_to_yaml`.  Field validation reuses
    the existing ``Schema.from_json`` path, so the same key allowlists and
    constraint checks apply.

    Parameters
    ----------
    source : str or path-like
        The input is resolved according to the following deterministic rules:

        * **Path-like object** (``pathlib.Path`` or any ``os.PathLike``):
          always treated as a file path.  ``FileNotFoundError`` is raised if
          the file does not exist.
        * **String without newlines**: treated as a file path.
          ``FileNotFoundError`` is raised if the file does not exist.
        * **String containing at least one newline**: parsed directly as raw
          YAML text.

    Returns
    -------
    Schema
        Fully validated :class:`~arnio.schema.Schema` object.

    Raises
    ------
    TypeError
        If *source* is not a ``str`` or ``os.PathLike``.
    FileNotFoundError
        If *source* resolves to a file path and the file is not found.
    ValueError
        If the YAML is syntactically invalid or the payload contains unknown
        schema or field keys.

    Notes
    -----
    Cross-field ``rules`` cannot be serialized and will never appear in a
    YAML file produced by :func:`schema_to_yaml`.  If the YAML payload
    contains ``rules_omitted: true`` (a marker written by ``Schema.to_json``
    when rules were present), a :class:`UserWarning` is emitted and the
    marker is silently ignored.  Re-attach rules manually after loading.

    PyYAML (``PyYAML>=6.0``) is required and is already listed as a project
    dependency in ``pyproject.toml``.

    Examples
    --------
    Load from a checked-in config file:

    >>> schema = ar.schema_from_yaml("contracts/users.yaml")
    >>> schema = ar.schema_from_yaml(pathlib.Path("contracts/users.yaml"))

    Parse an inline YAML string (at least one newline required):

    >>> yaml_text = \"\"\"
    ... fields:
    ...   age:
    ...     dtype: int64
    ...     nullable: false
    ...   email:
    ...     dtype: string
    ...     semantic: email
    ... \"\"\"
    >>> schema = ar.schema_from_yaml(yaml_text)
    """
    try:
        import yaml  # PyYAML — listed in pyproject.toml dependencies
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "schema_from_yaml requires PyYAML. "
            "Install it with: pip install 'PyYAML>=6.0'"
        ) from exc

    if isinstance(source, os.PathLike):
        # Always treat any path-like object as a file path.
        path = pathlib.Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Schema YAML file not found: {path}")
        text = path.read_text(encoding="utf-8")

    elif isinstance(source, str):
        if "\n" in source:
            # String with newlines → raw YAML text.
            text = source
        else:
            # String without newlines → treat as a file path.
            path = pathlib.Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"Schema YAML file not found: {path}")
            text = path.read_text(encoding="utf-8")

    else:
        raise TypeError(
            "schema_from_yaml expects a str or os.PathLike, "
            f"got {type(source).__name__}"
        )

    # --- Parse YAML ----------------------------------------------------------
    try:
        payload = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid schema YAML: {exc}") from exc

    if payload is None:
        raise ValueError(
            "Schema YAML is empty. Expected a mapping with at least a 'fields' key."
        )

    if not isinstance(payload, dict):
        raise TypeError(
            "Schema YAML must decode to a mapping with 'fields', "
            "'strict', and optional 'unique'. "
            f"Got: {type(payload).__name__}"
        )

    # Warn about rules_omitted before delegating to from_json, mirroring the
    # warning already present in Schema.to_json / Schema.from_json.
    if payload.get("rules_omitted"):
        warnings.warn(
            "schema_from_yaml: the YAML payload contains 'rules_omitted: true', "
            "which means cross-field rules were omitted during serialization. "
            "Re-attach rules manually after loading.",
            UserWarning,
            stacklevel=2,
        )

    # --- Delegate to Schema.from_json ----------------------------------------
    # yaml.safe_load may produce datetime.date / datetime.datetime objects for
    # timestamp-looking values; normalise these to ISO strings so json.dumps
    # does not raise and _parse_datetime_bound receives the expected type.
    try:
        return Schema.from_json(json.dumps(_normalize_yaml_payload(payload)))
    except (ValueError, TypeError) as exc:
        raise type(exc)(str(exc)) from exc
