from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_profiling_privacy():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Profiling privacy and redaction" in text
    assert "redact_sample_values" in text
    assert "sample_values" in text
    assert "top_values" in text
    assert "Safe sharing practices" in text
    assert "Aggregate-only" in text or "aggregate-only" in text


def test_readme_privacy_table_covers_key_exports():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section_start = text.index("### Profiling privacy and redaction")
    section_end = text.index("### Notebook dashboard", section_start)
    section = text[section_start:section_end]
    for phrase in (
        "to_markdown()",
        "to_html()",
        "ProfileComparison.to_dict()",
        "`top_values` unchanged",
    ):
        assert phrase in section, f"privacy section missing: {phrase!r}"


def test_api_reference_documents_profiling_redaction():
    text = (ROOT / "API_REFERENCE.md").read_text(encoding="utf-8")
    assert "redact_sample_values" in text
    assert "#### Privacy" in text
    assert "to_markdown()" in text
    section_start = text.index("### ColumnProfile")
    column_section = text[section_start : text.index("---", section_start)]
    assert "to_dict(redact_sample_values" in column_section
