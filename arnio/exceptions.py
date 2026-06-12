"""
arnio.exceptions
Custom exceptions for the Arnio library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import ValidationResult


class ArnioError(Exception):
    """Base exception for all Arnio errors."""

    pass


class UnknownStepError(ArnioError):
    """Raised when a pipeline step name is not registered."""

    def __init__(self, name: str, available: list[str]):
        super().__init__(
            f"Unknown pipeline step: '{name}'.\n"
            f"Available steps: {sorted(available)}\n"
            f"To add a custom step: ar.register_step('{name}', your_fn)"
        )


class CsvReadError(ArnioError):
    """Raised when a CSV file cannot be read."""

    pass


class JsonlReadError(ArnioError):
    """Raised when a JSON Lines file cannot be read or contains malformed data."""

    pass


class RemoteReadError(ArnioError):
    """Raised when a remote CSV URL cannot be fetched or the response is invalid.

    Attributes
    ----------
    url : str
        The URL that failed.
    status_code : int or None
        HTTP status code from the response, or ``None`` for network-level
        failures (DNS, timeout, connection refused, etc.).
    """

    def __init__(self, message: str, *, url: str = "", status_code: int | None = None):
        self.url = url
        self.status_code = status_code
        super().__init__(message)


class TypeCastError(ArnioError):
    """Raised when cast_types encounters an incompatible type."""

    pass


class PipelineStepError(ArnioError):
    """Raised when an execution error occurs inside a custom pipeline step."""

    def __init__(self, step_name: str, orig_err: Exception):
        self.step_name = step_name
        self.orig_err = orig_err
        super().__init__(
            f"Error occurred during custom pipeline step '{step_name}': {orig_err}"
        )


class SchemaValidationError(ArnioError):
    """Raised when a dataframe fails schema validation."""

    def __init__(self, message: str, result: ValidationResult = None):
        self.result = result
        super().__init__(message)


class PipelineSerializationError(ArnioError):
    """Raised when a declarative pipeline cannot be saved or loaded."""

    pass
