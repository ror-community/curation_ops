import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.geonames import fetch_all
from curation_validation.core.io import read_csv, read_json_dir


GEONAMES_INVALID_ID = "__INVALID_GEONAMES_ID__"

_session = requests.Session()
_retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retry))


def query_geonames_api(geonames_id: str, username: str) -> tuple[str, str]:
    api_url = "https://secure.geonames.org/getJSON"
    params = {"geonameId": geonames_id, "username": username}
    try:
        response = _session.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "status" in data:
            logging.warning(f"GeoNames API returned error for ID {geonames_id}: {data['status'].get('message', '')}")
            return GEONAMES_INVALID_ID, GEONAMES_INVALID_ID
        name = data.get("name", "")
        country = data.get("countryName", "")
        return name, country
    except requests.exceptions.RequestException as e:
        logging.warning(f"GeoNames API error for ID {geonames_id}: {e}")
        return "", ""


def _get_ror_display_name(record: dict) -> str:
    for name in record.get("names", []):
        if "ror_display" in name.get("types", []):
            return name.get("value", "")
    return ""


class AddressValidationValidator(BaseValidator):
    name = "address-validation"
    supported_formats = {"csv", "json"}
    output_filename = "address_discrepancies.csv"
    output_fields = [
        "issue_url", "ror_display_name", "ror_id", "geonames_id",
        "csv_city", "csv_country",
        "geonames_city", "geonames_country", "issue",
    ]
    requires_geonames = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            entries = self._parse_json(ctx)
        elif ctx.csv_file is not None:
            entries = self._parse_csv(ctx)
        else:
            return []

        results = fetch_all(
            lambda geonames_id: query_geonames_api(geonames_id, ctx.geonames_user),
            (entry["geonames_id"] for entry in entries),
        )
        discrepancies = []
        for entry in entries:
            discrepancy = _compare(entry, *results[entry["geonames_id"]])
            if discrepancy:
                discrepancies.append(discrepancy)
        return discrepancies

    def _parse_json(self, ctx: ValidatorContext) -> list[dict]:
        entries = []
        for record in read_json_dir(ctx.json_dir):
            locations = record.get("locations", [])
            if not locations:
                continue
            location = locations[0]
            geonames_id = location.get("geonames_id")
            if geonames_id is None:
                continue
            geonames_details = location.get("geonames_details", {})
            ror_id = record.get("id", "")
            entries.append({
                "issue_url": ror_id,
                "ror_display_name": _get_ror_display_name(record),
                "ror_id": ror_id,
                "geonames_id": str(geonames_id),
                "csv_city": geonames_details.get("name", ""),
                "csv_country": geonames_details.get("country_name", ""),
            })
        return entries

    def _parse_csv(self, ctx: ValidatorContext) -> list[dict]:
        entries = []
        for row in read_csv(ctx.csv_file):
            geonames_id = row.get("locations.geonames_id", "").strip()
            if not geonames_id:
                continue
            entries.append({
                "issue_url": row.get("html_url", ""),
                "ror_display_name": row.get("names.types.ror_display", ""),
                "ror_id": row.get("id", ""),
                "geonames_id": geonames_id,
                "csv_city": row.get("city", "").strip(),
                "csv_country": row.get("country", "").strip(),
            })
        return entries


def _compare(entry: dict, api_city: str, api_country: str) -> Optional[dict]:
    if api_city == GEONAMES_INVALID_ID:
        return {
            **entry,
            "geonames_city": "",
            "geonames_country": "",
            "issue": f"Invalid Geonames ID - {entry['geonames_id']} does not exist in GeoNames",
        }

    if not api_city and not api_country:
        return {
            **entry,
            "geonames_city": "",
            "geonames_country": "",
            "issue": "API error - could not retrieve data",
        }

    issues = []
    if entry["csv_city"] != api_city:
        issues.append("city mismatch")
    if entry["csv_country"] != api_country:
        issues.append("country mismatch")
    if not issues:
        return None
    return {
        **entry,
        "geonames_city": api_city,
        "geonames_country": api_country,
        "issue": ", ".join(issues),
    }
