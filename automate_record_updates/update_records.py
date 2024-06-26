import os
import re
import sys
import csv
import json
import logging
import pkg_resources
import requests
import update_address
from collections import defaultdict
from datetime import datetime


def generate_json_dir():
    now = datetime.now()
    json_dir = f'{os.getcwd()}/{now.strftime("%Y%m%d_%H%M%S")}/'
    os.makedirs(json_dir)
    return json_dir


def download_record(ror_id, json_dir, geonames_id=None):
    json_file_path = os.path.join(json_dir, f'{ror_id}.json')
    if not os.path.exists(json_file_path):
        api_url = f'https://api.ror.org/organizations/{ror_id}'
        ror_data = requests.get(api_url, verify=False).json()
        if geonames_id is None:
            ror_data = update_address.update_geonames(ror_data)
        else:
            ror_data = update_address.update_geonames(ror_data, geonames_id)

        with open(json_file_path, 'w', encoding='utf8') as f_out:
            json.dump(ror_data, f_out, ensure_ascii=False, indent=2)
    else:
        print(f"File {json_file_path} already exists. Skipping download.")


def export_json(json_data, json_file):
    json_file.seek(0)
    json.dump(json_data, json_file, ensure_ascii=False, indent=2)
    json_file.truncate()


def change_nonrepeating_field(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        json_data[field] = value
        export_json(json_data, json_in)


def add_repeating_field(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        json_data[field].append(value)
        export_json(json_data, json_in)


def replace_repeating_field(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        json_data[field] = [value]
        export_json(json_data, json_in)


def delete_repeating_field(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        value_index = json_data[field].index(value)
        del json_data[field][value_index]
        export_json(json_data, json_in)


def load_iso_codes():
    iso639_file = pkg_resources.resource_filename(
        __name__, 'iso_data/iso639_mappings.csv')
    iso639_codes = {}
    with open(iso639_file) as f_in:
        reader = csv.reader(f_in)
        for row in reader:
            lang_code, lang = row[0], row[1]
            iso639_codes[lang] = lang_code
    return iso639_codes


def add_label(json_file, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        # Update text string uses the convention "label*language" to denote the two parts
        value = value.split('*')
        label_text, label_lang = value[0], value[1]
        iso639_codes = load_iso_codes()
        try:
            if label_lang in iso639_codes.values():
                json_data['labels'].append(
                    {'label': label_text, 'iso639': label_lang})
            else:
                lang_iso_code = iso639_codes[label_lang]
                json_data['labels'].append(
                    {'label': label_text, 'iso639': lang_iso_code})
            export_json(json_data, json_in)
        except KeyError:
            logging.error('Error:', label_lang,
                          'not found in iso639 standard.')
            sys.exit()


def replace_label(json_file, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        # Update text string uses the convention "label*language" to denote the two parts
        value = value.split('*')
        label_text, label_lang = value[0], value[1]
        iso639_codes = load_iso_codes()
        try:
            if label_lang in iso639_codes.values():
                json_data['labels'] = [
                    {'label': label_text, 'iso639': label_lang}]
            else:
                lang_iso_code = iso639_codes[label_lang]
                json_data['labels'] = [
                    {'label': label_text, 'iso639': lang_iso_code}]
            export_json(json_data, json_in)
        except KeyError:
            logging.error('Error:', label_lang,
                          'not found in iso639 standard.')
            sys.exit()


def delete_label(json_file, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        del_index = ''
        for index, label in enumerate(json_data['labels']):
            if label['label'] == value:
                del_index = index
        if del_index == '':
            logging.error('Error:', value, 'not found in labels.')
            sys.exit()
        else:
            del json_data['labels'][del_index]
            export_json(json_data, json_in)


def check_in_relationships(json_file, related_id):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        relationships = json_data['relationships']
        if relationships != []:
            related_ids = [relationship['id']
                           for relationship in relationships]
            if related_id in related_ids:
                return True
    return False


def delete_relationships(json_file, related_id):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        del_index = ''
        for index, relationship in enumerate(json_data['relationships']):
            if related_id in relationship['id']:
                del_index = index
        if del_index == '':
            logging.error('Error:', related_id, 'not found in relationships.')
            sys.exit()
        else:
            del json_data['relationships'][del_index]
            export_json(json_data, json_in)


def add_external_id(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        preferred = False
        if "preferred" in value:
            value = value.split("*")[0]
            preferred = True
        if field in json_data['external_ids'].keys():
            if json_data['external_ids'][field]['preferred'] != None:
                if preferred == True:
                    json_data['external_ids'][field]['preferred'] = value
                    json_data['external_ids'][field]['all'].append(value)
                else:
                    json_data['external_ids'][field]['all'].append(value)
            else:
                if preferred == True:
                    json_data['external_ids'][field]['preferred'] = value
                    json_data['external_ids'][field]['all'].append(value)
                else:
                    json_data['external_ids'][field]['all'].append(value)
        else:
            json_data['external_ids'][field] = {
                'preferred': value, 'all': [value]}
        export_json(json_data, json_in)


def replace_external_id(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        json_data['external_ids'][field] = {
            'preferred': value, 'all': [value]}
        export_json(json_data, json_in)


def delete_external_id(json_file, field, value):
    with open(json_file, 'r+') as json_in:
        json_data = json.load(json_in)
        all_values = json_data['external_ids'][field]['all']
        if isinstance(all_values, str):
            json_data['external_ids'][field]['all'] = [all_values]
        if value == json_data['external_ids'][field]['preferred'] and len(json_data['external_ids'][field]['all']) > 1:
            del_index = json_data['external_ids'][field]['all'].index(value)
            del json_data['external_ids'][field]['all'][del_index]
            json_data['external_ids'][field]['preferred'] = json_data['external_ids'][field]['all'][0]
        elif json_data['external_ids'][field]['preferred'] == None and len(json_data['external_ids'][field]['all']) > 1:
            del_index = json_data['external_ids'][field]['all'].index(value)
            del json_data['external_ids'][field]['all'][del_index]
        elif json_data['external_ids'][field]['preferred'] != None and len(json_data['external_ids'][field]['all']) > 1:
            del_index = json_data['external_ids'][field]['all'].index(value)
            del json_data['external_ids'][field]['all'][del_index]
        else:
            del json_data['external_ids'][field]
        export_json(json_data, json_in)


def parse_record_updates_file(f):
    # See test data for update string examples related to this parsing.
    record_updates = defaultdict(list)
    ror_fields = ['name', 'status', 'established', 'wikipedia_url', 'links', 'types',
                  'aliases', 'acronyms', 'Wikidata', 'ISNI', 'FundRef', 'GRID', 'labels', 'relationships', 'Geonames']
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            ror_id = re.sub('https://ror.org/', '', row['ror_id'])
            update_field = row['update_field']
            updates = update_field.split(';')
            updates = [u for u in updates if u.strip() != '']
            for update in updates:
                change_type = update.split('.')[0].strip()
                change_field = re.search(
                    r'(?<=\.)(.*)(?=\=\=)', update).group(1)
                change_field = change_field.strip()
                if change_field not in ror_fields:
                    print(
                        change_field, "is not a valid field. Please check coding on", row['html_url'])
                    sys.exit()
                change_value = update.split('==')[1].strip()
                if 'https://ror.org/' in change_value:
                    change_value = re.sub('https://ror.org/', '', change_value)
                record_updates[ror_id].append(
                    {'change_type': change_type, 'change_field': change_field, 'change_value': change_value})
    return record_updates


def update_records(record_updates):
    non_repeating_fields = ['name', 'status', 'established', 'wikipedia_url']
    repeating_fields = ['links', 'types', 'aliases', 'acronyms']
    external_ids = ['Wikidata', 'ISNI', 'FundRef', 'GRID']
    json_dir = generate_json_dir()
    for ror_id, record_changes in record_updates.items():
        print('Updating', ror_id, '...')
        all_change_fields = [r_c['change_field'] for r_c in record_changes]
        if 'Geonames' in all_change_fields:
            geonames_index = all_change_fields.index('Geonames')
            geonames_change = record_changes[geonames_index]
            geonames_id = geonames_change['change_value']
            download_record(ror_id, json_dir, geonames_id)
        elif 'relationships' in all_change_fields:
            download_record(ror_id, json_dir)
            related_ids = [update['change_value']
                           for update in record_changes if update['change_field'] == 'relationships']
            for related_id in related_ids:
                download_record(related_id, json_dir)
        else:
            download_record(ror_id, json_dir)
        json_file_path = json_dir + ror_id + '.json'
        for record_change in record_changes:
            if record_change['change_field'] in non_repeating_fields:
                change_nonrepeating_field(
                    json_file_path, record_change['change_field'], record_change['change_value'])
            if record_change['change_field'] in repeating_fields:
                if record_change['change_type'] == 'add':
                    add_repeating_field(
                        json_file_path, record_change['change_field'], record_change['change_value'])
                elif record_change['change_type'] == 'replace':
                    replace_repeating_field(
                        json_file_path, record_change['change_field'], record_change['change_value'])
                elif record_change['change_type'] == 'delete':
                    delete_repeating_field(
                        json_file_path, record_change['change_field'], record_change['change_value'])
            if record_change['change_field'] == 'labels':
                if record_change['change_type'] == 'add':
                    add_label(json_file_path,
                              record_change['change_value'])
                if record_change['change_type'] == 'replace':
                    replace_label(json_file_path,
                                  record_change['change_value'])
                if record_change['change_type'] == 'delete':
                    delete_label(json_file_path,
                                 record_change['change_value'])
            if record_change['change_field'] == 'relationships':
                related_id = record_change['change_value']
                related_file_path = f'{json_dir}{related_id}.json'
                full_related_id, full_ror_id = f'https://ror.org/{related_id}', f'https://ror.org/{ror_id}'
                delete_relationships(json_file_path, full_related_id)
                if check_in_relationships(related_file_path, full_ror_id):
                    delete_relationships(related_file_path, full_ror_id)
            if record_change['change_field'] in external_ids:
                if record_change['change_type'] == 'add':
                    add_external_id(
                        json_file_path, record_change['change_field'], record_change['change_value'])
                if record_change['change_type'] == 'replace':
                    replace_external_id(
                        json_file_path, record_change['change_field'], record_change['change_value'])
                if record_change['change_type'] == 'delete':
                    delete_external_id(
                        json_file_path, record_change['change_field'], record_change['change_value'])


if __name__ == '__main__':
    record_updates = parse_record_updates_file(sys.argv[1])
    update_records(record_updates)
