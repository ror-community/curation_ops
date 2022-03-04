import os
import sys
import csv
from github import Github


GITHUB = {}
GITHUB['TOKEN'] = ''

def add_to_milestone(f, milestone):
    g = Github(GITHUB['TOKEN'])
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            repo = g.get_repo("ror-community/ror-updates")
            issue_number = int(row['issue_number'])
            issue = repo.get_issue(number=issue_number)
            issue.edit(milestone=repo.get_milestone(int(milestone))


if __name__ == '__main__':
    update_issues_for_release(sys.argv[1], sys.argv[2])
