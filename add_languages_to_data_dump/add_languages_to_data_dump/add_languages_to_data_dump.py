import csv
import json
import argparse


def parse_csv(file_path):
    csv_data = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            id = row['id']
            name = row['name']
            lang = row['lang']
            if id not in csv_data:
                csv_data[id] = []
            csv_data[id].append((name, lang))
    return csv_data


def parse_json(file_path):
    with open(file_path, 'r') as file:
        data_dump = json.load(file)
    return data_dump


def update_json_records(data_dump, csv_data):
    for record in data_dump:
        record_id = record['id']
        if record_id in csv_data:
            for name_obj in record['names']:
                for name, lang in csv_data[record_id]:
                    if name_obj['value'] == name:
                        name_obj['lang'] = lang
    return data_dump


def save_json(file_path, data_dump):
    with open(file_path, 'w') as file:
        json.dump(data_dump, file, indent=4)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Update JSON records with language information from CSV.')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Path to the input CSV file')
    parser.add_argument('-d', '--data_dump_file',
                        required=True, help='Path to the input JSON file')
    parser.add_argument('-o', '--output_file', default='dump_w_languages_added.json',
                        help='Path to the output JSON file')
    return parser.parse_args()


def main():
    args = parse_args()
    csv_data = parse_csv(args.input_file)
    data_dump = parse_json(args.data_dump_file)
    updated_data_dump = update_json_records(data_dump, csv_data)
    save_json(args.output_file, updated_data_dump)
    print(f'Updated JSON records saved to {args.output_file}')


if __name__ == '__main__':
    main()
