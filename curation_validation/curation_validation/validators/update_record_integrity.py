import json
import re
from collections import defaultdict
from pathlib import Path

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv
from curation_validation.core.json_utils import simplify_and_invert_json

VALID_FIELDS = [
    "status",
    "types",
    "names.types.acronym",
    "names.types.alias",
    "names.types.label",
    "names.types.ror_display",
    "links.type.website",
    "established",
    "links.type.wikipedia",
    "external_ids.type.isni.preferred",
    "external_ids.type.isni.all",
    "external_ids.type.wikidata.preferred",
    "external_ids.type.wikidata.all",
    "external_ids.type.fundref.preferred",
    "external_ids.type.fundref.all",
    "locations.geonames_id",
]


def parse_update_field(update_str):
    updates = {}
    parts = update_str.split(";")
    current_change_type = None
    for part in parts:
        subparts = part.split("==", 1)
        if len(subparts) == 2:
            current_change_type = subparts[0].strip()
            value = subparts[1].strip()
            if current_change_type in updates:
                updates[current_change_type].append(value)
            else:
                updates[current_change_type] = [value]
        else:
            if current_change_type:
                updates[current_change_type].append(subparts[0].strip())
            else:
                updates.setdefault("replace", []).append(subparts[0].strip())
    return updates


def parse_row_updates(row):
    row_updates = {}
    for field, update_str in row.items():
        row_updates[field] = parse_update_field(update_str)
    return row_updates


def parse_record_updates_file(records):
    record_updates = defaultdict(list)
    for row in records:
        ror_id = row["id"]
        html_url = row["html_url"]
        row_updates = parse_row_updates(row)
        for field, updates in row_updates.items():
            if field in VALID_FIELDS:
                for change_type, values in updates.items():
                    for value in values:
                        if value:
                            record_updates[ror_id].append({
                                "html_url": html_url,
                                "change_type": change_type,
                                "field": field,
                                "value": value,
                            })
    return record_updates


def check_if_updates_applied(csv_file, json_directory):
    csv_file = Path(csv_file)
    json_directory = Path(json_directory)

    records = read_csv(csv_file)
    record_updates = parse_record_updates_file(records)

    results = []
    for ror_id, updates in record_updates.items():
        ror_id_file_prefix = re.sub(r"https://ror\.org/", "", ror_id)
        json_file_path = json_directory / f"{ror_id_file_prefix}.json"
        with open(json_file_path, "r", encoding="utf-8") as f_in:
            json_file = json.load(f_in)

        simplified_json, inverted_json = simplify_and_invert_json(json_file)

        additions = ["add", "replace"]
        deletions = ["delete"]

        for update in updates:
            issue_url = update["html_url"]
            change_type = update["change_type"]
            field = update["field"]
            value = update["value"]

            if "*" in value:
                value = value.split("*")[0]

            if field in ("locations.geonames_id", "established"):
                value = int(value)

            if field == "types":
                value = value.lower()

            if change_type in additions:
                if value not in simplified_json["all"] and value not in ["delete", "Delete"]:
                    results.append({
                        "html_url": issue_url,
                        "ror_id": ror_id,
                        "field": field,
                        "type": change_type,
                        "value": str(value),
                        "position": "",
                        "status": "missing",
                    })

            if change_type in deletions:
                inverted_fields = inverted_json.get(value, [])
                if value in simplified_json["all"] and field in inverted_fields:
                    results.append({
                        "html_url": issue_url,
                        "ror_id": ror_id,
                        "field": field,
                        "type": change_type,
                        "value": "",
                        "position": str(value),
                        "status": "still_present",
                    })

            if change_type == "replace" and value in ["delete", "Delete"]:
                if simplified_json.get(field):
                    results.append({
                        "html_url": issue_url,
                        "ror_id": ror_id,
                        "field": field,
                        "type": change_type,
                        "value": "delete",
                        "position": "",
                        "status": "still_present",
                    })

    return results


class UpdateRecordIntegrityValidator(BaseValidator):
    name = "update-record-integrity"
    supported_formats = {"csv_json"}
    output_filename = "update_record_integrity.csv"
    output_fields = [
        "html_url",
        "ror_id",
        "field",
        "type",
        "value",
        "position",
        "status",
    ]
    requires_data_source = False

    def run(self, ctx: ValidatorContext) -> list[dict]:
        return check_if_updates_applied(ctx.csv_file, ctx.json_dir)
