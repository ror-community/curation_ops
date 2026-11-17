import pytest

from curation_validation.core.normalize import (
    _normalize_simple_url,
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


def _furl_normalize(url):
    """normalize_url as implemented before the fast path, used as the oracle."""
    from furl import furl

    if not url or not url.strip():
        return None
    try:
        f = furl(url)
        f.path.normalize()
        f.path = ""
        f.remove(args=True, fragment=True)
        host = f.host
        if not host:
            return None
        if host.startswith("www."):
            f.host = host[4:]
        f.scheme = None
        return f.url.lower()
    except Exception:
        return None


class TestNormalizeUrlFastPath:
    @pytest.mark.parametrize("url", [
        "https://www.Example.com/a/b?x=1#f", "HTTP://WWW.EXAMPLE.COM", "https://www.www.example.com",
        "https://example.com/ path", "https://example.com/é?q=中#[x]", "https://example.com\\path",
        "https://example.com:443/", "https://example.com:8080/x", "https://user@example.com/",
        "https://bücher.de/", "https://xn--bcher-kva.de/", "https://example.com./", "https://a..b.com/",
        "https://www./", "https://" + "a" * 63 + ".com/", "https://" + "a" * 64 + ".com/",
        " https://example.com", "https://example.com\t", "ftp://example.com/", "www.example.com",
        "example.com", "https://ex_ample.com/", "https://-example-.com", "https://1.2.3.4/x",
    ])
    def test_matches_furl(self, url):
        assert normalize_url(url) == _furl_normalize(url)

    @pytest.mark.parametrize("url,expected", [
        ("https://www.Example.com/a?b#c", "//example.com"),
        ("http://example.com", "//example.com"),
        ("https://www.www.example.com", "//www.example.com"),
    ])
    def test_fast_path_results(self, url, expected):
        assert _normalize_simple_url(url) == expected

    @pytest.mark.parametrize("url", [
        "https://example.com:443/", "https://user@example.com/", "https://bücher.de/",
        "https://xn--bcher-kva.de/", "https://example.com./", "https://a..b.com/",
        "https://" + "a" * 64 + ".com/", " https://example.com", "https://example.com/ path",
        "ftp://example.com/", "https://ex_ample.com/",
    ])
    def test_unusual_urls_use_furl(self, url):
        assert _normalize_simple_url(url) is None

    def test_randomized_matches_furl(self):
        import random

        rng = random.Random(7)
        host_chars = "abcXYZ019-." + "é_@:"
        tail_chars = "abc/?#&=%20.-_~:@[]\\ \té中"
        for _ in range(3000):
            host = "".join(rng.choice(host_chars) for _ in range(rng.randint(1, 15)))
            if rng.random() < 0.3:
                host = rng.choice(["www.", "WWW."]) + host
            url = rng.choice(["http", "https", "HTTPS", "ftp", ""]) + rng.choice(["://", ":/", ""]) + host
            if rng.random() < 0.7:
                url += rng.choice("/?#") + "".join(rng.choice(tail_chars) for _ in range(rng.randint(0, 10)))
            assert normalize_url(url) == _furl_normalize(url), url
