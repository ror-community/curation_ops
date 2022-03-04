import os
import sys
import csv
from github import Github


GITHUB = {}
GITHUB['TOKEN'] = ''

def update_issues_for_release(f, release_number):
    g = Github(GITHUB['TOKEN'])
    with open(f, encoding='utf-8-sig') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            ror_id = row['ror_id']
            repo = g.get_repo("ror-community/ror-updates")
            issue_number = int(row['issue_number'])
            record_type = row['record_type']
            issue = repo.get_issue(number=issue_number)
            if record_type == 'new':
                comment = 'Assigned %s in release %s.' % (ror_id, release_number)
            else:
                comment = 'Record updated in release %s.' % (release_number)
            issue.create_comment(body=comment)
            #Update with milestone number created for the specific release.
            milestone = 2
            issue.edit(milestone=repo.get_milestone(milestone), state='closed')


if __name__ == '__main__':
    update_issues_for_release(sys.argv[1], sys.argv[2])
