"""Validate address data against GeoNames API."""

import logging
import requests

from validate_ror_records_input_csvs.core.io import read_csv
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


def query_geonames_api(geonames_id: str, username: str) -> tuple[str, str]:
    """Returns (city_name, country_name). Returns ("", "") on error."""
    api_url = "http://api.geonames.org/getJSON"
    params = {
        "geonameId": geonames_id,
        "username": username
    }
    try:
        logging.debug(f"Querying GeoNames API for ID: {geonames_id}")
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        name = data.get("name", "")
        country = data.get("countryName", "")
        if name and country:
            logging.debug(f"Successfully retrieved data: {name}, {country}")
        else:
            logging.warning(f"Incomplete data received for ID {geonames_id}")
        return name, country
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed for ID {geonames_id}: {str(e)}")
        return "", ""


class AddressValidationValidator(BaseValidator):
    name = "address-validation"
    output_filename = "address_discrepancies.csv"
    output_fields = [
        "ror_display_name",
        "ror_id",
        "geonames_id",
        "csv_city",
        "csv_country",
        "geonames_city",
        "geonames_country",
        "issue",
    ]
    requires_data_source = False
    requires_geonames = True
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)
        discrepancies = []

        for row in records:
            geonames_id = row.get("locations.geonames_id", "").strip()
            if not geonames_id:
                continue

            csv_city = row.get("city", "").strip()
            csv_country = row.get("country", "").strip()
            ror_display_name = row.get("names.types.ror_display", "")
            ror_id = row.get("id", "")

            api_city, api_country = query_geonames_api(geonames_id, ctx.geonames_user)
            if not api_city and not api_country:
                discrepancies.append({
                    "ror_display_name": ror_display_name,
                    "ror_id": ror_id,
                    "geonames_id": geonames_id,
                    "csv_city": csv_city,
                    "csv_country": csv_country,
                    "geonames_city": "",
                    "geonames_country": "",
                    "issue": "API error - could not retrieve data",
                })
                continue

            city_matches = csv_city == api_city
            country_matches = csv_country == api_country

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
                    "csv_city": csv_city,
                    "csv_country": csv_country,
                    "geonames_city": api_city,
                    "geonames_country": api_country,
                    "issue": ", ".join(issues),
                })

        return discrepancies
