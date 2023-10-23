import argparse
import copy
import json
import os
import logging
import sys
import re
from datetime import date
from zipfile import ZipFile, ZIP_DEFLATED
sys.path.append('../utilities/data_dump_to_csv')
import convert_to_csv

import v1_fields
import v1_enums
import v2_enums

TODAY = date.today()
ERROR_LOG = "errors.log"
INPUT_PATH = "./V1_INPUT/"
OUTPUT_PATH = "./V2_OUTPUT/"
V1_TEMPLATE = "./v1_template.json"

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def extract_date(file_name):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
    if match:
        return match.group(1)
    return None

# relationships
def format_relationships(v2_relationships):
    for v2_rel in v2_relationships:
        v2_rel['type'] = v2_rel['type'].title()
    return v2_relationships

# external_ids
def get_v1_ext_id_type(v2_ext_id_type):
    type_key = "".join([k for k in v1_enums.EXTERNAL_ID_TYPES if v1_enums.EXTERNAL_ID_TYPES[k]==v2_ext_id_type.upper()])
    if type_key:
        return v1_enums.EXTERNAL_ID_TYPES[type_key]
    else:
        return None

def format_external_ids(v2_external_ids):
    v1_external_ids = {}
    for v2_external_id in v2_external_ids:
        v1_ext_id_type = get_v1_ext_id_type(v2_external_id['type'])
        if v1_ext_id_type:
            v1_external_id = copy.deepcopy(v1_fields.v1_external_id_template)
            if isinstance(v2_external_id['all'], list) and len(v2_external_id['all']) > 0:
                v1_external_id['all'] = v2_external_id['all']
            if isinstance(v2_external_id['all'], str) and len(v2_external_id['all']) > 0:
                v1_external_id['all'].append(v2_external_id['all'])
            if v2_external_id['preferred']:
                v1_external_id['preferred'] = v2_external_id['preferred']
            if v1_external_id['preferred'] or v1_external_id['all']:
                v1_external_ids[v1_ext_id_type] = v1_external_id
    return v1_external_ids

# links
def format_links(v2_links):
    v1_links = []
    v2_links = filter(None, v2_links)
    for link in v2_links:
        if link['type'] == v2_enums.LINK_TYPES['WEBSITE']:
            v1_links.append(format_links['value'])
    return v2_links

# wikipedia_url
def format_wikipedia_url(v2_links):
    v2_links = filter(None, v2_links)
    for link in v2_links:
        if link['type'] == v2_enums.LINK_TYPES['WIKIPEDIA']:
            return link['value']
    return None

# addresses
def format_addresses(v2_locations):
    v1_addresses = []
    v2_location = v2_locations[0]
    v1_address = copy.deepcopy(v1_fields.v1_address_template)
    if v2_location['geonames_id']:
        v1_address['geonames_city']['id'] = v2_location['geonames_id']
    if v2_location['geonames_details']:
        if v2_location['geonames_details']['lat']:
            v1_address['lat'] = v2_location['geonames_details']['lat']
        if v2_location['geonames_details']['lng']:
            v1_address['lng'] = v2_location['geonames_details']['lng']
        if v2_location['geonames_details']['name']:
            v1_address['geonames_city']['city'] = v2_location['geonames_details']['name']:
    v1_addresses.append(v1_address)
    return v1_addresses

# country
def format_country(v2_locations):
    v2_location = v2_locations[0]
    v1_country = copy.deepcopy(v1_fields.v1_country_template)
        # temp until missing geonames IDs/names are fixed
    if v2_location['geonames_details']:
        if v2_location['geonames_details']['country_code']:
            v1_country['country_code'] = v2_location['geonames_details']['country_code']
        if v2_location['geonames_details']['country_name']:
            v1_country['country_name'] = v2_location['geonames_details']['country_name']
    return v1_country

# name
def format_name(v2_names):
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ROR_DISPLAY'] in v2_name['types']:
            return v2_name['value']
    return None

