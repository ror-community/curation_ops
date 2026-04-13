import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _create_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class GeoNamesClient:
    BASE_URL = "https://secure.geonames.org/getJSON"

    def __init__(self, username: str):
        self.username = username
        self._cache: dict[str, Optional[str]] = {}
        self.lookup_failures: list[dict] = []
        self._session = _create_session()

    def get_country_code(
        self,
        geonames_id: str,
        record_identifier: str = ""
    ) -> Optional[str]:
        if not geonames_id or not geonames_id.strip():
            self.lookup_failures.append({
                "geonames_id": geonames_id,
                "record_identifier": record_identifier,
                "error": "Empty geonames_id"
            })
            return None

        geonames_id = geonames_id.strip()

        if geonames_id in self._cache:
            return self._cache[geonames_id]

        params = {
            "geonameId": geonames_id,
            "username": self.username
        }

        try:
            response = self._session.get(self.BASE_URL, params=params, timeout=10)
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

        except Exception as e:
            logging.warning(f"GeoNames lookup failed for ID {geonames_id}: {e}")
            self.lookup_failures.append({
                "geonames_id": geonames_id,
                "record_identifier": record_identifier,
                "error": str(e)
            })
            self._cache[geonames_id] = None
            return None
