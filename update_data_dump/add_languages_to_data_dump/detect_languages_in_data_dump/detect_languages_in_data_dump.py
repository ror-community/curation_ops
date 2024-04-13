import json
import csv
import argparse
from detect_language import detect_language


def parse_args():
    parser = argparse.ArgumentParser(
        description='Parse JSON and detect language')
    parser.add_argument('-i', '--input', required=True,
                        help='Path to the input JSON file')
    parser.add_argument('-o', '--output', default='tagged_languages.csv',
                        help='Path to the output CSV file')
    return parser.parse_args()


def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def process_records(records, output_file):
    csv_writer = csv.writer(output_file)
    csv_writer.writerow(['id', 'name', 'lang', 'country_code'])
    for record in records:
        record_id = record['id']
        country_code = record['locations'][0]['geonames_details']['country_code']
        for name_obj in record['names']:
            if not name_obj['lang'] and 'acronym' not in name_obj['types']:
                name = name_obj['value']
                lang = detect_language(name)
                if lang:
                    csv_writer.writerow([record_id, name, lang, country_code])


def main():
    args = parse_args()
    input_file = args.input
    output_file_path = args.output
    try:
        json_data = load_json(input_file)
        with open(output_file_path, 'w', newline='') as output_file:
            process_records(json_data, output_file)
        print(f'Processed {input_file}. Results written to {output_file_path}')
    except FileNotFoundError:
        print(f'Input file {input_file} not found')
    except json.JSONDecodeError:
        print(f'Invalid JSON format in {input_file}')
    except Exception as e:
        print(f'An error occurred: {str(e)}')


if __name__ == '__main__':
    main()
