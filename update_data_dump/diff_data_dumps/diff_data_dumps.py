import json
import csv
import argparse
from deepdiff import DeepDiff
from deepdiff.model import PrettyOrderedSet


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
    # Check for removed records
    for record_id in dd_1_records.keys() - dd_2_records.keys():
        differences.append({
            'id': record_id,
            'change_type': 'record_removed',
            'diff': None
        })
    # Check for added records
    for record_id in dd_2_records.keys() - dd_1_records.keys():
        differences.append({
            'id': record_id,
            'change_type': 'record_added',
            'diff': None
        })
    # Check for changes in existing records
    for record_id in dd_1_records.keys() & dd_2_records.keys():
        diff = DeepDiff(dd_1_records[record_id], dd_2_records[record_id], ignore_order=True)
        if diff:
            differences.append({
                'id': record_id,
                'change_type': 'record_changed',
                'diff': dict(diff)
            })
    return differences


def parse_diff(diff):
    changes = []
    for change_type, change_data in diff.items():
        if isinstance(change_data, list):
            for item in change_data:
                if isinstance(item, str):
                    field_path = item
                    values = None
                else:
                    field_path, values = next(iter(item.items()))
                changes.append(parse_change(change_type, field_path, values))
        elif isinstance(change_data, dict):
            for field_path, values in change_data.items():
                changes.append(parse_change(change_type, field_path, values))
    return changes


def parse_change(change_type, field_path, values):
    if change_type == 'dictionary_item_removed':
        return {
            'field_path': str(field_path),
            'change_type': 'item_removed',
            'old_value': 'Present',
            'new_value': 'Removed'
        }
    elif change_type == 'type_changes':
        return {
            'field_path': str(field_path),
            'change_type': 'type_change',
            'old_value': str(values['old_value']),
            'new_value': str(values['new_value'])
        }
    elif change_type == 'values_changed':
        return {
            'field_path': str(field_path),
            'change_type': 'value_change',
            'old_value': str(values['old_value']),
            'new_value': str(values['new_value'])
        }
    elif change_type in ['iterable_item_added', 'dictionary_item_added']:
        return {
            'field_path': str(field_path),
            'change_type': 'item_added',
            'old_value': 'Not present',
            'new_value': 'Added'
        }
    elif change_type in ['iterable_item_removed']:
        return {
            'field_path': str(field_path),
            'change_type': 'item_removed',
            'old_value': str(values),
            'new_value': 'Removed'
        }
    else:
        raise ValueError(f"Unhandled change_type: {change_type} for field_path: {field_path} and values: {values}")


def write_differences_to_csv(differences, output_file):
    with open(output_file, 'w') as csvfile:
        fieldnames = ['id', 'change_type', 'field_path', 'old_value', 'new_value']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for diff in differences:
            if diff['change_type'] in ['record_added', 'record_removed']:
                writer.writerow({
                    'id': diff['id'],
                    'change_type': diff['change_type'],
                    'field_path': 'entire_record',
                    'old_value': 'Present' if diff['change_type'] == 'record_removed' else 'Not present',
                    'new_value': 'Removed' if diff['change_type'] == 'record_removed' else 'Added'
                })
            elif diff['change_type'] == 'record_changed':
                for change_type, change_data in diff['diff'].items():
                    if isinstance(change_data, (list, PrettyOrderedSet)):
                        for item in change_data:
                            change = parse_change(change_type, item, None)
                            writer.writerow({
                                'id': diff['id'],
                                **change
                            })
                    elif isinstance(change_data, dict):
                        for field_path, values in change_data.items():
                            change = parse_change(change_type, field_path, values)
                            writer.writerow({
                                'id': diff['id'],
                                **change
                            })
                    else:
                        raise ValueError(f"Unexpected change_data type: {type(change_data)} for diff: {diff}")
            else:
                raise ValueError(f"Unhandled change_type: {diff['change_type']} for diff: {diff}")
            print(f"Wrote row for diff: {diff['id']}")


def main():
    args = parse_arguments()
    dd_1_records, dd_2_records = load_json_files(args.file1, args.file2)
    differences = compare_records(dd_1_records, dd_2_records)
    write_differences_to_csv(differences, args.output)


if __name__ == '__main__':
    main()
