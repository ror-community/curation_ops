import re
from validate_ror_records_input_csvs.core.patterns import (
    ACRONYMS_PATTERN,
    NAMES_PATTERN,
    URL_PATTERN,
    WIKIPEDIA_URL_PATTERN,
    ISNI_PATTERN,
    WIKIDATA_PATTERN,
    FUNDREF_PATTERN,
    GEONAMES_PATTERN,
    VALID_STATUSES,
    VALID_TYPES,
)


class TestAcronymsPattern:
    def test_valid_uppercase(self):
        assert ACRONYMS_PATTERN.match("MIT")

    def test_valid_with_numbers(self):
        assert ACRONYMS_PATTERN.match("ABC123")

    def test_valid_with_spaces(self):
        assert ACRONYMS_PATTERN.match("AB CD")

    def test_invalid_lowercase(self):
        assert not ACRONYMS_PATTERN.match("mit")

    def test_invalid_special_chars(self):
        assert not ACRONYMS_PATTERN.match("M.I.T")


class TestNamesPattern:
    def test_valid_with_lang_suffix(self):
        assert NAMES_PATTERN.match("University Name*en")

    def test_valid_with_longer_lang(self):
        assert NAMES_PATTERN.match("Name*eng")

    def test_invalid_no_suffix(self):
        assert not NAMES_PATTERN.match("University Name")

    def test_invalid_short_lang(self):
        assert not NAMES_PATTERN.match("Name*e")


class TestUrlPattern:
    def test_valid_https(self):
        assert URL_PATTERN.match("https://example.org")

    def test_valid_http(self):
        assert URL_PATTERN.match("http://example.org")

    def test_invalid_no_scheme(self):
        assert not URL_PATTERN.match("example.org")


class TestWikipediaUrlPattern:
    def test_valid_en_wikipedia(self):
        assert WIKIPEDIA_URL_PATTERN.match("https://en.wikipedia.org/wiki/MIT")

    def test_valid_de_wikipedia(self):
        assert WIKIPEDIA_URL_PATTERN.match("https://de.wikipedia.org/wiki/Test")

    def test_valid_delete(self):
        assert WIKIPEDIA_URL_PATTERN.match("delete")

    def test_invalid_no_lang(self):
        assert not WIKIPEDIA_URL_PATTERN.match("https://wikipedia.org/wiki/Test")


class TestIsniPattern:
    def test_valid_isni(self):
        assert ISNI_PATTERN.match("0000 0001 2345 6789")

    def test_valid_isni_with_x(self):
        assert ISNI_PATTERN.match("0000 0001 2345 678X")

    def test_valid_isni_preferred(self):
        assert ISNI_PATTERN.match("0000 0001 2345 6789*preferred")

    def test_valid_delete(self):
        assert ISNI_PATTERN.match("delete")

    def test_invalid_no_spaces(self):
        assert not ISNI_PATTERN.match("0000000123456789")

    def test_invalid_wrong_first_group(self):
        assert not ISNI_PATTERN.match("1234 0001 2345 6789")


class TestWikidataPattern:
    def test_valid_q_number(self):
        assert WIKIDATA_PATTERN.match("Q12345")

    def test_valid_q_preferred(self):
        assert WIKIDATA_PATTERN.match("Q12345*preferred")

    def test_valid_delete(self):
        assert WIKIDATA_PATTERN.match("delete")

    def test_invalid_lowercase_q(self):
        assert not WIKIDATA_PATTERN.match("q12345")

    def test_invalid_q_zero(self):
        assert not WIKIDATA_PATTERN.match("Q0")

    def test_invalid_no_q(self):
        assert not WIKIDATA_PATTERN.match("12345")


class TestFundrefPattern:
    def test_valid_number(self):
        assert FUNDREF_PATTERN.match("100000001")

    def test_valid_preferred(self):
        assert FUNDREF_PATTERN.match("100000001*preferred")

    def test_valid_delete(self):
        assert FUNDREF_PATTERN.match("delete")

    def test_invalid_leading_zero(self):
        assert not FUNDREF_PATTERN.match("0123")


class TestGeonamesPattern:
    def test_valid_number(self):
        assert GEONAMES_PATTERN.match("5128581")

    def test_valid_preferred(self):
        assert GEONAMES_PATTERN.match("5128581*preferred")

    def test_valid_delete(self):
        assert GEONAMES_PATTERN.match("delete")

    def test_invalid_leading_zero(self):
        assert not GEONAMES_PATTERN.match("0123")


class TestValidSets:
    def test_valid_statuses(self):
        assert VALID_STATUSES == {"active", "inactive", "withdrawn"}

    def test_valid_types(self):
        expected = {
            "education", "healthcare", "company", "funder", "archive",
            "nonprofit", "government", "facility", "other"
        }
        assert VALID_TYPES == expected
