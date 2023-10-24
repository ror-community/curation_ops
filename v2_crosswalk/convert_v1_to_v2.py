import argparse
import copy
import json
import os
import logging
import sys
import re
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.append('../utilities/data_dump_to_csv')
import convert_to_csv_v2

import v2_fields
import v2_enums
import update_dates_v2

TODAY = datetime.today().strftime('%Y-%m-%d')
ERROR_LOG = "errors.log"
INPUT_PATH = "./V1_INPUT/"
OUTPUT_PATH = "./V2_OUTPUT/"
V2_TEMPLATE = "./v2_template.json"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def extract_date(file_name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
    if match:
        return match.group(1)
    return None

# admin
def format_admin(file_date):
    v2_admin = v2_fields.v2_admin_template
    v2_admin['created']['date'] = file_date
    v2_admin['created']['schema_version'] = copy.copy(v2_enums.SCHEMA_VERSIONS['1'])
    v2_admin['last_modified']['date'] = file_date
    v2_admin['last_modified']['schema_version'] = copy.copy(v2_enums.SCHEMA_VERSIONS['2'])
    return v2_admin

# relationships
def format_relationships(v1_relationships):
    for v1_rel in v1_relationships:
        v1_rel['type'] = v1_rel['type'].lower()
    return v1_relationships

# external_ids
def get_v2_ext_id_type(v1_ext_id_type):
    type_key = "".join([k for k in v2_enums.EXTERNAL_ID_TYPES if v2_enums.EXTERNAL_ID_TYPES[k]==v1_ext_id_type.lower()])
    if type_key:
        return v2_enums.EXTERNAL_ID_TYPES[type_key]
    else:
        return None

def format_external_ids(v1_external_ids):
    v2_external_ids = []
    for k in v1_external_ids:
        v2_ext_id_type = get_v2_ext_id_type(k)
        if v2_ext_id_type:
            v2_external_id = copy.deepcopy(v2_fields.v2_external_id_template)
            v2_external_id['type'] = v2_ext_id_type
            if isinstance(v1_external_ids[k]['all'], list) and len(v1_external_ids[k]['all']) > 0:
                v2_external_id['all'] = v1_external_ids[k]['all']
            if isinstance(v1_external_ids[k]['all'], str) and len(v1_external_ids[k]['all']) > 0:
                v2_external_id['all'].append(v1_external_ids[k]['all'])
            if v1_external_ids[k]['preferred']:
                v2_external_id['preferred'] = v1_external_ids[k]['preferred']
            if v2_external_id['preferred'] or v2_external_id['all']:
                v2_external_ids.append(v2_external_id)
    return v2_external_ids

# links
def format_links(v1_links, v1_wikipedia_url):
    v2_links = []
    v1_links = filter(None, v1_links)
    for link in v1_links:
        v2_link = copy.deepcopy(v2_fields.v2_link_template)
        v2_link['value'] = link
        v2_link['type'] = copy.copy(v2_enums.LINK_TYPES['WEBSITE'])
        v2_links.append(v2_link)
    if v1_wikipedia_url:
        v2_link = copy.deepcopy(v2_fields.v2_link_template)
        v2_link['value'] = v1_wikipedia_url
        v2_link['type'] = copy.copy(v2_enums.LINK_TYPES['WIKIPEDIA'])
        v2_links.append(v2_link)
    return v2_links

# locations
def format_locations(v1_data):
    v2_locations = []
    for address in v1_data['addresses']:
        v2_location = copy.deepcopy(v2_fields.v2_location_template)
        # temp until missing geonames IDs/names are fixed
        if address['geonames_city']:
            if address['geonames_city']['id']:
                v2_location['geonames_id'] = address['geonames_city']['id']
            if address['geonames_city']['city']:
                v2_location['geonames_details']['name'] = address['geonames_city']['city']
        if v1_data['country']['country_code']:
            v2_location['geonames_details']['country_code'] = v1_data['country']['country_code']
        if v1_data['country']['country_name']:
            v2_location['geonames_details']['country_name'] = v1_data['country']['country_name']
        if address['lat']:
            v2_location['geonames_details']['lat'] = address['lat']
        if address['lng']:
            v2_location['geonames_details']['lng'] = address['lng']
        v2_locations.append(v2_location)
    return v2_locations

# names
def format_names(v1_data):
    v2_names = []

    if v1_data['name']:
        v2_name = copy.deepcopy(v2_fields.v2_name_template)
        v2_name['value'] = v1_data['name']
        v2_name['types'].extend([v2_enums.NAME_TYPES['ROR_DISPLAY'], v2_enums.NAME_TYPES['LABEL']])
        v2_names.append(v2_name)

    if len(v1_data['aliases']) > 0:
        for alias in v1_data['aliases']:
            v2_alias = copy.deepcopy(v2_fields.v2_name_template)
            v2_alias['value'] = alias
            v2_alias['types'].append(v2_enums.NAME_TYPES['ALIAS'])
            v2_names.append(v2_alias)

    if len(v1_data['labels']) > 0:
        for label in v1_data['labels']:
            v2_label = copy.deepcopy(v2_fields.v2_name_template)
            v2_label['value'] = label['label']
            v2_label['lang'] = label['iso639']
            v2_label['types'].append(v2_enums.NAME_TYPES['LABEL'])
            v2_names.append(v2_label)

    if len(v1_data['acronyms']) > 0:
        for acronym in v1_data['acronyms']:
            v2_acronym = copy.deepcopy(v2_fields.v2_name_template)
            v2_acronym['value'] = acronym
            v2_acronym['types'].append(v2_enums.NAME_TYPES['ACRONYM'])
            v2_names.append(v2_acronym)

    return v2_names

def convert_v1_to_v2(v1_data, file_date):
    try:
        with open(V2_TEMPLATE) as template_file:
            v2_data = json.load(template_file)
            # these fields don't change
            v2_data['id'] = v1_data['id']
            v2_data['types'] = [type.lower() for type in v1_data['types']]
            v2_data['status'] = v1_data['status']
            v2_data['established'] = v1_data['established']
            v2_data['domains'] = []
            # these fields DO change
            v2_data['relationships'] = format_relationships(v1_data['relationships'])
            v2_data['external_ids'] = format_external_ids(v1_data['external_ids'])
            v2_data['links'] = format_links(v1_data['links'], v1_data['wikipedia_url'])
            v2_data['locations'] = format_locations(v1_data)
            v2_data['names'] = format_names(v1_data)
            v2_data['admin'] = format_admin(file_date)
            return v2_data
    except Exception as e:
        logging.error(f"Error converting v1 data to v2: {e}")

def create_v2_dump(v1_dump_zip_path):
    file_date = extract_date(os.path.split(v1_dump_zip_path)[1])
    print("file date is:")
    print(file_date)
    v1_dump_unzipped = ''
    v2_records = []
    with ZipFile(v1_dump_zip_path, "r") as zf:
        json_files_count = sum('.json' in s for s in zf.namelist())
        if json_files_count == 1:
            for name in zf.namelist():
                # assumes ror-data zip will only contain 1 JSON file
                if '.json' in name:
                    v1_dump_unzipped = zf.extract(name, INPUT_PATH)
        else:
            print("Dump zip contains multiple json files. Something is wrong.")

    #try:
    f = open(v1_dump_unzipped, 'r')
    v1_records = json.load(f)
    print(str(len(v1_records)) + " records in v1 dump")
    for v1_record in v1_records:
        print("processing dump record " + str(v1_record['id']))
        v2_record = convert_v1_to_v2(v1_record, file_date)
        v2_records.append(v2_record)
    print(str(len(v2_records)) + " to be added to v2 dump")
    path, file = os.path.split(v1_dump_unzipped)
    filename = file.strip(".json")
    open(OUTPUT_PATH + filename + "_schema_v2.json", "w").write(
        json.dumps(v2_records, indent=4, separators=(',', ': '))
    )
    if os.path.exists(OUTPUT_PATH + filename + "_schema_v2.json"):
        return OUTPUT_PATH + filename + "_schema_v2.json"
    else:
        return None


def create_v2_file(v1_file, file_date):
    try:
        with open(v1_file) as infile:
            v1_data = json.load(infile)
            ror_id = re.sub('https://ror.org/', '', v1_data['id'])
            v2_record_data = convert_v1_to_v2(v1_data, file_date)
        with open(OUTPUT_PATH + ror_id + ".json", "w") as writer:
            writer.write(
            json.dumps(v2_record_data, indent=4, separators=(',', ': '))
            )
    except Exception as e:
        logging.error(f"Error concatenating files: {e}")


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
    parser = argparse.ArgumentParser(description="Script to generate v2 ROR record from v1 record")
    parser.add_argument('-i', '--inputpath', type=str, default='./V1_INPUT')
    parser.add_argument('-o', '--outputpath', type=str, default='./V2_OUTPUT')
    parser.add_argument('-f', '--dumpfile', type=str)
    parser.add_argument('-d', '--datesfile', type=str)
    args = parser.parse_args()
    global INPUT_PATH
    global OUTPUT_PATH
    global TODAY

    if args.dumpfile:
        if os.path.exists(args.dumpfile):
            try:
                print("Creating v2 dump JSON file")
                v2_dump_file = create_v2_dump(args.dumpfile)
                print("Updating created and last mod dates")
                update_dates_v2.update_dates(v2_dump_file, args.datesfile)
                print("Creating v2 dump CSV file")
                convert_to_csv_v2.get_all_data(v2_dump_file)
                print("Updating zip file:")
                print(args.dumpfile)
                with ZipFile(args.dumpfile, "a", ZIP_DEFLATED) as myzip:
                    myzip.write(os.path.splitext(v2_dump_file)[0] + ".json", os.path.split(v2_dump_file)[1])
                    myzip.write(os.path.splitext(v2_dump_file)[0] + ".csv", os.path.split(v2_dump_file)[1].replace("json", "csv"))
            except Exception as e:
                logging.error("Error creating new dump: {e}")
        else:
            print("File " + args.dumpfile + " does not exist. Cannot process files.")

    else:
        files = get_files(args.inputpath)

        if files:
            for file in files:
                print("processing " + file)
                create_v2_file(file, TODAY)
        else:
            print("No files exist in " + INPUT_PATH)

    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    main()

