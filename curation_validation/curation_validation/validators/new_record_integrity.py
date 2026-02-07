import json
import re
from urllib.parse import unquote

from curation_validation.validators.base import BaseValidator, ValidatorContext
from curation_validation.core.io import read_csv
from curation_validation.core.json_utils import simplify_json
from curation_validation.core.normalize import normalize_wikipedia_url

ROR_DATA_FIELDS = [
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


def _check_value(value, field, simplified_json, ror_id, findings):
    if value not in simplified_json[field] and value in simplified_json['all']:
        findings.append({
            'id': ror_id,
            'type': 'transposition',
            'field': field,
            'value': value,
        })
    if value not in simplified_json['all']:
        findings.append({
            'id': ror_id,
            'type': 'missing',
            'field': field,
            'value': value,
        })


def check_record_integrity(row, simplified_json):
    findings = []
    ror_id = row['id']

    for field in ROR_DATA_FIELDS:
        if not row.get(field):
            continue

        field_value = unquote(row[field]).strip()

        if field == 'links.type.wikipedia':
            field_value = normalize_wikipedia_url(field_value)

        if field in ['established', 'locations.geonames_id'] and ';' not in field_value:
            field_value = int(field_value)

        if not isinstance(field_value, int):
            if ';' in field_value:
                values = field_value.split(';')
                values = [v.split('*')[0].strip() for v in values]
                if field == 'links.type.wikipedia':
                    values = [normalize_wikipedia_url(v) for v in values]
                for value in values:
                    if field == 'locations.geonames_id':
                        value = int(value)
                    _check_value(value, field, simplified_json, ror_id, findings)
            else:
                field_value = field_value.split('*')[0].strip()
                _check_value(field_value, field, simplified_json, ror_id, findings)
        else:
            _check_value(field_value, field, simplified_json, ror_id, findings)

    return findings


class NewRecordIntegrityValidator(BaseValidator):
    name = "new-record-integrity"
    supported_formats = {"csv_json"}
    output_filename = "new_record_integrity.csv"
    output_fields = ["id", "type", "field", "value"]
    requires_data_source = False
    requires_geonames = False

    def run(self, ctx: ValidatorContext) -> list[dict]:
        rows = read_csv(ctx.csv_file)
        findings = []

        for row in rows:
            ror_id = row['id']
            ror_id_file_prefix = re.sub('https://ror.org/', '', ror_id)
            json_file_path = ctx.json_dir / f'{ror_id_file_prefix}.json'

            with open(json_file_path, 'r', encoding='utf8') as f:
                json_data = json.load(f)

            simplified_json = simplify_json(json_data)
            findings.extend(check_record_integrity(row, simplified_json))

        return findings
