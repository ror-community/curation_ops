import os
import re
import json
import requests
import update_address

API_URL = "http://api.ror.org/organizations/"
UPDATED_RECORDS_PATH = "updates/"
updated_file_report = []

def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()

def update_release_file(release_file, related_id, related_name):
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
                    export_json(release_file_data, json_in)
                    updated_file_report.append(['release', release_file, related_id, related_name])

def check_update_production_file(ror_id, related_id, related_name):
    api_record = API_URL + ror_id
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
                prod_record = update_address.update_geonames(prod_record)
                json_file = short_id + '.json'
                json_file_path = UPDATED_RECORDS_PATH + json_file
                with open(json_file_path, 'w', encoding='utf8') as f_out:
                    json.dump(prod_record, f_out, ensure_ascii=False, indent=2)
                updated_file_report.append(['production', ror_id, related_id, related_name])


def check_name_production(ror_id, related_name):
    api_record = API_URL + ror_id
    prod_record = requests.get(api_record).json()
    if prod_record['name'] == related_name:
        return True
    return False

def get_files(top):
    filepaths = []
    for dirpath, dirs, files in os.walk(top, topdown=True):
        for file in files:
            filepaths.append(os.path.join(dirpath, file))
    return filepaths

def update_related(initial_release_files):
    for json_file in initial_release_files:
        with open(json_file, 'r', encoding='utf8') as json_in:
            json_data = json.load(json_in)
            ror_id = json_data['id']
            name = json_data['name']
            relationships = json_data['relationships']
            print("Checking prod name for: " + ror_id + " " + name)
            same_name_check = check_name_production(ror_id, name)
            if relationships != [] and same_name_check == False:
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
                        update_release_file(related_file_path, ror_id, name)
                    else:
                        check_update_production_file(related_id, ror_id, name)

if __name__ == '__main__':
    update_related(get_files(UPDATED_RECORDS_PATH))
    print(str(len(updated_file_report)) + " relationships updated")
    print(updated_file_report)
