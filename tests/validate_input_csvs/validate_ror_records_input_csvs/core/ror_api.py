import logging
import threading
import time

import requests

from validate_ror_records_input_csvs.core.normalize import normalize_text


class RateLimiter:
    def __init__(self, max_calls: int = 1000, period: float = 300):
        self.max_calls = max_calls
        self.period = period
        self._calls: list[float] = []
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < self.period]

            if len(self._calls) >= self.max_calls:
                sleep_time = self.period - (now - self._calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                now = time.time()
                self._calls = [t for t in self._calls if now - t < self.period]

            self._calls.append(time.time())


class RORAPIClient:
    BASE_URL = "https://api.ror.org/v2/organizations"

    def __init__(self, rate_limiter: RateLimiter = None):
        self.rate_limiter = rate_limiter or RateLimiter()

    def search_query(self, name: str) -> list[dict]:
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
        normalized = normalize_text(name)
        params = {"affiliation": normalized}

        try:
            self.rate_limiter.wait()
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("number_of_results", 0) == 0:
                return []

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

    def search_all(self, name: str) -> list[dict]:
        query_results = self.search_query(name)
        affiliation_results = self.search_affiliation(name)

        seen_ids = set()
        combined = []

        for result in query_results + affiliation_results:
            ror_id = result.get("id")
            if ror_id and ror_id not in seen_ids:
                seen_ids.add(ror_id)
                combined.append(result)

        return combined
