import re
from multiprocessing import Pool, cpu_count

from validate_ror_records_input_csvs.core.io import read_csv
from validate_ror_records_input_csvs.validators.base import BaseValidator, ValidatorContext


def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip())


def process_input_csv(records: list[dict]) -> list[dict]:
    processed_records = []

    for row in records:
        record = {
            'id': row.get('id', ''),
            'names': [{'types': ['ror_display'], 'value': row.get('names.types.ror_display', '')}],
            'external_ids': []
        }

        for id_type in ['fundref', 'grid', 'isni', 'wikidata']:
            all_ids = row.get(f'external_ids.type.{id_type}.all', '')
            preferred_id = row.get(f'external_ids.type.{id_type}.preferred', '')

            if all_ids or preferred_id:
                record['external_ids'].append({
                    'all': [normalize_whitespace(id_val) for id_val in all_ids.split(';') if id_val.strip()],
                    'preferred': normalize_whitespace(preferred_id) if preferred_id else '',
                    'type': id_type
                })

        processed_records.append(record)

    return processed_records


def extract_external_ids(record: dict) -> set[str]:
    external_ids = set()

    for id_obj in record.get('external_ids', []):
        external_ids.update(id_obj.get('all', []))
        if id_obj.get('preferred'):
            external_ids.add(id_obj['preferred'])

    return external_ids


def normalize_data_dump_external_ids(records: list[dict]) -> list[dict]:
    for record in records:
        for id_obj in record.get('external_ids', []):
            id_obj['all'] = [normalize_whitespace(id_val) for id_val in id_obj.get('all', [])]
            if id_obj.get('preferred'):
                id_obj['preferred'] = normalize_whitespace(id_obj['preferred'])

    return records


def get_ror_display_name(record: dict) -> str:
    for name in record.get('names', []):
        if 'ror_display' in name.get('types', []):
            return name.get('value', '')
    return ''


def _find_matches_for_csv_record(args: tuple) -> list[dict]:
    csv_record, data_dump_records = args
    matches = []

    csv_external_ids = extract_external_ids(csv_record)
    if not csv_external_ids:
        return matches

    csv_ror_display_name = get_ror_display_name(csv_record)

    for data_dump_record in data_dump_records:
        data_dump_external_ids = extract_external_ids(data_dump_record)
        common_ids = csv_external_ids.intersection(data_dump_external_ids)

        if common_ids:
            data_dump_ror_display_name = get_ror_display_name(data_dump_record)

            for external_id in common_ids:
                matches.append({
                    'id': csv_record.get('id', ''),
                    'ror_display_name': csv_ror_display_name,
                    'data_dump_id': data_dump_record.get('id', ''),
                    'data_dump_ror_display_name': data_dump_ror_display_name,
                    'overlapping_external_id': external_id
                })

    return matches


def find_matches(csv_records: list[dict], data_dump_records: list[dict]) -> list[dict]:
    normalized_data_dump = normalize_data_dump_external_ids(data_dump_records)

    if len(csv_records) <= 10 or len(data_dump_records) <= 100:
        matches = []
        for csv_record in csv_records:
            matches.extend(_find_matches_for_csv_record((csv_record, normalized_data_dump)))
        return matches

    args_list = [(csv_record, normalized_data_dump) for csv_record in csv_records]

    num_processes = min(cpu_count(), len(csv_records))
    with Pool(processes=num_processes) as pool:
        results = pool.map(_find_matches_for_csv_record, args_list)

    matches = []
    for result in results:
        matches.extend(result)

    return matches


class DuplicateExternalIdsValidator(BaseValidator):
    name = "duplicate-external-ids"
    output_filename = "duplicate_external_ids.csv"
    output_fields = [
        "id",
        "ror_display_name",
        "data_dump_id",
        "data_dump_ror_display_name",
        "overlapping_external_id"
    ]
    requires_data_source = True
    requires_geonames = False
    new_records_only = True

    def run(self, ctx: ValidatorContext) -> list[dict]:
        records = read_csv(ctx.input_file)
        csv_records = process_input_csv(records)
        data_dump_records = ctx.data_source.get_all_records()
        matches = find_matches(csv_records, data_dump_records)

        return matches
