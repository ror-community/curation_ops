# Production Duplicates Validator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a validator that checks input CSV records against the live ROR API to find potential duplicate organizations already in production.

**Architecture:** Three new modules - ROR API client with rate limiting, GeoNames client for country code lookup, and the validator itself. Uses parallel processing with ThreadPoolExecutor (5 workers) and 85% fuzzy matching threshold.

**Tech Stack:** Python 3, requests, thefuzz, concurrent.futures (stdlib), threading (stdlib)

---

## Task 1: Rate Limiter

**Files:**
- Create: `validate_ror_records_input_csvs/core/ror_api.py`
- Test: `tests/test_ror_api.py`

**Step 1: Write the failing test for RateLimiter**

```python
# tests/test_ror_api.py
import time
from unittest.mock import patch

import pytest

from validate_ror_records_input_csvs.core.ror_api import RateLimiter


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ror_api.py -v`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# validate_ror_records_input_csvs/core/ror_api.py
"""ROR API client with rate limiting."""

import threading
import time


class RateLimiter:
    """Thread-safe rate limiter for API calls."""

    def __init__(self, max_calls: int = 1000, period: float = 300):
        """
        Args:
            max_calls: Maximum calls allowed in the period
            period: Time period in seconds (default 5 minutes)
        """
        self.max_calls = max_calls
        self.period = period
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Wait if necessary to stay under rate limit."""
        with self._lock:
            now = time.time()
            # Prune old calls
            self._calls = [t for t in self._calls if now - t < self.period]

            if len(self._calls) >= self.max_calls:
                sleep_time = self.period - (now - self._calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                # Prune again after sleeping
                now = time.time()
                self._calls = [t for t in self._calls if now - t < self.period]

            self._calls.append(time.time())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ror_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/core/ror_api.py tests/test_ror_api.py
git commit -m "feat: add RateLimiter for ROR API rate limiting"
```

---

## Task 2: ROR API Client - Basic Search

**Files:**
- Modify: `validate_ror_records_input_csvs/core/ror_api.py`
- Modify: `tests/test_ror_api.py`

**Step 1: Write the failing test for search_query**

```python
# Add to tests/test_ror_api.py
from unittest.mock import Mock, patch

from validate_ror_records_input_csvs.core.ror_api import RateLimiter, RORAPIClient


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchQuery -v`
Expected: FAIL with "AttributeError" or "ImportError"

**Step 3: Write minimal implementation**

```python
# Add to validate_ror_records_input_csvs/core/ror_api.py
import logging
import re
import string

import requests

# Add after RateLimiter class:

def normalize_text(text: str) -> str:
    """Lowercase and remove punctuation for search queries."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    exclude = set(string.punctuation)
    text = ''.join(ch for ch in text if ch not in exclude)
    return text


class RORAPIClient:
    """Client for ROR API v2 search endpoints."""

    BASE_URL = "https://api.ror.org/v2/organizations"

    def __init__(self, rate_limiter: RateLimiter = None):
        self.rate_limiter = rate_limiter or RateLimiter()

    def search_query(self, name: str) -> list[dict]:
        """Search using ?query= parameter. Returns list of organization dicts."""
        normalized = normalize_text(name)
        params = {"query": normalized}

        try:
            self.rate_limiter.wait()
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("number_of_results", 0) == 0:
                return []

            return data.get("items", [])
        except requests.exceptions.RequestException as e:
            logging.warning(f"ROR API query search failed for '{name}': {e}")
            return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchQuery -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/core/ror_api.py tests/test_ror_api.py
git commit -m "feat: add RORAPIClient.search_query method"
```

---

## Task 3: ROR API Client - Affiliation Search

**Files:**
- Modify: `validate_ror_records_input_csvs/core/ror_api.py`
- Modify: `tests/test_ror_api.py`

**Step 1: Write the failing test for search_affiliation**

```python
# Add to tests/test_ror_api.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchAffiliation -v`
Expected: FAIL with "AttributeError"

**Step 3: Write minimal implementation**

