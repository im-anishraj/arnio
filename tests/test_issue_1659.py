import pandas as pd
import arnio as ar
import pytest

def test_required_if_empty_string():
    # Reproduction from issue #1659
    frame = ar.from_pandas(pd.DataFrame({
        "kind": ["business", "personal", "business"],
        "tax_id": ["", None, "   "],
    }))

    schema = ar.Schema({
        "kind": ar.String(),
        "tax_id": ar.String(required_if=("kind", "business")),
    })

    result = ar.validate(frame, schema)
    
    # After fix, we expect 2 issues:
    # Row 1 (index 0): "" is null-like, kind is "business" -> ERROR
    # Row 3 (index 2): "   " is null-like, kind is "business" -> ERROR
    assert result.issue_count == 2
    
    issues = result.to_dict()['issues']
    rows_with_issues = sorted([issue['row_index'] for issue in issues])
    assert rows_with_issues == [1, 3]
    for issue in issues:
        assert issue['rule'] == "required_if"
        assert "is required when" in issue['message']

def test_required_if_non_triggered():
    frame = ar.from_pandas(pd.DataFrame({
        "kind": ["personal", "personal"],
        "tax_id": ["", "   "],
    }))

    schema = ar.Schema({
        "kind": ar.String(),
        "tax_id": ar.String(required_if=("kind", "business")),
    })

    result = ar.validate(frame, schema)
    assert result.passed
    assert result.issue_count == 0

def test_required_if_real_none():
    frame = ar.from_pandas(pd.DataFrame({
        "kind": ["business"],
        "tax_id": [None],
    }))

    schema = ar.Schema({
        "kind": ar.String(),
        "tax_id": ar.String(required_if=("kind", "business")),
    })

    result = ar.validate(frame, schema)
    assert not result.passed
    assert result.issue_count == 1
    assert result.issues[0].row_index == 1

if __name__ == "__main__":
    # If arnio core is missing, these will fail with ImportError
    # But we can at least check the logic if we could run it.
    try:
        test_required_if_empty_string()
        test_required_if_non_triggered()
        test_required_if_real_none()
        print("All issue 1659 verification tests passed!")
    except ImportError as e:
        print(f"Skipping runtime test due to missing C++ core: {e}")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
