import os
import sys
import requests
from github import Github

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN_PERSONAL')
ROR_UPDATES_REPO = "ror-community/ror-updates"


def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(
        description='Create or update ROR records.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-n', '--new', action='store_true',
                       help='Create a new record')
    group.add_argument('-u', '--update', action='store_true',
                       help='Update an existing record')
    return parser.parse_args()


def get_ror_name(ror_id):
    response = requests.get(f"https://api.ror.org/organizations/{ror_id}")
    response.raise_for_status()
    return response.json()['name']


def create_new_record_issue():
    print("Creating a new record...")
    name = input("Name of organization: ")
    website = input("Website: ")
    website = input("Domains: ")
    link_to_publications = input("Link to publications: ")
    organization_type = input("Organization type: ")
    wikipedia_page = input("Wikipedia page: ")
    wikidata_id = input("Wikidata ID: ")
    isni_id = input("ISNI ID: ")
    grid_id = input("GRID ID: ")
    crossref_funder_id = input("Crossref Funder ID: ")
    other_names_for_the_organization = input(
        "Other names for the organization: ")
    aliases = input("Aliases: ")
    labels = input("Labels: ")
    acronym_abbreviation = input("Acronym/abbreviation: ")
    related_organizations = input("Related organizations: ")
    city = input("City: ")
    country = input("Country: ")
    geonames_id = input("Geonames ID: ")
    year_established = input("Year established: ")
    how_will_a_ror_id_for_this_organization_be_used = input(
        "How will a ROR ID for this organization be used? ")
    other_information_about_this_request = input(
        "Other information about this request: ")

    issue_title = f"Add a new organization to ROR: {name}"
    issue_body = f"""
    Summary of request: Add a new organization to ROR
    Name of organization: {name}
    Website: {website}
    Domains: {website}
    Link to publications: {link_to_publications}
    Organization type: {organization_type}
    Wikipedia page: {wikipedia_page}
    Wikidata ID: {wikidata_id}
    ISNI ID: {isni_id}
    GRID ID: {grid_id}
    Crossref Funder ID: {crossref_funder_id}
    Other names for the organization: {other_names_for_the_organization}
    Aliases: {aliases}
    Labels: {labels}
    Acronym/abbreviation: {acronym_abbreviation}
    Related organizations: {related_organizations}
    City: {city}
    Country: {country}
    Geonames ID: {geonames_id}
    Year established: {year_established}
    How will a ROR ID for this organization be used? {how_will_a_ror_id_for_this_organization_be_used}
    Other information about this request: {other_information_about_this_request}
    """
    issue_labels = ["triage needed", "level 1", "new record", "jaguar"]
    return create_github_issue(issue_title, issue_body, issue_labels)


def create_update_record_issue():
    print("Updating an existing record...")
    ror_id = input('Enter ROR ID: ').strip()
    name = get_ror_name(ror_id)
    fields = input('Enter fields to be changed: ')
    description = input('Enter description of change: ')

    issue_title = f"Modify the information in an existing ROR record: {name} - {ror_id}"
    issue_body = f"""
    Summary of request: Modify the information in an existing ROR record
    Name of organization: {name}
    ROR ID: {ror_id}
    Which part of the record needs to be changed? {fields}
    Description of change: {description}
    """
    issue_labels = ["triage needed", "level 2", "update record", "jaguar"]
    return create_github_issue(issue_title, issue_body, issue_labels)


def create_github_issue(title, body, labels):
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(ROR_UPDATES_REPO)
    issue = repo.create_issue(title=title, body=body, labels=labels)
    return issue


def main():
    args = parse_arguments()
    if args.new:
        issue = create_new_record_issue()
    elif args.update:
        issue = create_update_record_issue()
    print(f"Created issue: {issue.html_url}")


if __name__ == '__main__':
    main()
