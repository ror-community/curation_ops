import os
import sys
import argparse
import logging
from github import Github, GithubException
from github_project_issues import get_column_issue_numbers


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Add issues from a specific project column to a milestone in a Github repository.')
    parser.add_argument('-r', '--repo', default="ror-community/ror-updates",
                        help='GitHub repository name in the format owner/repo (default is ror-updates)')
    parser.add_argument('-p', '--project_number', type=int, default=19,
                        help='GitHub project number (default 19, ror-updates project)')
    parser.add_argument('-c', '--column_name', default="Ready for production release",
                        help='Project column name where records are located (default is Ready for production release)')
    parser.add_argument('-m', '--milestone', type=int, required=True,
                        help='The milestone number to add issues to')
    return parser.parse_args()


def get_repo_and_milestone(g, repo_name, milestone_number):
    try:
        repo = g.get_repo(repo_name)
        milestone = repo.get_milestone(milestone_number)
        return repo, milestone
    except GithubException as e:
        logger.error(f"Error accessing repository or milestone: {e}")
        sys.exit(1)


def add_issues_to_milestone(repo, milestone, issue_numbers):
    for number in issue_numbers:
        try:
            issue = repo.get_issue(number)
            if issue.milestone != milestone:
                issue.edit(milestone=milestone)
                logger.info(f"Added issue #{number} to milestone {milestone.title}")
            else:
                logger.info(f"Issue #{number} already in milestone {milestone.title}")
        except GithubException as e:
            logger.error(f"Error adding issue #{number} to milestone: {e}")


def main():
    args = parse_arguments()
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        logger.error('Error: GITHUB_TOKEN environment variable not set.')
        sys.exit(1)
    else:
        g = Github(token)

    repo, milestone = get_repo_and_milestone(g, args.repo, args.milestone)

    try:
        issue_numbers = get_column_issue_numbers(
            args.repo, args.project_number, args.column_name)
        logger.info(f"Retrieved {len(issue_numbers)} issues from column '{args.column_name}'")
    except Exception as e:
        logger.error(f"Error retrieving issues from column: {e}")
        sys.exit(1)

    add_issues_to_milestone(repo, milestone, issue_numbers)

    logger.info("Finished adding issues to milestone")


if __name__ == '__main__':
    main()
