import os
import re
import sys
import string
import urllib
import itertools
import requests
import openai
from ast import literal_eval
from collections import defaultdict
from github import Github
from thefuzz import fuzz
from bs4 import BeautifulSoup
from detect_language import detect_language
from generate_aliases import generate_aliases
from search_geonames import search_geonames

USER = os.environ.get('GITHUB_USER')
TOKEN = os.environ.get('GITHUB_TOKEN')


def catch_requests_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            return None
    return wrapper


def normalize_text(text):
    text = re.sub('-', ' ', text)
    return ''.join(ch for ch in re.sub(r'[^\w\s-]', '', text.lower()) if ch not in set(string.punctuation))


def get_issue_comments(issue):
    comments_content = ''
    for comment in issue.get_comments():
        comments_content += ' ' + comment.body
    return comments_content


@catch_requests_exceptions
def check_existing_issues(org_name, ror_id=None):
    existing_issues = {}
    in_issues_list = []
    g = Github(TOKEN)
    repo = g.get_repo('ror-community/ror-updates')
    states = ['open', 'closed']
    for state in states:
        issues = repo.get_issues(state=state)
        issue_count = 0
        for issue in issues:
            if issue_count >= 2000:
                break
            issue_html_url = issue.html_url
            if ror_id:
                issue_text = issue.body + get_issue_comments(issue)
                if ror_id in issue_text:
                    in_issues_list.append(issue_html_url)
            issue_number = issue.number
            # Exclude specific issues from duplicate checks
            if issue_number in [892, 862]:
                continue
            issue_title = re.sub(r'[\n()]', '', issue.title)
            label_names = [label.name for label in issue.labels]
            if 'new record' in label_names:
                try:
                    pattern = re.compile(r'(?<=\:)(.*)($)')
                    title_name = pattern.search(issue_title).group(0).strip()
                    existing_issues[issue_number] = {
                        'title_name': title_name, 'html_url': issue_html_url}
                except AttributeError:
                    pass
            issue_count += 1
    for key, value in existing_issues.items():
        mr = fuzz.ratio(normalize_text(org_name),
                        normalize_text(value['title_name']))
        if mr > 90 or normalize_text(org_name) in normalize_text(value['title_name']):
            in_issues_list.append(value['html_url'])
    if in_issues_list != []:
        return '; '.join(in_issues_list)
    else:
        return None


@catch_requests_exceptions
def search_wikidata(all_names):
    best_match_ratio = 0
    for name in all_names:
        language = detect_language(name)
        params = {"action": "wbsearchentities", "search": name, "language": language, "format": "json"}
        try:
            r = requests.get("https://www.wikidata.org/w/api.php", params=params)
            api_response = r.json()
        except requests.exceptions.RequestException as e:
            return None, None, None
        search_results = api_response.get('search', [])
        for result in search_results:
            match_ratio = fuzz.ratio(normalize_text(name), normalize_text(result.get('label', '')))
            if match_ratio > best_match_ratio and match_ratio >= 85:
                wikidata_id, wikidata_label = result['id'], result['label']
                best_match_ratio = match_ratio
    if best_match_ratio >= 85:
        return wikidata_label, wikidata_id, best_match_ratio
    else:
        return None, None, None


@catch_requests_exceptions
def get_location_entity(wikidata_id):
    url = 'https://www.wikidata.org/w/api.php?action=wbgetentities'
    params = {'ids': wikidata_id, 'format': 'json'}
    api_response = requests.get(url, params=params).json()
    entity = api_response['entities'][wikidata_id]
    labels = entity['labels']
    claims = entity['claims']
    location_name = labels.get('en', {}).get('value')
    geonames_id = claims.get('P1566', [{}])[0].get(
        'mainsnak', {}).get('datavalue', {}).get('value', '')
    if location_name is not None:
        return location_name, geonames_id
    else:
        return None, None


@catch_requests_exceptions
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


