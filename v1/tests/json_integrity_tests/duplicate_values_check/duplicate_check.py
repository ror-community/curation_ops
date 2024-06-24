import os
import sys
import csv
import glob
import json

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

def check_in_json():
	outfile = os.getcwd() + '/duplicate_check.csv'
	header = ['ror_id', 'field', 'value', 'duplicated_in']
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for file in glob.glob("*.json"):
		with open(file, 'r+', encoding='utf8') as f_in:
			json_file = json.load(f_in)
		ror_id = json_file['id']
		flattened = flatten_json(json_file)
		seen = {}
		ignore = ['', None, []]
		for key, value in flattened.items():
			if isinstance(value, str) and value not in ignore and value in seen.values():
				if 'address' not in key:
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						inverted_seen = {v: k for k, v in seen.items()}
						writer.writerow([ror_id, key, value, inverted_seen[value]])
			else:
				seen[key] = value
if __name__ == '__main__':
	check_in_json()




