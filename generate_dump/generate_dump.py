import argparse
import json
import os
import logging
import sys
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import sys
sys.path.append('../utilities/data_dump_to_csv')
import convert_to_csv, convert_to_csv_v2
sys.path.append('../v2_crosswalk')
import crosswalk

NOW = datetime.now()
ERROR_LOG = "errors.log"
INPUT_PATH = "./"
OUTPUT_PATH = "./"
TEMP_NEW_UPDATED_RECORDS_CONCAT = "temp-updated-records"
TEMP_DUMP_UPDATED_RECORDS_REMOVED = "temp-dump-updated-records-removed"
NEW_DUMP_SUFFIX = "-" + NOW.strftime("%Y-%m-%d") + "-ror-data"
V2_SUFFIX = "_schema_v2"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')


def create_other_version_files(input_dir, output_dir, schema_version):
    files = crosswalk.get_files(input_dir)
    file_count = 0
    if files:
        print(f"Converting files to v{str(schema_version)}")
        for file in files:
            if file.endswith('.json'):
                print(f"Processing {file}")
                crosswalk.convert_file(file, schema_version, output_dir)
                file_count += 1
        print(f"Converted {str(file_count)} files to v{str(schema_version)}")
    else:
        print("No files exist in " + input_dir)


def concat_files(filepath, schema_version):
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
        if schema_version == 2:
            filename = TEMP_NEW_UPDATED_RECORDS_CONCAT + V2_SUFFIX + '.json'
        else:
            filename = TEMP_NEW_UPDATED_RECORDS_CONCAT + '.json'
        with open(os.path.join(INPUT_PATH, filename), "w") as f:
            f.write(json.dumps(updated_records, indent=4, separators=(',', ': ')))
    except Exception as e:
        logging.error(f"Error concatenating files: {e}")

    print(str(updated_count) + " new/updated records found")
    print(updated_record_ids)
    return updated_record_ids


# update to handle either version
def remove_existing_records(ror_ids, existing_dump_zip_path, schema_version):
    print("removing existing records")
    existing_dump_unzipped = ''
    indexes = []
    records_to_remove = []
    with ZipFile(existing_dump_zip_path, "r") as zf:
        json_files = [f for f in zf.namelist() if '.json' in f]
        print(json_files)
        if len(json_files)==1:
            existing_dump_unzipped = zf.extract(json_files[0], INPUT_PATH)
        elif len(json_files) == 2:
            if schema_version == 1:
                v1_dump = [f for f in json_files if V2_SUFFIX not in json_files]
                existing_dump_unzipped = zf.extract(v1_dump[0], INPUT_PATH)
            if schema_version == 2:
                v2_dump = [f for f in json_files if V2_SUFFIX in f]
                existing_dump_unzipped = zf.extract(v2_dump[0], INPUT_PATH)
        else:
            print("Dump zip contains more than 2 files. Something is wrong.")
    try:
        f = open(existing_dump_unzipped, 'r')
        json_data = json.load(f)
        for i in range(len(json_data)):
            for ror_id in ror_ids:
                if(json_data[i]["id"] == ror_id):
                    indexes.append(i)
                    records_to_remove.append(ror_id)
                    break

        print(str(len(json_data)) + " records in existing dump " + existing_dump_unzipped)
        print(str(len(records_to_remove)) + " records to remove")
        print(records_to_remove)
        for index in sorted(indexes, reverse=True):
            del json_data[index]
        if schema_version == 2:
            filename = TEMP_DUMP_UPDATED_RECORDS_REMOVED + V2_SUFFIX + '.json'
        else:
            filename = TEMP_DUMP_UPDATED_RECORDS_REMOVED + '.json'
        with open(os.path.join(INPUT_PATH, filename), "w") as f:
            f.write(json.dumps(json_data, indent=4, separators=(',', ': ')))
    except Exception as e:
        logging.error("Error removing existing records: {e}")

