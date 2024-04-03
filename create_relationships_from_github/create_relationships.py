import os
import re
import csv
import sys
import argparse
import requests
from github import Github


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def get_ror_name(ror_id):
    url = f'https://api.ror.org/v2/organizations/{ror_id}'
    record = requests.get(url).json()
    ror_display_name = get_ror_display_name(record)
    return ror_display_name


def dict_from_csv(f):
    ids_k_names_v, names_k_ids_v = {}, {}
    release_ids = []
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            ror_id = row['id']
            release_ids.append(ror_id)
            if row['names.types.ror_display']:
                name = row['names.types.ror_display']
            else:
                name = get_ror_name(ror_id)
            ids_k_names_v[ror_id] = name
            names_k_ids_v[name] = ror_id
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


def extract_relationships(input_file, output_file):
    release_ids, ids_k_names_v, names_k_ids_v = dict_from_csv(input_file)
    header = ['Issue # from Github', 'Issue URL', 'Issue title from Github', 'Name of org in Record ID', 'Record ID',
              'Related ID', 'Name of org in Related ID', 'Relationship of Related ID to Record ID', 'Current location of Related ID']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
    g = Github(os.environ['GITHUB_TOKEN'])
    repo = g.get_repo("ror-community/ror-updates")
    project = repo.get_projects()[0]
    columns = project.get_columns()
    ready_for_prod = [column for column in columns if column.name == 'Ready for sign-off / metadata QA'][0]
    cards = ready_for_prod.get_cards()
    issues = []
    for card in cards:
        issue = card.get_content()
        if issue:
            issues.append(issue)
    for issue in issues:
        issue_number = issue.number
        issue_title = issue.title
        org_name, org_ror_id = '', ''
        issue_body = issue.body
        issue_text = issue_body + \
            ' '.join([comment.body for comment in issue.get_comments()])
        issue_html_url = issue.html_url
        rel_pattern = re.compile(
            r'[https]{0,5}\:\/\/ror\.org\/[a-z0-9]{9}\s+\([a-zA-Z\-]{0,}\)')
        relationships = rel_pattern.findall(issue_text)
        if relationships:
            org_ror_id = find_between(issue_body, 'ROR ID:', '\n')
            org_name = find_between(issue_body, 'Name of organization:', '\n')
            if not org_ror_id:
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
                        related_name = ''
                else:
                    related_name = get_ror_name(related_ror_id)
                with open(output_file, 'a') as f_out:
                    writer = csv.writer(f_out)
                    locations = ['Release', 'Release'] if related_ror_id in release_ids else [
                        'Production', 'Release']
                    entry = [issue_number, issue_html_url, issue_title, org_name, org_ror_id,
                             related_ror_id, related_name, relationship_type, locations[0]]
                    rel_type_mappings = {'Parent': 'Child', 'Child': 'Parent',
                                         'Successor': 'Predecessor', 'Predecessor': 'Successor', 'Related': 'Related'}
                    if relationship_type == 'Successor-np':
                        entry = [issue_number, issue_html_url, issue_title, org_name,
                                 org_ror_id, related_ror_id, related_name, 'Successor', locations[0]]
                        writer.writerow(entry)
                    elif relationship_type == 'Predecessor-ns':
                        entry = [issue_number, issue_html_url, issue_title, org_name,
                                 org_ror_id, related_ror_id, related_name, 'Predecessor', locations[0]]
                        writer.writerow(entry)
                    else:
                        try:
                            inverted_entry = [issue_number, issue_html_url, issue_title, related_name, related_ror_id,
                                              org_ror_id, org_name, rel_type_mappings[relationship_type], locations[1]]
                        except KeyError:
                            inverted_entry = [issue_number, issue_html_url, issue_title,
                                              related_name, related_ror_id, org_ror_id, org_name, 'Error', 'Error']
                        writer.writerow(entry)
                        writer.writerow(inverted_entry)


def main():
    parser = argparse.ArgumentParser(
        description='Extract relationships from GitHub issues.')
    parser.add_argument('-i', '--input', required=True,
                        help='Input CSV file (default: relationships.csv)')
    parser.add_argument('-o', '--output', default='relationships.csv',
                        help='Output CSV file (default: output_relationships.csv)')
    args = parser.parse_args()
    extract_relationships(args.input, args.output)


if __name__ == '__main__':
    main()