@catch_requests_exceptions
def get_wikidata_claims(org_name, wikidata_id, match_ratio):
    org_metadata = {"Wikidata Name": org_name, "Wikidata ID": wikidata_id,
                    "Wikidata name match ratio": match_ratio}
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={wikidata_id}&format=json"
    api_response = requests.get(url).json()
    if 'entities' not in api_response:
        return org_metadata
    wikipedia_url = get_wikipedia_url(wikidata_id)
    if wikipedia_url:
        org_metadata['wikipedia_url'] = wikipedia_url
    try:
        claims = api_response['entities'][wikidata_id]['claims']
        org_metadata.update({
            "Wikidata Established": claims['P571'][0]['mainsnak']['datavalue']['value']['time'][1:5] if 'P571' in claims else None,
            "Wikidata Admin territory name": get_location_entity(claims['P131'][0]['mainsnak']['datavalue']['value']['id'])[0] if 'P131' in claims else None,
            "Wikidata Admin territory Geonames ID": get_location_entity(claims['P131'][0]['mainsnak']['datavalue']['value']['id'])[1] if 'P131' in claims else None,
            "Wikidata City": get_location_entity(claims['P276'][0]['mainsnak']['datavalue']['value']['id'])[0] if 'P276' in claims else None,
            "Wikidata City Geonames ID": get_location_entity(claims['P276'][0]['mainsnak']['datavalue']['value']['id'])[1] if 'P276' in claims else None,
            "Wikidata Country": get_location_entity(claims['P17'][0]['mainsnak']['datavalue']['value']['id'])[0] if 'P17' in claims else None,
            "Wikidata links": claims['P856'][0]['mainsnak']['datavalue']['value'] if 'P856' in claims else None,
            "Wikidata GRID ID": claims['P2427'][0]['mainsnak']['datavalue']['value'] if 'P2427' in claims else None,
            "Wikidata ROR ID": 'https://ror.org/' + claims['P6782'][0]['mainsnak']['datavalue']['value'] if 'P6782' in claims else None,
            "Wikidata ISNI ID": claims['P213'][0]['mainsnak']['datavalue']['value'] if 'P213' in claims else None
        })
    except KeyError as e:
        pass
    return org_metadata


@catch_requests_exceptions
def search_ror(all_names):
    for org_name in all_names:
        matches =[]
        base_url = "https://api.ror.org/v2/organizations"
        params = {'affiliation': org_name}
        matches = []
        api_response = requests.get(base_url, params=params).json()
        results = api_response.get('items', [])
        for result in results:
            record = result.get('organization')
            ror_id = record.get('id')
            for name_entry in record.get('names', []):
                name_value = name_entry.get('value')
                name_type = name_entry.get('types')[0]
                name_mr = fuzz.ratio(normalize_text(org_name),
                                     normalize_text(name_value))
                if name_mr >= 90:
                    matches.append([ror_id, name_value, name_type])
        matches = list(matches for matches,
                           _ in itertools.groupby(matches))
        if matches:
            if len(matches) == 1:
                return f"{matches[0][2]}: {matches[0][0]} - {matches[0][1]}"
            else:
                return '; '.join([f"{match[2]}: {match[0]} - {match[1]}" for match in matches])
    return None


@catch_requests_exceptions
def search_isni(all_names):
    for org_name in all_names:
        matches = []
        normalized_name = normalize_text(org_name)
        query_url = 'https://isni.ringgold.com/api/stable/search'
        params = {'q': normalized_name}
        response = requests.get(query_url, params=params)
        api_response = response.json()
        institutions = api_response.get('institutions', [])
        if institutions:
            for institution in institutions:
                isni_id = institution.get('isni')
                isni_names = [institution.get(
                    'name')] + institution.get('alt_names', [])
                for isni_name in isni_names:
                    match_ratio = fuzz.ratio(normalize_text(
                        org_name), normalize_text(isni_name))
                    if match_ratio > 90:
                        matches.append((isni_id, isni_name))
        if matches:
            if len(matches) == 1:
                matched = f"{matches[0][1]} - {matches[0][0]}"
            else:
                return '; '.join([f"{match[1]} - {match[0]}" for match in matches])
    return None


@catch_requests_exceptions
def search_funder_registry(all_names):
    for org_name in all_names:
        base_url = 'https://api.crossref.org/funders'
        params = {'query': org_name}
        api_response = requests.get(base_url, params=params).json()
        funders = api_response.get('message',[]).get('items',[])
        if funders:
            for funder in funders:
                match_ratio = fuzz.token_set_ratio(
                    org_name, normalize_text(funder['name']))
                if match_ratio > 90:
                    return funder['id']
                elif org_name in funder['alt-names']:
                    return funder['id']
    return None


@catch_requests_exceptions
def search_orcid(all_names):
    for org_name in all_names:
        orcid_urls = []
        search_url = f"https://pub.orcid.org/v3.0/expanded-search/?q=affiliation-org-name:\"{org_name}\"&fl=orcid,current-institution-affiliation-name,past-institution-affiliation-name"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, 'lxml')
        expanded_search = soup.find('expanded-search:expanded-search')
        if expanded_search:
            num_found = expanded_search['num-found']
            if num_found != '0':
                orcid_id_tags = soup.find_all('expanded-search:orcid-id')
                for tag in orcid_id_tags:
                    orcid_id = tag.text
                    orcid_url = f"https://orcid.org/{orcid_id}"
                    orcid_urls.append(orcid_url)
                orcid_urls = orcid_urls[:5] if len(orcid_urls) >= 5 else orcid_urls
                orcid_urls = '; '.join(orcid_urls)
                return orcid_urls
    return None


