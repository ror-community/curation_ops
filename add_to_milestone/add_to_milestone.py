import os
import sys
import csv
from github import Github


GITHUB = {}
GITHUB['TOKEN'] = ''
MILESTONE = 

def add_to_milestone():
    g = Github(GITHUB['TOKEN'])
    repo = g.get_repo("ror-community/ror-updates")
    project = repo.get_projects()[0]
    columns = project.get_columns()
    prod_release_column = [column for column in columns if column.name ==
               'Ready for production release'][0]
    prod_release_cards = prod_release_column.get_cards()
    for card in prod_release_cards:
        issue = card.get_content()
        if issue is not None:
            issue.edit(milestone=repo.get_milestone(MILESTONE))


if __name__ == '__main__':
    add_to_milestone()
