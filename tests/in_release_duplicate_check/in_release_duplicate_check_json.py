import re
import csv
import json
import glob
import argparse
from copy import deepcopy
from string import punctuation
from furl import furl
from thefuzz import fuzz


def normalize_text(org_name):
    org_name = org_name.lower()
    org_name = re.sub(r'[^\w\s]', '', org_name)
    exclude = set(punctuation)
    org_name = ''.join(ch for ch in org_name if ch not in exclude)
    return org_name


def normalize_url_furl(url, context=None):
    if url is None:
        return None
    try:
        f = furl(url)
        f.path.normalize()
        f.path = ''
        f.remove(args=True, fragment=True)
        if f.host.startswith('www.'):
            f.host = f.host[4:]
        f.scheme = None
        return f.url.lower()
    except Exception as e:
        print(f"Error normalizing URL: {url}, Context: {context}, Error: {e}")
        return None


def get_all_names(record):
    all_names = []
    name_types = ['ror_display', 'alias', 'label']
    for name_type in name_types:
        all_names += [name['value']
                      for name in record.get('names', []) if name_type in name.get('types', [])]
    return all_names


def get_urls(record):
    return [link['value'] for link in record.get('links', []) if link['type'] == 'website']


def get_all_names_and_urls(record):
    all_names = get_all_names(record)
    urls = get_urls(record)
    return all_names, urls


def get_country_code(record):
    if 'locations' in record and len(record['locations']) > 0:
        location = record['locations'][0]
        if 'geonames_details' in location and 'country_code' in location['geonames_details']:
            return location['geonames_details']['country_code']
    return None


def check_url_matches(urls1, urls2):
    for url1 in urls1:
        for url2 in urls2:
            if normalize_url_furl(url1) == normalize_url_furl(url2):
                return True, url1, url2
    return False, None, None


def check_name_matches(names1, names2):
    matches = []
    for name1 in names1:
        for name2 in names2:
            name_match_ratio = fuzz.ratio(
                normalize_text(name1), normalize_text(name2))
            if name_match_ratio >= 85:
                matches.append((name1, name2, name_match_ratio))
    return matches


def check_duplicates(input_dir, output_file):
    all_records = {}
    header = ['ror_id', 'name', 'url', 'duplicate_ror_id',
              'duplicate_name', 'duplicate_url', 'match_type', 'match_ratio']
    unique_matches = {}
    unique_name_pairs = set()
    for file in glob.glob(f"{input_dir}/*.json"):
        with open(file, 'r') as f_in:
            record = json.load(f_in)
            ror_id = record['id']
            country_code = get_country_code(record)
            names, urls = get_all_names_and_urls(record)
            all_records[ror_id] = (names, country_code, urls)
    for record_id, (record_names, record_country, record_urls) in all_records.items():
        for copied_id, (copied_names, copied_country, copied_urls) in all_records.items():
            if copied_id <= record_id:  # Skip self-comparisons and avoid duplicate comparisons
                continue
            if record_country and copied_country and record_country != copied_country:
                continue
            match_key = tuple(sorted([record_id, copied_id]))
            unique_matches[match_key] = []
            url_match, match_url1, match_url2 = check_url_matches(
                record_urls, copied_urls)
            if url_match:
                unique_matches[match_key].append({
                    'ror_id': record_id,
                    'name': record_names[0],
                    'url': match_url1,
                    'duplicate_ror_id': copied_id,
                    'duplicate_name': copied_names[0],
                    'duplicate_url': match_url2,
                    'match_type': 'url',
                    'match_ratio': 100
                })
            name_matches = check_name_matches(record_names, copied_names)
            for name1, name2, match_ratio in name_matches:
                name_pair = tuple(sorted([name1, name2]))
                if name_pair not in unique_name_pairs:
                    unique_name_pairs.add(name_pair)
                    unique_matches[match_key].append({
                        'ror_id': record_id,
                        'name': name1,
                        'url': record_urls[0] if record_urls else '',
                        'duplicate_ror_id': copied_id,
                        'duplicate_name': name2,
                        'duplicate_url': copied_urls[0] if copied_urls else '',
                        'match_type': 'name',
                        'match_ratio': match_ratio
                    })
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        for matches in unique_matches.values():
            for match in matches:
                writer.writerow([match[field] for field in header])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for duplicate name and URL metadata in a directory containing ROR records")
    parser.add_argument("-i", "--input_dir", required=True,
                        help="Input directory path.")
    parser.add_argument("-o", "--output_file",
                        default="in_release_duplicates.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_duplicates(args.input_dir, args.output_file)


if __name__ == '__main__':
    main()
