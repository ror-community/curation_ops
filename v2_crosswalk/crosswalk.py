import argparse
import copy
import json
import os
import logging
import sys
import re
from datetime import date
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.append('../utilities/data_dump_to_csv')
import convert_to_csv
import convert_to_csv_v2

import convert_v1_to_v2
import convert_v2_to_v1
import update_dates_v2


DEFAULT_DATE = datetime.today().strftime('%Y-%m-%d')
ERROR_LOG = "errors.log"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def extract_date(file_name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
    if match:
        return match.group(1)
    return None

def convert_dump(dump_zip_path, output_schema_version, input_path, output_path):
    file_date = extract_date(os.path.split(dump_zip_path)[1])
    print("file date is:")
    print(file_date)
    dump_unzipped = ''
    converted_records = []
    with ZipFile(dump_zip_path, "r") as zf:
        json_files_count = sum('.json' in s for s in zf.namelist())
        if json_files_count == 1:
            for name in zf.namelist():
                # assumes ror-data zip will only contain 1 JSON file
                if '.json' in name:
                    dump_unzipped = zf.extract(name, input_path)
        else:
            print("Dump zip contains multiple json files. Something is wrong.")

    #try:
    f = open(dump_unzipped, 'r')
    records = json.load(f)
    print(str(len(records)) + f" records in v{output_schema_version} dump")
    for record in records:
        print("processing dump record " + str(record['id']))
        if output_schema_version == 2:
            converted_record = convert_v1_to_v2.convert_v1_to_v2(record, file_date)
        else:
            converted_record = convert_v2_to_v1.convert_v2_to_v1(record)
        converted_records.append(converted_record)
    print(str(len(converted_records)) + f" to be added to v{output_schema_version} dump")
    path, file = os.path.split(dump_unzipped)
    print(file)
    if output_schema_version == 2:
        filename = file.strip(".json") + "_schema_v2.json"
    else:
        filename = file.replace('_schema_v2.json', '') + ".json"
    print(filename)

    open(output_path + filename, "w").write(
        json.dumps(converted_records, ensure_ascii=False, indent=4, separators=(',', ': '))
    )
    if os.path.exists(output_path + filename):
        return output_path + filename
    else:
        return None
    #except:
    #    logging.error(f"Error creating v{output_schema_version} dump file: {e}")

def convert_file(file, output_schema_version, output_path):

    try:
        with open(file) as infile:
            record = json.load(infile)
            ror_id = re.sub('https://ror.org/', '', record['id'])
            if output_schema_version == 2:
                converted_record = convert_v1_to_v2.convert_v1_to_v2(record, DEFAULT_DATE)
            else:
                converted_record = convert_v2_to_v1.convert_v2_to_v1(record)
        with open(output_path + ror_id + ".json", "w") as writer:
            writer.write(
            json.dumps(converted_record, ensure_ascii=False, indent=2, separators=(',', ': '))
            )
    except Exception as e:
        logging.error(f"Error converting file: {e}")


def get_files(input):
    files = []
    if os.path.isfile(input):
        files.append(input)
    elif os.path.isdir(input):
        file = []
        path = os.path.normpath(input)
        for f in os.listdir(input):
            file.append(f)
        files = list(map(lambda x: path+"/"+x, file))
    else:
        raise RuntimeError(f"{input} must be a valid file or directory")
    return files


def main():
    parser = argparse.ArgumentParser(description="Script to generate v1 ROR record from v2 record")
    parser.add_argument('-i', '--inputpath', type=str, required=True)
    parser.add_argument('-o', '--outputpath', type=str, required=True)
    parser.add_argument('-f', '--dumpfile', type=str)
    parser.add_argument('-d', '--datesfile', type=str)
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Output schema version (1 or 2)')
    args = parser.parse_args()
    global DEFAULT_DATE

    if args.dumpfile:
        if os.path.exists(args.dumpfile):
            #try:
            print(f"Creating v{args.schemaversion} dump JSON file")
            dump_file = convert_dump(args.dumpfile, args.schemaversion, args.inputpath, args.outputpath)
            if args.schemaversion == 2:
                print("Updating created and last mod dates")
                update_dates_v2.update_dates(dump_file, args.datesfile)
            print("Creating v2 dump CSV file")
            if args.schemaversion == 2:
                convert_to_csv_v2.get_all_data(dump_file)
            else:
                convert_to_csv.get_all_data(dump_file)
            print("Updating zip file:")
            print(dump_file)
            with ZipFile(args.dumpfile, "a", ZIP_DEFLATED) as myzip:
                myzip.write(os.path.splitext(dump_file)[0] + ".json", os.path.split(dump_file)[1])
                myzip.write(os.path.splitext(dump_file)[0] + ".csv", os.path.split(dump_file)[1].replace("json", "csv"))
            #except Exception as e:
            #    logging.error("Error creating new dump: {e}")
        else:
            print(f"File {args.dumpfile} does not exist. Cannot process files.")

    else:
        files = get_files(args.inputpath)

        if files:
            print(f"Converting files to v{args.schemaversion}")
            for file in files:
                print(f"Processing {file}")
                convert_file(file, args.schemaversion, args.outputpath)
        else:
            print("No files exist in " + args.inputpath)

    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()

