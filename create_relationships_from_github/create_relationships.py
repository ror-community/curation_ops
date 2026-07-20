import os
import re
import csv
import sys
import json
import time
import asyncio
import logging
import argparse
import unicodedata
from dataclasses import dataclass
import requests
from github_project_issues import get_column_issues

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RelationshipRow:
    issue_number: str
    issue_url: str
    issue_title: str
    record_name: str
    record_id: str
    related_id: str
    related_name: str
    rel_type: str
    location: str

    FIELD_LABELS = {
        'issue_number': 'Issue # from Github',
        'issue_url': 'Issue URL',
        'issue_title': 'Issue title from Github',
        'record_name': 'Name of org in Record ID',
        'record_id': 'Record ID',
        'related_id': 'Related ID',
        'related_name': 'Name of org in Related ID',
        'rel_type': 'Relationship of Related ID to Record ID',
        'location': 'Current location of Related ID',
    }

    @classmethod
    def header(cls):
        return list(cls.FIELD_LABELS.values())

    def to_csv_row(self):
        return {label: getattr(self, attr) for attr, label in self.FIELD_LABELS.items()}


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


# U+200B ZERO WIDTH SPACE, U+200C/200D ZERO WIDTH (NON-)JOINER,
# U+2060 WORD JOINER, U+FEFF ZERO WIDTH NO-BREAK SPACE
ZERO_WIDTH_CHARS_RE = re.compile('[\u200b\u200c\u200d\u2060\ufeff]')


def normalize_name(name):
    """Remove invisible characters and normalize whitespace in an org name.

    Names pasted into GitHub issues sometimes carry zero-width characters
    (notably U+200B). str.strip() does not remove them, so an otherwise
    identical name fails the exact-match lookup against the release CSV and
    the record's ROR ID is silently written as an empty string.
    """
    name = ZERO_WIDTH_CHARS_RE.sub('', name)
    name = unicodedata.normalize('NFKC', name)
    return ' '.join(name.split())


RELATED_ORGS_RE = re.compile(
    r'^[ \t]*Related organizations?:(.*)$', re.MULTILINE | re.IGNORECASE)


def related_orgs_field(issue_text):
    """Return only the text of the issue's 'Related organizations:' field.

    Relationships are declared in this field alone. Free-text fields such as
    'Description of change' often restate a relationship informally, and
    scanning the whole body treats that prose as an authoritative
    declaration, producing relationships the curator did not ask for.
    """
    return '\n'.join(RELATED_ORGS_RE.findall(issue_text))


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
            names_k_ids_v[normalize_name(name)] = ror_id
    return release_ids, ids_k_names_v, names_k_ids_v


def flag_circular_relationships(rows):
    contradictory_pairs = [
        frozenset({'Parent', 'Child'}),
        frozenset({'Successor', 'Predecessor'}),
    ]
    groups = {}
    for row in rows:
        if not row.record_id or not row.related_id:
            continue
        groups.setdefault((row.record_id, row.related_id), []).append(row)

    flagged = 0
    for group_rows in groups.values():
        types = {row.rel_type for row in group_rows}
        if any(pair.issubset(types) for pair in contradictory_pairs):
            for row in group_rows:
                row.rel_type = 'Error'
                flagged += 1
    if flagged:
        logger.warning(
            f"Flagged {flagged} row(s) with contradictory/circular relationships.")
    return rows


def extract_relationships(issues, input_file, output_file):
    release_ids, ids_k_names_v, names_k_ids_v = dict_from_csv(input_file)
    with open(output_file, 'w') as f_out:
        writer = csv.DictWriter(f_out, fieldnames=RelationshipRow.header())
        writer.writeheader()
        rows = []
        for issue in issues:
            issue_number = str(issue['number'])
            issue_title = issue['title']
            issue_text = issue['body']
            issue_url = issue['url']
            org_name, org_ror_id = '', ''
            rel_pattern = re.compile(
                r'[https]{0,5}\:\/\/ror\.org\/[a-z0-9]{9}\s+\([a-zA-Z\-]{0,}\)')
            relationships = rel_pattern.findall(related_orgs_field(issue_text))
            if relationships:
                org_ror_id = find_between(issue_text, 'ROR ID:', '\n')
                org_name = find_between(
                    issue_text, 'Name of organization:', '\n')
                org_name = normalize_name(org_name.split('*')[0])
                if not org_ror_id:
                    org_ror_id = names_k_ids_v.get(org_name, '')
                    if not org_ror_id:
                        logger.warning(
                            f"Issue {issue_number}: no ROR ID found for "
                            f"'{org_name}'. Record ID will be empty.")
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
                    rel_type_mappings = {'Parent': 'Child', 'Child': 'Parent',
                                         'Successor': 'Predecessor', 'Predecessor': 'Successor', 'Related': 'Related', 'Delete': 'Delete'}
                    if relationship_type == 'Successor-np':
                        rows.append(RelationshipRow(issue_number, issue_url, issue_title, org_name,
                                                    org_ror_id, related_ror_id, related_name, 'Successor', locations[0]))
                    elif relationship_type == 'Predecessor-ns':
                        rows.append(RelationshipRow(issue_number, issue_url, issue_title, org_name,
                                                    org_ror_id, related_ror_id, related_name, 'Predecessor', locations[0]))
                    else:
                        entry = RelationshipRow(issue_number, issue_url, issue_title, org_name, org_ror_id,
                                                related_ror_id, related_name, relationship_type, locations[0])
                        try:
                            inverted_entry = RelationshipRow(issue_number, issue_url, issue_title, related_name, related_ror_id,
                                                             org_ror_id, org_name, rel_type_mappings[relationship_type], locations[1])
                        except KeyError:
                            inverted_entry = RelationshipRow(issue_number, issue_url, issue_title, related_name,
                                                             related_ror_id, org_ror_id, org_name, 'Error', 'Error')
                        rows.append(entry)
                        rows.append(inverted_entry)
        flag_circular_relationships(rows)
        writer.writerows(row.to_csv_row() for row in rows)


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
