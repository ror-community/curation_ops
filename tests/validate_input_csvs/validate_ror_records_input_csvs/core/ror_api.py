"""ROR API client with rate limiting."""

import logging
import threading
import time

import requests

from validate_ror_records_input_csvs.core.normalize import normalize_text


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
