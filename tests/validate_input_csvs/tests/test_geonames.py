# tests/test_geonames.py
import pytest
from unittest.mock import Mock, patch

from validate_ror_records_input_csvs.core.geonames import GeoNamesClient


class TestGeoNamesClient:
    def test_init_requires_username(self):
        client = GeoNamesClient(username="test_user")
        assert client.username == "test_user"

    @patch("validate_ror_records_input_csvs.core.geonames.requests.get")
    def test_get_country_code_returns_code(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "geonameId": 5128581,
            "name": "New York City",
            "countryCode": "US",
            "countryName": "United States"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = GeoNamesClient(username="test_user")
        code = client.get_country_code("5128581", "Test Org")

        assert code == "US"

    @patch("validate_ror_records_input_csvs.core.geonames.requests.get")
    def test_get_country_code_caches_result(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"countryCode": "GB"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = GeoNamesClient(username="test_user")
        client.get_country_code("12345", "Org A")
        client.get_country_code("12345", "Org B")

        # Should only call API once due to caching
        assert mock_get.call_count == 1

    @patch("validate_ror_records_input_csvs.core.geonames.requests.get")
    def test_get_country_code_logs_failure(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Timeout")

        client = GeoNamesClient(username="test_user")
        result = client.get_country_code("99999", "Failed Org")

        assert result is None
        assert len(client.lookup_failures) == 1
        assert client.lookup_failures[0]["geonames_id"] == "99999"
        assert client.lookup_failures[0]["record_identifier"] == "Failed Org"

    @patch("validate_ror_records_input_csvs.core.geonames.requests.get")
    def test_get_country_code_handles_missing_code(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"name": "Some Place"}  # No countryCode
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = GeoNamesClient(username="test_user")
        result = client.get_country_code("11111", "Test Org")

        assert result is None
        assert len(client.lookup_failures) == 1

    def test_get_country_code_empty_id_returns_none(self):
        client = GeoNamesClient(username="test_user")
        result = client.get_country_code("", "Test Org")

        assert result is None
        assert len(client.lookup_failures) == 1
