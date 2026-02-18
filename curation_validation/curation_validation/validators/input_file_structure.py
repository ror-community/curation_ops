import csv
import io
import re
from pathlib import Path

import chardet

from curation_validation.validators.base import BaseValidator, ValidatorContext


UPDATE_ACTIONS = {
    "ADD": "add",
    "DELETE": "delete",
    "REPLACE": "replace",
}

UPDATE_ACTIONS_MULTI = [UPDATE_ACTIONS["ADD"], UPDATE_ACTIONS["DELETE"], UPDATE_ACTIONS["REPLACE"]]
UPDATE_ACTIONS_SINGLE = [UPDATE_ACTIONS["DELETE"], UPDATE_ACTIONS["REPLACE"]]

CSV_REQUIRED_FIELDS_ACTIONS = {
    "id": None,
    "domains": UPDATE_ACTIONS_MULTI,
    "established": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.fundref.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.fundref.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.grid.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.grid.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.isni.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.isni.preferred": UPDATE_ACTIONS_SINGLE,
    "external_ids.type.wikidata.all": UPDATE_ACTIONS_MULTI,
    "external_ids.type.wikidata.preferred": UPDATE_ACTIONS_SINGLE,
    "links.type.website": UPDATE_ACTIONS_MULTI,
    "links.type.wikipedia": UPDATE_ACTIONS_MULTI,
    "locations.geonames_id": UPDATE_ACTIONS_MULTI,
    "names.types.acronym": UPDATE_ACTIONS_MULTI,
    "names.types.alias": UPDATE_ACTIONS_MULTI,
    "names.types.label": UPDATE_ACTIONS_MULTI,
    "names.types.ror_display": [UPDATE_ACTIONS["REPLACE"]],
    "status": [UPDATE_ACTIONS["REPLACE"]],
    "types": UPDATE_ACTIONS_MULTI,
}

NO_DELETE_ACTION_FIELDS = ["id", "locations.geonames_id", "names.types.ror_display", "status", "types"]

NEW_RECORD_REQUIRED_FIELDS = ["names.types.ror_display", "status", "types", "locations.geonames_id"]

NAME_FIELDS = ["names.types.acronym", "names.types.alias", "names.types.label", "names.types.ror_display"]

IMPLICIT_REPLACE_FIELDS = [
    "id", "established",
    "external_ids.type.fundref.preferred",
    "external_ids.type.grid.preferred",
    "external_ids.type.isni.preferred",
    "external_ids.type.wikidata.preferred",
    "status", "names.types.ror_display",
]

UPDATE_DELIMITER = "=="
LANG_DELIMITER = "*"

ROR_ID_PATTERN = re.compile(r'^https://ror\.org/[a-z0-9]{9}$')


def _truncate_value(value: str, max_length: int = 100) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length - 3] + "..."


def _validate_ror_id(ror_id: str) -> str | None:
    if not ror_id:
        return None

    ror_id = ror_id.strip()
    if not ror_id:
        return None

    if not ROR_ID_PATTERN.match(ror_id):
        if ' ' in ror_id:
            return f"ROR ID '{_truncate_value(ror_id)}' contains whitespace"
        elif not ror_id.startswith('https://ror.org/'):
            return f"ROR ID '{_truncate_value(ror_id)}' must start with 'https://ror.org/'"
        else:
            return f"ROR ID '{_truncate_value(ror_id)}' must be 'https://ror.org/' followed by exactly 9 lowercase alphanumeric characters"
    return None


def _validate_name_format(name_value: str) -> str | None:
    if not isinstance(name_value, str) or not name_value.strip():
        return None

    name_value = name_value.strip()

    asterisk_count = name_value.count(LANG_DELIMITER)
    if asterisk_count > 1:
        return f"Name '{_truncate_value(name_value)}' contains multiple '{LANG_DELIMITER}' characters. Only one language code delimiter is allowed per name (e.g., 'Microsoft*en')"

    if name_value.endswith('*'):
        return f"Name '{_truncate_value(name_value)}' ends with asterisk but has no language code (e.g., 'Microsoft*en')"

    asterisk_pos = name_value.rfind('*')
    if asterisk_pos != -1:
        lang_code = name_value[asterisk_pos + 1:]
        if lang_code and (len(lang_code) != 2 or not lang_code.isalpha()):
            return f"Name '{_truncate_value(name_value)}' has invalid language code after asterisk. Must be exactly two letters (e.g., 'Microsoft*en')"

    return None


