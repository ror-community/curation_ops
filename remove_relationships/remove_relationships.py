import argparse
from curses import noecho
import json
import os
import logging
import requests
import sys
from urllib.parse import urlparse
from datetime import datetime

ERROR_LOG = "relationship_errors.log"
logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')
V1_API_URL = "http://api.ror.org/v1/organizations/"
V2_API_URL = "http://api.ror.org/v2/organizations/"
UPDATED_RECORDS_PATH = "updates/"
INACTIVE_STATUSES = ('inactive', 'withdrawn')
LAST_MOD_DATE =  datetime.now().strftime("%Y-%m-%d")

def remove_relationships_from_file(inactive_id, related_filepath, version):
    removed_relationships = {}
    try:
        with open(related_filepath, 'r+') as f:
            file_data = json.load(f)
            if (file_data['status'] =='active') and len(file_data['relationships']) > 0:
                original_relationships = file_data['relationships']
                updated_relationships = [r for r in original_relationships if ((not r['id'] == inactive_id) or (r['id'] == inactive_id and r['type'].lower() == 'predecessor'))]
                file_data['relationships'] = updated_relationships
                if version == 2:
                    file_data['admin']['last_modified']['date'] = LAST_MOD_DATE
                f.seek(0)
                json.dump(file_data, f, ensure_ascii=False, indent=2)
                f.truncate()
                removed_relationships.update({file_data['id']: [r for r in original_relationships if r not in updated_relationships]})
        removed_relationships_pruned = {k:v for k,v in removed_relationships.items() if v}
    except Exception as e:
        logging.error(f"Error opening file {related_filepath}: {e}")
    return removed_relationships_pruned

def get_record(id, filename, inactive_id, version):
    filepath = ''
    api_url = V2_API_URL if version == 2 else V1_API_URL
    download_url=api_url + id
    if not os.path.exists(UPDATED_RECORDS_PATH):
        os.makedirs(UPDATED_RECORDS_PATH)
    try:
        rsp = requests.get(download_url)
    except requests.exceptions.RequestException as e:
        logging.error(f"Request for {download_url}: {e}")

    try:
        response = rsp.json()
        if (response['status'] =='active') and len(response['relationships']) > 0:
            inactive_relationships = [r for r in response['relationships'] if (r['id'] == inactive_id and r['type'].lower() != 'predecessor')]
            if len(inactive_relationships) > 0:
                with open(UPDATED_RECORDS_PATH + filename, "w", encoding='utf8') as f:
                    json.dump(response, f,  ensure_ascii=False)
                filepath = check_file(filename)
    except Exception as e:
        logging.error(f"Error writing {filename}: {e}")
    return filepath

def check_file(file):
    filepath = ''
    for root, dirs, files in os.walk(".", topdown=True):
        if file in files:
            filepath = (os.path.join(root, file))
    return filepath

def get_inactive_ids_relationships():
    inactive_ids_relationships = {}
    for root, dirs, files in os.walk(".", topdown=True):
        for file in files:
            filename, file_extension = os.path.splitext(file)
            if file_extension == '.json':
                filepath = (os.path.join(root, file))
                try:
                    with open(filepath, 'r+') as f:
                        file_data = json.load(f)
                        if file_data['status'] in INACTIVE_STATUSES and len(file_data['relationships']) > 0:
                            inactive_ids_relationships.update({file_data['id']: file_data['relationships']})
                except Exception as e:
                    logging.error(f"Error opening file {filepath}: {e}")
    return inactive_ids_relationships

def remove_relationships(version):
    all_removed_relationships = []
    no_relationship_in_related_file = []
    inactive_ids_relationships = get_inactive_ids_relationships()
    print("Found relationship(s) in " + str(len(inactive_ids_relationships)) + " inactive record(s):")
    print(inactive_ids_relationships)
    for inactive_id, relationships in inactive_ids_relationships.items():
        for relationship in relationships:
            related_filename = urlparse(relationship['id']).path + ".json"
            related_filename = related_filename.strip("/")
            related_filepath = check_file(related_filename)
            # download record if it's not already in updates dir
            # get_record() checks if relationship actually exists in record before downloading
            if related_filepath == '':
                related_filepath = get_record(relationship['id'], related_filename, inactive_id, version)
            # get_record() returns empty string if record not downloaded bc relationship doesn't exist
            if related_filepath != '':
                removed_relationships = remove_relationships_from_file(inactive_id, related_filepath, version)
                all_removed_relationships.append(removed_relationships)
            else:
                no_relationship_in_related_file.append([inactive_id, relationship])
    all_removed_relationships_pruned = [r for r in all_removed_relationships if r]
    return all_removed_relationships_pruned, no_relationship_in_related_file

def main(version):
    removed_relationships, no_relationship_in_related_file = remove_relationships(version)
    print(str(len(removed_relationships)) + " relationship(s) removed")
    if len(removed_relationships) > 0:
        print(removed_relationships)
    if len(no_relationship_in_related_file) > 0:
        print(str(len(no_relationship_in_related_file)) + " relationship(s) in inactive record(s) were not found in correspoding related record(s) or were of type Predecessor, so were not removed")
        print(no_relationship_in_related_file)
    file_size = os.path.getsize(ERROR_LOG)
    if (file_size == 0):
        os.remove(ERROR_LOG)
    elif (file_size != 0):
        print("ERRORS RECORDED IN relationship_errors.log")
        with open(ERROR_LOG, 'r') as f:
            print(f.read())
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to updated organization names on related records")
    parser.add_argument('-v', '--schemaversion', choices=[1, 2], type=int, required=True, help='Schema version (1 or 2)')
    args = parser.parse_args()
    main(args.schemaversion)
