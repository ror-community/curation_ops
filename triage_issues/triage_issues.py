import os
import re
import random
import signal
import argparse
from github import Github
from triage import triage
from contextlib import contextmanager
from encode_updates import encode_update
from validate_encoding import validate_encoding

TOKEN = os.environ.get('GITHUB_TOKEN')


def timeout_handler(signum, frame):
    raise TimeoutError


@contextmanager
def time_limit(seconds):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def get_matched_value(pattern, text):
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    else:
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None


def sort_by_issue_number(issue_list):
    return sorted(issue_list, key=lambda x: x['issue_number'])


def find_issues_with_labels(repo_path, label, start_number=None, end_number=None, issue_number=None):
    g = Github(TOKEN)
    repo = g.get_repo(repo_path)
    issues = []

    if issue_number:
        issue = repo.get_issue(issue_number)
        issues = [issue]
    elif start_number:
        all_open_issues = repo.get_issues(state="open")
        for issue in all_open_issues:
            if any(label.name == "triage needed" for label in issue.labels):
                if issue.number >= start_number and (end_number is None or issue.number <= end_number):
                    issues.append(issue)

    processed_issues = []
    for issue in issues:
        if 'Add a new' in issue.title:
            organization_name = get_matched_value(
                r'Name of organization: *([^\n]+)', issue.body)
            aliases = get_matched_value(
                r'Aliases: *([^\n]+)', issue.body)
            website = get_matched_value(r'Website:(.*?)\n', issue.body)
            city = get_matched_value(r'City:(.*?)\n', issue.body)
            country = get_matched_value(r'Country:(.*?)\n', issue.body)
            if organization_name:
                processed_issues.append({'issue_number': issue.number, 'body': issue.body,
                                         'name': organization_name, 'aliases': aliases, 'url': website, 'city': city, 'country': country, 'type': 'new'})
        elif 'Modify the information' in issue.title:
            organization_name = get_matched_value(
                r'Name of organization: *([^\n]+)', issue.body)
            ror_id_match = re.search(
                r'https://ror.org/0[a-z0-9]{6}[0-9]{2}|0[a-z0-9]{6}[0-9]{2}', issue.body, re.DOTALL)
            description_match = re.search(
                r'Description of change:\s*([\s\S]*?)(?=\nMerge\/split\/deprecate records:|$)', issue.body)
            if ror_id_match and description_match:
                ror_id = ror_id_match.group(0).strip()
                description_of_change = description_match.group(1).strip()
                processed_issues.append(
                    {'issue_number': issue.number, 'ror_id': ror_id, 'name': organization_name, 'change': description_of_change, 'type': 'update'})

    return sort_by_issue_number(processed_issues)


def convert_dict_to_comment(d):
    comment = ''
    for key, value in d.items():
        if value:
            comment += f'{key}: {value}\n'
    return comment.strip()


def add_comment_to_issue(repo_path, issue_number, comment_text):
    g = Github(TOKEN)
    repo = g.get_repo(repo_path)
    issue = repo.get_issue(issue_number)
    issue.create_comment(comment_text)
    print(f'Added comment to issue #{issue_number}')


def triage_requests(start_number=None, end_number=None, issue_number=None):
    repo_path = 'ror-community/ror-updates'
    label = 'triage needed'

    records = find_issues_with_labels(
        repo_path, label, start_number=start_number, end_number=end_number, issue_number=issue_number)

    new_records = [record for record in records if record['type'] == 'new']
    update_records = [
        record for record in records if record['type'] == 'update']

    for record in new_records:
        try:
            with time_limit(300):
                print(f'Triaging new record request - issue #{record["issue_number"]}...')
                triaged_record = triage(record)
                triaged_comment = convert_dict_to_comment(triaged_record)
                if triaged_comment:
                    add_comment_to_issue(
                        repo_path, record['issue_number'], triaged_comment)
        except TimeoutError:
            print(f'Timed out while processing new record issue #{record["issue_number"]}')

    for record in update_records:
        try:
            with time_limit(300):
                print(f'Triaging update record request - issue #{record["issue_number"]}...')
                update = encode_update(record['ror_id'], record['change'])
                if update:
                    update = validate_encoding(update)
                    if update:
                        add_comment_to_issue(
                            repo_path, record['issue_number'], update)
        except TimeoutError:
            print(f'Timed out while processing update record issue #{record["issue_number"]}')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Process ROR issues for triage.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--start', type=int, help='Start issue number')
    group.add_argument('-i', '--issue', type=int,
                       help='Specific issue number to process')
    parser.add_argument('-e', '--end', type=int, 
                       help='End issue number (inclusive) when using --start')
    args = parser.parse_args()
    if args.end is not None and args.issue is not None:
        parser.error("--end can only be used with --start")
    if args.end is not None and args.start is not None and args.end < args.start:
        parser.error("--end must be greater than or equal to --start")
    return args


if __name__ == '__main__':
    args = parse_arguments()
    if args.start:
        triage_requests(start_number=args.start, end_number=args.end)
    elif args.issue:
        triage_requests(issue_number=args.issue)