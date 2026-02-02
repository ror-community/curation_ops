# tests/test_normalize.py
import pytest
from validate_ror_records_input_csvs.core.normalize import normalize_url, normalize_text, normalize_whitespace


class TestNormalizeUrl:
    """Tests for URL normalization.

    Note: The normalized output includes '//' prefix (scheme-relative URL format)
    to match the original implementation's behavior for parity.
    """

    def test_strips_scheme_https(self):
        assert normalize_url("https://example.org") == "//example.org"

    def test_strips_scheme_http(self):
        assert normalize_url("http://example.org") == "//example.org"

    def test_strips_www(self):
        assert normalize_url("https://www.example.org") == "//example.org"

    def test_strips_path(self):
        assert normalize_url("https://example.org/about/us") == "//example.org"

    def test_strips_query(self):
        assert normalize_url("https://example.org?ref=123") == "//example.org"

    def test_strips_fragment(self):
        assert normalize_url("https://example.org#section") == "//example.org"

    def test_lowercases(self):
        assert normalize_url("https://EXAMPLE.ORG") == "//example.org"

    def test_complex_url(self):
        url = "https://www.Example.Org/path/to/page?query=1#section"
        assert normalize_url(url) == "//example.org"

    def test_invalid_url_returns_none(self):
        assert normalize_url("not a url") is None

    def test_empty_string_returns_none(self):
        assert normalize_url("") is None


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("Hello World") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_text("Hello, World!") == "hello world"

    def test_removes_special_chars(self):
        assert normalize_text("Test (123)") == "test 123"

    def test_preserves_alphanumeric(self):
        assert normalize_text("ABC123") == "abc123"

    def test_handles_empty_string(self):
        assert normalize_text("") == ""


class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_strips_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_handles_tabs(self):
        assert normalize_whitespace("hello\tworld") == "hello world"

    def test_handles_newlines(self):
        assert normalize_whitespace("hello\nworld") == "hello world"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""
