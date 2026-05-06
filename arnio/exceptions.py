"""
arnio.exceptions
Custom exceptions for the Arnio library.
"""


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


class TypeCastError(ArnioError):
    """Raised when cast_types encounters an incompatible type."""

    pass