def _get_actions_values(csv_field: str) -> dict[str, list[str] | None]:
    actions_values: dict[str, list[str] | None] = {}
    if not isinstance(csv_field, str):
        return actions_values

    csv_field_strip = csv_field.strip()
    csv_field_lower = csv_field_strip.lower()

    if csv_field_lower == UPDATE_ACTIONS["DELETE"]:
        actions_values[UPDATE_ACTIONS["DELETE"]] = None
        return actions_values

    pattern = re.compile(r"(add|delete|replace)==", re.IGNORECASE)
    matches = list(pattern.finditer(csv_field_strip))

    action_data = []

    if not matches:
        if csv_field_strip:
            action_data.append((UPDATE_ACTIONS["REPLACE"], csv_field_strip))
    else:
        for i, match in enumerate(matches):
            action = match.group(1).lower()
            action_end = match.end()

            value_start = action_end
            value_end = matches[i + 1].start() if i + 1 < len(matches) else len(csv_field_strip)
            value_str = csv_field_strip[value_start:value_end].strip()

            action_data.append((action, value_str))

    for action, value_str in action_data:
        values = [v.strip() for v in value_str.split(';') if v.strip()]
        if values:
            if action in actions_values:
                actions_values[action].extend(values)
            else:
                actions_values[action] = values
        elif action == UPDATE_ACTIONS["DELETE"]:
            actions_values[action] = None

    if UPDATE_ACTIONS["DELETE"] in actions_values and isinstance(actions_values[UPDATE_ACTIONS["DELETE"]], list) and not actions_values[UPDATE_ACTIONS["DELETE"]]:
        actions_values[UPDATE_ACTIONS["DELETE"]] = None

    return actions_values


