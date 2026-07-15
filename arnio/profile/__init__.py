"""arnio.profile — Profiling engine.

Public API:
    profile        — Profile data quality, return a comprehensive report.
    suggest        — Auto-suggest cleaning steps from data profiling.
    ProfileReport  — Result object with quality_score, column profiles, etc.
    ColumnProfile  — Per-column quality metrics.
"""

from arnio.profile._engine import profile
from arnio.profile._report import ColumnProfile, ProfileReport
from arnio.profile._suggest import suggest

__all__ = [
    "ColumnProfile",
    "ProfileReport",
    "profile",
    "suggest",
]
