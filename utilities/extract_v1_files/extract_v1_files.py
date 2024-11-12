import json
import os
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract records based on matching ROR IDs")
    parser.add_argument("-d", "--data_dump", required=True,
                        help="Path to the input JSON file")
    parser.add_argument(
        "-r", "--release_directory", required=True, help="Path to the directory containing ROR ID files")
    parser.add_argument("-o", "--output_directory", default="extracted_files",
                        help="Path to the output directory for extracted records")
    return parser.parse_args()


def read_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file {file_path}")
        return None
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return None


def list_directory_files(directory_path):
    try:
        return [f for f in os.listdir(directory_path) if f.endswith('.json')]
    except FileNotFoundError:
        print(f"Error: Directory not found - {directory_path}")
        return []


def extract_ror_ids_from_filenames(file_list):
    return set(f.split('.')[0] for f in file_list)


def extract_matching_records(json_data, ror_ids):
    return [record for record in json_data if record.get('id', '').split('/')[-1] in ror_ids]


def save_records_to_output(matched_records, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for record in matched_records:
        ror_id = record['id'].split('/')[-1]
        output_file = os.path.join(output_dir, f"{ror_id}.json")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            print(f"Saved: {ror_id}.json")
        except IOError as e:
            print(f"Error saving {ror_id}.json: {e}")


def main():
    args = parse_arguments()
    json_data = read_json_file(args.data_dump)
    if json_data is None:
        return
    id_files = list_directory_files(args.release_directory)
    if not id_files:
        return
    ror_ids = extract_ror_ids_from_filenames(id_files)
    matched_records = extract_matching_records(json_data, ror_ids)
    save_records_to_output(matched_records, args.output_directory)
    print(f"Extraction complete. {len(matched_records)} records saved to {args.output_directory}")


if __name__ == "__main__":
    main()
