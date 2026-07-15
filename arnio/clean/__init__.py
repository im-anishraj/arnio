"""arnio.clean — Cleaning pipeline.

Public API:
    clean     — Apply declarative cleaning steps to data.
    Pipeline  — Reusable, serializable cleaning pipeline.
"""

from arnio.clean._pipeline import Pipeline, clean

__all__ = [
    "Pipeline",
    "clean",
]
