import os
import re
import sys
import csv
import json
import argparse
from collections import defaultdict


def parse_update_field(update_str):
	updates = {}
	parts = update_str.split(';')
	for part in parts:
		subparts = part.split('==', 1)
		if len(subparts) == 2:
			change_type, value = subparts[0].strip(), subparts[1].strip()
			if change_type in updates:
				updates[change_type].append(value)
			else:
				updates[change_type] = [value]
		else:
			updates.setdefault('replace', []).append(subparts[0].strip())
	return updates


def parse_row_updates(row):
	row_updates = {}
	for field, update_str in row.items():
		row_updates[field] = parse_update_field(update_str)
	return row_updates


def parse_record_updates_file(input_file):
	valid_fields = [
		'status',
		'types',
		'names.types.acronym',
		'names.types.alias',
		'names.types.label',
		'names.types.ror_display',
		'links.type.website',
		'established',
		'links.type.wikipedia',
		'external_ids.type.isni.preferred',
		'external_ids.type.isni.all',
		'external_ids.type.wikidata.preferred',
		'external_ids.type.wikidata.all',
		'external_ids.type.fundref.preferred',
		'external_ids.type.fundref.all',
		'locations.geonames_id'
	]
	record_updates = defaultdict(list)
	field_value_pairs = []
	with open(input_file, 'r+', encoding='utf-8-sig') as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = row['id']
			html_url = row['html_url']
			row_updates = parse_row_updates(row)
			for field, updates in row_updates.items():
				if field in valid_fields:
					for change_type, values in updates.items():
						for value in values:
							if value:
								record_updates[ror_id].append(
									{'html_url': html_url, 'change_type': change_type, 'field': field, 'value': value})
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


def check_if_updates_applied(input_file, output_file):
	record_updates = parse_record_updates_file(input_file)
	header = ['html_url', 'ror_id', 'field',
			  'type', 'value', 'position', 'status']
	with open(output_file, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for ror_id, updates in record_updates.items():
		ror_id_file_prefix = re.sub('https://ror.org/', '', ror_id)
		json_file_path = f'{ror_id_file_prefix}.json'
		with open(json_file_path, 'r+', encoding='utf8') as f_in:
			json_file = json.load(f_in)
		flattened = flatten_json(json_file)
		replace_nulls = {k:("null value" if v is None else v) for k, v in flattened.items()}
		inverted_json = {v: k for k, v in flattened.items()}
		additions = ['add', 'replace']
		deletions = ['delete']
		for update in updates:
			issue_url = update['html_url']
			change_type, field, value = update[
				'change_type'], update['field'], update['value']
			if '*' in value:
				value = value.split('*')[0]
			if field == 'locations.geonames_id':
				value = int(value)
			if change_type in additions:
				if value not in flattened.values() and value not in ['delete', 'Delete']:
					with open(output_file, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow(
							[issue_url, ror_id, field, change_type, value, '', 'missing'])
			if change_type in deletions:
				if value in inverted_json.keys():
					with open(output_file, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([issue_url, ror_id, field, change_type,
										 value, inverted_json[value], 'still_present'])
			if change_type == 'replace' and value in ['delete', 'Delete']:
				if 'external' in field:
					external_id_type = field.split('.')[2]
					if any(external_id_type in key for key in inverted_json if not isinstance(key, int) and key is not None):
						with open(output_file, 'a') as f_out:
							writer = csv.writer(f_out)
							writer.writerow([issue_url, ror_id, field, change_type,
											 value, '', 'still_present'])
			# implement case for use of "delete" in other fields where value will still exist but be None


def parse_arguments():
	parser = argparse.ArgumentParser(description="Check integrity of JSON files based on update records CSV.")
	parser.add_argument("-i", "--input_file", required=True,
						help="Input CSV file path.")
	parser.add_argument("-o", "--output_file",
						default="update_records_integrity_check.csv", help="Output CSV file path.")
	return parser.parse_args()


def main():
	args = parse_arguments()
	check_if_updates_applied(args.input_file, args.output_file)


if __name__ == '__main__':
	main()
