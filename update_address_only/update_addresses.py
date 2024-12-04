import argparse
import os
import json
import logging
import sys
import copy
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import update_address


RECORDS_PATH = "."
ERROR_LOG = "address_update_errors.log"
LAST_MOD_DATE =  datetime.now().strftime("%Y-%m-%d")
NEW_V2_1_FIELDS = (
    'continent_code',
    'continent_name',
    'country_subdivision_code',
    'country_subdivision_name'
)
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=4)
    json_file.truncate()

def get_files(top):
    filepaths = []
    for dirpath, dirs, files in os.walk(top, topdown=True):
        for file in files:
            filepaths.append(os.path.join(dirpath, file))
    print(filepaths)
    return filepaths

def compare_locations(original_locations, updated_locations):
    i = 0
    is_equal = True
    for original_location in original_locations:
        for key in original_location['geonames_details']:
            if original_location['geonames_details'].get(key) != updated_locations[i]['geonames_details'].get(key) \
                or not isinstance(original_location['geonames_details'].get(key), type(updated_locations[i]['geonames_details'].get(key))):
                is_equal = False
        v2_1_keys_not_in_location = [f for f in NEW_V2_1_FIELDS if f not in original_location['geonames_details'].keys()]
        if v2_1_keys_not_in_location:
            is_equal = False
        i += 1
    return is_equal

def update_record_locations(json_data, version):
    if version == 2:
        updated_data,cache_hit = update_address.update_geonames_v2(json_data)
        updated_data['admin']['last_modified']['date'] = LAST_MOD_DATE
    if version == 1:
        updated_data,cache_hit = update_address.update_geonames(json_data)
    return updated_data,cache_hit

def update_addresses_dump(dump_zip_path, version):
    dump_unzipped = ''
    updated_records = []
    with ZipFile(dump_zip_path, "r") as zf:
        print(zf.namelist())
        json_files_count = sum('.json' in s for s in zf.namelist())
        if json_files_count == 1:
            for name in zf.namelist():
                # assumes ror-data zip will only contain 1 JSON file
                if '.json' in name:
                    dump_unzipped = zf.extract(name, RECORDS_PATH)
        else:
            print("Dump zip contains multiple json files. Something is wrong.")

    #try:
    f = open(dump_unzipped, 'r')
    records = json.load(f)
    print(str(len(records)) + f" records in v{version} dump")
    cache_hits = 0
    geonames_requests = 0
    for record in records:
        print("processing dump record " + str(record['id']))
        updated_record,cache_hit = update_record_locations(record, version)
        updated_records.append(updated_record)
        if cache_hit:
            cache_hits += 1
        else:
            geonames_requests += 1
    open(dump_unzipped, "w").write(
        json.dumps(updated_records, ensure_ascii=False, indent=4, separators=(',', ': '))
    )
    return cache_hits,geonames_requests
    #except:
    #    logging.error(f"Error creating v{output_schema_version} dump file: {e}")

def update_addresses(filepaths, version):
    cache_hits = 0
    geonames_requests = 0
    for filepath in filepaths:
        filename, file_extension = os.path.splitext(filepath)
        if file_extension == '.json':
            #try:
            with open(filepath, 'r+') as json_in:
                record_data = json.load(json_in)
                if isinstance(record_data, list):
                    updated_records = []
                    for record in record_data:
                        original_locations = copy.deepcopy(record['locations'])
                        updated_record,cache_hit = update_record_locations(record, version)
                        updated_records.append(updated_record)
                        if cache_hit:
                            cache_hits += 1
                        else:
                            geonames_requests += 1
                    export_json(updated_records, json_in)
                if isinstance(record_data, dict):
                    print("updating " + filepath)
                    original_locations = copy.deepcopy(record_data['locations'])
                    updated_record,cache_hit = update_record_locations(record_data, version)
                    if cache_hit:
                            cache_hits += 1
                    else:
                        geonames_requests += 1
                    if updated_record:
                        if not compare_locations(original_locations, updated_record['locations']):
                            export_json(updated_record, json_in)
    return cache_hits,geonames_requests
        #except Exception as e:
             #   logging.error(f"Error updating file {filepath}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to update location information")
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Output schema version (1 or 2)')
    parser.add_argument('-f', '--dumpfile', type=str)
    parser.add_argument('-i', '--inputpath', type=str, default=RECORDS_PATH)
    args = parser.parse_args()
    if args.dumpfile:
        if os.path.exists(args.dumpfile):
            cache_hits,geonames_requests = update_addresses_dump(args.dumpfile, args.schemaversion)
    else:
        cache_hits,geonames_requests = update_addresses(get_files(args.inputpath), args.schemaversion)
    print(f"{str(cache_hits)} cache hits, {str(geonames_requests)} geonames requests")
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN address_update_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)
