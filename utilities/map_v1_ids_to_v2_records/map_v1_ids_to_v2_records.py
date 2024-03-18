import os
import re
import json
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description='ROR ID Mapping Tool')
    parser.add_argument('-v1', '--v1_directory', required=True,
                        help='Directory containing v1 JSON files')
    parser.add_argument('-v2', '--v2_directory', required=True,
                        help='Directory containing v2 JSON files')
    parser.add_argument('-o', '--output_directory', default='mapped_files',
                        help='Directory to save mapped JSON files')
    return parser.parse_args()


def read_json_files(directory):
    json_data = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            with open(filepath, 'r') as file:
                try:
                    json_data[filename] = json.load(file)
                except json.JSONDecodeError as e:
                    print(f'Error parsing JSON file: {filename}. Error: {str(e)}')
    return json_data


def map_ids(v1_data, v2_data):
    mapped_data = {}
    for v1_filename, v1_obj in v1_data.items():
        for v2_filename, v2_obj in v2_data.items():
            if (v1_obj.get('name') == v2_obj.get('names', [{}])[0].get('value')
                    and v1_obj.get('links', [None])[0] == next((link['value'] for link in v2_obj.get('links', []) if link.get('type') == 'website'), None)
                    and v1_obj.get('addresses', [{}])[0].get('geonames_city', {}).get('id') == v2_obj.get('locations', [{}])[0].get('geonames_id')):
                v2_obj['id'] = v1_obj['id']
                mapped_data[v1_obj['id']] = v2_obj
                break
    return mapped_data


def save_mapped_files(mapped_data, output_directory):
    os.makedirs(output_directory, exist_ok=True)
    for ror_id, mapped_obj in mapped_data.items():
        v1_filename = re.sub('https://ror.org/', '', ror_id)
        output_filename = f"{v1_filename}.json"
        output_filepath = os.path.join(output_directory, output_filename)
        with open(output_filepath, 'w') as file:
            json.dump(mapped_obj, file, indent=2)


def log_failed_mappings(v1_data, mapped_ids):
    v1_filenames = set(v1_data.keys())
    mapped_filenames = set(re.sub('https://ror.org/', '', mapped_id) + '.json' for mapped_id in mapped_ids)
    unmapped_files = v1_filenames - mapped_filenames
    if unmapped_files:
        print('Failed to map the following files:')
        for filename in unmapped_files:
            print(filename)
    else:
        print('All files mapped successfully.')


def main():
    args = parse_arguments()
    v1_data = read_json_files(args.v1_directory)
    v2_data = read_json_files(args.v2_directory)
    mapped_data = map_ids(v1_data, v2_data)
    save_mapped_files(mapped_data, args.output_directory)
    log_failed_mappings(v1_data, mapped_data.keys())


if __name__ == '__main__':
    main()
