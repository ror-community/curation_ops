import os
import re
import string
import itertools
import requests
from urllib.parse import urlparse
from collections import defaultdict
from github import Github
from thefuzz import fuzz
from bs4 import BeautifulSoup
from lingua import LanguageDetectorBuilder, Language
from search_geonames import search_geonames

USER = os.environ.get('GITHUB_USER')
TOKEN = os.environ.get('GITHUB_TOKEN')

try:
    LINGUA_DETECTOR = LanguageDetectorBuilder.from_all_spoken_languages().build()
except Exception as e:
    print(f"CRITICAL: Failed to initialize Lingua Language Detector: {e}. Language detection will not work.")
    LINGUA_DETECTOR = None


def catch_requests_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            print(f"DEBUG: RequestException in {func.__name__}: {e}")
            return None
    return wrapper


def format_isni_with_hyperlink(isni_id):
    if not isni_id or len(isni_id) != 16 or not isni_id.isdigit():
        return isni_id
    
    formatted_isni = f"{isni_id[:4]} {isni_id[4:8]} {isni_id[8:12]} {isni_id[12:16]}"
    return f"[{formatted_isni}](https://isni.org/isni/{isni_id})"


def format_funder_id_with_hyperlink(funder_id):
    if not funder_id:
        return funder_id
    
    return f"[{funder_id}](https://api.crossref.org/funders/{funder_id})"


def normalize_text(text):
    text = re.sub('-', ' ', text)
    return ''.join(ch for ch in re.sub(r'[^\w\s-]', '', text.lower()) if ch not in set(string.punctuation))


def normalize_country_value(country):
    if not country or not isinstance(country, str):
        return None
    normalized = country.strip().lower()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized if normalized else None


def normalize_url_host(url):
    if not url or not isinstance(url, str):
        return None
    candidate_url = url.strip()
    if not candidate_url:
        return None
    if not re.match(r'^[a-z]+://', candidate_url, flags=re.IGNORECASE):
        candidate_url = f"https://{candidate_url}"
    try:
        parsed = urlparse(candidate_url)
    except ValueError:
        return None
    host = parsed.netloc or ''
    if not host and parsed.path:
        host = parsed.path.split('/')[0]
    host = host.lower()
    if host.startswith('www.'):
        host = host[4:]
    host = host.split(':')[0]
    return host or None


def organization_matches_country(organization, normalized_issue_country):
    if not normalized_issue_country:
        return True
    locations = organization.get('locations', [])
    for location in locations:
        country_info = location.get('country') or {}
        country_name = country_info.get('country_name')
        country_code = country_info.get('country_code')
        if country_name and normalize_country_value(country_name) == normalized_issue_country:
            return True
        if country_code and country_code.lower() == normalized_issue_country:
            return True
    return False


ADVANCED_QUERY_RESERVED_CHARS = set(r'+-=!(){}[]^"~*?:\/&|<>')


def escape_for_advanced_query(value):
    if value is None:
        return ""
    escaped_chars = []
    for char in value:
        if char in ADVANCED_QUERY_RESERVED_CHARS:
            escaped_chars.append(f"\\{char}")
        else:
            escaped_chars.append(char)
    return ''.join(escaped_chars)


def perform_ror_advanced_query(query_string, headers, page=1):
    base_url = "https://api.ror.org/v2/organizations"
    params = {'query.advanced': query_string, 'page': page}
    response = requests.get(base_url, params=params, headers=headers, timeout=10)
    response.raise_for_status()
    api_response = response.json()
    return api_response.get('items', []) or []


def get_display_name_for_organization(organization):
    if not isinstance(organization, dict):
        return None
    if organization.get('name'):
        return organization['name']
    names = organization.get('names', [])
    if isinstance(names, list):
        for name_entry in names:
            types = name_entry.get('types', []) if isinstance(name_entry, dict) else []
            if isinstance(types, list) and 'ror_display' in types:
                return name_entry.get('value')
        for name_entry in names:
            if isinstance(name_entry, dict) and name_entry.get('value'):
                return name_entry.get('value')
    return None


