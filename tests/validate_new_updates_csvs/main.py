import argparse
from file_utils import read_csv, write_report
from validation_utils import validate_updates, validate_field_value


def parse_arguments():
    parser = argparse.ArgumentParser(description="Validate a CSV file.")
    parser.add_argument("-i", "--input_file", required=True,
                        help="Input CSV file path.")
    parser.add_argument("-f", "--file_type", required=True, choices=[
                        'new', 'updates'], help="New or updates record file. Choices are 'new' or 'updates'")
    parser.add_argument("-o", "--output_file",
                        default="validation_report.csv", help="Output CSV file path.")
    return parser.parse_args()


def validate_new_records_file(new_records_file, output_file):
    validation_report = []
    for row in new_records_file:
        for field_name, field_value in row.items():
            if field_name in ['city', 'country']:
                values = [field_value]
            elif field_name == 'locations.geonames_id' and not field_value:
                field_value = 'null'
            else:
                values = field_value.split(';') if field_value else []
            for value in values:
                value = value.strip()
                errors = validate_field_value(field_name, value)
                if errors:
                    validation_report.append({'html_url': row.get('html_url'),
                                              'ror_id': row.get('id'), 'messages': errors})
    write_report(validation_report, output_file)


def validate_update_records_file(update_records_file, output_file):
    validation_report = []
    for row in update_records_file:
        update_field_errors, field_value_pairs = validate_updates(row)
        if update_field_errors:
            validation_report.append({'html_url': row.get('html_url'),
                                      'ror_id': row.get('id'), 'messages': update_field_errors})
        for field_name, field_value in field_value_pairs:
            errors = validate_field_value(field_name, field_value)
            if errors:
                validation_report.append({'html_url': row.get('html_url'),
                                          'ror_id': row.get('id'), 'messages': errors})
    write_report(validation_report, output_file)


def main():
    args = parse_arguments()
    input_file = read_csv(args.input_file)
    file_type = args.file_type
    output_file = args.output_file
    if file_type == 'updates':
        validate_update_records_file(input_file, output_file)
    if file_type == 'new':
        validate_new_records_file(input_file, output_file)


if __name__ == "__main__":
    main()
