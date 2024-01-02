import csv
import logging
import argparse
from language_detection import detect_language

logging.basicConfig(filename='corrections.log',
                    filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def read_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        return list(csv.DictReader(file))


def parse_new_records(data, field):
    values = data.get(field, "")
    if values:
        if field in ["aliases", "labels"]:
            values = [val.strip() for val in values.split(';') if val.strip()]
            if field == "labels":
                values = [remove_language_tags(val) for val in values]
        else:
            values = [values.strip()]
        return values
    return []


def parse_update_field(update_field):
    extracted_values = []
    updates = update_field.split(';')
    for update in updates:
        if update.startswith('delete'):
            continue
        parts = update.split('==')
        if len(parts) == 2:
            change_type, field_value = parts
            if any(substring in change_type for substring in ['name', 'aliases', 'labels']):
                extracted_values.append(field_value.strip())
    return extracted_values


def process_row(record, writer, file_type, high_precision=True):
    all_names = []
    if file_type == 'updates':
        all_names.extend(parse_update_field(
            record.get('update_field', '')))
    else:
        for field in ['name', 'aliases', 'labels']:
            all_names.extend(parse_new_records(record, field))
    no_language_names = [name for name in all_names if '*' not in name]
    for name in all_names:
        try:
            detected_language = detect_language(name, high_precision)
            if detected_language:
                writer.writerow({
                    'html_url': record['html_url'],
                    'name': name,
                    'detected_language': detected_language,
                    'name_w_lang': f'{name}*{detected_language}'
                })
        except Exception as e:
            logging.error(f'Unexpected error processing record for {name}: {e}')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Process a CSV file for organization name corrections.')
    parser.add_argument('-i', '--input', type=str,
                        help='Input CSV file path', required=True)
    parser.add_argument('-o', '--output', type=str,
                        help='Output CSV file path', default='detected_langauges.csv')
    parser.add_argument('-f', '--file-type', type=str, choices=['new', 'updates'],
                        help='Type of the input file', required=True)
    parser.add_argument('-p', '--high-precision', type=bool, choices=[True, False],
                        help='Use high precision language detection. True or False. Default is True', default=True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    input_file = args.input
    output_file = args.output
    file_type = args.file_type
    records = read_csv(input_file)
    with open(output_file, mode='w', encoding='utf-8') as file:
        writer = csv.DictWriter(
            file, fieldnames=['html_url', 'name','detected_language', 'name_w_lang'])
        writer.writeheader()
        for record in records:
            process_row(record, writer, file_type)


if __name__ == '__main__':
    main()
