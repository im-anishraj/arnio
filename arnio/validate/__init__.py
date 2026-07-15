"""arnio.validate — Validation engine.

Public API:
    validate          — Check data against a schema, return structured results.
    ValidationResult  — Result object with .passed, .issues, .to_dict(), etc.
    Issue             — Single validation issue.
"""

from arnio.validate._engine import validate
from arnio.validate._result import Issue, ValidationResult

__all__ = [
    "Issue",
    "ValidationResult",
    "validate",
]
