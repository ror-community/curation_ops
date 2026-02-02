import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from validate_ror_records_input_csvs.validators.base import ValidatorContext
from validate_ror_records_input_csvs.validators.address_validation import AddressValidationValidator


@pytest.fixture
def validator():
    return AddressValidationValidator()


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
        assert validator.name == "address-validation"

    def test_output_filename(self, validator):
        assert validator.output_filename == "address_discrepancies.csv"

    def test_output_fields(self, validator):
        assert "ror_display_name" in validator.output_fields
        assert "ror_id" in validator.output_fields
        assert "geonames_id" in validator.output_fields
        assert "csv_city" in validator.output_fields
        assert "csv_country" in validator.output_fields
        assert "geonames_city" in validator.output_fields
        assert "geonames_country" in validator.output_fields
        assert "issue" in validator.output_fields

    def test_requires_data_source(self, validator):
        assert validator.requires_data_source is False

    def test_requires_geonames(self, validator):
        assert validator.requires_geonames is True


class TestCanRun:
    def test_can_run_with_geonames_user(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id,names.types.ror_display,locations.geonames_id,city,country\n")

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        can_run, reason = validator.can_run(ctx)

        assert can_run is True
        assert reason == ""

    def test_cannot_run_without_geonames_user(self, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text("id,names.types.ror_display,locations.geonames_id,city,country\n")

        ctx = make_context(csv_path, tmp_path, geonames_user=None)
        can_run, reason = validator.can_run(ctx)

        assert can_run is False
        assert "geonames" in reason.lower()


class TestCityCountryMismatch:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_detects_city_mismatch(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,Wrong City,United States\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["csv_city"] == "Wrong City"
        assert results[0]["geonames_city"] == "New York City"
        assert results[0]["issue"] == "city mismatch"

    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_detects_country_mismatch(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,Canada\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["csv_country"] == "Canada"
        assert results[0]["geonames_country"] == "United States"
        assert results[0]["issue"] == "country mismatch"

    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_detects_both_mismatch(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,Wrong City,Wrong Country\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert "city" in results[0]["issue"]
        assert "country" in results[0]["issue"]


class TestValidAddress:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_valid_address_no_issues(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,United States\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 0


class TestAPIErrorHandling:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_handles_api_request_exception(self, mock_get, validator, tmp_path):
        import requests

        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,United States\n"
        )

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert "api error" in results[0]["issue"].lower()

    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_handles_incomplete_api_response(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,United States\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) >= 1

    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_handles_http_error(self, mock_get, validator, tmp_path):
        import requests

        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,United States\n"
        )

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert "api error" in results[0]["issue"].lower()


class TestMultipleRecords:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_processes_multiple_records(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test1,Org One*en,5128581,New York City,United States\n"
            "https://ror.org/test2,Org Two*en,2643743,Wrong City,United Kingdom\n"
        )

        def mock_api_call(url, params, timeout):
            geonames_id = params["geonameId"]
            response = Mock()
            response.raise_for_status = Mock()
            if geonames_id == "5128581":
                response.json.return_value = {
                    "name": "New York City",
                    "countryName": "United States"
                }
            else:
                response.json.return_value = {
                    "name": "London",
                    "countryName": "United Kingdom"
                }
            return response

        mock_get.side_effect = mock_api_call

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        assert results[0]["ror_id"] == "https://ror.org/test2"
        assert results[0]["geonames_city"] == "London"


class TestOutputFields:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_output_includes_all_fields(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,Wrong City,Wrong Country\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1
        result = results[0]
        assert result["ror_display_name"] == "Test Org*en"
        assert result["ror_id"] == "https://ror.org/test123"
        assert result["geonames_id"] == "5128581"
        assert result["csv_city"] == "Wrong City"
        assert result["csv_country"] == "Wrong Country"
        assert result["geonames_city"] == "New York City"
        assert result["geonames_country"] == "United States"


class TestEmptyOrMissingData:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_handles_empty_geonames_id(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,,Boston,United States\n"
        )

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        mock_get.assert_not_called()
        assert len(results) == 0

    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_handles_empty_city_country(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,,\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        results = validator.run(ctx)

        assert len(results) == 1


class TestAPICall:
    @patch("validate_ror_records_input_csvs.validators.address_validation.requests.get")
    def test_api_called_with_correct_params(self, mock_get, validator, tmp_path):
        csv_path = tmp_path / "input.csv"
        csv_path.write_text(
            "id,names.types.ror_display,locations.geonames_id,city,country\n"
            "https://ror.org/test123,Test Org*en,5128581,New York City,United States\n"
        )

        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "New York City",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        ctx = make_context(csv_path, tmp_path, geonames_user="test_user")
        validator.run(ctx)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "http://api.geonames.org/getJSON"
        assert call_args[1]["params"]["geonameId"] == "5128581"
        assert call_args[1]["params"]["username"] == "test_user"
        assert call_args[1]["timeout"] == 10
