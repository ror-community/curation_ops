import os
import re
import sys
import csv
import json
import random


def count_csv_lines(filename):
	with open(filename, 'r') as csv_file:
		csv_reader = csv.reader(csv_file)
		header = next(csv_reader)
		line_count = 0
		for row in csv_reader:
			line_count += 1
		return line_count

def get_random_subset(records, k):
	reservoir = []
	for i, record in enumerate(records):
		if i < k:
			reservoir.append(record)
		else:
			j = random.randint(0, i)
			if j < k:
				reservoir[j] = record
	return reservoir


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


def random_flattened(records):
	random_dict = {}
	random_ids = []
	random_records = get_random_subset(records, 100)
	for record in random_records:
		ror_id = record['id']
		random_ids.append(ror_id)
		flattened = flatten_json(record)
		flattened_values = [str(v) for v in list(flattened.values())]
		random_dict[record['id']] = flattened_values
	return random_dict, random_ids


def check_csv_against_data_dump(csv_file, records, id_list):
	results = []
	with open(csv_file, 'r') as f:
		reader = csv.DictReader(f)
		for row in reader:
			ror_id = row['id']
			if ror_id in id_list:
				matching_record = records[ror_id]
				for field, value in row.items():
					if value not in matching_record:
						if value != '' and value != None:
							results.append([field, value])
	return results


def check_csv(data_dump_file, csv_file):
	outfile = 'csv_checks.csv'
	with open(data_dump_file, 'r+') as f_in:
		records = json.load(f_in)
	dd_len = len(records)
	csv_len = count_csv_lines(csv_file)
	if dd_len != csv_len:
		print("Data dump and CSV have different records counts\nData dump:",dd_len, "\nCSV:", csv_len)
	else:
		print("Data dump and CSV record counts match")
	print("Getting random records...")
	random_records, random_ids = random_flattened(records)
	print("Checking against csv...")
	csv_checks = check_csv_against_data_dump(csv_file, random_records, random_ids)
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(['field', 'value'])
		for csv_check in csv_checks:
			writer.writerow(csv_check)


if __name__ == '__main__':
	check_csv(sys.argv[1],sys.argv[2])




