"""Validator to detect duplicate URLs between CSV and data source."""

from validate_ror_records_input_csvs.core.io import read_csv
from validate_ror_records_input_csvs.core.normalize import normalize_url
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


def get_ror_display_name(record: dict) -> str:
    for name in record.get("names", []):
        if "ror_display" in name.get("types", []):
            return name.get("value", "")
    return ""


def get_website_url(record: dict) -> str | None:
    for link in record.get("links", []):
        if link.get("type") == "website":
            return link.get("value")
    return None


def preprocess_data_source(records: list[dict]) -> dict[str, dict]:
    """Build URL lookup dict. Also includes www. prefixed versions for matching."""
    url_dict = {}

    for record in records:
        website_url = get_website_url(record)
        if not website_url:
            continue

        normalized = normalize_url(website_url)
        if not normalized:
            continue

        record_info = {
            "ror_id": record.get("id", ""),
            "ror_display_name": get_ror_display_name(record),
            "original_url": website_url,
        }

        url_dict[normalized] = record_info

        # Also add www. prefixed version (normalized URL has '//' prefix after scheme removal)
        if normalized.startswith("//") and not normalized.startswith("//www."):
            www_version = "//www." + normalized[2:]
            url_dict[www_version] = record_info

    return url_dict


def find_url_matches(csv_records: list[dict], url_dict: dict[str, dict]) -> list[dict]:
    matches = []

    for csv_row in csv_records:
        csv_url = csv_row.get("links.type.website", "")
        if csv_url:
            csv_url = csv_url.strip()

        if not csv_url:
            continue

        normalized_csv_url = normalize_url(csv_url)
        if not normalized_csv_url:
            continue

        if normalized_csv_url in url_dict:
            data_source_record = url_dict[normalized_csv_url]
            matches.append({
                "ror_display_name": csv_row.get("names.types.ror_display", ""),
                "ror_id": csv_row.get("id", ""),
                "data_dump_id": data_source_record["ror_id"],
                "data_dump_ror_display_name": data_source_record["ror_display_name"],
                "csv_url": csv_url,
                "data_dump_url": data_source_record["original_url"],
            })

    return matches


class DuplicateUrlsValidator(BaseValidator):
    """
    Checks if any website URLs in the input CSV already exist in the ROR data source.
    URL normalization strips scheme, www. prefix, path/query/fragment, and lowercases domain.
    """

    name = "duplicate-urls"
    output_filename = "duplicate_urls.csv"
    output_fields = [
        "ror_display_name",
        "ror_id",
        "data_dump_id",
        "data_dump_ror_display_name",
        "csv_url",
        "data_dump_url",
    ]
    requires_data_source = True
    requires_geonames = False
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)
        data_dump_records = ctx.data_source.get_all_records()
        url_dict = preprocess_data_source(data_dump_records)
        matches = find_url_matches(records, url_dict)

        return matches
