import os
import re
import sys
import csv
import asyncio
import argparse
import urllib.parse
import logging
from collections import defaultdict

from github_project_issues import get_column_issues

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def find_between(text, first, last):
    """Extract text between two delimiters."""
    try:
        start = text.index(first) + len(first)
        stop = text.index(last, start)
        match = text[start:stop]
        match = match.strip()
        return match
    except ValueError:
        return ''


def make_printable(s):
    """Remove non-printable characters except line breaks."""
    line_break_chars = set(["\n", "\r"])
    noprint_trans_table = {
        i: None for i in range(0, sys.maxunicode + 1)
        if not chr(i).isprintable() and chr(i) not in line_break_chars
    }
    return s.translate(noprint_trans_table)


def normalize_text(text):
    """Collapse whitespace and remove non-printable characters."""
    text = re.sub(' +', ' ', text)
    text = make_printable(text)
    text = text.strip()
    return text


def fix_types(record_data):
    """Clean organization type field by removing parenthetical content."""
    types = record_data['types'].lower()
    if '(' in types:
        types = types.split('(')[0].strip()
    record_data['types'] = types
    return record_data


def fix_wikipedia_url(wikipedia_url):
    """URL-encode Wikipedia URLs that aren't already encoded."""
    if wikipedia_url and urllib.parse.unquote(wikipedia_url) == wikipedia_url:
        wikipedia_url = wikipedia_url[0:30] + \
            urllib.parse.quote(wikipedia_url[30:])
    return wikipedia_url


def add_ror_display_to_labels(record_data):
    """Prepend ROR display name to labels field."""
    if record_data['names.types.label']:
        record_data['names.types.label'] = '; '.join(
            [record_data['names.types.ror_display'], record_data['names.types.label']])
    else:
        record_data['names.types.label'] = record_data['names.types.ror_display']
    return record_data


def fix_and_supplement_record_data(record_data):
    """Apply fixes and add derived fields to parsed record data."""
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
    """Parse issue body for new record requests."""
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
    """Parse issue body for record update requests."""
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


API_FIELDS = ['html_url']

ROR_FIELDS = [
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

NEW_ISSUE_MAPPINGS = {
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

UPDATE_ISSUE_MAPPINGS = {
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


def process_issue(issue: dict, issue_type: str) -> list:
    """Process a single issue and return a CSV row."""
    api_data = [issue['url']]
    issue_text = normalize_text(issue['body'])

    if issue_type == 'new':
        record_data = parse_new_issue_text(issue_text, NEW_ISSUE_MAPPINGS)
    else:
        record_data = parse_update_issue_text(issue_text, UPDATE_ISSUE_MAPPINGS)

    ror_data = [record_data.get(k, '') for k in ROR_FIELDS]
    return api_data + ror_data


async def create_records_metadata(
    repo: str,
    project_number: int,
    column_name: str,
    outfile: str,
    issue_type: str
) -> None:
    """Fetch issues from project column and write metadata to CSV."""
    label_filter = f"{issue_type} record"

    logger.info(f"Fetching issues from column '{column_name}'")

    issues = await get_column_issues(
        repo=repo,
        project_number=project_number,
        column_name=column_name,
        label_filter=label_filter
    )

    if not issues:
        logger.warning("No issues found matching criteria")
        return

    rows = []
    skipped = 0

    for issue in issues:
        try:
            row = process_issue(issue, issue_type)
            rows.append(row)
        except Exception as e:
            logger.warning(f"Issue #{issue['number']} - parsing failed: {e}")
            skipped += 1

    with open(outfile, 'w', newline='') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(API_FIELDS + ROR_FIELDS)
        writer.writerows(rows)

    logger.info(f"Processed {len(rows)}/{len(issues)} issues, {skipped} skipped")
    logger.info(f"Output written to {outfile}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Extract ROR metadata from GitHub project issues using GraphQL API'
    )
    parser.add_argument(
        '-r', '--repo',
        default="ror-community/ror-updates",
        help='GitHub repository name in the format owner/repo'
    )
    parser.add_argument(
        '-p', '--project_number',
        type=int,
        default=19,
        help='GitHub project number'
    )
    parser.add_argument(
        '-c', '--column_name',
        default="Ready for sign-off / metadata QA",
        help='Project column name where records are located'
    )
    parser.add_argument(
        '-t', '--issue_type',
        choices=['new', 'update', 'all'],
        required=True,
        help='Type of issues to process: new, update, or all (both)'
    )
    parser.add_argument(
        '-f', '--output_file',
        help='Output file path (default: {type}_records_metadata.csv). Ignored when issue_type is "all".'
    )
    args = parser.parse_args()
    if not args.output_file and args.issue_type != 'all':
        args.output_file = f"{args.issue_type}_records_metadata.csv"
    return args


async def run_all(repo, project_number, column_name):
    """Run extraction for both new and update issue types."""
    for issue_type in ['new', 'update']:
        outfile = f"{issue_type}_records_metadata.csv"
        await create_records_metadata(
            repo=repo,
            project_number=project_number,
            column_name=column_name,
            outfile=outfile,
            issue_type=issue_type
        )


def main():
    args = parse_arguments()
    if args.issue_type == 'all':
        asyncio.run(
            run_all(
                repo=args.repo,
                project_number=args.project_number,
                column_name=args.column_name
            )
        )
    else:
        asyncio.run(
            create_records_metadata(
                repo=args.repo,
                project_number=args.project_number,
                column_name=args.column_name,
                outfile=args.output_file,
                issue_type=args.issue_type
            )
        )


if __name__ == '__main__':
    main()
