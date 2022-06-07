import os
import sys
import json
import glob
import urllib
import itertools
import requests
from thefuzz import fuzz

def clean_org_name(org_name):
    org_name = org_name.lower()
    return org_name

def ror_search(org_name):
    query_url = 'https://api.ror.org/organizations?query="' + \
       org_name + '"'
    affiliation_url =  'https://api.ror.org/organizations?affiliation="' + \
       org_name + '"'
    all_urls = [query_url, affiliation_url]
    ror_matches = []
    for url in all_urls:
        api_response = requests.get(url).json()
        if api_response['number_of_results'] != 0:
            results = api_response['items']
            for result in results:
                if 'organization' in result.keys():
                    result = result['organization']
                ror_id = result['id']
                ror_name = result['name']
                aliases = result['aliases']
                labels = []
                if result['labels'] != []:
                    labels = [label['label'] for label in result['labels']]
                name_mr = fuzz.ratio(clean_org_name(org_name), clean_org_name(ror_name))
                if name_mr >= 90:
                    match_type = 'name match'
                    ror_matches.append([ror_id, ror_name, match_type])
                for alias in record['aliases']:
                    alias_mr = fuzz.ratio(clean_org_name(org_name), clean_org_name(alias))
                    if alias_mr >= 90:
                        match_type = 'alias match'
                        ror_matches.append([ror_id, ror_name, match_type])
                for label in record['labels']:
                    label_mr = fuzz.ratio(clean_org_name(org_name), clean_org_name(label))
                    if label_mr >= 90:
                        match_type = 'label match'
                        ror_matches.append([ror_id, ror_name, match_type])
                elif 'relationships' in result:
                    for relationship in result['relationships']:
                        rel_mr = fuzz.ratio(clean_org_name(org_name), clean_org_name(relationship['label']))
                        if rel_mr >= 90:
                            match_type = 'relationship'
                            ror_matches.append([relationship['id'], relationship['label'], match_type])
    ror_matches = list(ror_matches for ror_matches,_ in itertools.groupby(ror_matches))
    return ror_matches

def search_json():
    for file in glob.glob("*.json"):
        with open(file, 'r+') as f_in:
            json_file = json.load(f_in)
        ror_id = json_file['id']
        org_name = json_file['name']
        all_names = [org_name]
        if json_file['aliases'] != []:
            all_names += json_file['aliases']
        if json_file['labels'] != []:
            all_names += [label['label'] for label in json_file['labels']]
        for name in all_names:
            ror_search(name)

if __name__ == '__main__':
    search_json()
