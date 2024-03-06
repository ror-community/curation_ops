import re
import csv
import json
import glob
import argparse
from copy import deepcopy
from string import punctuation
from thefuzz import fuzz


def normalize_text(text):
	text = re.sub(' +', ' ', text)
	text = text.strip().lower()
	return text


def get_all_names(j):
	all_names = []
	name_types = ['ror_display', 'alias', 'label']
	for name_type in name_types:
		all_names += [name['value'] for name in j.get('names', []) if name_type in name.get('types', [])]
	return all_names


def check_duplicates(input_dir, output_file):
	all_records = {}
	header = ['ror_id', 'name', 'duplicate_ror_id', 'duplicate_name' , 'match_ratio']
	with open(output_file, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for file in glob.glob(f"{input_dir}/*.json"):
		with open(file, 'r+') as f_in:
			record = json.load(f_in)
		ror_id = record['id']
		all_records[ror_id] = get_all_names(record)
	copy_all_records = deepcopy(all_records)
	for record_id, record_names in all_records.items():
		for record_name in record_names:
			for copied_id, copied_names in copy_all_records.items():
				if copied_id == record_id:
					pass
				else:
					for copied_name in copied_names:
						match_ratio = fuzz.ratio(normalize_text(record_name), normalize_text(copied_name))
						if match_ratio >= 85:
							with open(output_file, 'a') as f_out:
								writer = csv.writer(f_out)
								writer.writerow([record_id, record_name, copied_id, copied_name, match_ratio])


def parse_arguments():
	parser = argparse.ArgumentParser(
		description="Check for duplicate name metadata in a directory containing ROR records")
	parser.add_argument("-i", "--input_dir", required=True,
						help="Input directory path.")
	parser.add_argument("-o", "--output_file",
						default="in_release_duplicates.csv", help="Output CSV file path.")
	return parser.parse_args()


def main():
	args = parse_arguments()
	check_duplicates(args.input_dir, args.output_file)


if __name__ == '__main__':
	main()


