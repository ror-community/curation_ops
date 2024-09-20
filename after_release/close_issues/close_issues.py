import os
import sys
import csv
import re
import argparse
from github import Github


def parse_arguments():
	parser = argparse.ArgumentParser(
		description='Close issues using release CSVs')
	parser.add_argument('-r', '--release', required=True,
						help='Release number')
	parser.add_argument('-i', '--input', required=True,
						help='Input CSV file path')
	parser.add_argument('-t', '--type', required=True,
						choices=['new', 'updates'], help='File type (new or updates)')
	return parser.parse_args()


def update_issues_for_release(release_number, input_file, record_type):
	g = Github(os.environ['GITHUB_TOKEN'])
	repo = g.get_repo("ror-community/ror-updates")

	with open(input_file, encoding='utf-8-sig') as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = row['id']
			issue_number = int(re.sub(
				r'https://github.com/ror-community/ror-updates/issues/', '', row['html_url']))
			issue = repo.get_issue(number=issue_number)
			if record_type == 'new':
				comment = 'Assigned ROR ID %s in release %s.' % (
					ror_id, release_number)
			else:
				comment = 'Record updated in release %s.' % (release_number)
			issue.create_comment(body=comment)
			issue.edit(state="closed")


def main():
	args = parse_arguments()
	update_issues_for_release(args.release, args.input, args.type)


if __name__ == '__main__':
	main()