def create_zip(release_name, base_version):
    file_list = []
    # always include v1 until sunset
    file_list.append(release_name + NEW_DUMP_SUFFIX)
    if base_version == 2:
        file_list.append(release_name + NEW_DUMP_SUFFIX + V2_SUFFIX)
    with ZipFile(OUTPUT_PATH + release_name + NEW_DUMP_SUFFIX + ".zip", 'w', ZIP_DEFLATED) as myzip:
        for f in file_list:
            myzip.write(INPUT_PATH + f + ".json", f + ".json")
            myzip.write(INPUT_PATH + f + ".csv", f + ".csv")

def create_dump_files(release_name, schema_version):
    if schema_version == 1:
        file_suffix = '.json'
    else:
        file_suffix = V2_SUFFIX + '.json'
    temp_dump_updated_records_removed = open(os.path.join(INPUT_PATH, TEMP_DUMP_UPDATED_RECORDS_REMOVED + file_suffix), 'r')
    temp_dump_updated_records_removed_json = json.load(temp_dump_updated_records_removed)
    updated_records = open(os.path.join(INPUT_PATH, TEMP_NEW_UPDATED_RECORDS_CONCAT + file_suffix), 'r')
    updated_records_json = json.load(updated_records)
    print(str(len(updated_records_json)) + " records added to dump")
    try:
        for i in updated_records_json:
            temp_dump_updated_records_removed_json.append(i)
        print(str(len(temp_dump_updated_records_removed_json)) + " records in new dump")

        if schema_version == 1:
            filename = release_name + NEW_DUMP_SUFFIX
        else:
            filename = release_name + NEW_DUMP_SUFFIX + V2_SUFFIX

        open(INPUT_PATH + filename + ".json", "w").write(
            json.dumps(temp_dump_updated_records_removed_json, indent=4, separators=(',', ': '))
        )
        if schema_version == 1:
            convert_to_csv.get_all_data(INPUT_PATH + filename + ".json")
        else:
            convert_to_csv_v2.get_all_data(INPUT_PATH + filename + ".json")

    except Exception as e:
        logging.error("Error creating dump files: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--releasedirname', type=str, required=True)
    parser.add_argument('-e', '--existingdumpname', type=str, required=True)
    parser.add_argument('-v', '--baseversion', choices=[1, 2], type=int, required=True, help='Schema version of the base file set (1 or 2)')
    parser.add_argument('-i', '--inputpath', type=str, default='.')
    parser.add_argument('-o', '--outputpath', type=str, default='.')
    args = parser.parse_args()
    global INPUT_PATH
    global OUTPUT_PATH

    INPUT_PATH = args.inputpath + '/'
    OUTPUT_PATH = args.outputpath + '/'

    release_dir = os.path.join(INPUT_PATH, args.releasedirname)
    existing_dump_zip_path = os.path.join(OUTPUT_PATH, args.existingdumpname + ".zip")
    base_version = args.baseversion
    if os.path.exists(release_dir):
        updated_record_ids = concat_files(release_dir, base_version)
        remove_existing_records(updated_record_ids, existing_dump_zip_path, base_version)
        create_dump_files(args.releasedirname, base_version)
        if base_version == 2:
            schema_version  = 1
            v1_dir = os.path.join(release_dir, 'v1/')
            os.mkdir(v1_dir)
            create_other_version_files(release_dir, v1_dir, schema_version)
            updated_record_ids = concat_files(v1_dir, schema_version)
            remove_existing_records(updated_record_ids, existing_dump_zip_path, schema_version)
            create_dump_files(args.releasedirname, schema_version)
        if base_version == 1:
            schema_version  = 2
            v2_dir = os.path.join(release_dir, 'v2/')
            os.mkdir(v2_dir)
            create_other_version_files(release_dir, v2_dir, schema_version)
            updated_record_ids = concat_files(v2_dir, schema_version)
            remove_existing_records(updated_record_ids, existing_dump_zip_path, schema_version)
            create_dump_files(args.releasedirname, schema_version)
        create_zip(args.releasedirname, base_version)
        print("created new dump zip")
    else:
        print("File " + input_dir + " does not exist. Cannot process files.")

    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()