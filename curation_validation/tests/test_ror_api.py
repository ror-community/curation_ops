from unittest.mock import patch, Mock

from curation_validation.core.ror_api import RORAPIClient, RateLimiter


class TestRateLimiter:
    def test_allows_calls_within_limit(self):
        limiter = RateLimiter(max_calls=10, period=60)
        limiter.wait()  # should not raise


class TestRORAPIClient:
    def test_search_query(self):
        client = RORAPIClient(rate_limiter=RateLimiter())
        mock_response = Mock()
        mock_response.json.return_value = {
            "number_of_results": 1,
            "items": [{"id": "https://ror.org/012345"}],
        }
        mock_response.raise_for_status = Mock()

        with patch("curation_validation.core.ror_api.requests.get", return_value=mock_response):
            results = client.search_query("Test University")
        assert len(results) == 1

    def test_search_affiliation(self):
        client = RORAPIClient(rate_limiter=RateLimiter())
        mock_response = Mock()
        mock_response.json.return_value = {
            "number_of_results": 1,
            "items": [{"organization": {"id": "https://ror.org/012345"}}],
        }
        mock_response.raise_for_status = Mock()

        with patch("curation_validation.core.ror_api.requests.get", return_value=mock_response):
            results = client.search_affiliation("Test University")
        assert len(results) == 1
        assert results[0]["id"] == "https://ror.org/012345"

    def test_search_all_deduplicates(self):
        client = RORAPIClient(rate_limiter=RateLimiter())
        mock_response = Mock()
        mock_response.json.return_value = {
            "number_of_results": 1,
            "items": [{"id": "https://ror.org/012345"}],
        }
        mock_response.raise_for_status = Mock()

        with patch("curation_validation.core.ror_api.requests.get", return_value=mock_response):
            results = client.search_all("Test University")
        assert len(results) == 1

    def test_api_error_returns_empty(self):
        client = RORAPIClient(rate_limiter=RateLimiter())
        with patch("curation_validation.core.ror_api.requests.get", side_effect=Exception("timeout")):
            results = client.search_query("Test")
        assert results == []