# acronyms
def format_acronyms(v2_names):
    v1_acronyms = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ACRONYM'] in v2_name['types']:
            v1_acronyms.append(v2_name['value'])
    return v1_acronyms

# aliases
def format_aliases(v2_names):
    v1_aliases = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ALIAS'] in v2_name['types']:
            v1_aliases.append(v2_name['value'])
    return v1_aliases

# labels
def format_aliases(v2_names):
    v1_labels = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['LABEL'] in v2_name['types'] and v2_enums.NAME_TYPES['ROR_DISPLAY'] not in v2_name['types']:
            v1_label = copy.deepcopy(v1_fields.v1_label_template)
            v1_label['label'] = v2_name['value']
            v1_label['iso639'] = v2_name['lang']
            v1_labels.append(v1_label)
    return v1_labels

def convert_v2_to_v1(v2_data):
    try:
        with open(V1_TEMPLATE) as template_file:
            v1_data = json.load(template_file)
            # these fields don't change
            v1_data['id'] = v2_data['id']
            v1_data['types'] = [type.lower() for type in v2_data['types']]
            v1_data['status'] = v2_data['status']
            v1_data['established'] = v2_data['established']
            v1_data['email_address'] = None
            v1_data['ip_addresses'] = []
            # these fields DO change
            v1_data['relationships'] = format_relationships(v2_data['relationships'])
            v1_data['external_ids'] = format_external_ids(v2_data['external_ids'])
            v1_data['links'] = format_links(v2_data['links'])
            v1_data['wikipedia_url'] = format_wikipedia_url(v2_data['links'])
            v1_data['addresses'] = format_addresses(v2_data['locations'])
            v1_data['country'] = format_addresses(v2_data['locations'])
            v1_data['name'] = format_name(v2_data['names'])
            v1_data['acronyms'] = format_acronyms(v2_data['names'])
            v1_data['aliases'] = format_aliases(v2_data['names'])
            v1_data['labels'] = format_labels(v2_data['names'])
            return v1_data
    except Exception as e:
        logging.error(f"Error converting v1 data to v2: {e}")

def create_v1_dump(v2_dump_zip_path):
    file_date = extract_date(os.path.split(v2_dump_zip_path)[1])
    print("file date is:")
    print(file_date)
    v2_dump_unzipped = ''
    v1_records = []
    with ZipFile(v2_dump_zip_path, "r") as zf:
        json_files_count = sum('.json' in s for s in zf.namelist())
        if json_files_count == 1:
            for name in zf.namelist():
                # assumes ror-data zip will only contain 1 JSON file
                if '.json' in name:
                    v2_dump_unzipped = zf.extract(name, INPUT_PATH)
        else:
            print("Dump zip contains multiple json files. Something is wrong.")

    #try:
    f = open(v2_dump_unzipped, 'r')
    v2_records = json.load(f)
    print(str(len(v2_records)) + " records in v2 dump")
    for v2_record in v2_records:
        print("processing dump record " + str(v2_record['id']))
        v1_record = convert_v2_to_v1(v2_record)
        v1_records.append(v1_record)
    print(str(len(v1_records)) + " to be added to v1 dump")
    path, file = os.path.split(v2_dump_unzipped)
    filename = file.strip(".json")
    open(OUTPUT_PATH + filename + ".json", "w").write(
        json.dumps(v1_records, indent=4, separators=(',', ': '))
    )
    if os.path.exists(OUTPUT_PATH + filename + ".json"):
        return OUTPUT_PATH + filename + ".json"
    else:
        return None


def create_v1_file(v2_file):
    try:
        with open(v2_file) as infile:
            v2_data = json.load(infile)
            ror_id = re.sub('https://ror.org/', '', v2_data['id'])
            v1_record_data = convert_v2_to_v1(v2_data)
        with open(OUTPUT_PATH + ror_id + ".json", "w") as writer:
            writer.write(
            json.dumps(v1_record_data, indent=4, separators=(',', ': '))
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
                convert_to_csv.get_all_data(v1_dump_file)
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

