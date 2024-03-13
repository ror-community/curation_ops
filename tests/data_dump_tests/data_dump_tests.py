import os
import sys
import csv
import json
import glob
import random
import argparse
import requests
import jsondiff
from time import sleep


def get_ror_display_name(json_file):
    return next((name['value'] for name in json_file.get('names', []) if 'ror_display' in name.get('types', [])), None)


def release_files_in_data_dump(data_dump_file_path, release_dir, outfile):
    release_file_ids = []
    with open(data_dump_file_path, 'r+', encoding='utf8') as f_in:
        data_dump = json.load(f_in)
    print("Total record count in data dump:", len(data_dump))
    for file in glob.glob(f'{release_dir}/*.json'):
        with open(file, 'r+', encoding='utf8') as f_in:
            release_file = json.load(f_in)
        release_file_id = release_file['id']
        release_file_ids.append(release_file_id)
        if release_file not in data_dump:
            ror_display_name = get_ror_display_name(release_file)
            with open(outfile, 'a') as f_out:
                writer = csv.writer(f_out)
                writer.writerow([release_file_id, ror_display_name])
    return release_file_ids


def compare_old_data_dump_new_data_dump(release_ids, data_dump_file_path, old_data_dump_file_path, prod_data_dump_discrepancies_file):
    with open(data_dump_file_path, 'r+', encoding='utf8') as f_in:
        data_dump = json.load(f_in)
    with open(old_data_dump_file_path, 'r+', encoding='utf8') as f_in:
        old_data_dump = json.load(f_in)
    current_dd_minus_release_files = {
        record["id"]: record for record in data_dump if record["id"] not in release_ids
    }
    old_dd_minus_release_files = {
        record["id"]: record for record in old_data_dump if record["id"] not in release_ids
    }
    if len(old_dd_minus_release_files) != len(current_dd_minus_release_files):
        print("Data dumps are different lengths with release files removed\nOld:", len(
            old_dd_minus_release_files), '\nNew:', len(current_dd_minus_release_files), '\n')
    if current_dd_minus_release_files == old_dd_minus_release_files:
        print('Data dumps match with release files are removed')
    else:
        for key, value in old_dd_minus_release_files.items():
            old_record = value
            new_record = current_dd_minus_release_files[key]
            if old_record != new_record:
                record_diff = jsondiff.diff(
                    old_record, new_record, syntax='symmetric')
                with open(prod_data_dump_discrepancies_file, 'a') as f_out:
                    writer = csv.writer(f_out)
                    writer.writerow([key, record_diff])


def compare_random_data_dump_production_api(release_ids, data_dump_file_path, prod_data_dump_discrepancies_file, staging_flag):
    with open(data_dump_file_path, 'r+', encoding='utf8') as f_in:
        data_dump = json.load(f_in)
    minus_release_files = [
        record for record in data_dump if record["id"] not in release_ids]
    random_data_dump_records = []
    for _ in range(10):
        random_data_dump_records.append(random.choice(minus_release_files))
    for record in random_data_dump_records:
        ror_id = record["id"]
        if staging_flag:
	        api_url = f"https://api.staging.ror.org/v2/organizations/{ror_id}"
        else:
        	api_url = f"https://api.ror.org/v2/organizations/{ror_id}"
        print("Comparing data dump file and API for", ror_id, "...")
        api_json = requests.get(api_url).json()
        if api_json == record:
            print("Data dump file matches API.\n")
        if api_json != record:
            print("Data dump file does not match API.\n")
            record_diff = jsondiff.diff(record, api_json, syntax='symmetric')
            with open(prod_data_dump_discrepancies_file, 'a') as f_out:
                writer = csv.writer(f_out)
                writer.writerow([record['id'], record_diff])
        sleep(1)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Run data dump tests for ROR')
    parser.add_argument('-r', '--release_dir',
                        help='Path to release directory')
    parser.add_argument('-o', '--old_data_dump_file',
                        help='Path to the old data dump file')
    parser.add_argument('-n', '--new_data_dump_file',
                        help='Path to the new data dump file')
    parser.add_argument('-m', '--missing_ids_outfile', default='missing_ids.csv',
                        help='Path to the missing IDs output file')
    parser.add_argument('-p', '--prod_data_dump_discrepancies_file', default='prod_data_dump_discrepancies.csv',
                        help='Path to the prod/datadump discrepancies output file')
    parser.add_argument('-j', '--jsondiff_outfile', default='jsondiff.csv',
                        help='Path to the jsondiff output file')
    parser.add_argument('-s', '--staging_flag', choices=[
                        True, False], type=bool, default=False, help='Use staging for tests. True or False. Default is False')
    args = parser.parse_args()
    return args


def main():
    args = parse_arguments()
    release_ids = release_files_in_data_dump(
        args.new_data_dump_file, args.release_dir, args.missing_ids_outfile)
    compare_old_data_dump_new_data_dump(
        release_ids, args.new_data_dump_file, args.old_data_dump_file, args.jsondiff_outfile)
    compare_random_data_dump_production_api(
        release_ids, args.new_data_dump_file, args.prod_data_dump_discrepancies_file, args.staging_flag)


if __name__ == '__main__':
    main()
