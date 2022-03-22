import os
import sys
import csv
import json
import glob
import random
import requests
import jsondiff
from time import sleep

DATA_DUMP_FILE_PATH = '/Users/adambuttrick/Downloads/v1.0-2022-03-16-ror-data.json'


def release_files_in_data_dump():
	outfile = os.getcwd() + "/missing_from_data_dump.csv"
	release_file_ids = []
	with open(DATA_DUMP_FILE_PATH, 'r+', encoding='utf8') as f_in:
		data_dump = json.load(f_in)
	print("Total record count in data dump:", len(data_dump))
	for file in glob.glob('*.json'):
		with open(file, 'r+', encoding='utf8') as f_in:
			release_file = json.load(f_in)
		release_file_ids.append(release_file['id'])
		if release_file not in data_dump:
			with open(outfile, 'a') as f_out:
				writer = csv.writer(f_out)
				writer.writerow([release_file['id'], release_file['name']])
	return release_file_ids


def compare_random_data_dump_staging_api(release_ids):
	outfile = os.getcwd() + "/data_dump_staging_discrepancies.csv"
	with open(DATA_DUMP_FILE_PATH, 'r+', encoding='utf8') as f_in:
		data_dump = json.load(f_in)
	minus_release_files = [
		record for record in data_dump if record["id"] not in release_ids]
	random_data_dump_records = []
	for _ in range(100):
		random_data_dump_records.append(random.choice(minus_release_files))
	for record in random_data_dump_records:
		ror_id = record["id"]
		api_url = "https://api.staging.ror.org/organizations/" + ror_id
		print("Comparing data dump file and staging api for", ror_id, "...")
		api_json = requests.get(api_url).json()
		if api_json == record:
			print("Data dump file matches staging.\n")
		if api_json != record:
			print("Data dump file does not match staging.\n")
			with open(outfile, 'a') as f_out:
				writer = csv.writer(f_out)
				writer.writerow([record['id'], record['name']])


def compare_random_data_dump_staging_api(release_ids):
	outfile = os.getcwd() + "/data_dump_staging_api_discrepancies.csv"
	with open(DATA_DUMP_FILE_PATH, 'r+', encoding='utf8') as f_in:
		data_dump = json.load(f_in)
	minus_release_files = [
		record for record in data_dump if record["id"] not in release_ids]
	random_data_dump_records = []
	for _ in range(1000):
		random_data_dump_records.append(random.choice(minus_release_files))
	for record in random_data_dump_records:
		ror_id = record["id"]
		api_url = "https://api.staging.ror.org/organizations/" + ror_id
		print("Comparing data dump file and staging api for", ror_id, "...")
		api_json = requests.get(api_url).json()
		if api_json == record:
			print("Data dump file matches staging.\n")
		if api_json != record:
			print("Data dump file does not match staging.\n")
			record_diff = jsondiff.diff(record, api_json, syntax='symmetric')
			with open(outfile, 'a') as f_out:
				writer = csv.writer(f_out)
				writer.writerow([record['id'], record_diff])
		sleep(1)


def compare_old_data_dump_new_data_dump(release_ids, old_data_dump_file):
	outfile = os.getcwd() + "/old_current_data_dump_discrepancies.csv"
	with open(DATA_DUMP_FILE_PATH, 'r+', encoding='utf8') as f_in:
		data_dump = json.load(f_in)
	with open(old_data_dump_file, 'r+', encoding='utf8') as f_in:
		old_data_dump = json.load(f_in)
	current_dd_minus_release_files = {
		record["id"]:record for record in data_dump if record["id"] not in release_ids
	}
	old_dd_minus_release_files = {
		record["id"]:record for record in old_data_dump if record["id"] not in release_ids
	}
	if len(old_dd_minus_release_files) != len(current_dd_minus_release_files):
		print("Data dumps are different lengths with release files removed\nold:", len(
			old_dd_minus_release_files), '\ncurrent:', len(current_dd_minus_release_files), '\n')
		sys.exit()
	if current_dd_minus_release_files == old_dd_minus_release_files:
		print('Data dumps match with release files are removed')
	else:
		for key, value in old_dd_minus_release_files.items():
			old_record = value
			new_record = current_dd_minus_release_files[key]
			if old_record != new_record:
				record_diff = jsondiff.diff(old_record, new_record, syntax='symmetric')
				with open(outfile, 'a') as f_out:
					writer = csv.writer(f_out)
					writer.writerow([key, record_diff])


if __name__ == '__main__':
	release_ids = release_files_in_data_dump()
	compare_random_data_dump_staging_api(release_ids)
	compare_old_data_dump_new_data_dump(
		release_ids, '/Users/adambuttrick/Downloads/2021-09-23-ror-data.json')
