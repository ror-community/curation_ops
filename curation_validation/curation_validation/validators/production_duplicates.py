import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from thefuzz import fuzz

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir
from curation_validation.core.geonames import GeoNamesClient
from curation_validation.core.normalize import normalize_text
from curation_validation.core.ror_api import RORAPIClient

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


def _parse_json_names(record: dict) -> list[str]:
    names = []
    name_types = ["ror_display", "alias", "label"]
    for name_entry in record.get("names", []):
        entry_types = name_entry.get("types", [])
        if any(t in entry_types for t in name_types):
            value = name_entry.get("value", "")
            if value:
                names.append(value)
    return names


def _get_display_name_json(record: dict) -> str:
    for name_entry in record.get("names", []):
        if "ror_display" in name_entry.get("types", []):
            return name_entry.get("value", "")
    return ""


def _check_record(
    record_info: dict,
    geonames_client: GeoNamesClient,
    ror_client: RORAPIClient,
) -> list[dict]:
    geonames_id = record_info["geonames_id"]
    names = record_info["names"]
    issue_url = record_info["issue_url"]

    if not geonames_id or not names:
        return []

    country_code = geonames_client.get_country_code(
        str(geonames_id),
        record_identifier=issue_url,
    )
    if not country_code:
        return []

    findings = []

    for input_name in names:
        cleaned = clean_name(input_name)
        if not cleaned:
            continue

        search_results = ror_client.search_all(cleaned)

        for result in search_results:
            result_country = get_country_code_from_result(result)
            if result_country != country_code:
                continue

            result_names = get_all_names_from_result(result)
            normalized_input = normalize_text(cleaned)

            for result_name in result_names:
                match_ratio = fuzz.ratio(
                    normalized_input,
                    normalize_text(result_name),
                )
                if match_ratio >= FUZZY_THRESHOLD:
                    findings.append({
                        "issue_url": issue_url,
                        "input_name": input_name,
                        "matched_ror_id": result.get("id", ""),
                        "matched_name": result_name,
                        "match_ratio": match_ratio,
                    })

    return findings


class ProductionDuplicatesValidator(BaseValidator):
    name = "production-duplicates"
    supported_formats = {"csv", "json"}
    output_filename = "production_duplicates.csv"
    output_fields = [
        "issue_url",
        "input_name",
        "matched_ror_id",
        "matched_name",
        "match_ratio",
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
        if not records:
            return []

        geonames_client = GeoNamesClient(ctx.geonames_user)
        ror_client = RORAPIClient()

        record_infos = []
        for record in records:
            names = _parse_json_names(record)
            if not names:
                continue

            locations = record.get("locations", [])
            if not locations:
                continue

            geonames_id = locations[0].get("geonames_id")
            if not geonames_id:
                continue

            display_name = _get_display_name_json(record)
            issue_url = display_name or record.get("id", "")

            record_infos.append({
                "issue_url": issue_url,
                "names": names,
                "geonames_id": str(geonames_id),
                "display_name": display_name,
            })

        return self._process_records(record_infos, geonames_client, ror_client)

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        rows = read_csv(ctx.csv_file)
        if not rows:
            return []

        geonames_client = GeoNamesClient(ctx.geonames_user)
        ror_client = RORAPIClient()

        record_infos = []
        for row in rows:
            names = parse_csv_names(row)
            if not names:
                continue

            geonames_id = row.get("locations.geonames_id", "").strip()
            if not geonames_id:
                continue

            issue_url = row.get("html_url", "")
            display_name = row.get("names.types.ror_display", "").strip()

            record_infos.append({
                "issue_url": issue_url,
                "names": names,
                "geonames_id": geonames_id,
                "display_name": display_name,
            })

        return self._process_records(record_infos, geonames_client, ror_client)

    def _process_records(
        self,
        record_infos: list[dict],
        geonames_client: GeoNamesClient,
        ror_client: RORAPIClient,
    ) -> list[dict]:
        all_findings = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(
                    _check_record, info, geonames_client, ror_client
                ): info
                for info in record_infos
            }

            for future in as_completed(futures):
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    info = futures[future]
                    logging.warning(
                        f"Error checking record '{info.get('display_name', '')}': {e}"
                    )

        seen = set()
        deduplicated = []
        for finding in all_findings:
            key = (finding["input_name"], finding["matched_ror_id"])
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return deduplicated
