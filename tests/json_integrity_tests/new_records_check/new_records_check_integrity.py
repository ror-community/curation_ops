import os
import re
import sys
import csv
import json
import argparse
from urllib.parse import unquote


def simplify_json(j):
	simplified = {}
	name_types = ['ror_display', 'alias', 'label', 'acronym']
	link_types = ['wikipedia', 'website']
	external_id_types = ['isni', 'fundref', 'wikidata']
	simplified['status'] = [j.get('status', [])]
	simplified['types'] = j.get('types', [])
	simplified['established'] = [j.get('established', [])]
	simplified['locations.geonames_id'] = [location['geonames_id']
										   for location in j.get('locations', [])]
	for name_type in name_types:
		simplified[f'names.types.{name_type}'] = [name['value'] for name in j.get('names', []) if name_type in name.get('types', [])]
	for link_type in link_types:
		simplified[f'links.type.{link_type}'] = [link['value'] for link in j.get('links', []) if link.get('type') == link_type]
	for id_type in external_id_types:
		ids_of_type = [ext_id for ext_id in j.get(
			'external_ids', []) if ext_id.get('type') == id_type]
		simplified[f'external_ids.type.{id_type}.preferred'] = [ext_id['preferred'] for ext_id in ids_of_type]
		all_id_values = [ext_id.get('all', []) for ext_id in ids_of_type]
		simplified[f'external_ids.type.{id_type}.all'] = sum(all_id_values, []) if all(isinstance(v, list) for v in all_id_values) else []
	all_values = []
	for key, value in simplified.items():
		all_values += value
	all_values = [value for value in all_values if value]
	simplified['all'] = all_values
	return simplified


def check_in_json(input_file, output_file):
	ror_data_fields = [
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
	with open(input_file, 'r+') as f_in, open(output_file, 'w') as f_out:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = row['id']
			ror_id_file_prefix = re.sub('https://ror.org/', '', ror_id)
			json_file_path = f'{ror_id_file_prefix}.json'
			with open(json_file_path, 'r+', encoding='utf8') as f_in:
				json_file = json.load(f_in)
				simplified_json = simplify_json(json_file)
			for field in ror_data_fields:
				if row[field]:
					field_value = unquote(row[field]).strip()
					if field == 'established' or field == 'locations.geonames_id':
						field_value = int(field_value)
					if not isinstance(field_value, int):
						if ';' in field_value:
							field_value = field_value.split(';')
							field_value = [f_v.split('*')[0].strip()
										   for f_v in field_value]
							for value in field_value:
								if value not in simplified_json[field] and value in simplified_json['all']:
									writer = csv.writer(f_out)
									writer.writerow(
										[ror_id, 'transposition', field, field_value])
								if value not in simplified_json['all']:
									writer = csv.writer(f_out)
									writer.writerow(
										[ror_id, 'missing', field, value])

						else:
							field_value = field_value.split('*')[0].strip()
							if field_value not in simplified_json[field] and field_value in simplified_json['all']:
									writer = csv.writer(f_out)
									writer.writerow(
										[ror_id, 'transposition', field, field_value])
							if field_value not in simplified_json['all']:
								writer = csv.writer(f_out)
								writer.writerow(
									[ror_id, 'missing', field, field_value])
					elif field_value not in simplified_json[field] and field_value in simplified_json['all']:
						writer = csv.writer(f_out)
						writer.writerow(
							[ror_id, 'transposition', field, field_value])
					elif field_value not in simplified_json['all']:
						writer = csv.writer(f_out)
						writer.writerow(
							[ror_id, 'missing', field, field_value])


def parse_arguments():
	parser = argparse.ArgumentParser(
		description="Check integrity of JSON files based on new records CSV.")
	parser.add_argument("-i", "--input_file", required=True,
						help="Input CSV file path.")
	parser.add_argument("-o", "--output_file",
						default="new_records_integrity_check.csv", help="Output CSV file path.")
	return parser.parse_args()


def main():
	args = parse_arguments()
	check_in_json(args.input_file, args.output_file)


if __name__ == '__main__':
	main()
