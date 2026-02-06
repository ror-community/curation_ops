import os
import re
import csv
import sys
import json
import time
import asyncio
import logging
import argparse
import requests
from github_project_issues import get_column_issues

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def get_ror_name(ror_id, max_retries=3, retry_delay=5):
    url = f'https://api.ror.org/v2/organizations/{ror_id}'
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            record = response.json()
            ror_display_name = get_ror_display_name(record)
            return ror_display_name
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to retrieve ROR name for {ror_id} after {max_retries} attempts.")
                return ""
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for {ror_id}. Response: {response.text}")
            return ""


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        match = s[start:end]
        match = match.strip()
        return match
    except ValueError:
        return ''


def dict_from_csv(f):
    ids_k_names_v, names_k_ids_v = {}, {}
    release_ids = []
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            ror_id = row['id']
            release_ids.append(ror_id)
            ror_display = row['names.types.ror_display']
            if ror_display and "==" not in ror_display:
                name = ror_display.split('*')[0]
            else:
                name = get_ror_name(ror_id)
            ids_k_names_v[ror_id] = name
            names_k_ids_v[name] = ror_id
    return release_ids, ids_k_names_v, names_k_ids_v


def extract_relationships(issues, input_file, output_file):
    release_ids, ids_k_names_v, names_k_ids_v = dict_from_csv(input_file)
    header = ['Issue # from Github', 'Issue URL', 'Issue title from Github', 'Name of org in Record ID', 'Record ID',
              'Related ID', 'Name of org in Related ID', 'Relationship of Related ID to Record ID', 'Current location of Related ID']
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        for issue in issues:
            issue_number = str(issue['number'])
            issue_title = issue['title']
            issue_text = issue['body']
            issue_url = issue['url']
            org_name, org_ror_id = '', ''
            rel_pattern = re.compile(
                r'[https]{0,5}\:\/\/ror\.org\/[a-z0-9]{9}\s+\([a-zA-Z\-]{0,}\)')
            relationships = rel_pattern.findall(issue_text)
            if relationships:
                org_ror_id = find_between(issue_text, 'ROR ID:', '\n')
                org_name = find_between(
                    issue_text, 'Name of organization:', '\n')
                org_name = org_name.split('*')[0]
                if not org_ror_id:
                    org_ror_id = names_k_ids_v.get(org_name, '')
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
                    locations = ['Release', 'Release'] if related_ror_id in release_ids else [
                        'Production', 'Release']
                    entry = [issue_number, issue_url, issue_title, org_name, org_ror_id,
                             related_ror_id, related_name, relationship_type, locations[0]]
                    rel_type_mappings = {'Parent': 'Child', 'Child': 'Parent',
                                         'Successor': 'Predecessor', 'Predecessor': 'Successor', 'Related': 'Related', 'Delete': 'Delete'}
                    if relationship_type == 'Successor-np':
                        entry = [issue_number, issue_url, issue_title, org_name,
                                 org_ror_id, related_ror_id, related_name, 'Successor', locations[0]]
                        writer.writerow(entry)
                    elif relationship_type == 'Predecessor-ns':
                        entry = [issue_number, issue_url, issue_title, org_name,
                                 org_ror_id, related_ror_id, related_name, 'Predecessor', locations[0]]
                        writer.writerow(entry)
                    else:
                        try:
                            inverted_entry = [issue_number, issue_url, issue_title, related_name, related_ror_id,
                                              org_ror_id, org_name, rel_type_mappings[relationship_type], locations[1]]
                        except KeyError:
                            inverted_entry = [issue_number, issue_url, issue_title,
                                              related_name, related_ror_id, org_ror_id, org_name, 'Error', 'Error']
                        writer.writerow(entry)
                        writer.writerow(inverted_entry)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract relationships from GitHub issues using GraphQL API.')
    parser.add_argument('-r', '--repo', default="ror-community/ror-updates",
                        help='GitHub repository name in the format owner/repo')
    parser.add_argument('-p', '--project_number', type=int, default=19,
                        help='GitHub project number')
    parser.add_argument('-c', '--column_name', default="Ready for production release",
                        help='Project column name where records are located')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Input CSV file with ROR data')
    parser.add_argument('-o', '--output_file', default='relationships.csv',
                        help='Output CSV file for relationships')
    return parser.parse_args()


async def main():
    args = parse_arguments()
    issues = await get_column_issues(
        args.repo, args.project_number, args.column_name)
    extract_relationships(issues, args.input_file, args.output_file)
    logger.info(f"Relationships extracted and saved to {args.output_file}")


if __name__ == '__main__':
    asyncio.run(main())
