import os
import re
import sys
import json
import glob
import copy
import requests

JSON_FILES = [re.sub('updates/', '', file)
              for file in glob.glob("updates/*.json")]
RELEASE_FILES = copy.deepcopy(JSON_FILES)


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


def check_update_production_file(ror_id, related_id, related_name):
    api_url = 'https://api.ror.org/organizations/' + ror_id
    short_id = re.sub('https://ror.org/', '', ror_id)
    prod_record = requests.get(api_url).json()
    relationships = prod_record['relationships']
    for index, relationship in enumerate(relationships):
        if relationship['id'] == related_id:
            if relationship['label'] != related_name:
                print('Updating relationship label for production record:', ror_id,)
                print('Current name:', prod_record['relationships']
                      [index]['label'], '- Updated Name:', related_name)
                prod_record['relationships'][index]['label'] = related_name
                json_file = short_id + '.json'
                json_file_path = os.getcwd() + '/updates/' + json_file
                with open(json_file_path, 'w', encoding='utf8') as f_out:
                    json.dump(prod_record, f_out, ensure_ascii=False, indent=2)
                    RELEASE_FILES.append(json_file)


def check_name_production(ror_id, related_name):
    api_url = 'https://api.ror.org/organizations/' + ror_id
    prod_record = requests.get(api_url).json()
    if prod_record['name'] == related_name:
        return True
    return False


def update_related():
    for json_file in JSON_FILES:
        json_file_path = os.getcwd() + '/updates/' + json_file
        with open(json_file_path, 'r+', encoding='utf8') as json_in:
            json_data = json.load(json_in)
            ror_id = json_data['id']
            name = json_data['name']
            relationships = json_data['relationships']
            same_name_check = check_name_production(ror_id, name)
            if relationships != [] and same_name_check == False:
                print("Checking", str(len(relationships)),
                      "relationships for ROR ID:", ror_id, '-', name)
                for relationship in relationships:
                    related_id = relationship['id']
                    short_related_filename = re.sub(
                        'https://ror.org/', '', related_id) + '.json'
                    if short_related_filename in RELEASE_FILES:
                        related_file_path = os.getcwd() + '/updates/' + short_related_filename
                        update_release_file(related_file_path, ror_id, name)
                    else:
                        check_update_production_file(related_id, ror_id, name)


if __name__ == '__main__':
    update_related()
