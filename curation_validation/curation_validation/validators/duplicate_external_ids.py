import re

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv, read_json_dir


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def process_input_csv(records: list[dict]) -> list[dict]:
    processed_records = []
    for row in records:
        record = {
            "id": row.get("id", ""),
            "issue_url": row.get("html_url", ""),
            "names": [
                {
                    "types": ["ror_display"],
                    "value": row.get("names.types.ror_display", ""),
                }
            ],
            "external_ids": [],
        }
        for id_type in ["fundref", "grid", "isni", "wikidata"]:
            all_ids = row.get(f"external_ids.type.{id_type}.all", "")
            preferred_id = row.get(f"external_ids.type.{id_type}.preferred", "")
            if all_ids or preferred_id:
                record["external_ids"].append(
                    {
                        "all": [
                            normalize_whitespace(id_val)
                            for id_val in all_ids.split(";")
                            if id_val.strip()
                        ],
                        "preferred": (
                            normalize_whitespace(preferred_id)
                            if preferred_id
                            else ""
                        ),
                        "type": id_type,
                    }
                )
        processed_records.append(record)
    return processed_records


def extract_external_ids(record: dict) -> set[str]:
    external_ids = set()
    for id_obj in record.get("external_ids", []):
        external_ids.update(id_obj.get("all", []))
        if id_obj.get("preferred"):
            external_ids.add(id_obj["preferred"])
    return external_ids


def normalize_data_dump_external_ids(records: list[dict]) -> list[dict]:
    for record in records:
        for id_obj in record.get("external_ids", []):
            id_obj["all"] = [
                normalize_whitespace(id_val) for id_val in id_obj.get("all", [])
            ]
            if id_obj.get("preferred"):
                id_obj["preferred"] = normalize_whitespace(id_obj["preferred"])
    return records


def get_ror_display_name(record: dict) -> str:
    for name in record.get("names", []):
        if "ror_display" in name.get("types", []):
            return name.get("value", "")
    return ""


def find_matches(
    input_records: list[dict], data_dump_records: list[dict]
) -> list[dict]:
    normalized_data_dump = normalize_data_dump_external_ids(data_dump_records)
    matches = []
    for input_record in input_records:
        input_external_ids = extract_external_ids(input_record)
        if not input_external_ids:
            continue
        input_ror_display_name = get_ror_display_name(input_record)
        issue_url = input_record.get("issue_url", input_record.get("id", ""))
        for data_dump_record in normalized_data_dump:
            data_dump_external_ids = extract_external_ids(data_dump_record)
            common_ids = input_external_ids.intersection(data_dump_external_ids)
            if common_ids:
                data_dump_ror_display_name = get_ror_display_name(data_dump_record)
                for external_id in common_ids:
                    matches.append(
                        {
                            "issue_url": issue_url,
                            "id": input_record.get("id", ""),
                            "ror_display_name": input_ror_display_name,
                            "data_dump_id": data_dump_record.get("id", ""),
                            "data_dump_ror_display_name": data_dump_ror_display_name,
                            "overlapping_external_id": external_id,
                        }
                    )
    return matches


class DuplicateExternalIdsValidator(BaseValidator):
    name = "duplicate-external-ids"
    supported_formats = {"csv", "json"}
    output_filename = "duplicate_external_ids.csv"
    output_fields = [
        "issue_url",
        "id",
        "ror_display_name",
        "data_dump_id",
        "data_dump_ror_display_name",
        "overlapping_external_id",
    ]
    requires_data_source = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        data_dump_records = ctx.data_source.get_all_records()
        input_records = read_json_dir(ctx.json_dir)
        for record in input_records:
            for id_obj in record.get("external_ids", []):
                id_obj["all"] = [
                    normalize_whitespace(id_val)
                    for id_val in id_obj.get("all", [])
                ]
                if id_obj.get("preferred"):
                    id_obj["preferred"] = normalize_whitespace(id_obj["preferred"])
        return find_matches(input_records, data_dump_records)

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        data_dump_records = ctx.data_source.get_all_records()
        rows = read_csv(ctx.csv_file)
        input_records = process_input_csv(rows)
        return find_matches(input_records, data_dump_records)
