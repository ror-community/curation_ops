import csv
import json
import argparse
import re


def parse_args():
    parser = argparse.ArgumentParser(
        description='Find matches between a CSV file and an aggregate file.')
    parser.add_argument(
        '-i', '--input_csv', help='Path to the input CSV file.', required=True)
    parser.add_argument('-d', '--data_dump',
                        help='Path to the aggregate JSON file.', required=True)
    parser.add_argument('-o', '--output_file', default='duplicate_external_ids.csv',
                        help='Path to the output CSV file.')
    return parser.parse_args()


def load_data_dump(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def normalize_whitespace(text):
    return re.sub(r'\s+', ' ', text.strip())


def process_input_csv(input_csv_path):
    records = []
    with open(input_csv_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            record = {
                'id': row['id'],
                'names': [{'types': ['ror_display'], 'value': row['names.types.ror_display']}],
                'external_ids': []
            }
            for id_type in ['fundref', 'grid', 'isni', 'wikidata']:
                all_ids = row.get(f'external_ids.type.{id_type}.all', '')
                preferred_id = row.get(f'external_ids.type.{id_type}.preferred', '')
                if all_ids or preferred_id:
                    record['external_ids'].append({
                        'all': [normalize_whitespace(id) for id in all_ids.split(';') if id.strip()],
                        'preferred': normalize_whitespace(preferred_id) if preferred_id else '',
                        'type': id_type
                    })
            records.append(record)
    return records


def extract_external_ids(record):
    external_ids = set()
    for id_obj in record['external_ids']:
        external_ids.update(id_obj.get('all', []))
        if id_obj.get('preferred'):
            external_ids.add(id_obj['preferred'])
    return external_ids


def normalize_data_dump_external_ids(data_dump_records):
    for record in data_dump_records:
        for id_obj in record['external_ids']:
            id_obj['all'] = [normalize_whitespace(
                id) for id in id_obj.get('all', [])]
            if id_obj.get('preferred'):
                id_obj['preferred'] = normalize_whitespace(id_obj['preferred'])
    return data_dump_records


def find_matches(records, data_dump_records):
    matches = []
    normalized_data_dump_records = normalize_data_dump_external_ids(
        data_dump_records)
    for record in records:
        record_external_ids = extract_external_ids(record)
        for data_dump_record in normalized_data_dump_records:
            data_dump_external_ids = extract_external_ids(data_dump_record)
            common_external_ids = record_external_ids.intersection(
                data_dump_external_ids)
            if common_external_ids:
                ror_display_name = next(
                    (name['value'] for name in record['names'] if 'ror_display' in name['types']), '')
                data_dump_ror_display_name = next(
                    (name['value'] for name in data_dump_record['names'] if 'ror_display' in name['types']), '')
                for external_id in common_external_ids:
                    matches.append({
                        'id': record['id'],
                        'ror_display_name': ror_display_name,
                        'data_dump_id': data_dump_record['id'],
                        'data_dump_ror_display_name': data_dump_ror_display_name,
                        'overlapping_external_id': external_id
                    })
    return matches


def write_matches_to_csv(matches, output_file):
    fieldnames = ['id', 'ror_display_name', 'data_dump_id',
                  'data_dump_ror_display_name', 'overlapping_external_id']
    with open(output_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)


def main():
    args = parse_args()
    data_dump_records = load_data_dump(args.data_dump)
    csv_records = process_input_csv(args.input_csv)
    matches = find_matches(csv_records, data_dump_records)
    write_matches_to_csv(matches, args.output_file)


if __name__ == '__main__':
    main()
