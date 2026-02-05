# tests/test_validators/test_production_duplicates.py
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.production_duplicates import (
    ProductionDuplicatesValidator,
    get_country_code_from_result,
    get_all_names_from_result,
    parse_csv_names,
)


@pytest.fixture
def validator():
    return ProductionDuplicatesValidator()


def make_context(
    input_file: Path,
    tmp_path: Path,
    geonames_user: str = None,
) -> ValidatorContext:
    return ValidatorContext(
        input_file=input_file,
        output_dir=tmp_path,
        data_source=None,
        geonames_user=geonames_user,
    )


class TestValidatorProperties:
    def test_name(self, validator):
        assert validator.name == "production-duplicates"

    def test_output_filename(self, validator):
        assert validator.output_filename == "production_duplicates.csv"

    def test_output_fields(self, validator):
        assert "name" in validator.output_fields
        assert "display_name" in validator.output_fields
        assert "matched_ror_id" in validator.output_fields
        assert "matched_name" in validator.output_fields
        assert "match_ratio" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is False

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is True

    def test_new_records_only(self, validator):
        assert validator.new_records_only is True


class TestCanRun:
    def test_can_run_with_geonames_user(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("names.types.ror_display,locations.geonames_id\n")

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        can_run, reason = validator.can_run(ctx)

        assert can_run is True
        assert reason == ""

    def test_cannot_run_without_geonames_user(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("names.types.ror_display,locations.geonames_id\n")

        ctx = make_context(csv_path, tmp_path, geonames_user=None)
        can_run, reason = validator.can_run(ctx)

        assert can_run is False
        assert "geonames" in reason.lower()


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


class TestValidatorRun:
    @patch("validate_ror_records_input_csvs.validators.production_duplicates.GeoNamesClient")
    @patch("validate_ror_records_input_csvs.validators.production_duplicates.RORAPIClient")
    def test_finds_duplicate_with_matching_country(
        self, mock_ror_client_class, mock_geonames_class, validator, tmp_path
    ):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "names.types.ror_display,names.types.alias,names.types.label,locations.geonames_id\n"
            "Test University*en,,,5128581\n"
        )

        # Mock GeoNames
        mock_geonames = Mock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames.lookup_failures = []
        mock_geonames_class.return_value = mock_geonames

        # Mock ROR API
        mock_ror = Mock()
        mock_ror.search_all.return_value = [
            {
                "id": "https://ror.org/existing123",
                "names": [{"value": "Test University", "types": ["ror_display"]}],
                "locations": [{"geonames_details": {"country_code": "US"}}]
            }
        ]
        mock_ror_client_class.return_value = mock_ror

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) >= 1
        assert results[0]["matched_ror_id"] == "https://ror.org/existing123"

    @patch("validate_ror_records_input_csvs.validators.production_duplicates.GeoNamesClient")
    @patch("validate_ror_records_input_csvs.validators.production_duplicates.RORAPIClient")
    def test_filters_by_country_code(
        self, mock_ror_client_class, mock_geonames_class, validator, tmp_path
    ):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "names.types.ror_display,names.types.alias,names.types.label,locations.geonames_id\n"
            "Test University*en,,,5128581\n"
        )

        # Mock GeoNames - input record is in US
        mock_geonames = Mock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames.lookup_failures = []
        mock_geonames_class.return_value = mock_geonames

        # Mock ROR API - result is in UK (different country)
        mock_ror = Mock()
        mock_ror.search_all.return_value = [
            {
                "id": "https://ror.org/uk123",
                "names": [{"value": "Test University", "types": ["ror_display"]}],
                "locations": [{"geonames_details": {"country_code": "GB"}}]
            }
        ]
        mock_ror_client_class.return_value = mock_ror

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        # Should be empty because countries don't match
        assert len(results) == 0

    @patch("validate_ror_records_input_csvs.validators.production_duplicates.GeoNamesClient")
    @patch("validate_ror_records_input_csvs.validators.production_duplicates.RORAPIClient")
    def test_skips_record_when_geonames_fails(
        self, mock_ror_client_class, mock_geonames_class, validator, tmp_path
    ):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "names.types.ror_display,names.types.alias,names.types.label,locations.geonames_id\n"
            "Test University*en,,,99999\n"
        )

        # Mock GeoNames - lookup fails
        mock_geonames = Mock()
        mock_geonames.get_country_code.return_value = None
        mock_geonames.lookup_failures = [{"geonames_id": "99999", "record_identifier": "Test University*en"}]
        mock_geonames_class.return_value = mock_geonames

        # Mock ROR API
        mock_ror = Mock()
        mock_ror_client_class.return_value = mock_ror

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        # Should be empty because geonames lookup failed
        assert len(results) == 0
        # ROR API should not be called
        mock_ror.search_all.assert_not_called()

    @patch("validate_ror_records_input_csvs.validators.production_duplicates.GeoNamesClient")
    @patch("validate_ror_records_input_csvs.validators.production_duplicates.RORAPIClient")
    def test_applies_fuzzy_threshold(
        self, mock_ror_client_class, mock_geonames_class, validator, tmp_path
    ):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "names.types.ror_display,names.types.alias,names.types.label,locations.geonames_id\n"
            "Completely Different Name*en,,,5128581\n"
        )

        mock_geonames = Mock()
        mock_geonames.get_country_code.return_value = "US"
        mock_geonames.lookup_failures = []
        mock_geonames_class.return_value = mock_geonames

        mock_ror = Mock()
        mock_ror.search_all.return_value = [
            {
                "id": "https://ror.org/123",
                "names": [{"value": "Unrelated Organization", "types": ["ror_display"]}],
                "locations": [{"geonames_details": {"country_code": "US"}}]
            }
        ]
        mock_ror_client_class.return_value = mock_ror

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        # Should be empty because fuzzy match is below 85%
        assert len(results) == 0
