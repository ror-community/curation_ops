from curation_validation.core.normalize import (
    normalize_url,
    normalize_text,
    normalize_whitespace,
    normalize_wikipedia_url,
)


class TestNormalizeUrl:
    def test_strips_scheme(self):
        assert normalize_url("https://example.org") == "//example.org"

    def test_strips_www(self):
        result = normalize_url("https://www.example.org")
        assert "www" not in result

    def test_strips_path(self):
        result = normalize_url("https://example.org/path/to/page")
        assert "/path" not in result

    def test_strips_query(self):
        result = normalize_url("https://example.org?foo=bar")
        assert "foo" not in result

    def test_lowercases(self):
        result = normalize_url("https://EXAMPLE.ORG")
        assert result == "//example.org"

    def test_empty_returns_none(self):
        assert normalize_url("") is None

    def test_invalid_returns_none(self):
        assert normalize_url("not a url") is None


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("Hello WORLD") == "hello world"

    def test_removes_punctuation(self):
        assert normalize_text("hello, world!") == "hello world"

    def test_empty_returns_empty(self):
        assert normalize_text("") == ""


class TestNormalizeWhitespace:
    def test_collapses_spaces(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_strips(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_handles_tabs(self):
        assert normalize_whitespace("hello\tworld") == "hello world"

    def test_empty_returns_empty(self):
        assert normalize_whitespace("") == ""


class TestNormalizeWikipediaUrl:
    def test_normalizes_encoded_url(self):
        url = "https://en.wikipedia.org/wiki/Polic%C3%ADa"
        result = normalize_wikipedia_url(url)
        assert result == "https://en.wikipedia.org/wiki/Polic%C3%ADa"

    def test_normalizes_decoded_url(self):
        url = "https://en.wikipedia.org/wiki/Policía"
        result = normalize_wikipedia_url(url)
        assert result == "https://en.wikipedia.org/wiki/Polic%C3%ADa"

    def test_both_forms_normalize_same(self):
        url1 = "https://en.wikipedia.org/wiki/Policía"
        url2 = "https://en.wikipedia.org/wiki/Polic%C3%ADa"
        assert normalize_wikipedia_url(url1) == normalize_wikipedia_url(url2)

    def test_none_returns_none(self):
        assert normalize_wikipedia_url(None) is None

    def test_non_https_returns_unchanged(self):
        assert normalize_wikipedia_url("http://foo") == "http://foo"
