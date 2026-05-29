from scripts.check_docs_utf8 import check_utf8


def test_docs_utf8_check_reports_invalid_markdown(tmp_path):
    invalid_doc = tmp_path / "broken.md"
    invalid_doc.write_bytes(b"valid prefix \x95 invalid byte")

    errors = check_utf8([invalid_doc])

    assert len(errors) == 1
    assert "broken.md" in errors[0]
    assert "invalid UTF-8 byte" in errors[0]


def test_docs_utf8_check_ignores_non_docs_files(tmp_path):
    binary_fixture = tmp_path / "fixture.bin"
    binary_fixture.write_bytes(b"\x95")

    assert check_utf8([binary_fixture]) == []
