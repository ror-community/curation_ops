import os
import re
import json
import csv
import argparse
from datetime import datetime


def parse_json(file_path):
    with open(file_path, 'r') as file:
        data_dump = json.load(file)
    return data_dump


def save_individual_json(directory, record):
    record_id = record['id']
    file_prefix = re.sub('https://ror.org/', '', record_id)
    file_name = f'{file_prefix}.json'
    file_path = os.path.join(directory, file_name)
    with open(file_path, 'w') as file:
        json.dump(record, file, indent=4, ensure_ascii=False)


def update_last_mod(record, date):
    record['admin']['last_modified']['date'] = date


def update_json_records(data_dump, updates_dir, date, record_ids):
    for record in data_dump:
        if record['id'] in record_ids:
            update_last_mod(record, date)
            save_individual_json(updates_dir, record)
    return data_dump


def parse_csv(file_path):
    record_ids = set()
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            record_ids.add(row['id'])
    return record_ids


def save_json(file_path, data_dump):
    with open(file_path, 'w') as file:
        json.dump(data_dump, file, indent=4, ensure_ascii=False)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Update JSON records with the specified last_modified date.')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Path to the input CSV file containing record IDs')
    parser.add_argument('-d', '--data_dump_file',
                        required=True, help='Path to the input JSON file')
    parser.add_argument('-o', '--output_file', required=True,
                        help='Path to the output JSON file')
    parser.add_argument('-u', '--updates_dir', default='updates',
                        help='Directory to save individual JSON files')
    parser.add_argument('-t', '--date', required=True,
                        help='Date to update the last_modified field (YYYY-MM-DD)')
    return parser.parse_args()


def validate_date(date_string):
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_string}. Expected format: YYYY-MM-DD")


def main():
    args = parse_args()
    validate_date(args.date)
    record_ids = parse_csv(args.input_file)
    data_dump = parse_json(args.data_dump_file)
    os.makedirs(args.updates_dir, exist_ok=True)
    updated_data_dump = update_json_records(
        data_dump, args.updates_dir, args.date, record_ids)
    save_json(args.output_file, updated_data_dump)
    print(f'Updated JSON records saved to {args.output_file}')
    print(f'Individual JSON files saved in {args.updates_dir} directory')


if __name__ == '__main__':
    main()
