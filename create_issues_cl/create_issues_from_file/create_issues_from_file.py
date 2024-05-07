import os
import csv
import argparse
import requests
from github import Github
from time import sleep


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Create GitHub issues from a CSV file.')
    parser.add_argument('-f', '--file', required=True,
                        help='Path to the CSV file')
    parser.add_argument('-t', '--issue-type', required=True,
                        choices=['new', 'update'], help='Type of issue to create')
    parser.add_argument('-a', '--append-description',
                        help='Additional description to append to the issue body')
    return parser.parse_args()


def read_csv(file_path):
    with open(file_path, mode='r+', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        return list(reader)


def get_ror_display_name(record):
    return [name['value'] for name in record.get('names', []) if 'ror_display' in name.get('types', [])][0]


def get_ror_name(ror_id):
    url = f'https://api.ror.org/v2/organizations/{ror_id}'
    record = requests.get(url).json()
    ror_display_name = get_ror_display_name(record)
    return ror_display_name


def create_new_issue(repo, record):
    title_name = record['Organization name*'].split("*")[0]
    issue_title = f"Add a new organization to ROR: {title_name}"
    relationships = format_relationships(record)
    issue_body = f"""
    Summary of request: Add a new organization to ROR
    
    Add record:
    Name of organization: {record['Organization name*']}
    Website: {record['Organization website*']}
    Website: {record['Domains']}
    Link to publications: {record['Link to publications associated with this organization*']}
    Organization type: {record['Type of organization*']}
    Wikipedia page: {record['Wikipedia page']}
    Wikidata ID: {record['Wikidata ID']}
    ISNI ID: {record['ISNI ID']}
    GRID ID: {record['GRID ID']}
    Crossref Funder ID: {record['Crossref Funder ID']}
    Other names for the organization:
    Aliases: {record['Name variations']}
    Acronym/abbreviation: {record['Acronym (separate multiples with semicolon)']}
    Labels: {record['Names in other languages (separate multiples with semicolon)']}
    Related organizations: {relationships}
    City: {record['City where org is located*']}
    Country: {record['Country where org is located*']}
    Geonames ID: {record['Geonames ID']}
    Year established: {record['Year established']}
    Other information about this request: {record['Requestor comments']}
    """
    issue_labels = ["triage needed", "level 1", "new record", "jaguar"]
    issue = repo.create_issue(
        title=issue_title, body=issue_body, labels=issue_labels)
    return issue


def format_relationships(record):
    relationships = []
    relationship_types = {
        "Parent org in ROR": "parent",
        "Child org in ROR": "child",
        "Related org in ROR": "related"
    }
    for key, values in record.items():
        if key in relationship_types:
            for value in values.split(';'):
                if value.strip():
                    relationships.append(f"{value.strip()} ({relationship_types[key]})")
    return ';'.join(relationships)


def create_update_issue(repo, ror_id, fields, description):
    name = get_ror_name(ror_id)
    issue_title = f"Modify the information in an existing ROR record: {name} - {ror_id}"
    issue_body = f"""
    Summary of request: Modify the information in an existing ROR record
    
    Name of organization: {name}
    ROR ID: {ror_id}
    Which part of the record needs to be changed? {fields}
    Description of change: {description}
    """
    labels = ["triage needed", "level 2", "update record", "jaguar"]
    issue = repo.create_issue(
        title=issue_title, body=issue_body, labels=labels)
    return issue


def main():
    args = parse_arguments()
    records = read_csv(args.file)
    g = Github(os.environ.get('GITHUB_TOKEN'))
    repo = g.get_repo("ror-community/ror-updates")
    for record in records:
        if args.issue_type == 'new':
            if record['Organization name*']:
                issue = create_new_issue(repo, record)
                print(f"Created new issue: {issue.html_url}")
        elif args.issue_type == 'update':
            ror_id = record['ROR ID'].strip()
            fields = record['Fields']
            description = record['Description of change']
            if args.append_description:
                description += f" {args.append_description}"
            issue = create_update_issue(repo, ror_id, fields, description)
            print(f"Created update issue for {ror_id}: {issue.html_url}")
        sleep(10)


if __name__ == '__main__':
    main()
