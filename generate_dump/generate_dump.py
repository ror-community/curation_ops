import os
import sys
import json
import logging
import argparse
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.append('../utilities/data_dump_to_csv')

import convert_to_csv_v2

NOW = datetime.now()
ERROR_LOG = "errors.log"
INPUT_PATH = "./"
OUTPUT_PATH = "./"
TEMP_NEW_UPDATED_RECORDS_CONCAT = "temp-updated-records"
TEMP_DUMP_UPDATED_RECORDS_REMOVED = "temp-dump-updated-records-removed"
NEW_DUMP_SUFFIX = "-" + NOW.strftime("%Y-%m-%d") + "-ror-data"
V2_SUFFIX = "_schema_v2"  # Used only for reading legacy zip files

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')


def concat_files(filepath):
    updated_count = 0
    updated_record_ids = []
    updated_records = []
    files = [os.path.join(filepath, file) for file in os.listdir(filepath) if file.endswith('.json')]
    try:
        for f in files:
            with open(f) as infile:
                file_data = json.load(infile)
                updated_records.append(file_data)
                ror_id = file_data['id']
                updated_record_ids.append(ror_id)
            updated_count += 1
        filename = TEMP_NEW_UPDATED_RECORDS_CONCAT + '.json'
        with open(os.path.join(INPUT_PATH, filename), "w") as f:
            f.write(json.dumps(updated_records, indent=4, separators=(',', ': ')))
    except Exception as e:
        logging.error(f"Error concatenating files: {e}")

    print(str(updated_count) + " new/updated records found")
    print(updated_record_ids)
    return updated_record_ids


def remove_existing_records(ror_ids, existing_dump_zip_path):
    print("Removing existing records from dump")
    existing_dump_unzipped = ''
    indexes = []
    records_to_remove = []
    with ZipFile(existing_dump_zip_path, "r") as zf:
        json_files = [f for f in zf.namelist() if '.json' in f]
        if len(json_files) == 1:
            existing_dump_unzipped = zf.extract(json_files[0], INPUT_PATH)
        elif len(json_files) == 2:
            # Legacy zip with both v1 and v2 - extract v2 (has _schema_v2 suffix)
            v2_dump = [f for f in json_files if V2_SUFFIX in f]
            existing_dump_unzipped = zf.extract(v2_dump[0], INPUT_PATH)
        else:
            print("Dump zip contains unexpected number of files.")
            return
        print(f"Using existing dump {existing_dump_unzipped}")
    try:
        f = open(existing_dump_unzipped, 'r')
        json_data = json.load(f)
        for i in range(len(json_data)):
            for ror_id in ror_ids:
                if json_data[i]["id"] == ror_id:
                    indexes.append(i)
                    records_to_remove.append(ror_id)
                    break

        print(str(len(json_data)) + " records in existing dump " + existing_dump_unzipped)
        print(str(len(records_to_remove)) + " records to remove")
        print(records_to_remove)
        for index in sorted(indexes, reverse=True):
            del json_data[index]
        filename = TEMP_DUMP_UPDATED_RECORDS_REMOVED + '.json'
        with open(os.path.join(INPUT_PATH, filename), "w") as f:
            f.write(json.dumps(json_data, indent=4, separators=(',', ': ')))
    except Exception as e:
        logging.error(f"Error removing existing records: {e}")

def create_zip(release_name):
    filename = release_name + NEW_DUMP_SUFFIX
    with ZipFile(OUTPUT_PATH + filename + ".zip", 'w', ZIP_DEFLATED) as myzip:
        myzip.write(INPUT_PATH + filename + ".json", filename + ".json")
        myzip.write(INPUT_PATH + filename + ".csv", filename + ".csv")

def create_dump_files(release_name):
    temp_dump_updated_records_removed = open(os.path.join(INPUT_PATH, TEMP_DUMP_UPDATED_RECORDS_REMOVED + '.json'), 'r')
    temp_dump_updated_records_removed_json = json.load(temp_dump_updated_records_removed)
    updated_records = open(os.path.join(INPUT_PATH, TEMP_NEW_UPDATED_RECORDS_CONCAT + '.json'), 'r')
    updated_records_json = json.load(updated_records)
    print(str(len(updated_records_json)) + " records added to dump")
    for i in updated_records_json:
        temp_dump_updated_records_removed_json.append(i)
    print(str(len(temp_dump_updated_records_removed_json)) + " records in new dump")

    filename = release_name + NEW_DUMP_SUFFIX
    open(INPUT_PATH + filename + ".json", "w").write(
        json.dumps(temp_dump_updated_records_removed_json, indent=4, separators=(',', ': '))
    )
    convert_to_csv_v2.get_all_data(INPUT_PATH + filename + ".json")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--releasedirname', type=str, required=True)
    parser.add_argument('-e', '--existingdumpname', type=str, required=True)
    parser.add_argument('-i', '--inputpath', type=str, default='.')
    parser.add_argument('-o', '--outputpath', type=str, default='.')
    args = parser.parse_args()
    global INPUT_PATH
    global OUTPUT_PATH

    INPUT_PATH = args.inputpath + '/'
    OUTPUT_PATH = args.outputpath + '/'

    release_dir = os.path.join(INPUT_PATH, args.releasedirname)
    existing_dump_zip_path = os.path.join(OUTPUT_PATH, args.existingdumpname + ".zip")
    if os.path.exists(release_dir):
        updated_record_ids = concat_files(release_dir)
        remove_existing_records(updated_record_ids, existing_dump_zip_path)
        create_dump_files(args.releasedirname)
        create_zip(args.releasedirname)
        print("Created new dump zip")
    else:
        print("Directory " + release_dir + " does not exist. Cannot process files.")

    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()