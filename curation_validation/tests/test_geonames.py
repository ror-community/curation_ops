from unittest.mock import patch, Mock

from curation_validation.core.geonames import GeoNamesClient


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status = Mock()
    return response


class TestGeoNamesClient:
    def test_returns_country_code(self):
        client = GeoNamesClient("testuser")
        with patch.object(client._session, "get", return_value=_response({"countryCode": "US"})) as mock_get:
            result = client.get_country_code("5367440")
        assert result == "US"
        mock_get.assert_called_once_with(
            "https://secure.geonames.org/getJSON",
            params={"geonameId": "5367440", "username": "testuser"},
            timeout=10,
        )

    def test_caches_result(self):
        client = GeoNamesClient("testuser")
        with patch.object(client._session, "get", return_value=_response({"countryCode": "US"})) as mock_get:
            client.get_country_code("5367440")
            client.get_country_code("5367440")
        assert mock_get.call_count == 1

    def test_empty_id_returns_none(self):
        client = GeoNamesClient("testuser")
        result = client.get_country_code("")
        assert result is None
        assert len(client.lookup_failures) == 1

    def test_missing_country_code_returns_none(self):
        client = GeoNamesClient("testuser")
        payload = {"status": {"message": "no result found", "value": 15}}
        with patch.object(client._session, "get", return_value=_response(payload)):
            result = client.get_country_code("123")
        assert result is None
        assert client.lookup_failures[0]["error"] == "No countryCode in response"

    def test_api_error_returns_none(self):
        client = GeoNamesClient("testuser")
        with patch.object(client._session, "get", side_effect=Exception("timeout")):
            result = client.get_country_code("123", record_identifier="issue-1")
        assert result is None
        assert client.lookup_failures == [
            {"geonames_id": "123", "record_identifier": "issue-1", "error": "timeout"}
        ]