def generate_substring_permutations(org_name, limit=6):
    org_name_substrings = org_name.split(' ')
    if len(org_name_substrings) <= limit:
        return [' '.join(permutation) for permutation in itertools.permutations(org_name_substrings)]
    else:
        return [org_name]


def all_affiliation_usage_to_string(result_dict):
    csv_compatible = []
    for key, values in result_dict.items():
        values = [v for v in values if v]
        csv_row = f"{key}: {', '.join(values)}"
        csv_compatible.append(csv_row)
    csv_compatible_str = "; ".join(csv_compatible)
    return csv_compatible_str


@catch_requests_exceptions
def search_openalex(org_name):
    try:
        normalized_name = normalize_text(org_name)
        base_url = 'https://api.openalex.org/works'
        params = {
            'filter': 'raw_affiliation_string.search:"{}"'.format(normalized_name),
            'per-page': '100'
        }
        api_response = requests.get(base_url, params=params).json()
        if api_response.get('results'):
            substring_permutations = generate_substring_permutations(org_name)
            match_dict = defaultdict(set)
            works = api_response['results']
            for work in works:
                for author in work.get('authorships', []):
                    raw_affiliation = author.get('raw_affiliation_string')
                    if not raw_affiliation:
                        continue
                    normalized_affiliation = normalize_text(raw_affiliation)
                    partial_ratio = fuzz.partial_ratio(
                        normalized_name, normalized_affiliation)
                    token_set_ratio = fuzz.token_set_ratio(
                        normalized_name, normalized_affiliation)
                    max_ratio = max(partial_ratio, token_set_ratio)
                    for substring in substring_permutations:
                        if substring in normalized_affiliation:
                            doi = work.get("doi", work.get('id'))
                            match_dict[substring].add(doi)
                        elif fuzz.ratio(normalized_name, normalized_affiliation) >= 90:
                            doi = work.get("doi", work.get('id'))
                            match_dict[org_name].add(doi)
                        elif max_ratio >= 90:
                            doi = work.get("doi", work.get('id'))
                            match_dict[org_name].add(doi)
            for key in match_dict.keys():
                match_dict[key] = list(match_dict[key])[:10]
            return all_affiliation_usage_to_string(match_dict)
    except KeyError as err:
        #OpenAlex API error: Key not found in response
        return None
    return None


def get_publication_affiliation_usage(record, all_names):
    affiliation_aliases = []
    potential_aliases = generate_aliases(record['body'])
    if potential_aliases:
        all_names += potential_aliases
        all_names = list(set(all_names))
    pub_affiliation_usage = ''
    for name in all_names:
        affiliation_usage = search_openalex(name)
        if affiliation_usage:
            if pub_affiliation_usage:
                pub_affiliation_usage += ' | ' + affiliation_usage
                affiliation_aliases.append(name)
            else:
                pub_affiliation_usage = affiliation_usage
                affiliation_aliases.append(name)
    if pub_affiliation_usage:
        affiliation_aliases = '; '.join(affiliation_aliases)
        return pub_affiliation_usage, affiliation_aliases
    return None, None


def triage(record):
    org_metadata = {}
    org_name = record['name']
    aliases = record['aliases'].split(';')
    aliases = [alias.strip() for alias in aliases]
    all_names = [org_name] + ['aliases']
    wikidata_name, wikidata_id, best_match_ratio = search_wikidata(all_names)
    if wikidata_id:
        org_metadata = get_wikidata_claims(
            wikidata_name, wikidata_id, best_match_ratio)
    org_metadata['ISNI'] = search_isni(all_names)
    org_metadata['Funder ID'] = search_funder_registry(all_names)
    org_metadata['Publication affiliation usage'], org_metadata['Potential aliases'] = get_publication_affiliation_usage(
        record, all_names)
    org_metadata['ORCID affiliation usage'] = search_orcid(all_names)
    org_metadata['Possible ROR matches'] = search_ror(all_names)
    org_metadata['Previous requests'] = check_existing_issues(all_names)
    if record['city'] and record['country']:
        location = f"{record['city']}, {record['country']}"
        geonames_result = search_geonames(location)
        if geonames_result:
            org_metadata['Geonames match'] = geonames_result
    return org_metadata
