"""pandas DataFrame accessor — ``df.arnio.*`` convenience methods.

Registered automatically when arnio is imported.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


@pd.api.extensions.register_dataframe_accessor("arnio")
class ArnioPandasAccessor:
    """Arnio methods accessible directly on any pandas DataFrame.

    Usage::

        import arnio as ar
        import pandas as pd

        df = pd.DataFrame({"email": ["a@b.com", "bad"], "age": [25, -1]})

        # Profile
        report = df.arnio.profile()

        # Validate
        result = df.arnio.validate(schema)

        # Clean
        cleaned = df.arnio.clean(["strip_whitespace", "drop_duplicates"])
    """

    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._df = pandas_obj

    def validate(
        self,
        schema: Any,
        *,
        max_errors: int | None = None,
    ) -> Any:
        """Validate the DataFrame against a schema.

        Returns:
            A ValidationResult with all issues found.
        """
        from arnio.validate import validate
        return validate(self._df, schema, max_errors=max_errors)

    def profile(self) -> Any:
        """Profile the DataFrame's data quality.

        Returns:
            A ProfileReport with quality score and column metrics.
        """
        from arnio.profile import profile
        return profile(self._df)

    def clean(self, steps: list[Any]) -> pd.DataFrame:
        """Apply cleaning steps and return a cleaned DataFrame.

        Args:
            steps: List of step specifications.

        Returns:
            A cleaned pandas DataFrame.
        """
        from arnio.clean import clean
        return clean(self._df, steps)  # type: ignore[no-any-return]

    def suggest(self) -> list[dict[str, Any]]:
        """Suggest cleaning steps based on data profiling.

        Returns:
            A list of suggestion dicts.
        """
        from arnio.profile import suggest
        return suggest(self._df)

    def is_valid(self, schema: Any) -> bool:
        """Check if the DataFrame passes validation.

        Returns:
            True if no error-level issues were found.
        """
        from arnio.validate import validate
        return validate(self._df, schema).passed

    def check(self, schema: Any, **kwargs: Any) -> None:
        """Assert that the DataFrame passes validation. Raises on failure."""
        from arnio.gates import check
        check(self._df, schema, **kwargs)
