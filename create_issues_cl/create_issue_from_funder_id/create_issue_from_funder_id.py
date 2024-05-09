import os
import sys
import requests
from github import Github

TOKEN = os.environ.get('GITHUB_TOKEN_PERSONAL')
g = Github(TOKEN)
repo = g.get_repo("ror-community/ror-updates")


def get_funder_registry_record(funder_id):
    funder_record_url = f'https://api.crossref.org/funders/{funder_id}'
    response = requests.get(funder_record_url)
    if response.status_code == 200:
        funder_record = response.json()
        return funder_record['message']
    return None


def find_id_in_hierarchy(hierarchy, target_id, current_path=None):
    if current_path is None:
        current_path = []
    for id, sub_hierarchy in hierarchy.items():
        new_path = current_path + [id]
        if id == target_id:
            return new_path[-2] if len(new_path) > 1 else None
        if isinstance(sub_hierarchy, dict) and sub_hierarchy:
            result = find_id_in_hierarchy(sub_hierarchy, target_id, new_path)
            if result:
                return result
    return None


def get_ror_id_from_funder_id(funder_id):
    query_url = f'https://api.ror.org/organizations?query="{funder_id}"'
    response = requests.get(query_url)
    if response.status_code == 200:
        results = response.json()
        if results['items'] != []:
            return results['items'][0]['id']
    return funder_id


def create_github_issue(funder_id):
    funder_record = get_funder_registry_record(funder_id)
    if funder_record != None:
        name = funder_record['name']
        crossref_funder_id = funder_record['id']
        funder_aliases = funder_record['alt-names']
        if funder_aliases != []:
            if len(funder_aliases) == 1:
                aliases = funder_aliases[0]
            else:
                aliases = '; '.join(funder_aliases)
        else:
            aliases = ''
        parent = find_id_in_hierarchy(funder_record['hierarchy'],funder_id)
        if parent is not None:
            parent = get_ror_id_from_funder_id(parent)
            parent = parent + ' (parent)'
        else:
            parent = ''
        country = funder_record['location']
        issue_title = f"Add a new organization to ROR: {name}"
        issue_body = f"""
Summary of request: Add a new organization to ROR

Name of organization: {name}
Website: 
Link to publications: 
Organization type:
Wikipedia page: 
Wikidata ID: 
ISNI ID: 
GRID ID: 
Crossref Funder ID: {crossref_funder_id}
Other names for the organization: 
Aliases: {aliases}
Labels: 
Acronym/abbreviation: 
Related organizations: {parent}
City: 
Country: {country}
Geonames ID: 
Year established: 
How will a ROR ID for this organization be used? To identify research funders.
Other information about this request: Part of Funder Registry reconciliation.
    """
        issue_labels = ["triage needed", "level 1", "new record", "jaguar"]
        issue = repo.create_issue(title=issue_title, body=issue_body, labels=issue_labels)
        return issue

if __name__ == '__main__':
    issue = create_github_issue(sys.argv[1])
    print(f"Created issue: {issue.html_url}")
