import os
import csv
import argparse
import glob
import json


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def get_all_names_ror_ids(input_dir, output_file):
    with open(output_file, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['name', 'id'])

        for file in glob.glob(os.path.join(input_dir, "*.json")):
            with open(file, 'r+', encoding='utf8') as f_in:
                record = json.load(f_in)
                ror_id = record['id']
                name = get_ror_display_name(record)
                writer.writerow([name, ror_id])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract names and ROR IDs from JSON files.')
    parser.add_argument('-i', '--input_dir', type=str, required=True,
                        help='Input directory containing JSON files')
    parser.add_argument('-o', '--output_file', type=str, default='all_names_ror_ids.csv',
                        help='Output CSV file (default: all_names_ror_ids.csv)')
    return parser.parse_args()


def main():
    args = parse_arguments()
    get_all_names_ror_ids(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
