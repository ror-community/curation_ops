import re
import os
import sys
import csv
import json
import requests
import argparse
from datetime import datetime


def download_record(ror_id, schema_version, json_file_path):
    api_url = f'https://api.ror.org/v{schema_version}/organizations/{ror_id}'
    ror_data = requests.get(api_url).json()
    with open(json_file_path, 'w', encoding='utf8') as f_out:
        json.dump(ror_data, f_out, indent=4, ensure_ascii=False)


def parse_and_download(f, schema_version):
    now = datetime.now()
    json_dir = os.getcwd() + '/' + now.strftime("%Y%m%d_%H%M%S") + '/'
    os.makedirs(json_dir)
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            ror_id = row['id']
            print('Downloading', ror_id, '...')
            ror_id = ror_id.split('.org/')[1]
            json_file_path = ror_id + '.json'
            json_file_path = json_dir + json_file_path
            download_record(ror_id, schema_version, json_file_path)


def main():
    parser = argparse.ArgumentParser(description='Download ROR records')
    parser.add_argument('-i', '--input_file', type=str,
                        help='Path to the input CSV file')
    parser.add_argument('-s', '--schema_version', type=str,
                        choices=["1", "2"], help='Schema version for the records to download. Choices: 1 or 2')
    args = parser.parse_args()
    parse_and_download(args.input_file, args.schema_version)


if __name__ == '__main__':
    main()