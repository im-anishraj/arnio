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


def test_docs_utf8_check_reports_invalid_website_html(tmp_path):
    website_dir = tmp_path / "website"
    website_dir.mkdir()
    invalid_html = website_dir / "index.html"
    invalid_html.write_bytes(b"<html>\x95</html>")

    errors = check_utf8([invalid_html])

    assert len(errors) == 1
    assert "index.html" in errors[0]
    assert "invalid UTF-8 byte" in errors[0]


def test_docs_utf8_check_reports_invalid_website_css(tmp_path):
    website_dir = tmp_path / "website"
    website_dir.mkdir()
    invalid_css = website_dir / "style.css"
    invalid_css.write_bytes(b"body { color: \x95; }")

    errors = check_utf8([invalid_css])

    assert len(errors) == 1
    assert "style.css" in errors[0]


def test_docs_utf8_check_reports_invalid_website_js(tmp_path):
    website_dir = tmp_path / "website"
    website_dir.mkdir()
    invalid_js = website_dir / "main.js"
    invalid_js.write_bytes(b"const x = '\x95';")

    errors = check_utf8([invalid_js])

    assert len(errors) == 1
    assert "main.js" in errors[0]


def test_docs_utf8_check_accepts_valid_website_files(tmp_path):
    website_dir = tmp_path / "website"
    website_dir.mkdir()
    (website_dir / "index.html").write_text(
        "<html><body>Hello</body></html>", encoding="utf-8"
    )
    (website_dir / "style.css").write_text("body { color: red; }", encoding="utf-8")
    (website_dir / "main.js").write_text("const x = 'hello';", encoding="utf-8")

    files = [
        website_dir / "index.html",
        website_dir / "style.css",
        website_dir / "main.js",
    ]
    assert check_utf8(files) == []


def test_docs_utf8_check_ignores_non_website_html(tmp_path):
    # HTML files outside the website/ directory should not be checked
    html_file = tmp_path / "random.html"
    html_file.write_bytes(b"<html>\x95</html>")

    assert check_utf8([html_file]) == []


def test_docs_utf8_check_ignores_website_binary_assets(tmp_path):
    website_dir = tmp_path / "website"
    website_dir.mkdir()
    binary_asset = website_dir / "logo.png"
    binary_asset.write_bytes(b"\x89PNG\r\n\x1a\n\x95")

    assert check_utf8([binary_asset]) == []
