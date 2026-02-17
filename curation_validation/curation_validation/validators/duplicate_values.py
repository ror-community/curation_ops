import re
from collections import defaultdict

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.json_utils import flatten_json
from curation_validation.core.extract import extract_fields
from curation_validation.core.io import read_csv, read_json_dir

COMMON_TYPE_VALUES = frozenset({
    "related", "parent", "child", "predecessor", "successor",
})


def should_ignore_duplicate(value, field1, field2):
    if not value or value == "null":
        return True

    if "admin" in field1 and "admin" in field2:
        return True

    if "external_ids" in field1 and "external_ids" in field2:
        match1 = re.search(r"external_ids_(\d+)", field1)
        match2 = re.search(r"external_ids_(\d+)", field2)
        if match1 and match2 and match1.group(1) == match2.group(1):
            if ("preferred" in field1 and "all" in field2) or \
               ("preferred" in field2 and "all" in field1):
                return True

    if field1.endswith("_lang") and field2.endswith("_lang"):
        return True

    if "types_" in field1 and "types_" in field2:
        if ("names_" in field1 and "names_" in field2):
            return True
        if ("relationships_" in field1 and "relationships_" in field2):
            return True

    if (re.search(r"relationships_\d+_type$", field1) and
            re.search(r"relationships_\d+_type$", field2)):
        return True

    if value in COMMON_TYPE_VALUES:
        return True

    return False


def _should_ignore_csv_duplicate(value, field1, field2):
    if not value or value == "null":
        return True

    # Ignore ror_display + label pairs (ror_display must also have label type)
    if {field1, field2} == {"names.types.ror_display", "names.types.label"}:
        return True

    if "external_ids" in field1 and "external_ids" in field2:
        match1 = re.search(r"external_ids\.type\.(\w+)\.", field1)
        match2 = re.search(r"external_ids\.type\.(\w+)\.", field2)
        if match1 and match2 and match1.group(1) == match2.group(1):
            if ("preferred" in field1 and "all" in field2) or \
               ("preferred" in field2 and "all" in field1):
                return True

    return False


class DuplicateValuesValidator(BaseValidator):
    name = "duplicate_values"
    supported_formats = {"csv", "json"}
    output_filename = "duplicate_values.csv"
    output_fields = ["issue_url", "record_id", "value", "field1", "field2"]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.json_dir is not None:
            return self._run_json(ctx)
        elif ctx.csv_file is not None:
            return self._run_csv(ctx)
        return []

    def _run_json(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        records = read_json_dir(ctx.json_dir)
        for record in records:
            record_id = record.get("id", "")
            issue_url = record_id
            flattened = flatten_json(record)

            value_to_fields = defaultdict(list)
            for field, value in flattened.items():
                if isinstance(value, str) and value:
                    value_to_fields[value].append(field)

            for value, fields in value_to_fields.items():
                if len(fields) < 2:
                    continue
                for i in range(len(fields)):
                    for j in range(i + 1, len(fields)):
                        if not should_ignore_duplicate(value, fields[i], fields[j]):
                            results.append({
                                "issue_url": issue_url,
                                "record_id": record_id,
                                "value": value,
                                "field1": fields[i],
                                "field2": fields[j],
                            })

        return results

    def _run_csv(self, ctx: ValidatorContext) -> list[dict]:
        results = []
        rows = read_csv(ctx.csv_file)
        for row in rows:
            extracted = extract_fields(row, "csv")
            record_id = ""
            id_values = extracted.get("id", [])
            if id_values:
                record_id = id_values[0]
            issue_url = row.get("html_url", "")

            value_to_fields = defaultdict(list)
            for field, values in extracted.items():
                if field == "id":
                    continue
                for value in values:
                    if isinstance(value, str) and value:
                        value_to_fields[value].append(field)

            for value, fields in value_to_fields.items():
                if len(fields) < 2:
                    continue
                for i in range(len(fields)):
                    for j in range(i + 1, len(fields)):
                        if not _should_ignore_csv_duplicate(value, fields[i], fields[j]):
                            results.append({
                                "issue_url": issue_url,
                                "record_id": record_id,
                                "value": value,
                                "field1": fields[i],
                                "field2": fields[j],
                            })

        return results