@catch_requests_exceptions
def search_wikidata(all_names):
    best_match_ratio = 0
    wikidata_id_match = None
    wikidata_label_match = None

    if LINGUA_DETECTOR is None:
        print(
            "Lingua detector not available. Skipping language detection in search_wikidata.")

    for name in all_names:
        if not name:
            continue

        language_code_for_api = 'en'
        if LINGUA_DETECTOR:
            try:
                detected_language_obj = LINGUA_DETECTOR.detect_language_of(
                    name)
                if detected_language_obj:
                    iso_code_obj = detected_language_obj.iso_code_639_1
                    if iso_code_obj and hasattr(iso_code_obj, 'name'):
                        language_code_for_api = iso_code_obj.name.lower()
            except Exception as e:
                print(f"Error during Lingua language detection for '{name}': {e}. Defaulting to 'en'.")

        params = {"action": "wbsearchentities", "search": name,
                  "language": language_code_for_api, "format": "json", "uselang": language_code_for_api}
        headers = {
            'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
        try:
            r = requests.get("https://www.wikidata.org/w/api.php",
                             params=params, headers=headers, timeout=10)
            r.raise_for_status()
            api_response = r.json()
        except requests.exceptions.RequestException as e:
            print(f"Wikidata API request failed for name '{name}': {e}")
            continue

        search_results = api_response.get('search', [])
        normalized_query_name = normalize_text(name)
        for result in search_results:
            current_label = result.get('label', '')
            if not current_label:
                continue

            match_ratio = fuzz.ratio(
                normalized_query_name, normalize_text(current_label))
            if match_ratio > best_match_ratio and match_ratio >= 85:
                if 'id' in result and 'label' in result:
                    wikidata_id_match, wikidata_label_match = result['id'], result['label']
                    best_match_ratio = match_ratio

    if best_match_ratio >= 85 and wikidata_id_match:
        return wikidata_label_match, wikidata_id_match, best_match_ratio
    else:
        return None, None, None


@catch_requests_exceptions
def get_location_entity(wikidata_id):
    if not wikidata_id:
        return None, None
    url = 'https://www.wikidata.org/w/api.php?action=wbgetentities'
    params = {'ids': wikidata_id, 'format': 'json'}
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    api_response = requests.get(
        url, params=params, headers=headers, timeout=10).json()

    entity = api_response.get('entities', {}).get(wikidata_id)
    if not entity:
        return None, None

    labels = entity.get('labels', {})
    claims = entity.get('claims', {})

    location_name = labels.get('en', {}).get('value')

    geonames_id_value = None
    p1566_claims = claims.get('P1566')
    if p1566_claims and isinstance(p1566_claims, list) and len(p1566_claims) > 0:
        mainsnak = p1566_claims[0].get('mainsnak')
        if mainsnak:
            datavalue = mainsnak.get('datavalue')
            if datavalue:
                geonames_id_value = datavalue.get('value')

    if location_name is not None:
        return location_name, geonames_id_value
    else:
        return None, None


@catch_requests_exceptions
def get_wikipedia_url(wikidata_id):
    if not wikidata_id:
        return None
    url = 'https://www.wikidata.org/w/api.php?action=wbgetentities'
    params = {'props': 'sitelinks/urls', 'ids': wikidata_id, 'format': 'json'}
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    api_response = requests.get(
        url, params=params, headers=headers, timeout=10).json()

    entity = api_response.get('entities', {}).get(wikidata_id)
    if not entity:
        return None

    if 'sitelinks' in entity:
        sitelinks = entity['sitelinks']
        try:
            wikipedia_url = sitelinks['enwiki']['url']
            return wikipedia_url
        except KeyError:
            for lang in sitelinks.keys():
                if lang.endswith('wiki'):
                    if 'url' in sitelinks[lang]:
                        wikipedia_url = sitelinks[lang]['url']
                        return wikipedia_url
            return None
    else:
        return None


@catch_requests_exceptions
def get_wikidata_claims(org_name, wikidata_id, match_ratio):
    org_metadata = {"Wikidata Name": org_name, "Wikidata ID": wikidata_id,
                    "Wikidata name match ratio": match_ratio}
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={wikidata_id}&format=json"
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    api_response = requests.get(url, headers=headers, timeout=10).json()

    if 'entities' not in api_response or wikidata_id not in api_response['entities']:
        return org_metadata

    wikipedia_url = get_wikipedia_url(wikidata_id)
    if wikipedia_url:
        org_metadata['wikipedia_url'] = wikipedia_url

    try:
        claims = api_response['entities'][wikidata_id]['claims']

        def safe_get_claim(claim_key, path_keys, is_location=False):
            if claim_key in claims:
                try:
                    value_item = claims[claim_key][0]['mainsnak']['datavalue']
                    if is_location:
                        return value_item['value']['id']
                    if 'time' in path_keys:
                        return value_item['value']['time'][1:5]
                    return value_item['value']
                except (KeyError, IndexError, TypeError):
                    return None
            return None

        org_metadata["Wikidata Established"] = safe_get_claim('P571', ['time'])

        admin_terr_id = safe_get_claim('P131', [], is_location=True)
        if admin_terr_id:
            admin_name, admin_geonames = get_location_entity(admin_terr_id)
            if admin_name:
                org_metadata["Wikidata Admin territory name"] = admin_name
            if admin_geonames:
                org_metadata["Wikidata Admin territory Geonames ID"] = admin_geonames

        city_loc_id = safe_get_claim('P276', [], is_location=True)
        if city_loc_id:
            city_name, city_geonames = get_location_entity(city_loc_id)
            if city_name:
                org_metadata["Wikidata City"] = city_name
            if city_geonames:
                org_metadata["Wikidata City Geonames ID"] = city_geonames

        country_id = safe_get_claim('P17', [], is_location=True)
        if country_id:
            country_name, _ = get_location_entity(country_id)
            if country_name:
                org_metadata["Wikidata Country"] = country_name

        org_metadata["Wikidata links"] = safe_get_claim('P856', [])
        org_metadata["Wikidata GRID ID"] = safe_get_claim('P2427', [])

        ror_id_val = safe_get_claim('P6782', [])
        if ror_id_val:
            org_metadata["Wikidata ROR ID"] = 'https://ror.org/' + ror_id_val

        org_metadata["Wikidata ISNI ID"] = safe_get_claim('P213', [])

    except KeyError:
        pass
    return {k: v for k, v in org_metadata.items() if v is not None}


@catch_requests_exceptions
def search_ror(all_names, record):
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    base_url = "https://api.ror.org/v2/organizations"
    normalized_issue_country = normalize_country_value(
        record.get('country')) if isinstance(record, dict) else None

    unique_names = []
    seen_name_keys = set()
    for name in all_names:
        normalized_name = normalize_text(name) if name else None
        if not name or not normalized_name:
            continue
        if normalized_name in seen_name_keys:
            continue
        unique_names.append((name, normalized_name))
        seen_name_keys.add(normalized_name)

    all_matches = set()
    match_outputs = []

    for original_name, normalized_name in unique_names:
        request_variants = set()
        request_variants.add(('query', original_name))
        request_variants.add(('affiliation', original_name))
        if original_name != normalized_name:
            request_variants.add(('query', normalized_name))
            request_variants.add(('affiliation', normalized_name))

        for param_key, param_value in request_variants:
            params = {param_key: param_value}
            api_response = requests.get(
                base_url, params=params, headers=headers, timeout=10).json()
            results = api_response.get('items', [])
            for result in results:
                organization = result.get('organization') or result
                if not isinstance(organization, dict):
                    continue
                ror_id = organization.get('id')
                if not ror_id:
                    continue
                if not organization_matches_country(organization, normalized_issue_country):
                    continue

                for name_entry in organization.get('names', []):
                    name_value = name_entry.get('value')
                    if not name_value:
                        continue
                    name_match_ratio = fuzz.ratio(
                        normalized_name, normalize_text(name_value))
                    if name_match_ratio < 90:
                        continue

                    name_types_list = name_entry.get('types', [])
                    name_type = name_types_list[0] if name_types_list else 'N/A'
                    match_tuple = (ror_id, name_value, name_type)
                    if match_tuple in all_matches:
                        continue
                    all_matches.add(match_tuple)

    if not all_matches:
        return None

    sorted_matches = sorted(all_matches, key=lambda m: (m[0], m[1], m[2]))
    for match_tuple in sorted_matches:
        match_outputs.append(
            f"{match_tuple[2]}: {match_tuple[0]} - {match_tuple[1]}")

    if len(match_outputs) == 1:
        return match_outputs[0]
    return '; '.join(match_outputs)


@catch_requests_exceptions
def search_isni(all_names):
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    for org_name in all_names:
        if not org_name:
            continue
        matches = []
        normalized_name_query = normalize_text(org_name)
        query_url = 'https://isni.ringgold.com/api/stable/search'
        params = {'q': normalized_name_query}

        response = requests.get(query_url, params=params,
                                headers=headers, timeout=15)
        response.raise_for_status()
        api_response = response.json()

        institutions = api_response.get('institutions', [])
        if institutions:
            for institution in institutions:
                isni_id = institution.get('isni')
                isni_primary_name = institution.get('name')
                isni_alt_names = institution.get('alt_names', [])

                all_isni_names_for_record = []
                if isni_primary_name:
                    all_isni_names_for_record.append(isni_primary_name)
                all_isni_names_for_record.extend(isni_alt_names)

                for isni_name_variant in all_isni_names_for_record:
                    if not isni_name_variant:
                        continue
                    match_ratio = fuzz.ratio(normalize_text(
                        org_name), normalize_text(isni_name_variant))
                    if match_ratio > 90:
                        matches.append((isni_id, isni_name_variant))

        if matches:
            unique_matches_for_current_name = sorted(list(set(matches)))
            if len(unique_matches_for_current_name) == 1:
                isni_name = unique_matches_for_current_name[0][1]
                isni_id = unique_matches_for_current_name[0][0]
                formatted_isni = format_isni_with_hyperlink(isni_id)
                return f"{isni_name} - {formatted_isni}"
            else:
                formatted_matches = []
                for match in unique_matches_for_current_name:
                    isni_name = match[1]
                    isni_id = match[0]
                    formatted_isni = format_isni_with_hyperlink(isni_id)
                    formatted_matches.append(f"{isni_name} - {formatted_isni}")
                return '; '.join(formatted_matches)
    return None


@catch_requests_exceptions
def search_ror_by_url(record):
    if not isinstance(record, dict):
        return None

    website_url = record.get('url')
    if not website_url:
        body = record.get('body')
        if isinstance(body, str):
            url_match = re.search(r'https?://[^\s)]+', body)
            if url_match:
                website_url = url_match.group(0)

    normalized_host = normalize_url_host(website_url)
    if not normalized_host:
        return None

    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    normalized_issue_country = normalize_country_value(record.get('country'))

    query_values = {normalized_host}
    if not normalized_host.startswith('www.'):
        query_values.add(f"www.{normalized_host}")

    matches = defaultdict(set)

    for query_value in query_values:
        escaped_value = escape_for_advanced_query(query_value)
        query_string = f"(links.value:*{escaped_value}* OR domains:*{escaped_value}*)"
        try:
            results = perform_ror_advanced_query(query_string, headers)
        except requests.exceptions.RequestException as exc:
            print(f"DEBUG: search_ror_by_url failed for query '{query_string}': {exc}")
            continue

        for result in results:
            organization = result.get('organization') or result
            if not isinstance(organization, dict):
                continue
            ror_id = organization.get('id')
            display_name = get_display_name_for_organization(organization)
            if not ror_id or not display_name:
                continue
            if not organization_matches_country(organization, normalized_issue_country):
                continue

            matched = False

            for org_link in organization.get('links', []):
                link_value = org_link.get('value') if isinstance(org_link, dict) else org_link
                normalized_link_host = normalize_url_host(link_value)
                if normalized_link_host == normalized_host:
                    matched = True
                    matches[(ror_id, display_name)].add(normalized_link_host)
                    break

            if not matched:
                domains = organization.get('domains', [])
                for domain in domains:
                    normalized_domain_host = normalize_url_host(domain)
                    if normalized_domain_host == normalized_host:
                        matched = True
                        matches[(ror_id, display_name)].add(normalized_domain_host)
                        break

    if not matches:
        return None

    sorted_matches = sorted(matches.items(), key=lambda item: (item[0][0], item[0][1]))
    formatted = []
    for (ror_id, name), host_matches in sorted_matches:
        host_details = ''
        normalized_hosts = sorted({host for host in host_matches if host})
        if normalized_hosts:
            host_details = f" (matched host: {', '.join(normalized_hosts)})"
        formatted.append(f"{ror_id} - {name}{host_details}")
    if len(formatted) == 1:
        return formatted[0]
    return '; '.join(formatted)


def extract_external_ids(record):
    external_ids = set()

    raw_external_ids = record.get('external_ids') if isinstance(record, dict) else None
    if isinstance(raw_external_ids, dict):
        for key in ('all', 'preferred', 'values', 'value'):
            values = raw_external_ids.get(key)
            if isinstance(values, list):
                for val in values:
                    if isinstance(val, str):
                        external_ids.add(val.strip())
            elif isinstance(values, str):
                external_ids.add(values.strip())
    elif isinstance(raw_external_ids, list):
        for entry in raw_external_ids:
            if isinstance(entry, dict):
                for key in ('all', 'preferred', 'values', 'value'):
                    values = entry.get(key)
                    if isinstance(values, list):
                        for val in values:
                            if isinstance(val, str):
                                external_ids.add(val.strip())
                    elif isinstance(values, str):
                        external_ids.add(values.strip())
            elif isinstance(entry, str):
                external_ids.add(entry.strip())
    elif isinstance(raw_external_ids, str):
        external_ids.add(raw_external_ids.strip())

    body_text = record.get('body') if isinstance(record, dict) else None
    if isinstance(body_text, str):
        grid_matches = re.findall(r'grid\.[0-9]{4,8}\.[0-9a-z]{1,2}', body_text, flags=re.IGNORECASE)
        for match in grid_matches:
            external_ids.add(match.strip().lower())

        wikidata_matches = re.findall(r'\bQ\d+\b', body_text)
        for match in wikidata_matches:
            external_ids.add(match.strip())

        wikidata_url_matches = re.findall(r'https?://(?:www\.)?wikidata\.org/wiki/(Q\d+)', body_text, flags=re.IGNORECASE)
        for match in wikidata_url_matches:
            external_ids.add(match.strip())

        isni_block_matches = re.findall(r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b', body_text)
        for match in isni_block_matches:
            external_ids.add(match.strip())

        isni_compact_matches = re.findall(r'\b\d{16}\b', body_text)
        for match in isni_compact_matches:
            external_ids.add(' '.join([match[i:i+4] for i in range(0, len(match), 4)]))

        fundref_matches = re.findall(r'\b50\d{8}\b', body_text)
        for match in fundref_matches:
            external_ids.add(match.strip())

    cleaned_external_ids = {ext_id for ext_id in (value.strip() for value in external_ids) if ext_id}
    return cleaned_external_ids or None


def normalize_external_id_for_comparison(external_id):
    if not external_id:
        return ''
    return re.sub(r'\s+', '', external_id).lower()


def organization_has_external_id(organization, target_id_normalized):
    external_ids_field = organization.get('external_ids', [])
    if not isinstance(external_ids_field, list):
        return False

    for ext_entry in external_ids_field:
        if not isinstance(ext_entry, dict):
            continue
        for key in ('all', 'preferred'):
            values = ext_entry.get(key)
            if isinstance(values, list):
                for val in values:
                    if isinstance(val, str) and normalize_external_id_for_comparison(val) == target_id_normalized:
                        return True
            elif isinstance(values, str) and normalize_external_id_for_comparison(values) == target_id_normalized:
                return True
    return False


@catch_requests_exceptions
def search_ror_by_external_ids(record):
    if not isinstance(record, dict):
        return None

    extracted_ids = extract_external_ids(record)
    if not extracted_ids:
        return None

    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    normalized_issue_country = normalize_country_value(record.get('country'))

    matches = {}

    for external_id in extracted_ids:
        escaped_external_id = escape_for_advanced_query(external_id)
        query_string = f'(external_ids.all:"{escaped_external_id}" OR external_ids.preferred:"{escaped_external_id}")'
        try:
            results = perform_ror_advanced_query(query_string, headers)
        except requests.exceptions.RequestException as exc:
            print(f"DEBUG: search_ror_by_external_ids failed for '{external_id}': {exc}")
            continue

        normalized_target_id = normalize_external_id_for_comparison(external_id)
        for result in results:
            organization = result.get('organization') or result
            if not isinstance(organization, dict):
                continue
            if not organization_matches_country(organization, normalized_issue_country):
                continue
            if not organization_has_external_id(organization, normalized_target_id):
                continue

            ror_id = organization.get('id')
            display_name = get_display_name_for_organization(organization)
            if not ror_id or not display_name:
                continue
            key = (ror_id, display_name)
            matches.setdefault(key, set()).add(external_id)

    if not matches:
        return None

    sorted_matches = sorted(matches.items(), key=lambda item: (item[0][0], item[0][1]))
    formatted_results = []
    for (ror_id, name), ids in sorted_matches:
        sorted_ids = sorted(ids)
        formatted_results.append(f"{ror_id} - {name} (matched external ID: {', '.join(sorted_ids)})")

    if len(formatted_results) == 1:
        return formatted_results[0]
    return '; '.join(formatted_results)


@catch_requests_exceptions
def search_funder_registry(all_names):
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    for org_name in all_names:
        if not org_name:
            continue
        base_url = 'https://api.crossref.org/funders'
        params = {'query': org_name, 'mailto': 'support@ror.org'}
        api_response = requests.get(
            base_url, params=params, headers=headers, timeout=10).json()
        funders = api_response.get('message', {}).get('items', [])
        if funders:
            for funder in funders:
                funder_name = funder.get('name', '')
                match_ratio = fuzz.token_set_ratio(
                    org_name, normalize_text(funder_name))
                if match_ratio > 90:
                    funder_id = funder['id']
                    formatted_funder_id = format_funder_id_with_hyperlink(funder_id)
                    return f"{funder_name} - {formatted_funder_id}"
                alt_names = funder.get('alt-names', [])
                if isinstance(alt_names, list) and org_name in alt_names:
                    funder_id = funder['id']
                    formatted_funder_id = format_funder_id_with_hyperlink(funder_id)
                    return f"{funder_name} - {formatted_funder_id}"
    return None


@catch_requests_exceptions
def search_orcid(all_names):
    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    for org_name in all_names:
        if not org_name:
            continue
        orcid_urls = []
        search_url = f"https://pub.orcid.org/v3.0/expanded-search/?q=affiliation-org-name:\"{org_name}\"&fl=orcid,current-institution-affiliation-name,past-institution-affiliation-name"
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        expanded_search = soup.find('expanded-search:expanded-search')
        if expanded_search:
            num_found_attr = expanded_search.get('num-found', '0')
            if num_found_attr != '0':
                orcid_id_tags = soup.find_all('expanded-search:orcid-id')
                for tag in orcid_id_tags:
                    orcid_id = tag.text
                    orcid_url = f"https://orcid.org/{orcid_id}"
                    orcid_urls.append(orcid_url)

                orcid_urls = orcid_urls[:5] if len(
                    orcid_urls) >= 5 else orcid_urls
                if orcid_urls:
                    return '; '.join(orcid_urls)
    return None


def generate_substring_permutations(org_name, limit=6):
    if not org_name:
        return [org_name]
    org_name_substrings = org_name.split(' ')
    if len(org_name_substrings) <= limit and len(org_name_substrings) > 1:
        return [' '.join(permutation) for permutation in itertools.permutations(org_name_substrings)]
    else:
        return [org_name]


def all_affiliation_usage_to_string(result_dict):
    print(f"DEBUG: all_affiliation_usage_to_string received result_dict: {result_dict}")
    csv_compatible = []
    for key, values in result_dict.items():
        if isinstance(values, int):
            if values > 0:
                csv_row = f"{key}: {values}"
                csv_compatible.append(csv_row)
        elif isinstance(values, list):
            values = [v for v in values if v]
            if values:
                csv_row = f"{key}: {', '.join(map(str, values))}"
                csv_compatible.append(csv_row)
    if not csv_compatible:
        print("DEBUG: all_affiliation_usage_to_string: No CSV compatible rows generated, returning None.")
        return None
    csv_compatible_str = "; ".join(csv_compatible)
    print(f"DEBUG: all_affiliation_usage_to_string returning: {csv_compatible_str}")
    return csv_compatible_str


@catch_requests_exceptions
def search_openalex(org_name):
    print(f"DEBUG: search_openalex called with org_name: '{org_name}'")
    if not org_name:
        print("DEBUG: search_openalex: org_name is empty, returning None.")
        return None
    normalized_name = normalize_text(org_name)
    print(f"DEBUG: search_openalex: normalized_name: '{normalized_name}'")
    base_url = 'https://api.openalex.org/works'
    params = {
        'filter': f'raw_affiliation_strings.search:"{normalized_name}"',
        'per-page': '100',
        'mailto': 'support@ror.org'
    }
    request_url = requests.Request(
        'GET', base_url, params=params).prepare().url
    print(f"DEBUG: search_openalex: Requesting URL: {request_url}")

    headers = {
        'User-Agent': 'ROROrgTriageBot/1.0 (ror.org, mailto:support@ror.org)'}
    api_response_json = requests.get(
        base_url, params=params, headers=headers, timeout=20).json()

    results = api_response_json.get('results')
    if not results:
        print(f"DEBUG: search_openalex: No 'results' in API response for '{org_name}'. Returning None.")
        return None
    print(f"DEBUG: search_openalex: Found {len(results)} results from OpenAlex for '{org_name}'.")

    substring_permutations = generate_substring_permutations(org_name)
    print(f"DEBUG: search_openalex: Substring permutations for '{org_name}': {substring_permutations}")
    match_dict = defaultdict(set)
    author_count_dict = defaultdict(set)

    for i, work in enumerate(results):
        authorships = work.get('authorships', [])
        for author in authorships:
            raw_affiliations_list = author.get('raw_affiliation_strings', [])
            if not isinstance(raw_affiliations_list, list):
                raw_affiliations_list = [
                    raw_affiliations_list] if raw_affiliations_list else []

            if not raw_affiliations_list:
                raw_single_aff = author.get('raw_affiliation_string')
                if raw_single_aff:
                    raw_affiliations_list = [raw_single_aff]
                else:
                    continue

            author_info = author.get('author', {})
            author_name = author_info.get('display_name', '')
            author_orcid = author_info.get('orcid', '')

            for raw_affiliation in raw_affiliations_list:
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
                        doi_or_id = work.get("doi") or work.get('id')
                        if doi_or_id:
                            match_dict[substring].add(doi_or_id)
                        if author_name:
                            author_count_dict[substring].add(author_name)
                        break

                if fuzz.ratio(normalized_name, normalized_affiliation) >= 90:
                    doi_or_id = work.get("doi") or work.get('id')
                    if doi_or_id:
                        match_dict[org_name].add(doi_or_id)
                    if author_name:
                        author_count_dict[org_name].add(author_name)
                elif max_ratio >= 90:
                    doi_or_id = work.get("doi") or work.get('id')
                    if doi_or_id:
                        match_dict[org_name].add(doi_or_id)
                    if author_name:
                        author_count_dict[org_name].add(author_name)

    for key in match_dict.keys():
        match_dict[key] = list(match_dict[key])[:10]
    
    author_count_by_affiliation = {}
    for key, author_set in author_count_dict.items():
        author_count_by_affiliation[key] = len(author_set)

    print(f"DEBUG: search_openalex: match_dict before all_affiliation_usage_to_string: {match_dict}")
    print(f"DEBUG: search_openalex: author_count_by_affiliation: {author_count_by_affiliation}")
    
    final_result_str = all_affiliation_usage_to_string(
        match_dict) if match_dict else None
    author_count_str = all_affiliation_usage_to_string(
        author_count_by_affiliation) if author_count_by_affiliation else None
    
    print(f"DEBUG: search_openalex: Returning from search_openalex for '{org_name}': {final_result_str}")
    print(f"DEBUG: search_openalex: Author count result for '{org_name}': {author_count_str}")
    
    return final_result_str, author_count_str


def get_publication_affiliation_usage(record, all_names):
    print(f"DEBUG: get_publication_affiliation_usage: Called with record (keys: {record.keys() if isinstance(record, dict) else type(record)}) and all_names: {all_names}")
    affiliation_aliases = []
    body_content = record.get('body')
    potential_aliases_from_body = []

    extended_all_names = list(all_names)
    if potential_aliases_from_body:
        extended_all_names.extend(potential_aliases_from_body)

    unique_search_names = sorted(
        list(set(n for n in extended_all_names if n)), key=len, reverse=True)
    print(f"DEBUG: get_publication_affiliation_usage: Unique search names for OpenAlex: {unique_search_names}")

    pub_affiliation_usage_parts = []
    author_count_usage_parts = []

    for name_idx, name in enumerate(unique_search_names):
        print(f"DEBUG: get_publication_affiliation_usage: Iteration {name_idx + 1}/{len(unique_search_names)} - Searching OpenAlex for: '{name}'")
        search_result = search_openalex(name)
        
        if isinstance(search_result, tuple) and len(search_result) == 2:
            affiliation_usage, author_count_usage = search_result
        else:
            affiliation_usage = search_result
            author_count_usage = None
            
        print(f"DEBUG: get_publication_affiliation_usage: Received from search_openalex for '{name}': affiliation='{affiliation_usage}', author_counts='{author_count_usage}'")
        
        if affiliation_usage:
            pub_affiliation_usage_parts.append(affiliation_usage)
            affiliation_aliases.append(name)
            print(f"DEBUG: get_publication_affiliation_usage: Added to pub_affiliation_usage_parts. Current parts: {pub_affiliation_usage_parts}")
        
        if author_count_usage:
            author_count_usage_parts.append(author_count_usage)
            
        if affiliation_usage and len(pub_affiliation_usage_parts) >= 2:
            print(
                "DEBUG: get_publication_affiliation_usage: Reached 2 affiliation usage parts, breaking loop.")
            break

    final_pub_affiliation_usage = ' | '.join(
        pub_affiliation_usage_parts) if pub_affiliation_usage_parts else None
    final_author_count_usage = ' | '.join(
        author_count_usage_parts) if author_count_usage_parts else None
    final_affiliation_aliases_str = '; '.join(
        sorted(list(set(affiliation_aliases)))) if affiliation_aliases else None

    print(f"DEBUG: get_publication_affiliation_usage: Returning final_pub_affiliation_usage: '{final_pub_affiliation_usage}'")
    print(f"DEBUG: get_publication_affiliation_usage: Returning final_author_count_usage: '{final_author_count_usage}'")
    print(f"DEBUG: get_publication_affiliation_usage: Returning final_affiliation_aliases_str: '{final_affiliation_aliases_str}'")
    return final_pub_affiliation_usage, final_author_count_usage, final_affiliation_aliases_str


def triage(record):
    print(f"DEBUG: triage: Starting triage for record (keys: {record.keys() if isinstance(record, dict) else type(record)})")
    org_metadata = {}
    raw_org_name = record.get('name')
    org_name = raw_org_name.split(
        "*")[0].strip() if isinstance(raw_org_name, str) else ""

    raw_aliases = record.get('aliases')
    aliases_list = []
    if isinstance(raw_aliases, str):
        aliases_list = [alias.split("*")[0].strip()
                        for alias in raw_aliases.split(';') if alias.strip()]

    raw_labels = record.get('labels', [])
    labels_list = []
    if isinstance(raw_labels, list):
        labels_list = [label.strip() for label in raw_labels if label.strip()]

    all_names = [name for name in [org_name] + aliases_list + labels_list if name]
    print(f"DEBUG: triage: Initial all_names: {all_names}")
    print(f"DEBUG: triage: Labels extracted: {labels_list}")
    print(f"DEBUG: triage: Names from org_name: {[org_name] if org_name else []}")
    print(f"DEBUG: triage: Names from aliases: {aliases_list}")
    print(f"DEBUG: triage: Names from labels: {labels_list}")

    if not all_names:
        org_metadata['Error'] = "No organization name or aliases found in issue."
        print("DEBUG: triage: No organization name or aliases found. Returning early.")
        return org_metadata

    wikidata_name, wikidata_id, best_match_ratio = search_wikidata(all_names)
    if wikidata_id:
        wikidata_claims_data = get_wikidata_claims(
            wikidata_name, wikidata_id, best_match_ratio)
        if wikidata_claims_data:
            org_metadata.update(wikidata_claims_data)

    org_metadata['ISNI'] = search_isni(all_names)
    org_metadata['Funder ID'] = search_funder_registry(all_names)

    print("DEBUG: triage: About to call get_publication_affiliation_usage.")
    affiliation_result = get_publication_affiliation_usage(record, all_names)
    
    if isinstance(affiliation_result, tuple) and len(affiliation_result) == 3:
        pub_usage, author_count_usage, potential_als = affiliation_result
        print(f"DEBUG: triage: Received from get_publication_affiliation_usage - pub_usage: '{pub_usage}', author_count_usage: '{author_count_usage}', potential_als: '{potential_als}'")
        org_metadata['Publication affiliation usage'] = pub_usage
        org_metadata['Author count by affiliation'] = author_count_usage
        org_metadata['Potential aliases'] = potential_als
    else:
        if isinstance(affiliation_result, tuple) and len(affiliation_result) == 2:
            pub_usage, potential_als = affiliation_result
        else:
            pub_usage = affiliation_result
            potential_als = None
        print(f"DEBUG: triage: Received from get_publication_affiliation_usage (legacy format) - pub_usage: '{pub_usage}', potential_als: '{potential_als}'")
        org_metadata['Publication affiliation usage'] = pub_usage
        org_metadata['Potential aliases'] = potential_als

    org_metadata['ORCID affiliation usage'] = search_orcid(all_names)
    org_metadata['Possible ROR matches'] = search_ror(all_names, record)
    org_metadata['Possible ROR matches by URL'] = search_ror_by_url(record)
    org_metadata['Possible ROR matches by External ID'] = search_ror_by_external_ids(record)

    if record.get('city') and record.get('country'):
        location = f"{record['city']}, {record['country']}"
        try:
            geonames_result = search_geonames(location)
            if geonames_result:
                org_metadata['Geonames match'] = geonames_result
        except NameError:
            print("Warning: search_geonames function is not defined.")
        except Exception as e:
            print(f"Error in search_geonames: {e}")

    print(f"DEBUG: triage: org_metadata before final filtering: {org_metadata}")
    filtered_metadata = {k: v for k,
                         v in org_metadata.items() if v is not None}
    print(f"DEBUG: triage: org_metadata after final filtering: {filtered_metadata}")
    return filtered_metadata
