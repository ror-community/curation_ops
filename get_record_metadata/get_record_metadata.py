import os
import re
import sys
import csv
import json
import argparse
import urllib.parse
import requests
from collections import defaultdict
from github import Github
from github_project_issues import get_column_issue_numbers

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')


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
    types = record_data['types'].lower()
    if '(' in types:
        types = types.split('(')[0].strip()
    record_data['types'] = types
    return record_data


def fix_wikipedia_url(wikipedia_url):
    if wikipedia_url and urllib.parse.unquote(wikipedia_url) == wikipedia_url:
        wikipedia_url = wikipedia_url[0:30] + \
            urllib.parse.quote(wikipedia_url[30:])
    return wikipedia_url


def add_ror_display_to_labels(record_data):
    if record_data['names.types.label']:
        record_data['names.types.label'] = '; '.join(
            [record_data['names.types.ror_display'], record_data['names.types.label']])
    else:
        record_data['names.types.label'] = record_data['names.types.ror_display']
    return record_data


def fix_and_supplement_record_data(record_data):
    record_data = fix_types(record_data)
    record_data['links.type.wikipedia'] = fix_wikipedia_url(
        record_data['links.type.wikipedia'])
    record_data = add_ror_display_to_labels(record_data)
    if record_data['external_ids.type.fundref.all'] and "funder" not in record_data['types']:
        if record_data['types']:
            record_data['types'] += "; funder"
        else:
            record_data['types'] = "funder"
    if not record_data['status']:
        record_data['status'] = 'active'
    return record_data


def parse_new_issue_text(issue_text, mappings):
    record_data = defaultdict(lambda: '')
    for key, values in mappings.items():
        for value in values:
            search_result = find_between(issue_text, value, '\n')
            if search_result:
                record_data[key] = search_result.strip()
                break
    record_data = fix_and_supplement_record_data(record_data)
    return record_data


def parse_update_issue_text(issue_text, mappings):
    parsed_data = {}
    parsed_data['id'] = find_between(issue_text, 'ROR ID:', '\n')
    issue_text = normalize_text(issue_text)
    update_field = find_between(issue_text, "Update:", '$')
    updates = update_field.split('|')
    for update in updates:
        operation = None
        value = ""
        if '==' in update:
            parts = update.split('==')
            key, value = parts[0].strip(), parts[1].strip()
            if '.delete' in key:
                operation = 'delete'
                key = key.replace('.delete', '')
            elif '.add' in key:
                operation = 'add'
                key = key.replace('.add', '')
            elif '.replace' in key:
                operation = 'replace'
                key = key.replace('.replace', '')
            for csv_column, keywords in mappings.items():
                if any(keyword in key for keyword in keywords):
                    op_value = f"{operation}=={value}" if operation else value
                    existing_value = parsed_data.get(csv_column, '')
                    if existing_value and not existing_value.endswith(';'):
                        existing_value += ';'
                    parsed_data[csv_column] = existing_value + \
                        op_value if existing_value else op_value
        if '.delete_field' in update:
            key = update.strip().replace('.delete_field', '')
            for csv_column, keywords in mappings.items():
                if any(keyword in key for keyword in keywords):
                    parsed_data[csv_column] = 'delete'
    for key, value in parsed_data.items():
        if value.endswith(';'):
            parsed_data[key] = value[:-1]
        if key == 'links.type.wikipedia' and value:
            parsed_data[key] = fix_wikipedia_url(value)
    return parsed_data


def process_issue(issue, api_fields, ror_fields, issue_ror_mappings, outfile, issue_type):
    api_data = [getattr(issue, f, '') for f in api_fields]
    issue_text = normalize_text(issue.body)

    if issue_type == 'new':
        record_data = parse_new_issue_text(issue_text, issue_ror_mappings)
    else:  # update
        record_data = parse_update_issue_text(issue_text, issue_ror_mappings)

    with open(outfile, 'a') as f_out:
        writer = csv.writer(f_out)
        record_entry = api_data + [record_data.get(k, '') for k in ror_fields]
        writer.writerow(record_entry)


def create_records_metadata(repo, project_number, column_name, outfile, issue_type):
    api_fields = ['html_url']
    ror_fields = [
        'id',
        'names.types.ror_display',
        'status',
        'types',
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

    if issue_type == 'new':
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
            'external_ids.type.wikidata.preferred': ['Wikidata ID:', 'Wikidata:'],
            'external_ids.type.wikidata.all': ['Wikidata ID:', 'Wikidata:'],
            'external_ids.type.fundref.preferred': ['Crossref Funder ID:'],
            'external_ids.type.fundref.all': ['Crossref Funder ID:'],
            'city': ['City:'],
            'country': ['Country:'],
            'locations.geonames_id': ['Geonames ID:', 'Geoname ID:']
        }
    else:  # update
        issue_ror_mappings = {
            'names.types.ror_display': ['ror_display'],
            'status': ['status'],
            'types': ['type', 'types'],
            'names.types.alias': ['alias', 'aliases'],
            'names.types.label': ['label', 'labels'],
            'names.types.acronym': ['acronym', 'acronyms'],
            'links.type.website': ['website'],
            'links.type.wikipedia': ['wikipedia'],
            'domains': ['domains'],
            'established': ['established'],
            'external_ids.type.isni.preferred': ['isni.preferred'],
            'external_ids.type.isni.all': ['isni.all'],
            'external_ids.type.grid.preferred': ['grid.preferred'],
            'external_ids.type.grid.all': ['grid.all'],
            'external_ids.type.wikidata.preferred': ['wikidata.preferred'],
            'external_ids.type.wikidata.all': ['wikidata.all'],
            'external_ids.type.fundref.preferred': ['fundref.preferred'],
            'external_ids.type.fundref.all': ['fundref.all'],
            'locations.geonames_id': ['geonames_id', 'geonames']
        }
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(api_fields + ror_fields)
    issue_numbers = get_column_issue_numbers(repo, project_number, column_name)
    g = Github(GITHUB_TOKEN)
    github_repo = g.get_repo(repo)
    for issue_number in issue_numbers:
        issue = github_repo.get_issue(issue_number)
        if f"{issue_type} record" in [label.name for label in issue.labels]:
            process_issue(issue, api_fields, ror_fields,
                          issue_ror_mappings, outfile, issue_type)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--repo', default="ror-community/ror-updates",
                        help='GitHub repository name in the format owner/repo')
    parser.add_argument('-p', '--project_number', type=int, default=19,
                        help='GitHub project number')
    parser.add_argument('-c', '--column_name', default="Ready for sign-off / metadata QA",
                        help='Project column name where records are located')
    parser.add_argument('-t', '--issue_type', choices=['new', 'update'], required=True,
                        help='Type of issues to process: new or update')
    parser.add_argument('-f', '--output_file',
                        help='Output file path (default: new_records_metadata.csv or update_records_metadata.csv based on issue type)')
    args = parser.parse_args()
    if not args.output_file:
        args.output_file = f"{args.issue_type}_records_metadata.csv"
    return args


def main():
    args = parse_arguments()
    create_records_metadata(args.repo, args.project_number,
                            args.column_name, args.output_file, args.issue_type)


if __name__ == '__main__':
    main()
