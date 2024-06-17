import os
import re
import csv
import sys
import urllib
import argparse
from github import Github

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Retrieve update records data')
    parser.add_argument('-c', '--column_id', type=int,
                        required=True, help='Project column ID')
    args = parser.parse_args()
    return args


def retrieve_issues(g, column_id):
    column = g.get_project_column(column_id)
    cards = column.get_cards()
    issue_urls = []
    for card in cards:
        issue = card.get_content()
        if issue and "update record" in [label.name for label in issue.labels]:
            issue_urls.append(issue)
    return issue_urls


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        match = s[start:end].strip()
        return match
    except ValueError:
        return ''


def make_printable(s):
    line_break_chars = set(["\n", "\r"])
    noprint_trans_table = {i: None for i in range(
        0, sys.maxunicode + 1) if not chr(i).isprintable() or chr(i) in line_break_chars}
    return s.translate(noprint_trans_table)


def fix_wikipedia_url(wikipedia_url):
    return wikipedia_url[0:30] + urllib.parse.quote(wikipedia_url[30:])


def normalize_text(text):
    text = re.sub(' +', ' ', text)
    text = make_printable(text)
    text = text.strip()
    return text


def parse_issue_text(issue_text, mappings):
    parsed_data = {}
    parsed_data['id'] = find_between(issue_text, 'ROR ID:', '\n')
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
                    parsed_data[csv_column] = existing_value + op_value if existing_value else op_value
        if '.delete_field' in update:
            key = update.strip().replace('.delete_field', '')
            for csv_column, keywords in mappings.items():
                if any(keyword in key for keyword in keywords):
                    parsed_data[csv_column] = 'delete'
    for key, value in parsed_data.items():
        if value.endswith(';'):
            parsed_data[key] = value[:-1]
        if key == 'wikipedia' and value:
            parsed_data[key] = fix_wikipedia_url(value)
    return parsed_data


def process_issue(issue, api_fields, ror_fields, issue_ror_mappings, outfile):
    api_data = [getattr(issue, f, '') for f in api_fields]
    issue_text = normalize_text(issue.body)
    record_data = parse_issue_text(issue_text, issue_ror_mappings)
    with open(outfile, 'a') as f_out:
        writer = csv.writer(f_out)
        record_entry = api_data + [record_data.get(k, '') for k in ror_fields]
        writer.writerow(record_entry)


def create_update_records_metadata(column_id):
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
        'locations.geonames_id'
    ]
    issue_ror_mappings = {
        'names.types.ror_display': ['ror_display'],
        'status': ['status'],
        'types': ['type','types'],
        'names.types.alias': ['alias', 'aliases'],
        'names.types.label': ['label','labels'],
        'names.types.acronym': ['acronym','acronyms'],
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
        'locations.geonames_id': ['geonames_id','geonames']
    }
    outfile = os.path.join(os.getcwd(), 'update_records_metadata.csv')
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(api_fields + ror_fields)
    g = Github(GITHUB_TOKEN)
    column = g.get_project_column(column_id)
    cards = column.get_cards()
    update_record_issues = []
    for card in cards:
        issue = card.get_content()
        if issue and "update record" in [label.name for label in issue.labels]:
            update_record_issues.append(issue)
    for issue in update_record_issues:
        process_issue(issue, api_fields, ror_fields,
                      issue_ror_mappings, outfile)


def main():
    args = parse_arguments()
    create_update_records_metadata(args.column_id)


if __name__ == '__main__':
    main()
