import re
import csv
import sys
import itertools
import requests
import urllib.parse
from unidecode import unidecode
from rapidfuzz import fuzz
from gensim.parsing.preprocessing import preprocess_string,strip_tags, strip_multiple_whitespaces, strip_punctuation, remove_stopwords


def preprocess_text(text):
    custom_filters = [lambda x: x.lower(), strip_tags,
                      strip_punctuation, strip_multiple_whitespaces, remove_stopwords]
    return unidecode(' '.join(preprocess_string(text, custom_filters)))


def preprocess_primary_name(name):
    name = re.sub(r'\s\(.*\)', '', name)
    name = preprocess_text(name)
    return name


def ror_search(org_name):
    query_url = 'http://localhost:9292/organizations?query="' + \
        urllib.parse.quote(org_name) + '"'
    affiliation_url = 'http://localhost:9292/organizations?affiliation="' + \
        urllib.parse.quote(org_name) + '"'
    all_urls = [query_url, affiliation_url]
    ror_matches = []
    for url in all_urls:
        try:
            api_response = requests.get(url).json()
            if api_response['number_of_results'] != 0:
                results = api_response['items']
                for result in results:
                    if 'organization' in result.keys():
                        result = result['organization']
                    ror_id = result['id']
                    ror_name = result['name']
                    aliases = result['aliases']
                    labels = []
                    if result['labels'] != []:
                        labels = [label['label'] for label in result['labels']]
                    name_mr = fuzz.ratio(preprocess_text(
                        org_name), preprocess_primary_name(ror_name))
                    if name_mr >= 90:
                        match_type = 'name match'
                        ror_matches.append([ror_id, ror_name, match_type, str(name_mr)])
                    elif org_name in aliases:
                        match_type = 'alias match'
                        ror_matches.append([ror_id, ror_name, match_type, '100'])
                    elif org_name in labels:
                        match_type = 'label match'
                        ror_matches.append([ror_id, ror_name, match_type, '100'])
        except Exception:
            pass
    ror_matches = list(ror_matches for ror_matches,
                       _ in itertools.groupby(ror_matches))
    if ror_matches == []:
        print("No matches in ROR found for", org_name)
    else:
        for match in ror_matches:
            print("Matched record in ROR", match[0], "-", match[1])
    return ror_matches


def compare(f):
    outfile = f.split('.')[0] + '_compared.csv'
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['funder_id', 'name', 'status', 'aliases', 'ror_id', 'ror_name', 'match_type', 'match_ratio'])
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            funder_id = row['funder_id']
            primary_name = row['name']
            aliases = row['aliases']
            all_names = []
            if aliases != '':
                if ';' in aliases:
                    aliases = aliases.split(';')
                    aliases = [alias.strip() for alias in aliases]
                    all_names = [primary_name] + aliases
                else:
                    all_names = [primary_name, aliases]
            else:
                all_names = [primary_name]
            for name in all_names:
                ror_matches = ror_search(name)
                if ror_matches != []:
                    with open(outfile, 'a') as f_out:
                        writer = csv.writer(f_out)
                        for match in ror_matches:
                            writer.writerow(list(row.values()) + match)


if __name__ == '__main__':
    compare(sys.argv[1])