class InputFileStructureValidator(BaseValidator):
    name = "input_file_structure"
    supported_formats = {"csv"}
    output_filename = "input_file_structure.csv"
    output_fields = [
        "issue_url",
        "row_number",
        "error_type",
        "field",
        "value",
        "message",
    ]

    def run(self, ctx: ValidatorContext) -> list[dict]:
        if ctx.csv_file is None:
            return []

        results = []
        csv_path = Path(ctx.csv_file)

        try:
            raw_data = csv_path.read_bytes()
        except FileNotFoundError:
            results.append({
                "issue_url": "",
                "row_number": 0,
                "error_type": "file_error",
                "field": "",
                "value": str(csv_path),
                "message": f"File not found: {csv_path}",
            })
            return results
        except Exception as e:
            results.append({
                "issue_url": "",
                "row_number": 0,
                "error_type": "file_error",
                "field": "",
                "value": str(csv_path),
                "message": f"Could not read file: {e}",
            })
            return results

        encoding_info = chardet.detect(raw_data)
        detected_encoding = encoding_info.get('encoding', 'utf-8')
        confidence = encoding_info.get('confidence', 0)
        file_encoding = detected_encoding if confidence > 0.7 else 'utf-8'

        # ASCII is a subset of UTF-8, so only warn for other encodings
        if not file_encoding.lower().startswith('utf-8') and file_encoding.lower() != 'ascii':
            results.append({
                "issue_url": "",
                "row_number": 0,
                "error_type": "encoding_warning",
                "field": "",
                "value": file_encoding,
                "message": f"File encoding detected as '{file_encoding}' but API expects UTF-8. This might cause errors during upload.",
            })

        try:
            file_content = raw_data.decode(file_encoding)
            csvfile = io.StringIO(file_content)
            reader = csv.DictReader(csvfile)

            header_results = self._validate_header(reader)
            results.extend(header_results)

            if any(r["error_type"] == "header_missing_columns" for r in header_results):
                return results

            for i, row in enumerate(reader):
                row_num = i + 2
                html_url = row.get("html_url", "")

                if None in row:
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "column_mismatch",
                        "field": "",
                        "value": _truncate_value(str(row[None])),
                        "message": f"Row has more columns than header. Extra data: {_truncate_value(str(row[None]))}",
                    })

                row_results = self._validate_row(row_num, row, html_url)
                results.extend(row_results)

        except UnicodeDecodeError as e:
            results.append({
                "issue_url": "",
                "row_number": 0,
                "error_type": "encoding_error",
                "field": "",
                "value": file_encoding,
                "message": f"Could not decode file using encoding '{file_encoding}'. Error: {e}",
            })
        except csv.Error as e:
            results.append({
                "issue_url": "",
                "row_number": 0,
                "error_type": "csv_parse_error",
                "field": "",
                "value": "",
                "message": f"CSV parsing error: {e}. Check CSV structure (quoting, delimiters, column count).",
            })

        return results

    def _validate_header(self, reader: csv.DictReader) -> list[dict]:
        results = []
        csv_fields = reader.fieldnames

        if not csv_fields:
            results.append({
                "issue_url": "",
                "row_number": 1,
                "error_type": "header_no_header",
                "field": "",
                "value": "",
                "message": "CSV file appears to have no header row.",
            })
            return results

        required_keys = CSV_REQUIRED_FIELDS_ACTIONS.keys()
        missing_fields = [field for field in required_keys if field not in csv_fields]

        if missing_fields:
            results.append({
                "issue_url": "",
                "row_number": 1,
                "error_type": "header_missing_columns",
                "field": "",
                "value": ", ".join(missing_fields),
                "message": f"CSV file is missing required columns: {', '.join(missing_fields)}",
            })

        return results

    def _validate_row(self, row_num: int, row_data: dict, html_url: str) -> list[dict]:
        results = []
        ror_id = row_data.get('id', '') or ''
        is_update = bool(ror_id.strip())

        if is_update:
            ror_id_error = _validate_ror_id(ror_id)
            if ror_id_error:
                results.append({
                    "issue_url": html_url,
                    "row_number": row_num,
                    "error_type": "ror_id_invalid",
                    "field": "id",
                    "value": _truncate_value(ror_id),
                    "message": ror_id_error,
                })

        for field, value in row_data.items():
            if isinstance(value, str) and ('\n' in value or '\r' in value):
                results.append({
                    "issue_url": html_url,
                    "row_number": row_num,
                    "error_type": "embedded_newline",
                    "field": field,
                    "value": _truncate_value(repr(value)),
                    "message": f"Field '{field}' contains embedded newline/carriage return character. This will cause API parsing errors.",
                })

        if not is_update:
            results.extend(self._validate_new_record(row_num, row_data, html_url))
        else:
            results.extend(self._validate_update_record(row_num, row_data, html_url))

        results.extend(self._validate_name_fields(row_num, row_data, html_url))

        return results

    def _validate_new_record(self, row_num: int, row_data: dict, html_url: str) -> list[dict]:
        results = []

        for field in NEW_RECORD_REQUIRED_FIELDS:
            field_value = row_data.get(field, '') or ''
            if not field_value.strip():
                results.append({
                    "issue_url": html_url,
                    "row_number": row_num,
                    "error_type": "new_record_missing_field",
                    "field": field,
                    "value": "",
                    "message": f"New record missing required field '{field}'.",
                })

        for field, value in row_data.items():
            if isinstance(value, str):
                if UPDATE_DELIMITER in value:
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "new_record_update_syntax",
                        "field": field,
                        "value": _truncate_value(value),
                        "message": f"Update syntax ('add==', 'delete==', 'replace==') used in field '{field}' for a new record (ID column is empty). Remove update syntax.",
                    })
                if value.strip().lower() == UPDATE_ACTIONS['DELETE']:
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "new_record_update_syntax",
                        "field": field,
                        "value": value,
                        "message": f"'delete' action used in field '{field}' for a new record (ID column is empty). Remove 'delete' action.",
                    })

        return results

    def _validate_update_record(self, row_num: int, row_data: dict, html_url: str) -> list[dict]:
        results = []

        for field, value in row_data.items():
            if field not in CSV_REQUIRED_FIELDS_ACTIONS or not isinstance(value, str) or not value.strip():
                continue

            allowed_actions = CSV_REQUIRED_FIELDS_ACTIONS.get(field)
            field_value_lower = value.strip().lower()

            if field_value_lower == UPDATE_ACTIONS['DELETE'] and field in NO_DELETE_ACTION_FIELDS:
                results.append({
                    "issue_url": html_url,
                    "row_number": row_num,
                    "error_type": "update_action_invalid",
                    "field": field,
                    "value": value,
                    "message": f"Cannot use 'delete' action in field '{field}'. Cannot remove all values from this required field.",
                })
                continue

            if UPDATE_DELIMITER in value or field_value_lower == UPDATE_ACTIONS['DELETE']:
                actions_values = _get_actions_values(value)
                update_actions_found = list(actions_values.keys())

                if not update_actions_found and field_value_lower != UPDATE_ACTIONS['DELETE']:
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "update_syntax_invalid",
                        "field": field,
                        "value": _truncate_value(value),
                        "message": f"Update delimiter '{UPDATE_DELIMITER}' found in field '{field}' but could not parse a valid action. Check syntax.",
                    })
                    continue

                if UPDATE_ACTIONS['REPLACE'] in update_actions_found and \
                   (UPDATE_ACTIONS['ADD'] in update_actions_found or UPDATE_ACTIONS['DELETE'] in update_actions_found):
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "update_action_conflict",
                        "field": field,
                        "value": _truncate_value(value),
                        "message": f"'{UPDATE_ACTIONS['REPLACE']}==' cannot be combined with '{UPDATE_ACTIONS['ADD']}==' or '{UPDATE_ACTIONS['DELETE']}==' in field '{field}'.",
                    })

                if allowed_actions is not None:
                    disallowed_used_actions = [ua for ua in update_actions_found if ua not in allowed_actions]
                    if disallowed_used_actions:
                        allowed_str = f"Allowed actions are: {', '.join(allowed_actions)}." if allowed_actions else "Only implicit replace is allowed."
                        results.append({
                            "issue_url": html_url,
                            "row_number": row_num,
                            "error_type": "update_action_invalid",
                            "field": field,
                            "value": _truncate_value(value),
                            "message": f"Invalid update action(s) '{', '.join(disallowed_used_actions)}' in field '{field}'. {allowed_str}",
                        })

            elif field not in IMPLICIT_REPLACE_FIELDS:
                if field in CSV_REQUIRED_FIELDS_ACTIONS and UPDATE_ACTIONS["ADD"] in (CSV_REQUIRED_FIELDS_ACTIONS.get(field) or []):
                    results.append({
                        "issue_url": html_url,
                        "row_number": row_num,
                        "error_type": "update_ambiguous",
                        "field": field,
                        "value": _truncate_value(value),
                        "message": f"Ambiguous update for multi-value field '{field}'. Use 'add=={value}' or 'replace=={value}' syntax.",
                    })

        return results

    def _validate_name_fields(self, row_num: int, row_data: dict, html_url: str) -> list[dict]:
        results = []

        for field in NAME_FIELDS:
            if field not in row_data or not row_data[field]:
                continue

            field_value = row_data[field]

            if isinstance(field_value, str) and (UPDATE_DELIMITER in field_value or field_value.strip().lower() == UPDATE_ACTIONS['DELETE']):
                actions_values = _get_actions_values(field_value)
                for action, values in actions_values.items():
                    if action != UPDATE_ACTIONS['DELETE'] and values:
                        for value in values:
                            error = _validate_name_format(value)
                            if error:
                                results.append({
                                    "issue_url": html_url,
                                    "row_number": row_num,
                                    "error_type": "name_format_invalid",
                                    "field": field,
                                    "value": _truncate_value(value),
                                    "message": error,
                                })
            else:
                if isinstance(field_value, str):
                    values = [v.strip() for v in field_value.split(';') if v.strip()]
                    for value in values:
                        error = _validate_name_format(value)
                        if error:
                            results.append({
                                "issue_url": html_url,
                                "row_number": row_num,
                                "error_type": "name_format_invalid",
                                "field": field,
                                "value": _truncate_value(value),
                                "message": error,
                            })

        return results
