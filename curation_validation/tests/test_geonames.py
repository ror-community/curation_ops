from unittest.mock import patch, Mock

from curation_validation.core.geonames import GeoNamesClient


class TestGeoNamesClient:
    def test_returns_country_code(self):
        client = GeoNamesClient("testuser")
        mock_response = Mock()
        mock_response.json.return_value = {"countryCode": "US"}
        mock_response.raise_for_status = Mock()

        with patch("curation_validation.core.geonames.requests.get", return_value=mock_response):
            result = client.get_country_code("5367440")
        assert result == "US"

    def test_caches_result(self):
        client = GeoNamesClient("testuser")
        mock_response = Mock()
        mock_response.json.return_value = {"countryCode": "US"}
        mock_response.raise_for_status = Mock()

        with patch("curation_validation.core.geonames.requests.get", return_value=mock_response) as mock_get:
            client.get_country_code("5367440")
            client.get_country_code("5367440")
        assert mock_get.call_count == 1

    def test_empty_id_returns_none(self):
        client = GeoNamesClient("testuser")
        result = client.get_country_code("")
        assert result is None
        assert len(client.lookup_failures) == 1

    def test_api_error_returns_none(self):
        client = GeoNamesClient("testuser")
        with patch("curation_validation.core.geonames.requests.get", side_effect=Exception("timeout")):
            result = client.get_country_code("123")
        assert result is None
