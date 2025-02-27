import argparse
import os
import re
import json
import urllib
import requests
from datetime import datetime

V1_API_URL = "https://api.ror.org/v1/organizations"
V2_API_URL = "https://api.ror.org/v2/organizations"
INACTIVE_STATUSES = ('inactive', 'withdrawn')
UPDATED_RECORDS_PATH = "updates/"
LAST_MOD_DATE =  datetime.now().strftime("%Y-%m-%d")

updated_file_report = []

def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()

def update_release_file(release_file, related_id, related_name, version):
    with open(release_file, 'r+', encoding='utf8') as json_in:
        release_file_data = json.load(json_in)
        relationships = release_file_data['relationships']
        for index, relationship in enumerate(relationships):
            if relationship['id'] == related_id:
                if relationship['label'] != related_name:
                    print('Updating relationship label for release file:',
                          release_file_data['id'])
                    print('Current name:', release_file_data['relationships']
                          [index]['label'], '- Updated Name:', related_name)
                    release_file_data['relationships'][index]['label'] = related_name
                    if version == 2:
                        release_file_data['admin']['last_modified']['date'] = LAST_MOD_DATE
                    export_json(release_file_data, json_in)
                    updated_file_report.append(['release', release_file, related_id, related_name])

def check_update_production_file(ror_id, related_id, related_name, version):
    api_url = V2_API_URL if version == 2 else V1_API_URL
    api_record = api_url + '/' + ror_id
    short_id = re.sub('https://ror.org/', '', ror_id)
    prod_record = requests.get(api_record).json()
    relationships = prod_record['relationships']
    for index, relationship in enumerate(relationships):
        if relationship['id'] == related_id:
            if relationship['label'] != related_name:
                print('Updating relationship label for production record:', ror_id,)
                print('Current name:', prod_record['relationships']
                      [index]['label'], '- Updated Name:', related_name)
                prod_record['relationships'][index]['label'] = related_name
                if version == 2:
                    prod_record['admin']['last_modified']['date'] = LAST_MOD_DATE
                json_file = short_id + '.json'
                json_file_path = UPDATED_RECORDS_PATH + json_file
                with open(json_file_path, 'w', encoding='utf8') as f_out:
                    json.dump(prod_record, f_out, ensure_ascii=False, indent=2)
                updated_file_report.append(['production', ror_id, related_id, related_name])

def get_record_name(record, version):
    record_name = None
    if version == 2:
        ror_display  = [name for name in record['names'] if 'ror_display' in name['types']]
        record_name = ror_display[0]['value']
    if version == 1:
        record_name = record['name']
    return record_name


def check_name_production(ror_id, related_name, version):
    api_url = V2_API_URL if version == 2 else V1_API_URL
    print("API URL :")
    print(api_url)
    api_record = api_url + '/' + ror_id
    prod_record = requests.get(api_record).json()
    print("prod record name:")
    print(get_record_name(prod_record, version))
    if get_record_name(prod_record, version) == related_name:
        return True
    return False

def get_files(top):
    filepaths = []
    for dirpath, dirs, files in os.walk(top, topdown=True):
        for file in files:
            filepaths.append(os.path.join(dirpath, file))
    return filepaths

def check_update_inactive_prod(related_id, name, version):
    # check for inactive prod records with relationships(s) to record with updated name
    print("Checking for inactive records to update in prod")
    query = 'status:inactive OR status:withdrawn AND relationships.id:' + related_id
    escaped_query = urllib.parse.quote_plus(query.replace('https://ror.org/', 'https\:\/\/ror.org\/'))
    params = {'query.advanced': escaped_query}
    api_url = V2_API_URL if version == 2 else V1_API_URL
    response = requests.get(api_url, params=params).json()
    print(response)
    count = 0
    if len(response['items']) > 0:
        for item in response['items']:
            if item['status'] in INACTIVE_STATUSES and len(item['relationships']) > 0:
                for r in item['relationships']:
                    if r['id'] == related_id:
                        count += 1
                        check_update_production_file(related_id, item['id'], name)
    print("Found " + str(count) + " relationships to " + related_id + " in inactive prod records")


def check_update_inactive_release(related_id, name, version):
    # check for inactive release records with relationships(s) to record with updated name
    print("Checking for inactive records to update in release")
    count = 0
    for file in get_files("."):
        print(file)
        filename, file_extension = os.path.splitext(file)
        print(file_extension)
        if file_extension == '.json':
            with open(file, 'r+') as f:
                file_data = json.load(f)
                if file_data['status'] in INACTIVE_STATUSES and len(file_data['relationships']) > 0:
                    for r in file_data['relationships']:
                        if r['id'] == related_id:
                            count += 1
                            update_release_file(file, related_id, name, version)
    print("Found " + str(count) + " relationships to " + related_id + " in inactive release records")

def update_related(initial_release_files, version):
    for json_file in initial_release_files:
        with open(json_file, 'r', encoding='utf8') as json_in:
            json_data = json.load(json_in)
            ror_id = json_data['id']
            name = get_record_name(json_data, version)
            relationships = json_data['relationships']
            print("Checking prod name for: " + ror_id + " " + name)
            same_name_check = check_name_production(ror_id, name, version)
            if same_name_check == False:
                if relationships != []:
                    print("Checking", str(len(relationships)),
                        "relationships for ROR ID:", ror_id, '-', name)
                    for relationship in relationships:
                        related_id = relationship['id']
                        short_related_filename = re.sub(
                            'https://ror.org/', '', related_id) + '.json'
                        print("Checking record location for: " + related_id)
                        current_release_files = get_files(".")
                        if any(short_related_filename in file for file in current_release_files):
                            related_file_path = [file for file in current_release_files if short_related_filename in file][0]
                            update_release_file(related_file_path, ror_id, name, version)
                        else:
                            check_update_production_file(related_id, ror_id, name, version)
                print("Checking inactive records for relationships to record:", ror_id, '-', name)
                check_update_inactive_release(ror_id, name, version)
                check_update_inactive_prod(ror_id, name, version)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script to updated organization names on related records")
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Schema version (1 or 2)')
    args = parser.parse_args()
    update_related(get_files(UPDATED_RECORDS_PATH), args.schemaversion)
    print(str(len(updated_file_report)) + " relationships updated")
    print(updated_file_report)
