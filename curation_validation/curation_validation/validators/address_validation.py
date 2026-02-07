import logging

import requests

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir


def query_geonames_api(geonames_id: str, username: str) -> tuple[str, str]:
    api_url = "http://api.geonames.org/getJSON"
    params = {"geonameId": geonames_id, "username": username}
    try:
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
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
        "ror_display_name", "ror_id", "geonames_id",
        "csv_city", "csv_country",
        "geonames_city", "geonames_country", "issue",
    ]
    requires_geonames = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        records = read_json_dir(ctx.json_dir)
        discrepancies = []
        for record in records:
            locations = record.get("locations", [])
            if not locations:
                continue
            location = locations[0]
            geonames_id = location.get("geonames_id")
            if geonames_id is None:
                continue
            geonames_id_str = str(geonames_id)
            geonames_details = location.get("geonames_details", {})
            input_city = geonames_details.get("name", "")
            input_country = geonames_details.get("country_name", "")
            ror_display_name = _get_ror_display_name(record)
            ror_id = record.get("id", "")

            api_city, api_country = query_geonames_api(geonames_id_str, ctx.geonames_user)

            if not api_city and not api_country:
                discrepancies.append({
                    "ror_display_name": ror_display_name,
                    "ror_id": ror_id,
                    "geonames_id": geonames_id_str,
                    "csv_city": input_city,
                    "csv_country": input_country,
                    "geonames_city": "",
                    "geonames_country": "",
                    "issue": "API error - could not retrieve data",
                })
                continue

            city_matches = input_city == api_city
            country_matches = input_country == api_country
            if not city_matches or not country_matches:
                issues = []
                if not city_matches:
                    issues.append("city mismatch")
                if not country_matches:
                    issues.append("country mismatch")
                discrepancies.append({
                    "ror_display_name": ror_display_name,
                    "ror_id": ror_id,
                    "geonames_id": geonames_id_str,
                    "csv_city": input_city,
                    "csv_country": input_country,
                    "geonames_city": api_city,
                    "geonames_country": api_country,
                    "issue": ", ".join(issues),
                })
        return discrepancies

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.csv_file)
        discrepancies = []
        for row in records:
            geonames_id = row.get("locations.geonames_id", "").strip()
            if not geonames_id:
                continue
            input_city = row.get("city", "").strip()
            input_country = row.get("country", "").strip()
            ror_display_name = row.get("names.types.ror_display", "")
            ror_id = row.get("id", "")

            api_city, api_country = query_geonames_api(geonames_id, ctx.geonames_user)

            if not api_city and not api_country:
                discrepancies.append({
                    "ror_display_name": ror_display_name,
                    "ror_id": ror_id,
                    "geonames_id": geonames_id,
                    "csv_city": input_city,
                    "csv_country": input_country,
                    "geonames_city": "",
                    "geonames_country": "",
                    "issue": "API error - could not retrieve data",
                })
                continue

            city_matches = input_city == api_city
            country_matches = input_country == api_country
            if not city_matches or not country_matches:
                issues = []
                if not city_matches:
                    issues.append("city mismatch")
                if not country_matches:
                    issues.append("country mismatch")
                discrepancies.append({
                    "ror_display_name": ror_display_name,
                    "ror_id": ror_id,
                    "geonames_id": geonames_id,
                    "csv_city": input_city,
                    "csv_country": input_country,
                    "geonames_city": api_city,
                    "geonames_country": api_country,
                    "issue": ", ".join(issues),
                })
        return discrepancies
