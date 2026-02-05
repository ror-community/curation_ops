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
    locations = result.get("locations", [])
    if not locations:
        return None

    geonames_details = locations[0].get("geonames_details", {})
    return geonames_details.get("country_code")


def get_all_names_from_result(result: dict) -> list[str]:
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
    return name.split("*")[0].strip()


class ProductionDuplicatesValidator(BaseValidator):
    name = "production-duplicates"
    output_filename = "production_duplicates.csv"
    output_fields = [
        "issue_url",
        "input_name",
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

        seen = set()
        deduplicated = []
        for finding in all_findings:
            key = (finding["input_name"], finding["matched_ror_id"])
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
        issue_url = row.get("html_url", "")
        display_name = row.get("names.types.ror_display", "")
        geonames_id = row.get("locations.geonames_id", "").strip()

        if not geonames_id:
            return []

        country_code = geonames_client.get_country_code(geonames_id, display_name)
        if not country_code:
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
                            "issue_url": issue_url,
                            "input_name": name,
                            "matched_ror_id": result["id"],
                            "matched_name": result_name,
                            "match_ratio": match_ratio,
                        })

        return findings
