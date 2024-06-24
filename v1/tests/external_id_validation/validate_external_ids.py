import os
import json
import re
import csv
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Process JSON files and log non-conforming values.")
    parser.add_argument("-d", "--input_directory",
                        help="Path to the input directory containing JSON files.")
    parser.add_argument("-o", "--output_csv", default="external_id_validation_report.csv",
                        help="Path to the output CSV file for logging non-conforming values.")
    return parser.parse_args()


def validate_data(json_data):
    non_conforming_values = []
    id = json_data.get("id", "")
    name = json_data.get("name", "")
    regex_patterns = {
        "ISNI": r"[0]{4} [0-9]{4} [0-9]{4} [0-9]{3}[0-9X]",
        "Wikidata": r"Q[1-9]\d*",
        "FundRef": r"[1-9]\d+"
    }
    external_ids = json_data.get("external_ids", {})
    for field, values in external_ids.items():
        if field in regex_patterns:
            pattern = regex_patterns[field]
            for key in ['preferred', 'all']:
                value_list = values.get(key, [])
                if not isinstance(value_list, list):
                    value_list = [value_list]
                for value in value_list:
                    if value and not re.match(pattern, value):
                        non_conforming_values.append((id, name, field, value))
    return non_conforming_values


def process_directory(directory, output_csv):
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(["ID", "Name", "Field", "Non-Conforming Value"])
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.json'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as json_file:
                            json_data = json.load(json_file)
                            non_conforming_values = validate_data(json_data)
                            for value in non_conforming_values:
                                csv_writer.writerow(value)
                    except Exception as e:
                        print(f"Error processing file {file_path}: {e}")


def main():
    args = parse_args()
    process_directory(args.input_directory, args.output_csv)


if __name__ == "__main__":
    main()
