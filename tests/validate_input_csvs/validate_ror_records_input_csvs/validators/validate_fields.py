from validate_ror_records_input_csvs.core.io import read_csv, detect_file_type
from validate_ror_records_input_csvs.core.patterns import (
    ACRONYMS_PATTERN,
    NAMES_PATTERN,
    URL_PATTERN,
    WIKIPEDIA_URL_PATTERN,
    ISNI_PATTERN,
    WIKIDATA_PATTERN,
    FUNDREF_PATTERN,
    GEONAMES_PATTERN,
    VALID_STATUSES,
    VALID_TYPES,
)
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


def validate_status(field_value: str) -> list[str]:
    if field_value and field_value in VALID_STATUSES:
        return []
    return [f"Error in 'status': Invalid value - {field_value}. Valid values are: {list(VALID_STATUSES)}"]


def validate_types(field_value: str) -> list[str]:
    type_value = field_value.split('(')[0].strip().lower()
    if type_value and type_value in VALID_TYPES:
        return []
    return [f"Error in 'types': Invalid value(s). Valid values are: {list(VALID_TYPES)}"]


def validate_acronyms(field_value: str) -> list[str]:
    acronym_part = field_value.split('*')[0]
    if field_value == "delete":
        return []
    if acronym_part and ACRONYMS_PATTERN.match(acronym_part):
        return []
    return [f"Warning in '{field_value}': Potential invalid value(s) - {field_value}. Expected format: uppercase letters, numbers, and spaces"]


def validate_names(field_value: str) -> list[str]:
    if field_value == "delete":
        return []
    if field_value and NAMES_PATTERN.match(field_value):
        return []
    return [f"Warning in '{field_value}': Expected format: Include language tagging - 'name*language'"]


def validate_links(field_value: str) -> list[str]:
    if field_value == "delete":
        return []
    if field_value and URL_PATTERN.match(field_value):
        return []
    return [f"Error in 'links': Invalid URL(s) - {field_value}. Expected format: 'http://' or 'https://' followed by the address"]


def validate_established(field_value: str) -> list[str]:
    try:
        year = int(field_value)
        if 1000 <= year <= 9999:
            return []
        else:
            return ["Error in 'established': Not a 4-digit year"]
    except ValueError:
        return [f"Error in 'established': {field_value} is not a valid year format. Expected a 4-digit year"]


def validate_wikipedia_url(field_value: str) -> list[str]:
    if field_value and WIKIPEDIA_URL_PATTERN.match(field_value):
        return []
    return [f"Error in 'wikipedia_url': Invalid Wikipedia URL - {field_value}. Expected format: 'http://[language_code].wikipedia.org/'"]


def validate_isni(field_value: str) -> list[str]:
    if field_value and ISNI_PATTERN.match(field_value):
        return []
    return [f"Error in 'ISNI': Invalid ISNI value(s) - {field_value}. Expected format: '[0]{{4}} [0-9]{{4}} [0-9]{{4}} [0-9]{{3}}[0-9X]' or 'delete'"]


def validate_wikidata(field_value: str) -> list[str]:
    if field_value and WIKIDATA_PATTERN.match(field_value):
        return []
    return [f"Error in 'Wikidata': Invalid Wikidata ID(s) - {field_value}. Expected format: 'Q[1-9]\\d*' or 'delete'"]


def validate_fundref(field_value: str) -> list[str]:
    if field_value and FUNDREF_PATTERN.match(field_value):
        return []
    return [f"Error in 'FundRef': Invalid FundRef ID(s) - {field_value}. Expected format: '[1-9]\\d+' or 'delete'"]


def validate_geonames(field_value: str) -> list[str]:
    if field_value and GEONAMES_PATTERN.match(field_value):
        return []
    return [f"Error in 'Geonames ID': Invalid or Null Geonames ID(s) - {field_value}. Expected format: '[1-9]\\d+'"]


def validate_city(field_value: str) -> list[str]:
    if field_value:
        return []
    return ["Warning in 'city': no city in record"]


def validate_country(field_value: str) -> list[str]:
    if field_value:
        return []
    return ["Warning in 'country': no country in record"]


