import os
import csv
import argparse
from github import Github
from github.GithubException import GithubException


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Assign GitHub issues to a specific user.")
    parser.add_argument("-i", "--input", required=True,
                        help="Path to the input CSV file")
    parser.add_argument("-a", "--assignee", required=True,
                        help="GitHub username of the assignee")
    parser.add_argument("-t", "--token", default=os.environ.get('GITHUB_TOKEN'), help="GitHub Personal Access Token (optional)")
    parser.add_argument("-r", "--repo", default="ror-community/ror-updates",
                        help="GitHub repository in the format 'owner/repo'")
    return parser.parse_args()


def read_csv_file(file_path):
    with open(file_path, 'r+', encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            yield row['issue']


def authenticate_github(token=None):
    if not token:
        raise ValueError(
            "GitHub token not provided and GITHUB_TOKEN environment variable not set")
    return Github(token)


def assign_issue(repo, issue_number, assignee):
    try:
        issue = repo.get_issue(number=issue_number)
        issue.edit(assignees=[])  # Clear existing assignees
        issue.edit(assignees=[assignee])
        print(f"Successfully assigned issue #{issue_number} to {assignee}")
    except GithubException as e:
        print(f"Error assigning issue #{issue_number}: {str(e)}")


def extract_issue_number(issue_url):
    return int(issue_url.split('/')[-1])


def main():
    args = parse_arguments()
    try:
        g = authenticate_github(args.token)
        repo = g.get_repo(args.repo)
    except ValueError as e:
        print(f"Authentication error: {str(e)}")
        return
    except GithubException as e:
        print(f"Error accessing repository: {str(e)}")
        return
    try:
        for issue_url in read_csv_file(args.input):
            issue_number = extract_issue_number(issue_url)
            assign_issue(repo, issue_number, args.assignee)
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
