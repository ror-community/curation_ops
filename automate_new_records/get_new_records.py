import os
import re
import sys
import csv
import json
import requests

GITHUB = {}
GITHUB['USER'] = ''
GITHUB['TOKEN'] = ''


def find_between(text, first, last):
    try:
        start = text.index(first) + len(first)
        stop = text.index(last, start)
        match = text[start:stop]
        match = match.strip()
        return match
    except ValueError:
        return ''


def get_issue_comments(comments_url):
    comments = requests.get(comments_url, auth=(
        GITHUB['USER'], GITHUB['TOKEN'])).json()
    if comments != []:
        comments_text = []
        for comment in comments:
            text = comment['body']
            comments_text.append(text)
        return ' '.join(comments_text)
    else:
        return ''


def make_printable(s):
    line_break_chars = set(["\n", "\r"])
    noprint_trans_table = {i: None for i in range(
        0, sys.maxunicode + 1) if not chr(i).isprintable() and not chr(i) in line_break_chars}
    return s.translate(noprint_trans_table)


def normalize_text(text):
    text = re.sub(' +', ' ', text)
    text = make_printable(text)
    return text


def fix_types(record_data):
    types = record_data['types']
    if '(' in types:
        types = types.split('(')[0].strip()
        record_data['types'] = types
    return record_data

def fix_wikipedia_url(record_data):
    wikipedia_url = record_data['wikipedia_url']
    if wikipedia_url != '' and urllib.parse.unquote(wikipedia_url) == wikipedia_url:
        wikipedia_url = wikipedia_url[0:30] + urllib.parse.quote(wikipedia_url[30:])
    return wikipedia_url


def create_new_records_metadata():
    # Assumes less than 200 approved records. Add additional pages for each hundred, if needed.
    pages = [1, 2, 3, 4, 5]
    issue_urls = []
    outfile = os.getcwd() + '/new_records_metadata.csv'
    api_fields = ['id', 'url', 'html_url']
    ror_fields = ['name', 'types', 'aliases', 'labels', 'acronyms', 'links', 'established', 'wikipedia_url',
                  'isni', 'grid', 'wikidata', 'fundref', 'city', 'country', 'geonames_id']
    issue_ror_mappings = {
        'name': ['Name of organization:', 'Name of organization to be added |'],
        'types': ['Organization type:', 'Type:'],
        'aliases': ['Other names for the organization:'],
        'labels': ['Label:', 'Labels:'],
        'acronyms': ['Acronym/abbreviation:', 'Acronym:'],
        'links': ['Website:', 'Organization website |'],
        'established': ['Year established:'],
        'wikipedia_url': ['Wikipedia page:', 'Wikipedia:', 'Wikipedia |'],
        'isni': ['ISNI ID:', 'ISNI:'],
        'grid': ['GRID ID:', 'GRID:'],
        'wikidata': ['Wikidata ID:', 'Wikidata:'],
        'fundref': ['Crossref Funder ID:'],
        'related': ['Related organizations:'],
        'city': ['City:'],
        'country': ['Country:'],
        'geonames_id': ['Geonames ID:', 'Geoname ID:']}
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(api_fields + ror_fields)
    approved_column_url = 'https://api.github.com/projects/columns/13954326/cards'
    for page in pages:
        params = {'page': page, 'per_page': 100}
        cards = requests.get(approved_column_url, auth=(
            GITHUB['USER'], GITHUB['TOKEN']), params=params).json()
        for card in cards:
            if 'content_url' in card:
                issue_urls.append(card['content_url'])
    for issue_url in issue_urls:
        issue_data = requests.get(issue_url, auth=(
            GITHUB['USER'], GITHUB['TOKEN'])).json()
        comments_url = issue_url + '/comments'
        label_data = issue_data['labels']
        labels = []
        for label in label_data:
            labels.append(label['name'])
        record_type = 'new record'
        if record_type in labels:
            api_data = [issue_data[f] for f in api_fields]
            record_data = {}
            issue_text = issue_data['body'] + get_issue_comments(comments_url)
            issue_text = normalize_text(issue_text)
            for key, values in issue_ror_mappings.items():
                text_search_results = []
                for value in values:
                    text_search_result = find_between(issue_text, value, '\n')
                    text_search_results.append(text_search_result)
                search_results = [
                    tsr for tsr in text_search_results if tsr != '']
                if search_results == []:
                    record_data[key] = ''
                else:
                    search_results = search_results[0]
                    record_data[key] = search_results
            record_data = fix_types(record_data)
            record_data = fix_wikipedia_url(record_data)
            with open(outfile, 'a') as f_out:
                record_entry = api_data + [record_data[k] for k in ror_fields]
                writer = csv.writer(f_out)
                writer.writerow(record_entry)


if __name__ == '__main__':
    create_new_records_metadata()
