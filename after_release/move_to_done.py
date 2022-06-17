import os
import sys
import csv
from github import Github


GITHUB = {}
GITHUB['TOKEN'] = ''


def move_to_done():
    g = Github(GITHUB['TOKEN'])
    repo = g.get_repo("ror-community/ror-updates")
    project = repo.get_projects()[0]
    columns = project.get_columns()
    approved_column = [column for column in columns if column.name ==
                       'Ready for production release'][0]
    done_column = [column for column in columns if column.name ==
                   'Done (released on production)'][0]
    approved_cards = approved_column.get_cards()
    for card in approved_cards:
        card.move('bottom',done_column)


if __name__ == '__main__':
    move_to_done()
