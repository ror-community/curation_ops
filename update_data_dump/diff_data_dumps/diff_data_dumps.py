import json
import csv
import argparse
from deepdiff import DeepDiff


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Compare JSON files and write differences to CSV.')
    parser.add_argument('-f1', '--file1', required=True,
                        help='Path to the first JSON file')
    parser.add_argument('-f2', '--file2', required=True,
                        help='Path to the second JSON file')
    parser.add_argument('-o', '--output', default='diff.csv',
                        help='Path to the output CSV file')
    return parser.parse_args()


def load_json_files(file1, file2):
    with open(file1) as f1, open(file2) as f2:
        dd_1_records = {record['id']: record for record in json.load(f1)}
        dd_2_records = {record['id']: record for record in json.load(f2)}
        return dd_1_records, dd_2_records


def compare_records(dd_1_records, dd_2_records):
    differences = []
    for record_id, record1 in dd_1_records.items():
        record2 = dd_2_records.get(record_id)
        if record2:
            diff = DeepDiff(record1, record2, ignore_order=True)
            if diff:
                differences.append(
                    {'id': record_id, 'diff': diff, 'error': None})
        else:
            differences.append(
                {'id': record_id, 'diff': None, 'error': 'Record missing in file2'})
    for record_id in dd_2_records.keys() - dd_1_records.keys():
        differences.append(
            {'id': record_id, 'diff': None, 'error': 'Record missing in file1'})
    return differences


def parse_diff(diff):
    changes = []
    for change_type, change_dict in diff.items():
        for field_path, values in change_dict.items():
            if change_type == 'type_changes':
                changes.append({
                    'field_path': field_path,
                    'change_type': 'type_change',
                    'old_value': str(values['old_value']),
                    'new_value': str(values['new_value'])
                })
            elif change_type == 'values_changed':
                changes.append({
                    'field_path': field_path,
                    'change_type': 'value_change',
                    'old_value': values['old_value'],
                    'new_value': values['new_value']
                })
            elif change_type in ['iterable_item_added', 'dictionary_item_added']:
                changes.append({
                    'field_path': field_path,
                    'change_type': 'item_added',
                    'old_value': None,
                    'new_value': values
                })
            elif change_type in ['iterable_item_removed', 'dictionary_item_removed']:
                changes.append({
                    'field_path': field_path,
                    'change_type': 'item_removed',
                    'old_value': values,
                    'new_value': None
                })
    return changes


def write_differences_to_csv(differences, output_file):
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['id', 'field_path',
                      'change_type', 'old_value', 'new_value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for diff in differences:
            if diff['diff']:
                changes = parse_diff(diff['diff'])
                for change in changes:
                    row = {
                        'id': diff['id'],
                        'field_path': change['field_path'],
                        'change_type': change['change_type'],
                        'old_value': change['old_value'],
                        'new_value': change['new_value']
                    }
                    writer.writerow(row)
            if diff['error']:
                writer.writerow({'id': diff['id'], 'field_path': None,
                                 'change_type': 'error', 'old_value': None,
                                 'new_value': diff['error']})


def main():
    args = parse_arguments()
    dd_1_records, dd_2_records = load_json_files(args.file1, args.file2)
    differences = compare_records(dd_1_records, dd_2_records)
    write_differences_to_csv(differences, args.output)


if __name__ == '__main__':
    main()
