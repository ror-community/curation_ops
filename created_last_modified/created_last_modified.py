import re
import csv
import json
import argparse
import os
import shutil
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED

DUMP_FILES_DIR = 'dump_files'


def extract_date(file_name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
    if match:
        return match.group(1)
    return None


def get_json_file(dump_path):
    if not os.path.exists(DUMP_FILES_DIR):
        os.mkdir(DUMP_FILES_DIR)
    dump_unzipped = None
    with ZipFile(dump_path, "r") as zf:
        json_filename = None
        for name in zf.namelist():
            # assumes ror-data zip will only contain 1 JSON file
            if name.endswith('.json') and not 'MACOSX' in name and not 'schema_v2' in name:
                json_filename = name
        dump_unzipped = zf.extract(json_filename, DUMP_FILES_DIR)
        json_file_date = extract_date(dump_unzipped)
        if json_file_date is None:
            head, tail = os.path.split(dump_path)
            filename = os.path.splitext(tail)
            os.rename(dump_unzipped, os.path.join(DUMP_FILES_DIR, filename[0] + '.json'))
            dump_unzipped = os.path.join(DUMP_FILES_DIR, filename[0] + '.json')
    return dump_unzipped


def write_to_csv(first_appearance, last_modified, output_file):
    with open(output_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["ror_id", "created", "last_modified"])
        for ror_id in first_appearance:
            writer.writerow([ror_id, first_appearance[ror_id],
                                last_modified.get(ror_id, first_appearance[ror_id])])


def find_last_modified(json_files):
    id_last_modified = {}
    previous_records = {}
    all_ids = set()
    for json_file in (json_files):
        release_date = extract_date(json_file)
        try:
            with open(json_file, 'r') as file:
                records = json.load(file)
                for record in records:
                    ror_id = record.get("id")
                    if ror_id not in all_ids:
                        all_ids.add(ror_id)
                        previous_records[ror_id] = record
                        id_last_modified[ror_id] = release_date
                    elif record != previous_records[ror_id]:
                        previous_records[ror_id] = record
                        id_last_modified[ror_id] = release_date
        except:
            print(f"Error processing file {json_file}.")
    return id_last_modified


def find_created(json_files):
    id_map = {}
    processed_ids = set()
    for json_file in json_files:
        release_date = extract_date(json_file)
        try:
            with open(json_file, 'r') as file:
                records = json.load(file)
                for record in records:
                    ror_id = record.get("id")
                    if ror_id not in processed_ids:
                        id_map[ror_id] = release_date
                        processed_ids.add(ror_id)
        except:
            print(f"Error processing file {json_file}.")
    return id_map


def extract_json_files(data_dumps):
    json_files = []
    for dump in data_dumps:
        json_file = get_json_file(dump)
        json_files.append(json_file)
    return json_files


def get_file_list(dump_dir):
    zip_files = [f for f in os.listdir(dump_dir) if f.endswith(".zip")]
    paths_dates = []
    for file in zip_files:
        date = extract_date(file)
        paths_dates.append({'path': os.path.join(dump_dir, file), 'date': date})
    paths_dates.sort(key = lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))
    ordered_files = [x['path'] for x in paths_dates]
    return ordered_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Parse ROR data dump files to determine when a record was first created and last modified.")
    parser.add_argument("-d", "--dump_directory", default="../../ror-data", help="Path to a directory that contains ROR dump files to extract dates from")
    return parser.parse_args()


def main():
    args = parse_args()
    data_dumps = get_file_list(args.dump_directory)
    output_file = os.path.split(data_dumps[len(data_dumps)-1])[1].strip(".zip") + "_created_last_mod.csv"
    json_files = extract_json_files(data_dumps)
    first_appearance_data = find_created(json_files)
    last_modified_data = find_last_modified(json_files)
    print("Output file is {0}".format(output_file))
    write_to_csv(first_appearance_data, last_modified_data, output_file)
    shutil.rmtree(DUMP_FILES_DIR)


if __name__ == "__main__":
	main()
