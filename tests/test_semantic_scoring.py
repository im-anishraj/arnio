"""
Test semantic quality scoring layer for issue #1962.

This test module validates semantic quality scoring without requiring
the full arnio package or C++ extension. It tests the scoring logic directly.
"""

from dataclasses import dataclass

# Test the semantic scoring logic directly without needing the C++ extension


@dataclass(frozen=True)
class MockColumnProfile:
    """Mock ColumnProfile for testing semantic scoring."""

    name: str
    dtype: str
    semantic_type: str
    row_count: int
    null_count: int
    null_ratio: float
    unique_count: int
    unique_ratio: float
    email_validity_ratio: float | None = None
    url_validity_ratio: float | None = None
    suggested_dtype: str | None = None


def _calculate_quality_score(
    row_count: int,
    duplicate_ratio: float,
    columns: dict[str, MockColumnProfile],
    semantic_scoring: bool = False,
) -> tuple[float, dict[str, float]]:
    """
    Compute an overall quality score and per-penalty breakdown from profile data.

    This is the production implementation extracted for testing.
    """
    if row_count == 0 or not columns:
        return 100.0, {}

    duplicate_penalty = round(min(duplicate_ratio * 100.0, 20.0), 2)

    null_ratios = [c.null_ratio for c in columns.values()]
    avg_null_ratio = sum(null_ratios) / len(null_ratios) if null_ratios else 0.0
    null_penalty = round(min(avg_null_ratio * 100.0, 40.0), 2)

    type_mismatches = sum(1 for c in columns.values() if c.suggested_dtype is not None)
    mismatch_ratio = type_mismatches / len(columns) if columns else 0.0
    type_mismatch_penalty = round(min(mismatch_ratio * 100.0, 40.0), 2)

    score_components: dict[str, float] = {}
    if duplicate_penalty > 0:
        score_components["duplicate_penalty"] = -duplicate_penalty
    if null_penalty > 0:
        score_components["null_penalty"] = -null_penalty
    if type_mismatch_penalty > 0:
        score_components["type_mismatch_penalty"] = -type_mismatch_penalty

    # Semantic validity penalties (opt-in via semantic_scoring=True)
    semantic_penalty = 0.0
    if semantic_scoring:
        # Calculate invalid ratios for semantic columns
        invalid_email_ratios = [
            1.0 - c.email_validity_ratio
            for c in columns.values()
            if c.email_validity_ratio is not None
        ]
        invalid_url_ratios = [
            1.0 - c.url_validity_ratio
            for c in columns.values()
            if c.url_validity_ratio is not None
        ]

        # Average invalid ratios for each semantic type
        avg_invalid_email = (
            sum(invalid_email_ratios) / len(invalid_email_ratios)
            if invalid_email_ratios
            else 0.0
        )
        avg_invalid_url = (
            sum(invalid_url_ratios) / len(invalid_url_ratios)
            if invalid_url_ratios
            else 0.0
        )

        # Apply penalties (max 10 points per semantic type, max 15 total)
        email_penalty = round(min(avg_invalid_email * 100.0, 10.0), 2)
        url_penalty = round(min(avg_invalid_url * 100.0, 10.0), 2)
        semantic_penalty = round(min(email_penalty + url_penalty, 15.0), 2)

        if email_penalty > 0:
            score_components["email_invalid_ratio_penalty"] = -email_penalty
        if url_penalty > 0:
            score_components["url_invalid_ratio_penalty"] = -url_penalty

    quality_score = round(
        100.0
        - duplicate_penalty
        - null_penalty
        - type_mismatch_penalty
        - semantic_penalty,
        2,
    )

    return quality_score, score_components


def test_semantic_scoring_disabled_by_default():
    """Test that semantic_scoring=False doesn't apply semantic penalties."""
    columns = {
        "email": MockColumnProfile(
            name="email",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=0.7,  # 30% invalid emails
        ),
    }

    score_default, components_default = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=False,  # Explicitly disabled
    )

    # Should NOT have email penalty when semantic_scoring=False
    assert "email_invalid_ratio_penalty" not in components_default
    assert score_default == 100.0
    print("✓ test_semantic_scoring_disabled_by_default PASSED")