```python
# Add to RORAPIClient class in validate_ror_records_input_csvs/core/ror_api.py

    def search_affiliation(self, name: str) -> list[dict]:
        """Search using ?affiliation= parameter. Returns list of organization dicts."""
        normalized = normalize_text(name)
        params = {"affiliation": normalized}

        try:
            self.rate_limiter.wait()
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("number_of_results", 0) == 0:
                return []

            # Affiliation results wrap organizations
            results = []
            for item in data.get("items", []):
                if "organization" in item:
                    results.append(item["organization"])
                else:
                    results.append(item)

            return results
        except requests.exceptions.RequestException as e:
            logging.warning(f"ROR API affiliation search failed for '{name}': {e}")
            return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchAffiliation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/core/ror_api.py tests/test_ror_api.py
git commit -m "feat: add RORAPIClient.search_affiliation method"
```

---

## Task 4: ROR API Client - Combined Search

**Files:**
- Modify: `validate_ror_records_input_csvs/core/ror_api.py`
- Modify: `tests/test_ror_api.py`

**Step 1: Write the failing test for search_all**

```python
# Add to tests/test_ror_api.py
class TestRORAPIClientSearchAll:
    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_all_combines_results(self, mock_get):
        def mock_api_call(url, params, timeout):
            response = Mock()
            response.raise_for_status = Mock()
            if "query" in params:
                response.json.return_value = {
                    "number_of_results": 1,
                    "items": [{"id": "https://ror.org/111", "names": [], "locations": []}]
                }
            else:  # affiliation
                response.json.return_value = {
                    "number_of_results": 1,
                    "items": [{"organization": {"id": "https://ror.org/222", "names": [], "locations": []}}]
                }
            return response

        mock_get.side_effect = mock_api_call

        client = RORAPIClient()
        results = client.search_all("Test")

        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert "https://ror.org/111" in ids
        assert "https://ror.org/222" in ids

    @patch("validate_ror_records_input_csvs.core.ror_api.requests.get")
    def test_search_all_deduplicates_by_id(self, mock_get):
        def mock_api_call(url, params, timeout):
            response = Mock()
            response.raise_for_status = Mock()
            # Both searches return the same org
            if "query" in params:
                response.json.return_value = {
                    "number_of_results": 1,
                    "items": [{"id": "https://ror.org/same", "names": [], "locations": []}]
                }
            else:
                response.json.return_value = {
                    "number_of_results": 1,
                    "items": [{"organization": {"id": "https://ror.org/same", "names": [], "locations": []}}]
                }
            return response

        mock_get.side_effect = mock_api_call

        client = RORAPIClient()
        results = client.search_all("Test")

        assert len(results) == 1
        assert results[0]["id"] == "https://ror.org/same"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchAll -v`
Expected: FAIL with "AttributeError"

**Step 3: Write minimal implementation**

```python
# Add to RORAPIClient class in validate_ror_records_input_csvs/core/ror_api.py

    def search_all(self, name: str) -> list[dict]:
        """Combines query and affiliation results, deduplicated by ROR ID."""
        query_results = self.search_query(name)
        affiliation_results = self.search_affiliation(name)

        # Deduplicate by ID
        seen_ids = set()
        combined = []

        for result in query_results + affiliation_results:
            ror_id = result.get("id")
            if ror_id and ror_id not in seen_ids:
                seen_ids.add(ror_id)
                combined.append(result)

        return combined
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_ror_api.py::TestRORAPIClientSearchAll -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/core/ror_api.py tests/test_ror_api.py
git commit -m "feat: add RORAPIClient.search_all combining query and affiliation"
```

---

## Task 5: GeoNames Client

**Files:**
- Create: `validate_ror_records_input_csvs/core/geonames.py`
- Create: `tests/test_geonames.py`

**Step 1: Write the failing test for GeoNamesClient**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_geonames.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# validate_ror_records_input_csvs/core/geonames.py
"""GeoNames API client with failure tracking."""

import logging
from typing import Optional

import requests


