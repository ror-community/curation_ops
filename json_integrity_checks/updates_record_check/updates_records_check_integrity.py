import os
import re
import sys
import csv
import json
from collections import defaultdict


def parse_record_updates_file(f):
	record_updates = defaultdict(list)
	ror_fields = ['name', 'established', 'wikipedia_url', 'links', 'types',
				  'aliases', 'acronyms', 'Wikidata', 'ISNI', 'FundRef', 'labels', 'Geonames']
	with open(f) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = re.sub('https://ror.org/', '', row['ror_id'])
			issue_url = row['issue_url']
			update_field = row['update_field']
			updates = update_field.split(';')
			updates = [u for u in updates if u.strip() != '']
			for update in updates:
				change_type = update.split('.')[0].strip()
				change_field = re.search(
					r'(?<=\.)(.*)(?=\=\=)', update).group(1)
				change_field = change_field.strip()
				if change_field not in ror_fields:
					print(
						change_field, "is not a valid field. Please check coding on", row['html_url'])
					sys.exit()
				change_value = update.split('==')[1].strip()
				record_updates[ror_id].append(
					{'issue_url':issue_url,'change_type': change_type, 'change_field': change_field, 'change_value': change_value})

	return record_updates


def flatten_json(j):
	flattened = {}

	def flatten(obj, name=''):
		if type(obj) is dict:
			for item in obj:
				flatten(obj[item], name + item + '_')
		elif type(obj) is list:
			i = 0
			for item in obj:
				flatten(item, name + str(i) + '_')
				i += 1
		else:
			flattened[name[:-1]] = obj
	flatten(j)
	return flattened


def check_if_updates_applied(f):
	record_updates = parse_record_updates_file(f)
	curr_dir = os.getcwd() + '/'
	outfile = os.getcwd() + '/updates_integrity_check.csv'
	header = ['issue_url', 'ror_id', 'field', 'type', 'value', 'position', 'status']
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for ror_id, updates in record_updates.items():
		json_file_path = curr_dir + ror_id + '.json'
		with open(json_file_path, 'r+', encoding='utf8') as f_in:
			json_file = json.load(f_in)
		flattened = flatten_json(json_file)
		inverted_json = {v: k for k, v in flattened.items()}
		additions = ['change','add', 'replace']
		deletions = ['delete']
		for update in updates:
			issue_url = update['issue_url']
			change_type, change_field, change_value = update[
				'change_type'], update['change_field'], update['change_value']
			if '*' in change_value:
				change_value = change_value.split('*')[0]
			if change_type in additions:
				if change_value not in flattened.values():
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([issue_url, ror_id, change_field, change_type, change_value, '', 'missing'])
			elif change_type in deletions:
				if change_value in flattened.values() and change_field in inverted_json[change_value]:
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([issue_url, ror_id, change_field, change_type, change_value, inverted_json[change_value], 'still_present'])

if __name__ == '__main__':
	check_if_updates_applied(sys.argv[1])
