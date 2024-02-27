import os
import re
import sys
import csv
import json
import urllib.parse
import requests
from collections import defaultdict
from github import Github

GITHUB_USER = os.environ.get('GITHUB_USER')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
COLUMN_ID = 12055464


def find_between(text, first, last):
    try:
        start = text.index(first) + len(first)
        stop = text.index(last, start)
        match = text[start:stop]
        match = match.strip()
        return match
    except ValueError:
        return ''


def make_printable(s):
    line_break_chars = set(["\n", "\r"])
    noprint_trans_table = {i: None for i in range(
        0, sys.maxunicode + 1) if not chr(i).isprintable() and not chr(i) in line_break_chars}
    return s.translate(noprint_trans_table)


def normalize_text(text):
    text = re.sub(' +', ' ', text)
    text = make_printable(text)
    text = text.strip()
    return text


def fix_types(record_data):
    types = record_data['types']
    if '(' in types:
        types = types.split('(')[0].strip()
        record_data['types'] = types
    return record_data


def fix_wikipedia_url(record_data):
    wikipedia_url = record_data['links.type.wikipedia']
    if wikipedia_url and urllib.parse.unquote(wikipedia_url) == wikipedia_url:
        wikipedia_url = wikipedia_url[0:30] + \
            urllib.parse.quote(wikipedia_url[30:])
        record_data['links.type.wikipedia'] = wikipedia_url
    return record_data


def parse_issue_text(issue_text, mappings):
    record_data = defaultdict(lambda:'')
    for key, values in mappings.items():
        for value in values:
            search_result = find_between(issue_text, value, '\n')
            if search_result:
                record_data[key] = search_result.strip()
                break
    record_data = fix_types(record_data)
    record_data = fix_wikipedia_url(record_data)
    return record_data


def process_issue(issue, api_fields, ror_fields, issue_ror_mappings, outfile):
    api_data = [getattr(issue, f, '') for f in api_fields]
    issue_text = issue.body
    record_data = parse_issue_text(issue_text, issue_ror_mappings)
    with open(outfile, 'a') as f_out:
        writer = csv.writer(f_out)
        record_entry = api_data + [record_data.get(k, '') for k in ror_fields]
        writer.writerow(record_entry)


def create_new_records_metadata():
    outfile = os.path.join(os.getcwd(), 'new_records_metadata.csv')
    api_fields = ['html_url']
    ror_fields = [
        'id',
        'names.types.ror_display',
        'status',
        'types'
        'names.types.alias',
        'names.types.label',
        'names.types.acronym',
        'links.type.website',
        'links.type.wikipedia',
        'domains',
        'established',
        'external_ids.type.fundref.all',
        'external_ids.type.fundref.preferred',
        'external_ids.type.grid.all',
        'external_ids.type.grid.preferred',
        'external_ids.type.isni.all',
        'external_ids.type.isni.preferred',
        'external_ids.type.wikidata.all',
        'external_ids.type.wikidata.preferred',
        'city',
        'country',
        'locations.geonames_id'
    ]
    issue_ror_mappings = {
        'names.types.ror_display': ['Name of organization:', 'Name of organization to be added |'],
        'status': ['Status:'],
        'types': ['Organization type:', 'Type:'],
        'names.types.alias': ['Other names for the organization:', "Aliases:", "Alias:"],
        'names.types.label': ['Label:', 'Labels:'],
        'names.types.acronym': ['Acronym/abbreviation:', 'Acronym:'],
        'links.type.website': ['Website:', 'Organization website |'],
        'links.type.wikipedia': ['Wikipedia page:', 'Wikipedia:', 'Wikipedia |'],
        'domains': ['Domains:'],
        'established': ['Year established:'],
        'external_ids.type.isni.preferred': ['ISNI ID:', 'ISNI:'],
        'external_ids.type.isni.all': ['ISNI ID:', 'ISNI:'],
        'external_ids.type.grid.preferred': ['GRID ID:', 'GRID:'],
        'external_ids.type.grid.all': ['GRID ID:', 'GRID:'],
        'wikidata': ['Wikidata ID:', 'Wikidata:'],
        'external_ids.type.fundref.preferred': ['Crossref Funder ID:'],
        'external_ids.type.fundref.all': ['Crossref Funder ID:'],
        'city': ['City:'],
        'country': ['Country:'],
        'locations.geonames_id': ['Geonames ID:', 'Geoname ID:']
        }
    with open(outfile, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(api_fields + ror_fields)

    g = Github(GITHUB_TOKEN)
    column = g.get_project_column(COLUMN_ID)
    cards = column.get_cards()
    new_record_issues = []
    for card in cards:
        issue = card.get_content()
        if issue and "new record" in [label.name for label in issue.labels]:
            new_record_issues.append(issue)

    for issue in new_record_issues:
        process_issue(issue, api_fields, ror_fields,
                      issue_ror_mappings, outfile)


if __name__ == '__main__':
    create_new_records_metadata()
