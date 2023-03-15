import os
import json
import logging
import sys
sys.path.append('/Users/ekrznarich/git/update_address')
import update_address

RECORDS_PATH = "."
ERROR_LOG = "address_update_errors.log"
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

def update_addresses(filepaths):
    for filepath in filepaths:
        filename, file_extension = os.path.splitext(filepath)
        if file_extension == '.json':
            try:
                with open(filepath, 'r+') as json_in:
                    print("updating " + filepath)
                    json_data = json.load(json_in)
                    json_data = update_address.update_geonames(json_data)
                    export_json(json_data, json_in)
            except Exception as e:
                logging.error(f"Writing {filepath}: {e}")

if __name__ == '__main__':
    update_addresses(get_files(RECORDS_PATH))
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN address_update_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)
