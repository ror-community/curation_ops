import argparse
import os
import json
import logging
import sys
import copy
from datetime import datetime
import update_address


RECORDS_PATH = "."
ERROR_LOG = "address_update_errors.log"
LAST_MOD_DATE =  datetime.now().strftime("%Y-%m-%d")
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def export_json(json_data, json_file, version):
    if version == 2:
        json_data['admin']['last_modified']['date'] = LAST_MOD_DATE
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()

def get_files(top):
    filepaths = []
    for dirpath, dirs, files in os.walk(top, topdown=True):
        for file in files:
            filepaths.append(os.path.join(dirpath, file))
    return filepaths

def compare_locations(original_locations, updated_locations):
    i = 0
    is_equal = True
    for original_location in original_locations:
        for key in original_location['geonames_details']:
            print(original_location['geonames_details'].get(key))
            print(updated_locations[i]['geonames_details'].get(key))
            if original_location['geonames_details'].get(key) != updated_locations[i]['geonames_details'].get(key) \
                or not isinstance(original_location['geonames_details'].get(key), type(updated_locations[i]['geonames_details'].get(key))):
                is_equal = False
        i += 1
    return is_equal


def update_addresses(filepaths, version):
    for filepath in filepaths:
        filename, file_extension = os.path.splitext(filepath)
        if file_extension == '.json':
            try:
                with open(filepath, 'r+') as json_in:
                    print("updating " + filepath)
                    json_data = json.load(json_in)
                    original_locations = copy.deepcopy(json_data['locations'])
                    if version == 2:
                        updated_data = update_address.update_geonames_v2(json_data)
                    if version == 1:
                        updated_data = update_address.update_geonames(json_data)
                    if updated_data:
                        if not compare_locations(original_locations, updated_data['locations']):
                            print("original locations:")
                            print(original_locations)
                            print("new locations:")
                            print(updated_data['locations'])
                            export_json(updated_data, json_in, version)
                    else:
                        logging.error(f"Error updating file {filepath}: {e}")
            except Exception as e:
                logging.error(f"Writing {filepath}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to update location information")
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Output schema version (1 or 2)')
    args = parser.parse_args()
    update_addresses(get_files(RECORDS_PATH), args.schemaversion)
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN address_update_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)
