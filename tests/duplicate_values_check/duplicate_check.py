import csv
import glob
import json
import argparse
import re


def flatten_json(j):
    flattened = {}

    def flatten(obj, name=''):
        if type(obj) is dict:
            for item in obj:
                flatten(obj[item], name + item + '_')
        elif type(obj) is list:
            i = 0
            for item in obj:
                flatten(item, name + str(i) + '_')
                i += 1
        else:
            flattened[name[:-1]] = obj
    flatten(j)
    return flattened


def should_ignore_duplicate(field1, field2, value):
    # Ignore null values
    if not value or value == '':
        return True

    # Ignore admin fields
    if field1.startswith('admin_') or field2.startswith('admin_'):
        return True

    # Ignore external_ids preferred/all pairs
    if 'external_ids_' in field1 and 'external_ids_' in field2:
        match1 = re.search(r'external_ids_(\d+)', field1)
        match2 = re.search(r'external_ids_(\d+)', field2)
        if match1 and match2 and match1.group(1) == match2.group(1):
            if ('preferred' in field1 and 'all' in field2) or \
               ('preferred' in field2 and 'all' in field1):
                return True

    # Ignore language tag duplications
    if field1.endswith('_lang') and field2.endswith('_lang'):
        return True

    # Ignore relationship type duplications - more flexible pattern matching
    if (('relationships_' in field1 and '_type' in field1) and
            ('relationships_' in field2 and '_type' in field2)):
        return True

    # Ignore name type duplications
    if ('names_' in field1 and 'types_' in field1 and
            'names_' in field2 and 'types_' in field2):
        return True
    return False


def check_duplicate_values(input_dir, output_file):
    header = ['ror_id', 'field', 'value', 'duplicated_in']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob(f"{input_dir}/*.json"):
        with open(file, 'r+', encoding='utf8') as f_in:
            json_file = json.load(f_in)
        ror_id = json_file['id']
        flattened = flatten_json(json_file)
        seen = {}
        for key, value in flattened.items():
            if isinstance(value, str):
                if value in seen.values():
                    inverted_seen = {v: k for k, v in seen.items()}
                    duplicate_field = inverted_seen[value]
                    if not should_ignore_duplicate(key, duplicate_field, value):
                        with open(output_file, 'a') as f_out:
                            writer = csv.writer(f_out)
                            writer.writerow(
                                [ror_id, key, value, duplicate_field])
                else:
                    seen[key] = value


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for duplicate values in directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input directory containing JSON files.")
    parser.add_argument("-o", "--output_file",
                        default="duplicate_values.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_duplicate_values(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
