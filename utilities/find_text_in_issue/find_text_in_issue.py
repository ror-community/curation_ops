import os
import re
import csv
import time
import argparse
from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Search for a specified string within GitHub issues and report findings.')
    parser.add_argument('-i', '--input_csv', required=True,
                        help='Path to the input CSV file containing GitHub issue numbers and ROR IDs.')
    parser.add_argument('-o', '--output_csv', default='matches_in_issue_body.csv',
                        help='Path to the output CSV file where issues containing the search string will be reported.')
    parser.add_argument('-s', '--search_string', required=True,
                        help='The string to search for within issue bodies and comments.')
    parser.add_argument('-r', '--repo', default="ror-community/ror-updates",
                        help='The GitHub repository in the format "owner/repo".')
    return parser.parse_args()



def check_issue_for_string(issue, search_string):
    issue_text = issue.body or ''
    found_in_issue_body = search_string.lower() in issue_text.lower()
    matching_comments = []

    for comment in issue.get_comments():
        if search_string.lower() in comment.body.lower():
            matching_comments.append(comment.html_url)

    if found_in_issue_body or matching_comments:
        match_details = [issue.number, issue.html_url, issue.title, issue_text]
        if matching_comments:
            match_details.append('; '.join(matching_comments))
        else:
            match_details.append('No matching comments')
        return match_details
    return None


def process_issue(repo, issue_number, search_string, ror_id, writer, max_retries=3, initial_wait=30):
    retries = 0
    while retries < max_retries:
        try:
            issue = repo.get_issue(int(issue_number))
            match_in_issue = check_issue_for_string(issue, search_string)
            if match_in_issue:
                writer.writerow(match_in_issue + [ror_id])
            return  # Successfully processed the issue, exit the function
        except RateLimitExceededException as e:
            wait_time = initial_wait * (2 ** retries)  # Exponential backoff
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")

            # Get the reset time from the exception
            reset_time = int(e.headers.get('X-RateLimit-Reset', 0))
            current_time = int(time.time())
            sleep_duration = max(reset_time - current_time, wait_time)
            time.sleep(sleep_duration)
            retries += 1
        except UnknownObjectException:
            print(f"Issue {issue_number} not found.")
            return  # Exit the function as retrying won't help for non-existent issues
        except Exception as e:
            print(f"Error processing issue {issue_number}: {str(e)}")
            return  # Exit the function for other exceptions

    print(f"Failed to process issue {issue_number} after {max_retries} retries.")


def extract_issue_number(url):
    return re.sub("https://github.com/ror-community/ror-updates/issues/", "", url)


def main():
    args = parse_arguments()
    g = Github(os.environ.get('GITHUB_TOKEN'))
    repo = g.get_repo(args.repo)
    with open(args.input_csv, mode='r', encoding='utf-8') as infile, \
            open(args.output_csv, mode='w', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)
        writer.writerow(['Issue Number', 'Issue URL', 'Issue Title',
                         'Issue Text', 'Matching Comment URLs', 'ROR ID'])
        for row in reader:
            html_url = row['html_url']
            ror_id = row['id']
            issue_number = extract_issue_number(html_url)
            if issue_number:
                process_issue(repo, issue_number,
                              args.search_string, ror_id, writer)
            else:
                print(f"Could not extract issue number from URL: {html_url}")


if __name__ == '__main__':
    main()
