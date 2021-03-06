import os
import re
import csv
import sys
import json
import requests


GITHUB = {}
GITHUB['USER'] = ''
GITHUB['TOKEN'] = ''

# Input here is a CSV file containing the Github issue url, ROR ID, 
# and name for each file in the release, both new and update records.
def dict_from_csv(f):
    ids_k_names_v, names_k_ids_v = {}, {}
    release_ids = []
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            release_ids.append(row['ror_id'])
            ids_k_names_v[row['ror_id']] = row['name']
            names_k_ids_v[row['name']] = row['ror_id']
    return release_ids, ids_k_names_v, names_k_ids_v


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        match = s[start:end]
        match = match.strip()
        return match
    except ValueError:
        return ''


def get_issue_comments(comments_url):
    comments = requests.get(comments_url, auth=(
        GITHUB['USER'], GITHUB['TOKEN'])).json()
    if comments != []:
        comments_text = []
        for comment in comments:
            text = comment['body']
            comments_text.append(text)
        return ' '.join(comments_text)
    else:
        return ''


def get_ror_name(ror_id):
    url = 'https://api.ror.org/organizations/' + ror_id
    ror_data = requests.get(url).json()
    return ror_data['name']


def extract_relationships(f):
    pages = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    api_urls = []
    release_ids, ids_k_names_v, names_k_ids_v = dict_from_csv(f)
    outfile = os.getcwd() + '/relationships.csv'
    header = ['Issue # from Github', 'Issue URL', 'Issue title from Github', 'Name of org in Record ID', 'Record ID',
              'Related ID', 'Name of org in Related ID', 'Relationship of Related ID to Record ID', 'Current location of Related ID']
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    # approved column url
    url = 'https://api.github.com/projects/columns/18464412/cards'
    for page in pages:
        params = {'page': page, 'per_page': 100}
        cards = requests.get(url, auth=(
            GITHUB['USER'], GITHUB['TOKEN']), params=params).json()
        for card in cards:
            if 'content_url' in card:
                api_urls.append(card['content_url'])
    for api_url in api_urls:
        issue_data = requests.get(api_url, auth=(
            GITHUB['USER'], GITHUB['TOKEN'])).json()
        issue_number = issue_data['number']
        issue_title = issue_data['title']
        org_name, org_ror_id = '', ''
        issue_body = issue_data['body']
        issue_text = issue_body + \
            get_issue_comments(api_url + '/comments')
        issue_html_url = issue_data['html_url']
        rel_pattern = re.compile(
            r'[https]{0,5}\:\/\/ror\.org\/[a-z0-9]{9}\s+\([a-zA-Z]{0,}\)')
        relationships = rel_pattern.findall(issue_text)
        if relationships != []:
            org_ror_id = find_between(issue_body, 'ROR ID:', '\n')
            org_name = find_between(issue_body, 'Name of organization:','\n')
            if org_ror_id == '':
                org_ror_id = names_k_ids_v[org_name]
            for relationship in relationships:
                relationship = relationship.split(' ')
                relationship = [r.strip() for r in relationship if r != '']
                related_ror_id = relationship[0].strip()
                relationship_type = relationship[1].strip().lower()
                relationship_type = re.sub(r'[()]', '', relationship_type)
                relationship_type = relationship_type.capitalize()
                if related_ror_id in release_ids:
                    try:
                        related_name = ids_k_names_v[related_ror_id]
                    except KeyError:
                        related_name == ''
                else:
                    related_name = get_ror_name(related_ror_id)
                with open(outfile, 'a') as f_out:
                    locations = ['Release', 'Release'] if related_ror_id in release_ids else ['Production', 'Release']
                    rel_type_mappings = {'Parent': 'Child', 'Child': 'Parent',
                                         'Related': 'Related'}
                    entry = [issue_number, issue_html_url, issue_title, org_name,
                             org_ror_id, related_ror_id, related_name, relationship_type, locations[0]]
                    try:
                        inverted_entry = [issue_number, issue_html_url, issue_title, related_name,
                                          related_ror_id, org_ror_id, org_name, rel_type_mappings[relationship_type], locations[1]]
                    except KeyError:
                        inverted_entry = [issue_number, issue_html_url, issue_title, related_name,
                                          related_ror_id, org_ror_id, org_name, 'Error', 'Error']
                    writer = csv.writer(f_out)
                    writer.writerow(entry)
                    writer.writerow(inverted_entry)


if __name__ == '__main__':
    extract_relationships(sys.argv[1])
