from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.fuzzy import ratio_matches
from curation_validation.core.io import read_csv, read_json_dir
from curation_validation.core.geonames import GeoNamesClient
from curation_validation.core.normalize import normalize_text

FUZZY_THRESHOLD = 85
# Concurrent GeoNames lookups for geonames IDs that cannot be resolved locally.
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


def _get_display_name_json(record: dict) -> str:
    for name_entry in record.get("names", []):
        if "ror_display" in name_entry.get("types", []):
            return name_entry.get("value", "")
    return ""


def build_geonames_country_index(records: list[dict]) -> dict[str, str]:
    """Map every geonames_id that appears in ROR records to its country code."""
    index = {}
    for record in records:
        for location in record.get("locations", []):
            geonames_id = location.get("geonames_id")
            country_code = (location.get("geonames_details") or {}).get("country_code")
            if geonames_id and country_code:
                index.setdefault(str(geonames_id), country_code)
    return index


def resolve_countries(
    record_infos: list[dict],
    records: list[dict],
    geonames_user: Optional[str],
) -> dict[str, Optional[str]]:
    """Resolve each input geonames_id to a country code.

    IDs already used by ROR records come from the data dump, then country codes
    embedded in input JSON records; GeoNames is queried only for the rest.
    """
    countries: dict[str, Optional[str]] = build_geonames_country_index(records)
    for info in record_infos:
        if info.get("country_code"):
            countries.setdefault(info["geonames_id"], info["country_code"])

    missing: dict[str, str] = {}
    for info in record_infos:
        if info["geonames_id"] not in countries:
            missing.setdefault(info["geonames_id"], info["issue_url"])

    if missing:
        client = GeoNamesClient(geonames_user)
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            resolved = executor.map(
                lambda item: client.get_country_code(item[0], record_identifier=item[1]),
                missing.items(),
            )
            countries.update(zip(missing, resolved))

    return countries


def find_production_duplicates(
    record_infos: list[dict],
    records: list[dict],
    countries: dict[str, Optional[str]],
) -> list[dict]:
    """Match input names against names of active ROR records in the same country.

    Each (input name, ROR record) pair reports the record's first name, in record
    order, scoring >= FUZZY_THRESHOLD, and each (input_name, matched_ror_id) is
    reported once. Findings follow input order, then descending score.
    """
    # country -> normalized input name -> [(input record position, name position)]
    queries: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
    for record_position, info in enumerate(record_infos):
        country_code = countries.get(info["geonames_id"])
        if not country_code:
            continue
        for name_position, name in enumerate(info["names"]):
            normalized = normalize_text(clean_name(name))
            if normalized:
                queries[country_code][normalized].append((record_position, name_position))

    # country -> normalized ROR name -> [(ROR record position, name position)]
    choices: dict[str, dict[str, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
    record_names: dict[int, list[str]] = {}
    for ror_position, record in enumerate(records):
        if record.get("status") != "active":
            continue
        country_code = get_country_code_from_result(record)
        if country_code not in queries:
            continue
        names = get_all_names_from_result(record)
        record_names[ror_position] = names
        for name_position, name in enumerate(names):
            choices[country_code][normalize_text(name)].append((ror_position, name_position))

    # (input record, input name, ROR record) -> (first matching name position, score)
    matches: dict[tuple[int, int, int], tuple[int, int]] = {}
    for country_code, country_queries in queries.items():
        country_choices = choices.get(country_code)
        if not country_choices:
            continue
        query_names = list(country_queries)
        choice_names = list(country_choices)
        for q, c, score in ratio_matches(query_names, choice_names, FUZZY_THRESHOLD):
            for record_position, name_position in country_queries[query_names[q]]:
                for ror_position, ror_name_position in country_choices[choice_names[c]]:
                    key = (record_position, name_position, ror_position)
                    if key not in matches or ror_name_position < matches[key][0]:
                        matches[key] = (ror_name_position, score)

    ordered = sorted(
        matches.items(),
        key=lambda item: (item[0][0], item[0][1], -item[1][1], item[0][2]),
    )
    findings = []
    seen = set()
    for (record_position, name_position, ror_position), (ror_name_position, score) in ordered:
        info = record_infos[record_position]
        input_name = info["names"][name_position]
        ror_id = records[ror_position].get("id", "")
        if (input_name, ror_id) in seen:
            continue
        seen.add((input_name, ror_id))
        findings.append({
            "issue_url": info["issue_url"],
            "input_name": input_name,
            "matched_ror_id": ror_id,
            "matched_name": record_names[ror_position][ror_name_position],
            "match_ratio": score,
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
    requires_data_source = True
    requires_geonames = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            record_infos = self._parse_json(ctx)
        elif ctx.csv_file is not None:
            record_infos = self._parse_csv(ctx)
        else:
            return []
        if not record_infos:
            return []

        records = ctx.data_source.get_all_records()
        countries = resolve_countries(record_infos, records, ctx.geonames_user)
        return find_production_duplicates(record_infos, records, countries)

    def _parse_json(self, ctx: ValidatorContext) -> list[dict]:
        record_infos = []
        for record in read_json_dir(ctx.json_dir):
            names = get_all_names_from_result(record)
            if not names:
                continue

            locations = record.get("locations", [])
            if not locations:
                continue

            geonames_id = locations[0].get("geonames_id")
            if not geonames_id:
                continue

            display_name = _get_display_name_json(record)
            record_infos.append({
                "issue_url": display_name or record.get("id", ""),
                "names": names,
                "geonames_id": str(geonames_id),
                "country_code": get_country_code_from_result(record),
            })
        return record_infos

    def _parse_csv(self, ctx: ValidatorContext) -> list[dict]:
        record_infos = []
        for row in read_csv(ctx.csv_file):
            names = parse_csv_names(row)
            if not names:
                continue

            geonames_id = row.get("locations.geonames_id", "").strip()
            if not geonames_id:
                continue

            record_infos.append({
                "issue_url": row.get("html_url", ""),
                "names": names,
                "geonames_id": geonames_id,
                "country_code": None,
            })
        return record_infos