FIELD_VALIDATORS = {
    'types': [validate_types],
    'status': [validate_status],
    'names.types.acronym': [validate_acronyms, validate_names],
    'names.types.alias': [validate_names],
    'names.types.label': [validate_names],
    'names.types.ror_display': [validate_names],
    'links.type.website': [validate_links],
    'established': [validate_established],
    'links.type.wikipedia': [validate_wikipedia_url],
    'external_ids.type.isni.preferred': [validate_isni],
    'external_ids.type.isni.all': [validate_isni],
    'external_ids.type.wikidata.preferred': [validate_wikidata],
    'external_ids.type.wikidata.all': [validate_wikidata],
    'external_ids.type.fundref.preferred': [validate_fundref],
    'external_ids.type.fundref.all': [validate_fundref],
    'geonames': [validate_geonames],
    'locations.geonames_id': [validate_geonames],
    'city': [validate_city],
    'country': [validate_country],
}


def validate_field_value(field_name: str, field_value: str) -> list[str]:
    if field_name not in FIELD_VALIDATORS:
        return []

    for validation_function in FIELD_VALIDATORS[field_name]:
        errors = validation_function(field_value)
        if errors:
            return errors
    return []


def parse_update_field(update_str: str) -> dict[str, list[str]]:
    updates = {}
    parts = update_str.split(';')
    for part in parts:
        subparts = part.split('==', 1)
        if len(subparts) == 2:
            change_type, value = subparts[0].strip(), subparts[1].strip()
            if change_type in updates:
                updates[change_type].append(value)
            else:
                updates[change_type] = [value]
        else:
            updates.setdefault('replace', []).append(subparts[0].strip())
    return updates


def validate_updates(row: dict) -> tuple[list[str], list[tuple[str, str]]]:
    valid_fields = [
        'status',
        'types',
        'names.types.acronym',
        'names.types.alias',
        'names.types.label',
        'names.types.ror_display',
        'links.type.website',
        'established',
        'links.type.wikipedia',
        'external_ids.type.isni.preferred',
        'external_ids.type.isni.all',
        'external_ids.type.wikidata.preferred',
        'external_ids.type.wikidata.all',
        'external_ids.type.fundref.preferred',
        'external_ids.type.fundref.all',
        'locations.geonames_id',
    ]

    errors = []
    field_value_pairs = []

    for field, update_str in row.items():
        if not update_str:
            continue
        updates = parse_update_field(update_str)
        if field in valid_fields:
            for change_type, values in updates.items():
                if change_type not in ['add', 'delete', 'replace']:
                    errors.append(
                        f"Invalid change type: '{change_type}' in field '{field}'. "
                        f"Valid types are: ['add', 'delete', 'replace']."
                    )
                    continue
                for value in values:
                    if value:
                        if change_type == 'delete':
                            continue
                        field_value_pairs.append((field, value))

    return errors, field_value_pairs


class ValidateFieldsValidator(BaseValidator):
    name = "validate-fields"
    output_filename = "validation_report.csv"
    output_fields = ["html_url", "ror_id", "error_warning"]
    requires_data_source = False
    requires_geonames = False

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)
        file_type = detect_file_type(records)

        if file_type == 'new':
            return self._validate_new_records(records)
        else:
            return self._validate_update_records(records)

    def _validate_new_records(self, records: list[dict]) -> list[dict]:
        validation_report = []

        for row in records:
            html_url = row.get('html_url', '')
            ror_id = row.get('id', '')

            for field_name, field_value in row.items():
                if field_name in ['city', 'country']:
                    values = [field_value]
                elif field_name == 'locations.geonames_id' and not field_value:
                    field_value = 'null'
                    values = [field_value]
                else:
                    values = field_value.split(';') if field_value else []

                for value in values:
                    value = value.strip()
                    if not value and field_name not in ['city', 'country']:
                        continue
                    errors = validate_field_value(field_name, value)
                    for error in errors:
                        validation_report.append({
                            'html_url': html_url,
                            'ror_id': ror_id,
                            'error_warning': error,
                        })

        return validation_report

    def _validate_update_records(self, records: list[dict]) -> list[dict]:
        validation_report = []

        for row in records:
            html_url = row.get('html_url', '')
            ror_id = row.get('id', '')

            update_errors, field_value_pairs = validate_updates(row)

            for error in update_errors:
                validation_report.append({
                    'html_url': html_url,
                    'ror_id': ror_id,
                    'error_warning': error,
                })

            for field_name, field_value in field_value_pairs:
                errors = validate_field_value(field_name, field_value)
                for error in errors:
                    validation_report.append({
                        'html_url': html_url,
                        'ror_id': ror_id,
                        'error_warning': error,
                    })

        return validation_report
