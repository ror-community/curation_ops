from unittest.mock import patch, Mock

from curation_validation.core.geonames import GeoNamesClient, fetch_all


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


class TestFetchAll:
    def test_calls_once_per_distinct_id_and_keeps_first_seen_order(self):
        calls = []

        def fetch(geonames_id):
            calls.append(geonames_id)
            return geonames_id * 2

        result = fetch_all(fetch, ["b", "a", "b", "c", "a"])
        assert result == {"b": "bb", "a": "aa", "c": "cc"}
        assert list(result) == ["b", "a", "c"]
        assert sorted(calls) == ["a", "b", "c"]

    def test_empty(self):
        assert fetch_all(lambda geonames_id: geonames_id, []) == {}
