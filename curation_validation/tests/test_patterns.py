from curation_validation.core.patterns import (
    ACRONYMS_PATTERN,
    NAMES_PATTERN,
    URL_PATTERN,
    WIKIPEDIA_URL_PATTERN,
    ISNI_PATTERN,
    WIKIDATA_PATTERN,
    FUNDREF_PATTERN,
    GEONAMES_PATTERN,
    DOMAIN_PATTERN,
    VALID_STATUSES,
    VALID_TYPES,
)


class TestPatterns:
    def test_acronyms_matches_uppercase(self):
        assert ACRONYMS_PATTERN.match("MIT")

    def test_acronyms_rejects_lowercase(self):
        assert not ACRONYMS_PATTERN.match("mit")

    def test_names_matches_language_tag(self):
        assert NAMES_PATTERN.match("Test University*en")

    def test_names_rejects_no_tag(self):
        assert not NAMES_PATTERN.match("Test University")

    def test_url_matches_https(self):
        assert URL_PATTERN.match("https://example.org")

    def test_url_rejects_bare(self):
        assert not URL_PATTERN.match("example.org")

    def test_wikipedia_matches(self):
        assert WIKIPEDIA_URL_PATTERN.match("https://en.wikipedia.org/wiki/Test")

    def test_wikipedia_matches_delete(self):
        assert WIKIPEDIA_URL_PATTERN.match("delete")

    def test_isni_matches(self):
        assert ISNI_PATTERN.match("0000 0001 2345 6789")

    def test_isni_matches_preferred(self):
        assert ISNI_PATTERN.match("0000 0001 2345 6789*preferred")

    def test_wikidata_matches(self):
        assert WIKIDATA_PATTERN.match("Q12345")

    def test_wikidata_rejects_lowercase(self):
        assert not WIKIDATA_PATTERN.match("q12345")

    def test_fundref_matches(self):
        assert FUNDREF_PATTERN.match("100000001")

    def test_geonames_matches(self):
        assert GEONAMES_PATTERN.match("5367440")


class TestDomainPattern:
    def test_domain_matches_simple(self):
        assert DOMAIN_PATTERN.match("example.com")

    def test_domain_matches_subdomain(self):
        assert DOMAIN_PATTERN.match("sub.example.co.uk")

    def test_domain_matches_hyphen(self):
        assert DOMAIN_PATTERN.match("my-site.org")

    def test_domain_rejects_uppercase(self):
        assert not DOMAIN_PATTERN.match("EXAMPLE.COM")

    def test_domain_rejects_protocol(self):
        assert not DOMAIN_PATTERN.match("http://example.com")

    def test_domain_rejects_bare_word(self):
        assert not DOMAIN_PATTERN.match("example")

    def test_domain_rejects_dot_only(self):
        assert not DOMAIN_PATTERN.match(".com")

    def test_domain_rejects_spaces(self):
        assert not DOMAIN_PATTERN.match("not a domain")


class TestValidSets:
    def test_valid_statuses(self):
        assert VALID_STATUSES == {"active", "inactive", "withdrawn"}

    def test_valid_types(self):
        assert "education" in VALID_TYPES
        assert "healthcare" in VALID_TYPES
        assert len(VALID_TYPES) == 9
