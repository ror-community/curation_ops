import os
import csv
import argparse
import requests
from github import Github
from time import sleep


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Create GitHub issues from a CSV file.')
    parser.add_argument('-i', '--input-file', required=True,
                        help='Path to the CSV file')
    parser.add_argument('-t', '--issue-type', required=True,
                        choices=['new', 'update'], help='Type of issue to create')
    parser.add_argument('-a', '--append-description',
                        help='Additional description to append to the issue body')
    parser.add_argument('-f', '--format', choices=['bulk', 'api'], default='bulk',
                        help='CSV file format: bulk (default) or api')
    parser.add_argument('-p', '--parent-issue', type=int,
                        help='Parent issue number to add created issues as sub-issues')
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


def add_sub_issue(repo, parent_issue_number, sub_issue):
    """Add a sub-issue to a parent issue using PyGithub's native method"""
    try:
        parent_issue = repo.get_issue(parent_issue_number)
        parent_issue.add_sub_issue(sub_issue.id)
        print(f"Successfully added issue #{sub_issue.number} as sub-issue to #{parent_issue_number}")
    except Exception as e:
        print(f"Failed to add sub-issue: {str(e)}")


def create_new_issue_bulk(repo, record):
    title_name = record.get('Organization name*', '').split("*")[0]
    issue_title = f"Add a new organization to ROR: {title_name}"
    
    # Handle potential empty values
    org_name = record.get('Organization name*', '')
    website = record.get('Organization website*', '')
    domains = record.get('Organization domain*', '')
    publications_link = record.get('Link to publications associated with this organization*', '')
    org_type = record.get('Type of organization*', '')
    wikipedia = record.get('Wikipedia page', '')
    wikidata_id = record.get('Wikidata ID', '')
    isni_id = record.get('ISNI ID', '')
    grid_id = record.get('GRID ID', '')
    fundref_id = record.get('Crossref Funder ID', '')
    aliases = record.get('Name variations', '')
    acronym = record.get('Acronym (separate multiples with semicolon)', '')
    labels = record.get('Names in other languages (separate multiples with semicolon)', '')
    relationships = format_relationships(record)
    city = record.get('City where org is located*', '')
    country = record.get('Country where org is located*', '')
    geonames_id = record.get('Geonames ID', '')
    established = record.get('Year established', '')
    comments = record.get('Requestor comments', '')
    
    issue_body = f"""
Summary of request: Add a new organization to ROR

Add record:
Name of organization: {org_name}
Website: {website}
Domains: {domains}
Link to publications: {publications_link}
Organization type: {org_type}
Wikipedia page: {wikipedia}
Wikidata ID: {wikidata_id}
ISNI ID: {isni_id}
GRID ID: {grid_id}
Crossref Funder ID: {fundref_id}
Other names for the organization:
Aliases: {aliases}
Acronym/abbreviation: {acronym}
Labels: {labels}
Related organizations: {relationships}
City: {city}
Country: {country}
Geonames ID: {geonames_id}
Year established: {established}
Other information about this request: {comments}
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


def create_new_issue_api(repo, record):
    title_name = record['names.types.ror_display']
    issue_title = f"Add a new organization to ROR: {title_name}"
    aliases = record.get('names.types.alias', '')
    labels = record.get('names.types.label', '')
    acronym = record.get('names.types.acronym', '')
    website = record.get('links.type.website', '')
    wikipedia = record.get('links.type.wikipedia', '')
    domains = record.get('domains', '')
    org_type = record.get('types', '')
    wikidata_id = record.get('external_ids.type.wikidata.preferred', '')
    isni_id = record.get('external_ids.type.isni.preferred', '')
    grid_id = record.get('external_ids.type.grid.preferred', '')
    fundref_id = record.get('external_ids.type.fundref.preferred', '')
    city = record.get('city', '')
    country = record.get('country', '')
    established = record.get('established', '')
    
    issue_body = f"""
Summary of request: Add a new organization to ROR

Add record:
Name of organization: {title_name}
Website: {website}
Domains: {domains}
Link to publications: 
Organization type: {org_type}
Wikipedia page: {wikipedia}
Wikidata ID: {wikidata_id}
ISNI ID: {isni_id}
GRID ID: {grid_id}
Crossref Funder ID: {fundref_id}
Other names for the organization:
Aliases: {aliases}
Acronym/abbreviation: {acronym}
Labels: {labels}
Related organizations: 
City: {city}
Country: {country}
Geonames ID: 
Year established: {established}
Other information about this request: 
"""
    issue_labels = ["triage needed", "level 1", "new record", "jaguar"]
    issue = repo.create_issue(
        title=issue_title, body=issue_body, labels=issue_labels)
    return issue


def main():
    args = parse_arguments()
    records = read_csv(args.input_file)
    github_token = os.environ.get('GITHUB_TOKEN_PERSONAL')
    g = Github(github_token)
    repo = g.get_repo("ror-community/ror-updates")
    for record in records:
        if args.issue_type == 'new':
            if args.format == 'bulk':
                if record.get('Organization name*'):
                    issue = create_new_issue_bulk(repo, record)
                    print(f"Created new issue: {issue.html_url}")
                    if args.parent_issue:
                        add_sub_issue(repo, args.parent_issue, issue)
            elif args.format == 'api':
                if record.get('names.types.ror_display'):
                    issue = create_new_issue_api(repo, record)
                    print(f"Created new issue: {issue.html_url}")
                    if args.parent_issue:
                        add_sub_issue(repo, args.parent_issue, issue)
        elif args.issue_type == 'update':
            if args.format == 'bulk':
                ror_id = record['ROR ID'].strip()
                fields = record['Fields']
                description = record['Description of change']
                if args.append_description:
                    description += f" {args.append_description}"
                issue = create_update_issue(repo, ror_id, fields, description)
                print(f"Created update issue for {ror_id}: {issue.html_url}")
                if args.parent_issue:
                    add_sub_issue(repo, args.parent_issue, issue)
            elif args.format == 'api':
                print(f"Update issues are not supported for API format")
        sleep(10)


if __name__ == '__main__':
    main()
