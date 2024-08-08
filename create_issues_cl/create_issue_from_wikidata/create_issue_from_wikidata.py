import os
import requests
from github import Github
import argparse


def get_location_entity(wikidata_id):
    try:
        url = 'https://www.wikidata.org/w/api.php?action=wbgetentities'
        params = {'ids': wikidata_id, 'format': 'json'}
        api_response = requests.get(url, params=params).json()
        entity = api_response['entities'][wikidata_id]
        labels = entity['labels']
        claims = entity['claims']
        location_name = labels.get('en', {}).get('value')
        geonames_id = claims.get('P1566', [{}])[0].get(
            'mainsnak', {}).get('datavalue', {}).get('value', None)
        if location_name is not None:
            return location_name, geonames_id
        else:
            return None, None
    except Exception:
        return None, None


def get_wikipedia_url(wikidata_id):
    url = 'https://www.wikidata.org/w/api.php?action=wbgetentities'
    params = {'props': 'sitelinks/urls', 'ids': wikidata_id, 'format': 'json'}
    api_response = requests.get(url, params=params).json()
    if 'sitelinks' in api_response['entities'][wikidata_id]:
        try:
            wikipedia_url = api_response['entities'][wikidata_id]['sitelinks']['enwiki']['url']
            return wikipedia_url
        except KeyError:
            for lang in api_response['entities'][wikidata_id]['sitelinks'].keys():
                if lang.endswith('wiki'):
                    if 'url' in api_response['entities'][wikidata_id]['sitelinks'][lang]:
                        wikipedia_url = api_response['entities'][wikidata_id]['sitelinks'][lang]['url']
                        return wikipedia_url
            return None
    else:
        return None


def get_organization_data(wikidata_id):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": wikidata_id,
        "languages": "en",
        "format": "json"
    }
    response = requests.get(url, params=params)
    data = response.json()

    entity = data['entities'][wikidata_id]
    labels = entity['labels']
    claims = entity['claims']

    # Extract relevant information
    name = labels['en']['value']
    website = claims['P856'][0]['mainsnak']['datavalue']['value'] if 'P856' in claims else None
    wikipedia_url = get_wikipedia_url(wikidata_id)
    wikidata_id = wikidata_id
    isni_id = claims['P213'][0]['mainsnak']['datavalue']['value'] if 'P213' in claims else None
    grid_id = claims['P2427'][0]['mainsnak']['datavalue']['value'] if 'P2427' in claims else None
    crossref_funder_id = claims['P3153'][0]['mainsnak']['datavalue']['value'] if 'P3153' in claims else None
    aliases = [alias['value'] for alias in labels['en']
               ['aliases']] if 'aliases' in labels['en'] else []
    acronym = claims['P1813'][0]['mainsnak']['datavalue']['value']['text'] if 'P1813' in claims else None
    city, geonames_id = get_location_entity(
        claims['P131'][0]['mainsnak']['datavalue']['value']['id']) if 'P131' in claims else (None, None)
    country, _ = get_location_entity(
        claims['P17'][0]['mainsnak']['datavalue']['value']['id']) if 'P17' in claims else (None, None)
    year_established = claims['P571'][0]['mainsnak']['datavalue']['value']['time'][1:5] if 'P571' in claims else None
    organization_data = {
        "name": name,
        "website": website,
        "wikipedia_url": wikipedia_url,
        "wikidata_id": wikidata_id,
        "isni_id": isni_id,
        "grid_id": grid_id,
        "crossref_funder_id": crossref_funder_id,
        "aliases": aliases,
        "acronym": acronym,
        "city": city,
        "country": country,
        "geonames_id": geonames_id,
        "year_established": year_established
    }

    return organization_data


def create_github_issue(repo, organization_data):
    record_type = input("Record type: ")
    issue_title = f"Add a new organization to ROR - {
        organization_data['name']}"
    issue_body = f"""
Summary of request: Add a new organization to ROR

Name of organization: {organization_data["name"]}
Website: {organization_data["website"]}
Link to publications:
Organization type: {record_type}
Wikipedia page: {organization_data["wikipedia_url"]}
Wikidata ID: {organization_data["wikidata_id"]}
ISNI ID: {organization_data["isni_id"]}
GRID ID: {organization_data["grid_id"]}
Crossref Funder ID: {organization_data["crossref_funder_id"]}
Other names for the organization: {', '.join(organization_data["aliases"])}
Aliases:
Labels:
Acronym/abbreviation: {organization_data["acronym"]}
Related organizations:
City: {organization_data["city"]}
Country: {organization_data["country"]}
Geonames ID: {organization_data["geonames_id"]}
Year established: {organization_data["year_established"]}
Other information about this request:
"""
    labels = ["triage needed", "level 1", "new record", "jaguar"]
    issue = repo.create_issue(
        title=issue_title, body=issue_body, labels=labels)
    return issue


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Process Wikidata ID to create a GitHub issue.')
    parser.add_argument('-i', '--wikidata_id',
                        help='Wikidata ID of the organization')
    args = parser.parse_args()
    return args


def main():
    TOKEN = os.environ.get('GITHUB_TOKEN')
    g = Github(TOKEN)
    repo = g.get_repo("ror-community/ror-updates")
    args = parse_arguments()
    organization_data = get_organization_data(args.wikidata_id)
    issue = create_github_issue(repo, organization_data)
    print(f"Created issue: {issue.html_url}")


if __name__ == '__main__':
    main()