class GeoNamesClient:
    """Client for GeoNames API lookups with failure tracking."""

    BASE_URL = "http://api.geonames.org/getJSON"

    def __init__(self, username: str):
        self.username = username
        self._cache: dict[str, Optional[str]] = {}
        self.lookup_failures: list[dict] = []

    def get_country_code(
        self,
        geonames_id: str,
        record_identifier: str = ""
    ) -> Optional[str]:
        """Lookup country code for a GeoNames ID.

        Returns cached result if available.
        On failure, logs to lookup_failures and returns None.
        """
        if not geonames_id or not geonames_id.strip():
            self.lookup_failures.append({
                "geonames_id": geonames_id,
                "record_identifier": record_identifier,
                "error": "Empty geonames_id"
            })
            return None

        geonames_id = geonames_id.strip()

        # Check cache
        if geonames_id in self._cache:
            return self._cache[geonames_id]

        params = {
            "geonameId": geonames_id,
            "username": self.username
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            country_code = data.get("countryCode")
            if not country_code:
                self.lookup_failures.append({
                    "geonames_id": geonames_id,
                    "record_identifier": record_identifier,
                    "error": "No countryCode in response"
                })
                self._cache[geonames_id] = None
                return None

            self._cache[geonames_id] = country_code
            return country_code

        except requests.exceptions.RequestException as e:
            logging.warning(f"GeoNames lookup failed for ID {geonames_id}: {e}")
            self.lookup_failures.append({
                "geonames_id": geonames_id,
                "record_identifier": record_identifier,
                "error": str(e)
            })
            self._cache[geonames_id] = None
            return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_geonames.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/core/geonames.py tests/test_geonames.py
git commit -m "feat: add GeoNamesClient with country code lookup and failure tracking"
```

---

## Task 6: Helper Functions for Validator

**Files:**
- Create: `validate_ror_records_input_csvs/validators/production_duplicates.py`
- Create: `tests/test_validators/test_production_duplicates.py`

**Step 1: Write the failing test for helper functions**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_validators/test_production_duplicates.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# validate_ror_records_input_csvs/validators/production_duplicates.py
"""Validator to check for duplicate records against ROR production API."""

from typing import Optional


def get_country_code_from_result(result: dict) -> Optional[str]:
    """Extract country code from ROR API result."""
    locations = result.get("locations", [])
    if not locations:
        return None

    geonames_details = locations[0].get("geonames_details", {})
    return geonames_details.get("country_code")


def get_all_names_from_result(result: dict) -> list[str]:
    """Extract all names (ror_display, alias, label) from ROR API result."""
    names = []
    name_types = ["ror_display", "alias", "label"]

    for name_entry in result.get("names", []):
        entry_types = name_entry.get("types", [])
        if any(t in entry_types for t in name_types):
            value = name_entry.get("value", "")
            if value:
                names.append(value)

    return names


def parse_csv_names(row: dict) -> list[str]:
    """Extract names from CSV row (display, aliases, labels)."""
    names = []

    display_name = row.get("names.types.ror_display", "")
    if display_name:
        names.append(display_name)

    aliases = row.get("names.types.alias", "")
    if aliases:
        for alias in aliases.split("; "):
            alias = alias.strip()
            if alias:
                names.append(alias)

    labels = row.get("names.types.label", "")
    if labels:
        for label in labels.split("; "):
            label = label.strip()
            if label:
                names.append(label)

    return names
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_validators/test_production_duplicates.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/validators/production_duplicates.py tests/test_validators/test_production_duplicates.py
git commit -m "feat: add helper functions for production duplicates validator"
```

---

## Task 7: Validator Class Properties

**Files:**
- Modify: `validate_ror_records_input_csvs/validators/production_duplicates.py`
- Modify: `tests/test_validators/test_production_duplicates.py`

**Step 1: Write the failing test for validator properties**

```python
# Add to tests/test_validators/test_production_duplicates.py
from pathlib import Path

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorProperties -v`
Expected: FAIL with "ImportError" or "AttributeError"

**Step 3: Write minimal implementation**

```python
# Add to validate_ror_records_input_csvs/validators/production_duplicates.py

from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


class ProductionDuplicatesValidator(BaseValidator):
    """
    Validator to check for potential duplicates against ROR production API.

    Searches the live ROR API using organization names from the input CSV,
    then applies fuzzy matching (85% threshold) to find potential duplicates.
    Results are filtered to only include matches with the same country code.
    """

    name = "production-duplicates"
    output_filename = "production_duplicates.csv"
    output_fields = [
        "name",
        "display_name",
        "matched_ror_id",
        "matched_name",
        "match_ratio",
    ]
    requires_data_source = False
    requires_geonames = True
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        # Placeholder - implemented in next task
        return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorProperties -v`
Expected: PASS

Run: `pytest tests/test_validators/test_production_duplicates.py::TestCanRun -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/validators/production_duplicates.py tests/test_validators/test_production_duplicates.py
git commit -m "feat: add ProductionDuplicatesValidator class with properties"
```

---

## Task 8: Validator Run Method - Core Logic

**Files:**
- Modify: `validate_ror_records_input_csvs/validators/production_duplicates.py`
- Modify: `tests/test_validators/test_production_duplicates.py`

**Step 1: Write the failing test for run method**

```python
# Add to tests/test_validators/test_production_duplicates.py
from unittest.mock import Mock, patch, MagicMock


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorRun -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# Replace the run method and add imports in validate_ror_records_input_csvs/validators/production_duplicates.py

"""Validator to check for duplicate records against ROR production API."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from thefuzz import fuzz

from validate_ror_records_input_csvs.core.geonames import GeoNamesClient
from validate_ror_records_input_csvs.core.io import read_csv
from validate_ror_records_input_csvs.core.normalize import normalize_text
from validate_ror_records_input_csvs.core.ror_api import RORAPIClient
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


FUZZY_THRESHOLD = 85
MAX_WORKERS = 5


def get_country_code_from_result(result: dict) -> Optional[str]:
    """Extract country code from ROR API result."""
    locations = result.get("locations", [])
    if not locations:
        return None

    geonames_details = locations[0].get("geonames_details", {})
    return geonames_details.get("country_code")


def get_all_names_from_result(result: dict) -> list[str]:
    """Extract all names (ror_display, alias, label) from ROR API result."""
    names = []
    name_types = ["ror_display", "alias", "label"]

    for name_entry in result.get("names", []):
        entry_types = name_entry.get("types", [])
        if any(t in entry_types for t in name_types):
            value = name_entry.get("value", "")
            if value:
                names.append(value)

    return names


def parse_csv_names(row: dict) -> list[str]:
    """Extract names from CSV row (display, aliases, labels)."""
    names = []

    display_name = row.get("names.types.ror_display", "")
    if display_name:
        names.append(display_name)

    aliases = row.get("names.types.alias", "")
    if aliases:
        for alias in aliases.split("; "):
            alias = alias.strip()
            if alias:
                names.append(alias)

    labels = row.get("names.types.label", "")
    if labels:
        for label in labels.split("; "):
            label = label.strip()
            if label:
                names.append(label)

    return names


def clean_name(name: str) -> str:
    """Remove language marker from name (e.g., 'Name*en' -> 'Name')."""
    return name.split("*")[0].strip()


class ProductionDuplicatesValidator(BaseValidator):
    """
    Validator to check for potential duplicates against ROR production API.

    Searches the live ROR API using organization names from the input CSV,
    then applies fuzzy matching (85% threshold) to find potential duplicates.
    Results are filtered to only include matches with the same country code.
    """

    name = "production-duplicates"
    output_filename = "production_duplicates.csv"
    output_fields = [
        "name",
        "display_name",
        "matched_ror_id",
        "matched_name",
        "match_ratio",
    ]
    requires_data_source = False
    requires_geonames = True
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)

        geonames_client = GeoNamesClient(username=ctx.geonames_user)
        ror_client = RORAPIClient()

        all_findings = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    self._process_record,
                    row,
                    geonames_client,
                    ror_client
                ): row
                for row in records
            }

            for future in as_completed(futures):
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    logging.error(f"Error processing record: {e}")

        # Deduplicate by (name, matched_ror_id)
        seen = set()
        deduplicated = []
        for finding in all_findings:
            key = (finding["name"], finding["matched_ror_id"])
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return deduplicated

    def _process_record(
        self,
        row: dict,
        geonames_client: GeoNamesClient,
        ror_client: RORAPIClient
    ) -> list[dict]:
        """Process a single CSV row. Returns list of findings."""
        display_name = row.get("names.types.ror_display", "")
        geonames_id = row.get("locations.geonames_id", "").strip()

        if not geonames_id:
            return []

        # Get country code for this record
        country_code = geonames_client.get_country_code(geonames_id, display_name)
        if not country_code:
            # Lookup failed - skip this record
            return []

        names = parse_csv_names(row)
        if not names:
            return []

        findings = []

        for name in names:
            cleaned_name = clean_name(name)
            if not cleaned_name:
                continue

            results = ror_client.search_all(cleaned_name)

            for result in results:
                result_country = get_country_code_from_result(result)
                if result_country != country_code:
                    continue

                result_names = get_all_names_from_result(result)
                normalized_input = normalize_text(cleaned_name)

                for result_name in result_names:
                    normalized_result = normalize_text(result_name)
                    match_ratio = fuzz.ratio(normalized_input, normalized_result)

                    if match_ratio >= FUZZY_THRESHOLD:
                        findings.append({
                            "name": name,
                            "display_name": display_name,
                            "matched_ror_id": result["id"],
                            "matched_name": result_name,
                            "match_ratio": match_ratio,
                        })

        return findings
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorRun -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/validators/production_duplicates.py tests/test_validators/test_production_duplicates.py
git commit -m "feat: implement ProductionDuplicatesValidator.run with parallel processing"
```

---

## Task 9: Register Validator

**Files:**
- Modify: `validate_ror_records_input_csvs/validators/__init__.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_validators/test_production_duplicates.py
class TestValidatorRegistration:
    def test_validator_is_registered(self):
        from validate_ror_records_input_csvs.validators import register_all_validators
        from validate_ror_records_input_csvs.runner import VALIDATORS

        register_all_validators()

        assert "production-duplicates" in VALIDATORS
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorRegistration -v`
Expected: FAIL

**Step 3: Implement registration**

```python
# validate_ror_records_input_csvs/validators/__init__.py
"""Validator registration and exports."""

from validate_ror_records_input_csvs.validators.validate_fields import ValidateFieldsValidator
from validate_ror_records_input_csvs.validators.duplicate_external_ids import DuplicateExternalIdsValidator
from validate_ror_records_input_csvs.validators.duplicate_urls import DuplicateUrlsValidator
from validate_ror_records_input_csvs.validators.address_validation import AddressValidationValidator
from validate_ror_records_input_csvs.validators.in_release_duplicates import InReleaseDuplicatesValidator
from validate_ror_records_input_csvs.validators.production_duplicates import ProductionDuplicatesValidator


def register_all_validators():
    """Called after runner module is loaded to avoid circular imports."""
    from validate_ror_records_input_csvs.runner import register_validator

    register_validator(ValidateFieldsValidator())
    register_validator(DuplicateExternalIdsValidator())
    register_validator(DuplicateUrlsValidator())
    register_validator(AddressValidationValidator())
    register_validator(InReleaseDuplicatesValidator())
    register_validator(ProductionDuplicatesValidator())


__all__ = [
    "ValidateFieldsValidator",
    "DuplicateExternalIdsValidator",
    "DuplicateUrlsValidator",
    "AddressValidationValidator",
    "InReleaseDuplicatesValidator",
    "ProductionDuplicatesValidator",
    "register_all_validators",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_validators/test_production_duplicates.py::TestValidatorRegistration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add validate_ror_records_input_csvs/validators/__init__.py
git commit -m "feat: register ProductionDuplicatesValidator"
```

---

## Task 10: Update README

**Files:**
- Modify: `README.md`

**Step 1: No test needed for documentation**

**Step 2: Update README**

Add to the Validators table:

```markdown
| `production-duplicates` | Checks for potential duplicates in ROR production via API search | `--geonames-user` (required) |
```

Add to the Output table:

```markdown
| `production-duplicates` | `production_duplicates.csv` |
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add production-duplicates validator to README"
```

---

## Task 11: Run Full Test Suite

**Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests pass

**Step 2: Run with coverage**

Run: `pytest --cov=validate_ror_records_input_csvs --cov-report=term-missing`
Expected: Coverage report shows new modules covered

**Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "chore: fix any test issues"
```

---

## Summary

| Task | Description | New Files | Modified Files |
|------|-------------|-----------|----------------|
| 1 | Rate Limiter | `core/ror_api.py`, `tests/test_ror_api.py` | - |
| 2 | ROR API search_query | - | `core/ror_api.py`, `tests/test_ror_api.py` |
| 3 | ROR API search_affiliation | - | `core/ror_api.py`, `tests/test_ror_api.py` |
| 4 | ROR API search_all | - | `core/ror_api.py`, `tests/test_ror_api.py` |
| 5 | GeoNames Client | `core/geonames.py`, `tests/test_geonames.py` | - |
| 6 | Validator helper functions | `validators/production_duplicates.py`, `tests/test_validators/test_production_duplicates.py` | - |
| 7 | Validator class properties | - | `validators/production_duplicates.py`, `tests/test_validators/test_production_duplicates.py` |
| 8 | Validator run method | - | `validators/production_duplicates.py`, `tests/test_validators/test_production_duplicates.py` |
| 9 | Register validator | - | `validators/__init__.py` |
| 10 | Update README | - | `README.md` |
| 11 | Full test suite | - | - |
