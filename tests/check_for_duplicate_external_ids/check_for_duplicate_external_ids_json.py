import os
import csv
import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description='Find matches between JSON files and an aggregate file.')
    parser.add_argument(
        '-i', '--input_directory', help='Directory containing the JSON files.', required=True)
    parser.add_argument('-d', '--data_dump',
                        help='Path to the aggregate JSON file.', required=True)
    parser.add_argument('-o', '--output_file', default='duplicate_external_ids.csv',
                        help='Path to the output CSV file.')
    return parser.parse_args()


def load_data_dump(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def process_json_files(input_directory, data_dump_records):
    matches = []
    for filename in os.listdir(input_directory):
        if filename.endswith('.json'):
            file_path = os.path.join(input_directory, filename)
            with open(file_path, 'r') as file:
                record = json.load(file)
                match = find_matches(record, data_dump_records)
                if match:
                    matches.extend(match)
    return matches


def extract_external_ids(record):
    external_ids = set()
    if isinstance(record.get('external_ids'), list):
        for external_id in record['external_ids']:
            external_ids.update(external_id.get('all', []))
            if external_id.get('preferred'):
                external_ids.add(external_id['preferred'])
    elif isinstance(record.get('external_ids'), str):
        external_ids.add(record['external_ids'])
    return external_ids


def find_matches(record, data_dump_records):
    record_external_ids = extract_external_ids(record)
    matches = []
    for data_dump_record in data_dump_records:
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
    with open(output_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)


def main():
    args = parse_args()
    data_dump_records = load_data_dump(args.data_dump)
    matches = process_json_files(args.input_directory, data_dump_records)
    write_matches_to_csv(matches, args.output_file)


if __name__ == '__main__':
    main()
