"""Quality gate — assertion-style validation for CI/CD.

``check()`` runs validation internally and raises ``ValidationError``
on failure. Designed for test files and CI pipelines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from arnio.exceptions import ValidationError
from arnio.validate._engine import validate

if TYPE_CHECKING:
    from arnio.schema._fields import Field
    from arnio.schema._schema import Schema


def check(
    data: Any,
    schema: Schema | dict[str, Field],
    *,
    max_errors: int | None = None,
) -> None:
    """Assert that data conforms to a schema. Raises on failure.

    This is the bridge between library and CI tool. In a notebook,
    use ``ar.validate()`` to see issues. In CI, use ``ar.check()``
    to block bad data.

    Args:
        data: Any supported data type.
        schema: A Schema or dict mapping column names to Field instances.
        max_errors: Maximum number of issues to collect.

    Raises:
        ValidationError: If validation fails (any error-level issues).
    """
    result = validate(data, schema, max_errors=max_errors)

    if not result.passed:
        # Build a useful error message
        error_issues = [i for i in result.issues if i.severity == "error"]
        summary_lines = [
            f"Data validation failed with {result.error_count} error(s):",
        ]
        for issue in error_issues[:10]:
            summary_lines.append(
                f"  - [{issue.column}] {issue.rule}: {issue.message}"
            )
        if len(error_issues) > 10:
            summary_lines.append(f"  ... and {len(error_issues) - 10} more")

        raise ValidationError(
            "\n".join(summary_lines),
            issues=error_issues,
        )
