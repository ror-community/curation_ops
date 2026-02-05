import logging
from typing import Optional

import requests


class GeoNamesClient:
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
