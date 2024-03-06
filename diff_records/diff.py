import os
import csv
import sys
import json
import glob
import argparse
import requests
import jsondiff


def get_diffs(input_dir, output_file):
    header = ['ror_id', 'field', 'change']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    for file in glob.glob(f"{input_dir}/*.json"):
        with open(file, 'r+') as f_in:
            json_file = json.load(f_in)
        ror_id = json_file['id']
        api_url = f'https://api.ror.org/v2/organizations/{ror_id}'
        api_json = requests.get(api_url).json()
        file_api_diffs = jsondiff.diff(api_json, json_file, syntax='symmetric')
        if type(file_api_diffs) == list:
            for diff in file_api_diffs:
                for key, value in diff.items():
                    with open(output_file, 'a') as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow([ror_id, key, value])
        else:
            for key, value in file_api_diffs.items():
                with open(output_file, 'a') as f_out:
                    writer = csv.writer(f_out)
                    writer.writerow([ror_id, key, value])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Compare records on production to files in a directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input directory path.")
    parser.add_argument("-o", "--output_file",
                        default="diffs.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    get_diffs(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
