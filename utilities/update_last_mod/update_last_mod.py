import argparse
import os
import json
import logging
import sys
import datetime

RECORDS_PATH = "."
ERROR_LOG = "update_last_mod_errors.log"
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()

def get_files(top):
    filepaths = []
    for dirpath, dirs, files in os.walk(top, topdown=True):
        for file in files:
            filepaths.append(os.path.join(dirpath, file))
    return filepaths

def update_last_mod(filepaths, date):
    for filepath in filepaths:
        filename, file_extension = os.path.splitext(filepath)
        if file_extension == '.json':
            try:
                with open(filepath, 'r+') as json_in:
                    print("updating " + filepath)
                    json_data = json.load(json_in)
                    json_data['admin']['last_modified']['date'] = date
                    if json_data:
                        export_json(json_data, json_in)
                    else:
                        logging.error(f"Error updating file {filepath}: {e}")
            except Exception as e:
                logging.error(f"Writing {filepath}: {e}")

def valid_date(date_arg: str) -> datetime.datetime:
    try:
        datetime.datetime.strptime(date_arg, "%Y-%m-%d")
        return date_arg
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {date_arg!r}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to update location information")
    parser.add_argument('-d', '--dateinput', required=True, type=valid_date, help='Date to use when updating last modified YYYY-DD-MM')
    args = parser.parse_args()
    print(args.dateinput)
    update_last_mod(get_files(RECORDS_PATH), args.dateinput)
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN update_last_mod_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)