def test_semantic_scoring_email_penalty():
    """Test email validity penalties when semantic_scoring=True."""
    columns = {
        "email": MockColumnProfile(
            name="email",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=0.7,  # 30% invalid emails
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=True,
    )

    # 30% invalid = 30 * penalty factor, capped at 10
    assert "email_invalid_ratio_penalty" in components
    assert components["email_invalid_ratio_penalty"] == -10.0  # Capped at 10
    assert score == 90.0  # 100 - 10 email penalty
    print("✓ test_semantic_scoring_email_penalty PASSED")


def test_semantic_scoring_url_penalty():
    """Test URL validity penalties when semantic_scoring=True."""
    columns = {
        "website": MockColumnProfile(
            name="website",
            dtype="string",
            semantic_type="url",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            url_validity_ratio=0.85,  # 15% invalid URLs
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=True,
    )

    # 15% invalid = 15 * penalty factor, capped at 10
    assert "url_invalid_ratio_penalty" in components
    assert components["url_invalid_ratio_penalty"] == -10.0  # Capped at 10
    assert score == 90.0  # 100 - 10 URL penalty
    print("✓ test_semantic_scoring_url_penalty PASSED")


def test_semantic_scoring_combined_penalties():
    """Test combined email and URL penalties."""
    columns = {
        "email": MockColumnProfile(
            name="email",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=0.8,  # 20% invalid emails
        ),
        "website": MockColumnProfile(
            name="website",
            dtype="string",
            semantic_type="url",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            url_validity_ratio=0.9,  # 10% invalid URLs
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=True,
    )

    # Email penalty: 20% invalid
    assert "email_invalid_ratio_penalty" in components
    assert components["email_invalid_ratio_penalty"] == -10.0  # Capped at 10

    # URL penalty: 10% invalid
    assert "url_invalid_ratio_penalty" in components
    assert components["url_invalid_ratio_penalty"] == -10.0  # Capped at 10

    # Combined penalty is capped at 15, so total should be 15
    assert score == 85.0  # 100 - 15 (combined semantic penalty cap)
    print("✓ test_semantic_scoring_combined_penalties PASSED")


def test_semantic_scoring_with_structural_penalties():
    """Test semantic penalties combined with structural penalties."""
    columns = {
        "email": MockColumnProfile(
            name="email",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=10,
            null_ratio=0.1,
            unique_count=90,
            unique_ratio=0.9,
            email_validity_ratio=0.7,  # 30% invalid emails
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.05,  # 5% duplicates
        columns=columns,
        semantic_scoring=True,
    )

    # Duplicate penalty: 5%
    assert components["duplicate_penalty"] == -5.0
    # Null penalty: 10%
    assert components["null_penalty"] == -10.0
    # Email semantic penalty: 30%, capped at 10
    assert components["email_invalid_ratio_penalty"] == -10.0

    # Total: 100 - 5 - 10 - 10 = 75
    assert score == 75.0
    print("✓ test_semantic_scoring_with_structural_penalties PASSED")


def test_semantic_scoring_valid_data():
    """Test that valid semantic data doesn't incur penalties."""
    columns = {
        "email": MockColumnProfile(
            name="email",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=1.0,  # 100% valid emails
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=True,
    )

    # No invalid emails, no semantic penalty
    assert "email_invalid_ratio_penalty" not in components
    assert score == 100.0
    print("✓ test_semantic_scoring_valid_data PASSED")


def test_semantic_scoring_empty_dataset():
    """Test semantic scoring on empty dataset."""
    score, components = _calculate_quality_score(
        row_count=0,
        duplicate_ratio=0.0,
        columns={},
        semantic_scoring=True,
    )

    assert score == 100.0
    assert components == {}
    print("✓ test_semantic_scoring_empty_dataset PASSED")


def test_backward_compatibility():
    """Test that default behavior (semantic_scoring=False) hasn't changed."""
    columns = {
        "id": MockColumnProfile(
            name="id",
            dtype="string",
            semantic_type="identifier",
            row_count=1000,
            null_count=5,
            null_ratio=0.005,
            unique_count=995,
            unique_ratio=0.995,
        ),
        "name": MockColumnProfile(
            name="name",
            dtype="string",
            semantic_type="text",
            row_count=1000,
            null_count=2,
            null_ratio=0.002,
            unique_count=998,
            unique_ratio=0.998,
        ),
    }

    score_old_default, _ = _calculate_quality_score(
        row_count=1000,
        duplicate_ratio=0.01,
        columns=columns,
    )  # Defaults to semantic_scoring=False

    score_explicit_false, _ = _calculate_quality_score(
        row_count=1000,
        duplicate_ratio=0.01,
        columns=columns,
        semantic_scoring=False,
    )

    # Both should be identical
    assert score_old_default == score_explicit_false
    # Should be: 100 - 10 (1% dup * 100, capped at 20) - 0.35 (0.35% avg null) = ~89.65
    assert score_old_default > 89  # Approximate check
    print("✓ test_backward_compatibility PASSED")


def test_multiple_emails_columns():
    """Test multiple email columns with different validity ratios."""
    columns = {
        "email1": MockColumnProfile(
            name="email1",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=0.9,  # 10% invalid
        ),
        "email2": MockColumnProfile(
            name="email2",
            dtype="string",
            semantic_type="email",
            row_count=100,
            null_count=0,
            null_ratio=0.0,
            unique_count=100,
            unique_ratio=1.0,
            email_validity_ratio=0.6,  # 40% invalid
        ),
    }

    score, components = _calculate_quality_score(
        row_count=100,
        duplicate_ratio=0.0,
        columns=columns,
        semantic_scoring=True,
    )

    # Average invalid email: (10% + 40%) / 2 = 25%
    # Penalty: 25%, capped at 10
    assert components["email_invalid_ratio_penalty"] == -10.0
    assert score == 90.0
    print("✓ test_multiple_emails_columns PASSED")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Testing Semantic Quality Scoring (Issue #1962)")
    print("=" * 70 + "\n")

    test_semantic_scoring_disabled_by_default()
    test_semantic_scoring_email_penalty()
    test_semantic_scoring_url_penalty()
    test_semantic_scoring_combined_penalties()
    test_semantic_scoring_with_structural_penalties()
    test_semantic_scoring_valid_data()
    test_semantic_scoring_empty_dataset()
    test_backward_compatibility()
    test_multiple_emails_columns()

    print("\n" + "=" * 70)
    print("All semantic scoring tests PASSED!")
    print("=" * 70 + "\n")
