# tests/test_ror_api.py
import time
from unittest.mock import Mock, patch

import pytest

from validate_ror_records_input_csvs.core.ror_api import RateLimiter, RORAPIClient


class TestRateLimiter:
    def test_allows_calls_under_limit(self):
        limiter = RateLimiter(max_calls=5, period=60)

        for _ in range(5):
            limiter.wait()

        # Should not raise or block significantly

    def test_tracks_call_count(self):
        limiter = RateLimiter(max_calls=5, period=60)

        for _ in range(3):
            limiter.wait()

        assert len(limiter._calls) == 3

    @patch("time.sleep")
    def test_sleeps_when_limit_reached(self, mock_sleep):
        limiter = RateLimiter(max_calls=2, period=60)

        limiter.wait()
        limiter.wait()
        limiter.wait()  # Should trigger sleep

        mock_sleep.assert_called()

    def test_prunes_old_calls(self):
        limiter = RateLimiter(max_calls=5, period=0.1)

        limiter.wait()
        limiter.wait()
        time.sleep(0.15)
        limiter.wait()

        # Old calls should be pruned
        assert len(limiter._calls) == 1


class TestRORAPIClientSearchQuery:
    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_query_returns_results(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "number_of_results": 1,
            "items": [
                {
                    "id": "https://ror.org/123",
                    "names": [{"value": "Test Org", "types": ["ror_display"]}],
                    "locations": []
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RORAPIClient()
        results = client.search_query("Test Org")

        assert len(results) == 1
        assert results[0]["id"] == "https://ror.org/123"

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_query_calls_api_with_query_param(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"number_of_results": 0, "items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RORAPIClient()
        client.search_query("University of Testing")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "query" in call_args[1]["params"]
        assert call_args[1]["params"]["query"] == "university of testing"

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_query_returns_empty_on_no_results(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"number_of_results": 0, "items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RORAPIClient()
        results = client.search_query("Nonexistent Organization")

        assert results == []

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_query_handles_api_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        client = RORAPIClient()
        results = client.search_query("Test")

        assert results == []


class TestRORAPIClientSearchAffiliation:
    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_affiliation_unwraps_organization(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {
            "number_of_results": 1,
            "items": [
                {
                    "organization": {
                        "id": "https://ror.org/456",
                        "names": [{"value": "Affiliated Org", "types": ["ror_display"]}],
                        "locations": []
                    },
                    "score": 0.95
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RORAPIClient()
        results = client.search_affiliation("Affiliated Org")

        assert len(results) == 1
        assert results[0]["id"] == "https://ror.org/456"

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_affiliation_calls_api_with_affiliation_param(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"number_of_results": 0, "items": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RORAPIClient()
        client.search_affiliation("Test University")

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "affiliation" in call_args[1]["params"]

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_affiliation_handles_api_error(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Timeout")

        client = RORAPIClient()
        results = client.search_affiliation("Test")

        assert results == []
