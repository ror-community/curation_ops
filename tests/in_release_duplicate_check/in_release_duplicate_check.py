import re
import csv
import json
import glob
import argparse
from copy import deepcopy
from string import punctuation
from thefuzz import fuzz


def normalize_text(org_name):
    org_name = org_name.lower()
    org_name = re.sub(r'[^\w\s]', '', org_name)
    exclude = set(punctuation)
    org_name = ''.join(ch for ch in org_name if ch not in exclude)
    return org_name


def get_all_names(record):
    all_names = []
    name_types = ['ror_display', 'alias', 'label']
    for name_type in name_types:
        all_names += [name['value']
                      for name in record.get('names', []) if name_type in name.get('types', [])]
    return all_names


def get_country_code(record):
    if 'locations' in record and len(record['locations']) > 0:
        location = record['locations'][0]
        if 'geonames_details' in location and 'country_code' in location['geonames_details']:
            return location['geonames_details']['country_code']
    return None


def check_duplicates(input_dir, output_file):
    all_records = {}
    header = ['ror_id', 'name', 'duplicate_ror_id',
              'duplicate_name', 'match_ratio']

    with open(output_file, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)

        for file in glob.glob(f"{input_dir}/*.json"):
            with open(file, 'r') as f_in:
                record = json.load(f_in)
                ror_id = record['id']
                country_code = get_country_code(record)
                all_records[ror_id] = (get_all_names(record), country_code)

        for record_id, (record_names, record_country) in all_records.items():
            for record_name in record_names:
                for copied_id, (copied_names, copied_country) in all_records.items():
                    if copied_id == record_id:
                        continue
                    if record_country and copied_country and record_country != copied_country:
                        continue
                    for copied_name in copied_names:
                        match_ratio = fuzz.ratio(normalize_text(
                            record_name), normalize_text(copied_name))
                        if match_ratio >= 85:
                            with open(output_file, 'a', newline='') as f_out:
                                writer = csv.writer(f_out)
                                writer.writerow(
                                    [record_id, record_name, copied_id, copied_name, match_ratio])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for duplicate name metadata in a directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input directory path.")
    parser.add_argument("-o", "--output_file",
                        default="in_release_duplicates.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_duplicates(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()