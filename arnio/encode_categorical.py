"""
arnio.encode_categorical
Encode categorical STRING columns into numerical representations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .frame import ArFrame


def encode_categorical(
    frame: ArFrame,
    columns: Sequence[str],
    method: str = "one_hot",
    ordinal_mappings: Mapping[str, Mapping[str, int]] | None = None,
) -> ArFrame:
    """Encode multiple text columns into numbers for machine learning processing.

    Parameters
    ----------
    frame : ArFrame
        Input frame.
    columns : Sequence[str]
        Column names to encode. All must be STRING dtype.
    method : str
        ``"one_hot"``  — appends one INT64 indicator column per unique value,
        named ``{column}_{category}``, sorted alphabetically. Nulls → 0.

        ``"ordinal"``  — appends one INT64 column per target column, named
        ``{column}_ordinal``, using the caller-supplied ``ordinal_mappings``.
        Nulls are preserved as null.
    ordinal_mappings : Mapping[str, Mapping[str, int]] | None
        Required when ``method="ordinal"``. Maps each column name to a
        ``{category_string: integer}`` dict.

    Returns
    -------
    ArFrame
        New frame with all original columns plus the encoded columns appended.

    Raises
    ------
    TypeError
        If ``frame`` is not an ArFrame.
    KeyError
        If any name in ``columns`` is not present in the frame.
    ValueError
        If ``method`` is not ``"one_hot"`` or ``"ordinal"``, or if
        ``ordinal_mappings`` is missing when ``method="ordinal"``.
    ValueError
        If a target column is not STRING dtype, a generated column name
        collides with another column, or an ordinal mapping is incomplete.
    """
    from ._core import _encode_one_hot_native, _encode_ordinal_native
    from .cleaning import _validate_existing_column_sequence
    from .frame import ArFrame

    _validate_arframe(frame)

    columns = _validate_existing_column_sequence(
        columns,
        available_columns=frame.columns,
        argument_name="columns",
        allow_empty=False,
        reject_duplicates=True,
    )

    if method == "one_hot":
        cpp_frame = _encode_one_hot_native(frame._frame, columns)
        return ArFrame(cpp_frame)

    elif method == "ordinal":
        if ordinal_mappings is None:
            raise ValueError("ordinal_mappings must be provided when method='ordinal'")
        for col in columns:
            if col not in ordinal_mappings:
                raise ValueError(
                    f"ordinal_mappings is missing an entry for column {col!r}"
                )
        # Convert to the plain dict[str, dict[str, int]] that pybind11 expects
        mappings: dict[str, dict[str, int]] = {
            col: dict(ordinal_mappings[col]) for col in columns
        }
        cpp_frame = _encode_ordinal_native(frame._frame, columns, mappings)
        return ArFrame(cpp_frame)

    else:
        raise ValueError(
            f"Unknown encoding method {method!r}. Use 'one_hot' or 'ordinal'."
        )
