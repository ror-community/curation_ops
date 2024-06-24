import os
import argparse
from github import Github


def add_to_milestone(milestone):
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print('Error: GITHUB_TOKEN environment variable not set.')
        sys.exit(1)

    g = Github(token)
    repo = g.get_repo("ror-community/ror-updates")
    project = repo.get_projects()[0]
    columns = project.get_columns()
    prod_release_column = [
        column for column in columns if column.name == 'Ready for production release'][0]
    prod_release_cards = prod_release_column.get_cards()

    for card in prod_release_cards:
        issue = card.get_content()
        if issue is not None:
            issue.edit(milestone=repo.get_milestone(milestone))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Add issues to a milestone in a Github repository.')
    parser.add_argument('-m', '--milestone', type=int,
                        help='The milestone number to which issues should be added.')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    add_to_milestone(args.milestone)
