import os
import re
import sys
import csv
import json
from urllib.parse import unquote

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

def check_in_json(f):
	outfile = os.getcwd() + '/not_in_json.csv'
	ror_data_fields = ['name', 'types', 'aliases', 'labels', 'acronyms', 'links', 'established',
	'wikipedia_url', 'isni', 'grid', 'wikidata', 'fundref', 'geonames_id']
	curr_dir = os.getcwd() + '/'
	with open(f) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = re.sub('https://ror.org/', '', row['ror_id'])
			json_file_name = ror_id + '.json'
			json_file_path = curr_dir + json_file_name
			with open(json_file_path, 'r+', encoding='utf8') as f_in:
				ror_json = flatten_json(json.load(f_in))
			inverted_json = {v: k for k, v in ror_json.items()}
			for field in ror_data_fields:
				if row[field] != '':
					field_value = unquote(row[field].strip())
					if field == 'established' or field == 'geonames_id':
						field_value = int(field_value)
					if not isinstance(field_value, int) and ';' in field_value:
						field_value = field_value.split(';')
						field_value = [f_v.split('*')[0].strip() for f_v in field_value if f_v != '']
						for value in field_value:
							if value not in ror_json.values():
								with open(outfile, 'a') as f_out:
									writer = csv.writer(f_out)
									writer.writerow([row['ror_id'], 'missing', field, value])
					elif not isinstance(field_value, int) and '*' in field_value:
						field_value = field_value.split('*')[0].strip()
						if field_value not in ror_json.values():
							with open(outfile, 'a') as f_out:
								writer = csv.writer(f_out)
								writer.writerow([row['ror_id'], 'missing', field, field_value])
					elif not isinstance(field_value, int) and field_value in inverted_json.keys() and field not in inverted_json[field_value].lower():
						with open(outfile, 'a') as f_out:
							writer = csv.writer(f_out)
							writer.writerow([row['ror_id'], 'transposition', field, field_value, inverted_json[field_value]])

					else:
						if field_value != '' and field_value not in ror_json.values():
							with open(outfile, 'a') as f_out:
								writer = csv.writer(f_out)
								writer.writerow([row['ror_id'], 'missing', field, field_value])
if __name__ == '__main__':
	check_in_json(sys.argv[1])




