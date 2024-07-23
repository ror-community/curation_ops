import json
import csv
import argparse
from detect_language_r1 import load_common_languages, detect_language, detect_language_fasttext, detect_language_lingua


def parse_args():
    parser = argparse.ArgumentParser(
        description='Parse JSON and detect language')
    parser.add_argument('-i', '--input', required=True,
                        help='Path to the input JSON file')
    parser.add_argument('-l', '--language_file', required=True,
                        help='Path to the input JSON file')
    parser.add_argument('-o', '--output', default='tagged_languages.csv',
                        help='Path to the output CSV file')
    return parser.parse_args()


def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def process_records(records, most_common_languages, output_file):
    csv_writer = csv.writer(output_file)
    csv_writer.writerow(['id', 'name', 'lang', 'fasttext_langs',
                         'fasttext_scores', 'lingua_langs', 'lingua_scores', 'country_code'])
    for record in records:
        record_id = record['id']
        country_code = record['locations'][0]['geonames_details']['country_code']
        for name_obj in record['names']:
            if not name_obj['lang'] and 'acronym' not in name_obj['types']:
                name = name_obj['value']
                lang_predictions_fasttext = detect_language_fasttext(name)
                lang_predictions_lingua = detect_language_lingua(name)
                if lang_predictions_fasttext or lang_predictions_lingua:
                    selected_lang = detect_language(
                        name, country_code, most_common_languages)
                    if selected_lang:
                        fasttext_langs = ';'.join(
                            [lang for lang, _ in lang_predictions_fasttext]) if lang_predictions_fasttext else ''
                        fasttext_scores = ';'.join([f"{score:.2f}" for _, score in lang_predictions_fasttext]) if lang_predictions_fasttext else ''
                        lingua_langs = ';'.join(
                            [lang for lang, _ in lang_predictions_lingua]) if lang_predictions_lingua else ''
                        lingua_scores = ';'.join([f"{score:.2f}" for _, score in lang_predictions_lingua]) if lang_predictions_lingua else ''
                        row = [record_id, name, selected_lang, fasttext_langs,
                               fasttext_scores, lingua_langs, lingua_scores, country_code]
                        csv_writer.writerow(row)


def main():
    args = parse_args()
    input_file = args.input
    output_file_path = args.output
    most_common_languages = load_common_languages(args.language_file)

    try:
        json_data = load_json(input_file)
        with open(output_file_path, 'w') as output_file:
            process_records(json_data, most_common_languages, output_file)
        print(f'Processed {input_file}. Results written to {output_file_path}')
    except FileNotFoundError:
        print(f'Input file {input_file} not found')
    except json.JSONDecodeError:
        print(f'Invalid JSON format in {input_file}')
    except Exception as e:
        print(f'An error occurred: {str(e)}')


if __name__ == '__main__':
    main()
