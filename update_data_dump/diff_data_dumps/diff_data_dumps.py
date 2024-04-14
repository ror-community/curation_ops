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
    parser.add_argument('-o', '--output', required=True,
                        help='Path to the output CSV file')
    return parser.parse_args()


def load_json_files(file1, file2):
    with open(file1) as f1, open(file2) as f2:
        data1 = {record['id']: record for record in json.load(f1)}
        data2 = {record['id']: record for record in json.load(f2)}
        return data1, data2


def compare_records(data1, data2):
    differences = []
    for record_id, record1 in data1.items():
        record2 = data2.get(record_id)
        if record2:
            diff = DeepDiff(record1, record2, ignore_order=True)
            if diff:
                differences.append(
                    {'id': record_id, 'diff': diff, 'error': None})
        else:
            differences.append(
                {'id': record_id, 'diff': None, 'error': 'Record missing in file2'})
    for record_id in data2.keys() - data1.keys():
        differences.append(
            {'id': record_id, 'diff': None, 'error': 'Record missing in file1'})
    return differences


def write_differences_to_csv(differences, output_file):
    with open(output_file, 'w') as csvfile:
        fieldnames = ['id', 'diff', 'error']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for diff in differences:
            writer.writerow(diff)


def main():
    args = parse_arguments()
    data1, data2 = load_json_files(args.file1, args.file2)
    differences = compare_records(data1, data2)
    write_differences_to_csv(differences, args.output)


if __name__ == '__main__':
    main()
