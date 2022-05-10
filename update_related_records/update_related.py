import os
import re
import sys
import json
import glob
import requests


def download_record(ror_id):
    api_url = 'https://api.ror.org/organizations/' + ror_id
    short_id = re.sub('https://ror.org/', '', ror_id)
    json_file_path = os.getcwd() + '/' + short_id + '.json'
    ror_data = requests.get(api_url).json()
    with open(json_file_path, 'w', encoding='utf8') as f_out:
        json.dump(ror_data, f_out, ensure_ascii=False, indent=2)
    return json_file_path


def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()


def update_related_name(json_file, related_id, related_name):
    with open(json_file, 'r+', encoding='utf8') as json_in:
        json_data = json.load(json_in)
        relationships = json_data['relationships']
        for index, relationship in enumerate(relationships):
            if relationship['id'] == related_id:
                json_data['relationships'][index]['label'] = related_name
                export_json(json_data, json_in)


def update_related():
    json_files = [file for file in glob.glob("*.json")]
    for json_file in json_files:
        json_file_path = os.getcwd() + '/' + json_file
        with open(json_file_path, 'r+', encoding='utf8') as json_in:
            json_data = json.load(json_in)
            ror_id = json_data['id']
            name = json_data['name']
            relationships = json_data['relationships']
            if relationships != []:
                for relationship in relationships:
                    related_id = relationship['id']
                    short_related_filename = re.sub('https://ror.org/', '', related_id) + '.json'
                    if short_related_filename in json_files:
                        related_file_path = os.getcwd() + '/' + short_related_filename
                        update_related_name(related_file_path, ror_id, name)
                    else:
                        related_file_path = download_record(related_id)
                        update_related_name(related_file_path, ror_id, name)


if __name__ == '__main__':
    update_related()
