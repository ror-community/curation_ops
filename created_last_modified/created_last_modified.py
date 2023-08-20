import re
import csv
import json
import argparse


def extract_date(file_name):
	match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
	if match:
		return match.group(1)
	return None


def find_created(files):
	id_map = {}
	processed_ids = set()
	for filepath in files:
		release_date = extract_date(filepath)
		try:
			with open(filepath, 'r') as file:
				records = json.load(file)
				for record in records:
					ror_id = record.get("id")
					if ror_id not in processed_ids:
						id_map[ror_id] = release_date
						processed_ids.add(ror_id)
		except:
			print(f"Error processing file {filepath}.")
	return id_map


def find_last_modified(files):
	id_last_modified = {}
	previous_records = {}
	all_ids = set()
	for filepath in (files):
		release_date = extract_date(filepath)
		try:
			with open(filepath, 'r') as file:
				records = json.load(file)
				for record in records:
					ror_id = record.get("id")
					if ror_id not in all_ids:
						all_ids.add(ror_id)
						previous_records[ror_id] = record
						id_last_modified[ror_id] = release_date
					elif record != previous_records[ror_id]:
						previous_records[ror_id] = record
						id_last_modified[ror_id] = release_date
		except:
			print(f"Error processing file {filepath}.")
	return id_last_modified


def write_to_csv(first_appearance, last_modified, output_file):
	with open(output_file, 'w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(["ror_id", "created", "last_modified"])
		for ror_id in first_appearance:
			writer.writerow([ror_id, first_appearance[ror_id],
							 last_modified.get(ror_id, first_appearance[ror_id])])


def parse_args():
	parser = argparse.ArgumentParser(
		description="Parse ROR data dump files to determine when a record was first created and last modified.")
	parser.add_argument("-l", "--file_list", help="Sorted list of paths for the data dump files")
	parser.add_argument("-o", "--output", default="created_last_modified.csv",
						help="Name of the CSV output file.")
	return parser.parse_args()


def main():
	args = parse_args()
	with open(args.file_list) as f_in:
		data_dumps = [line.strip() for line in f_in]
	first_appearance_data = find_created(data_dumps)
	last_modified_data = find_last_modified(data_dumps)
	write_to_csv(first_appearance_data, last_modified_data, args.output)


if __name__ == "__main__":
	main()
