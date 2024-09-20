import io
import os
import csv
import json
import zipfile
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Parse ROR JSON data to CSV")
    parser.add_argument("-i", "--input_file",
                        help="Path to input to the data dump ZIP or ROR schema v2 JSON file", required=True)
    parser.add_argument("-o", "--output_file", help="Path to output CSV file")
    args = parser.parse_args()
    return args


def get_json_data(input_file):
    if input_file.endswith('.zip'):
        with zipfile.ZipFile(input_file, 'r') as zip_ref:
            json_files = [f for f in zip_ref.namelist(
            ) if f.endswith('_schema_v2.json')]
            if not json_files:
                raise ValueError(
                    "No '_schema_v2.json' file found in the ZIP archive")
            with zip_ref.open(json_files[0]) as json_file:
                return json.load(json_file)
    elif input_file.endswith('.json'):
        with open(input_file, 'r', encoding="utf8") as json_file:
            return json.load(json_file)
    else:
        raise ValueError("Input file must be either a ZIP file or a JSON file")


def process_ror_data(json_data, output_file):
    headers = ["ROR Display Name", "ROR ID", "Name", "Name Type"]
    try:
        with open(output_file, 'w', newline='', encoding="utf8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            for ror_object in json_data:
                ror_display_name = next(
                    (name['value'] for name in ror_object['names'] if 'ror_display' in name['types']), None)
                ror_id = ror_object['id']
                for name in ror_object['names']:
                    for name_type in name['types']:
                        writer.writerow({
                            "ROR Display Name": ror_display_name,
                            "ROR ID": ror_id,
                            "Name": name['value'],
                            "Name Type": name_type
                        })
    except IOError as e:
        print(f"Error: I/O error occurred: {str(e)}")
        exit(1)


def main():
    args = parse_arguments()
    if not args.output_file:
        input_base = os.path.splitext(os.path.basename(args.input_file))[0]
        args.output_file = f"{input_base}_all_names.csv"
    try:
        json_data = get_json_data(args.input_file)
        process_ror_data(json_data, args.output_file)
        print(f"CSV file has been created: {args.output_file}")
    except ValueError as e:
        print(f"Error: {str(e)}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {args.input_file}")
        exit(1)


if __name__ == "__main__":
    main()
