import os
import re
import sys
import csv
import json
import glob
from copy import deepcopy
from string import punctuation
from thefuzz import fuzz


def normalize(text):
	text = text.lower()
	text = text.translate(str.maketrans('', '', punctuation))
	return text

def duplicate_check():
	all_records = {}
	outfile = os.getcwd() + '/duplicates.csv'
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(['ror_id', 'name', 'duplicate_ror_id', 'duplicate_name' , 'match_ratio'])
	for json_file in glob.glob('*.json'):
		with open(json_file, 'r+', encoding='utf-8') as f_in:
			record = json.load(f_in)
		all_names =[]
		ror_id = record['id']
		name = record['name']
		all_names += [name]
		if record['aliases'] != []:
			all_names += record['aliases']
		if record['labels'] != []:
			all_names += [label['label'] for label in record['labels']]
		all_records[ror_id] =  all_names
	copy_all_records = deepcopy(all_records)
	for record_id, record_names in all_records.items():
		for record_name in record_names:
			for copied_id, copied_names in copy_all_records.items():
				if copied_id == record_id:
					pass
				else:
					for copied_name in copied_names:
						match_ratio = fuzz.ratio(normalize(record_name), normalize(copied_name))
						if match_ratio >= 85:
							print(record_name, normalize(record_name), copied_name, normalize(copied_name), match_ratio)
							with open(outfile, 'a') as f_out:
								writer = csv.writer(f_out)
								writer.writerow([record_id, record_name, copied_id, copied_name, match_ratio])

if __name__ == '__main__':
	duplicate_check()



