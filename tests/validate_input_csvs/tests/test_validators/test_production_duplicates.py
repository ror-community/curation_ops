# tests/test_validators/test_production_duplicates.py
import pytest

from validate_ror_records_input_csvs.validators.production_duplicates import (
    get_country_code_from_result,
    get_all_names_from_result,
    parse_csv_names,
)


class TestGetCountryCodeFromResult:
    def test_extracts_country_code(self):
        result = {
            "locations": [
                {"geonames_details": {"country_code": "US"}}
            ]
        }
        assert get_country_code_from_result(result) == "US"

    def test_returns_none_for_empty_locations(self):
        result = {"locations": []}
        assert get_country_code_from_result(result) is None

    def test_returns_none_for_missing_locations(self):
        result = {}
        assert get_country_code_from_result(result) is None

    def test_returns_none_for_missing_geonames_details(self):
        result = {"locations": [{}]}
        assert get_country_code_from_result(result) is None


class TestGetAllNamesFromResult:
    def test_extracts_ror_display_names(self):
        result = {
            "names": [
                {"value": "Test University", "types": ["ror_display"]},
            ]
        }
        names = get_all_names_from_result(result)
        assert "Test University" in names

    def test_extracts_alias_names(self):
        result = {
            "names": [
                {"value": "Main Name", "types": ["ror_display"]},
                {"value": "Alias One", "types": ["alias"]},
            ]
        }
        names = get_all_names_from_result(result)
        assert "Alias One" in names

    def test_extracts_label_names(self):
        result = {
            "names": [
                {"value": "English Name", "types": ["label"]},
            ]
        }
        names = get_all_names_from_result(result)
        assert "English Name" in names

    def test_returns_empty_for_no_names(self):
        result = {"names": []}
        assert get_all_names_from_result(result) == []


class TestParseCsvNames:
    def test_extracts_display_name(self):
        row = {"names.types.ror_display": "Test Org*en"}
        names = parse_csv_names(row)
        assert "Test Org*en" in names

    def test_extracts_aliases(self):
        row = {
            "names.types.ror_display": "Main*en",
            "names.types.alias": "Alias1*en; Alias2*de"
        }
        names = parse_csv_names(row)
        assert "Alias1*en" in names
        assert "Alias2*de" in names

    def test_extracts_labels(self):
        row = {
            "names.types.ror_display": "Main*en",
            "names.types.label": "Label1*fr; Label2*es"
        }
        names = parse_csv_names(row)
        assert "Label1*fr" in names
        assert "Label2*es" in names

    def test_returns_empty_for_missing_fields(self):
        row = {}
        names = parse_csv_names(row)
        assert names == []
