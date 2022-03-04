import csv
import sys
import os
import json
import requests
from thefuzz import fuzz

def get_ror_name(ror_id):
	search_url =  "https://api.ror.org/organizations/" + ror_id
	response = requests.get(search_url)
	if response.status_code == 404:
		print('No record in ROR for ', ror_id)
		print(search_url)
		return None
	else:
		response = response.json()
		ror_name = response['name']
		return ror_name

def get_release_file(json_dir, ror_id):
	ror_id = ror_id.split('.org/')[1]
	release_filepath = json_dir + ror_id + '.json'
	try:
		with open(release_filepath) as f_in:
			release_file = json.load(f_in)
			release_name = release_file['name']
			return release_name
	except OSError:
		print('Unable to located file at', release_filepath)
		return None

def check_relationships_file(f):
	outfile = os.getcwd() + '/release_file_check.csv'
	# Add directory where the JSON files for the release are located
	json_dir = ''
	with open(f) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			name = row['Name of org in Record ID']
			record_id = row['Record ID']
			related_id = row['Related ID']
			related_name = row['Name of org in Related ID']
			json_name = get_release_file(json_dir, record_id)
			json_mr = fuzz.ratio(name, json_name)
			if row['Current location of Related ID'] == 'Production':
				ror_name = get_ror_name(related_id)
				ror_mr = fuzz.ratio(related_name, ror_name)
				with open(outfile, 'a') as f_out:
					writer = csv.writer(f_out)
					writer.writerow([record_id, name, json_name, json_mr, related_id, related_name, ror_name, ror_mr])
			else:
				ror_name = get_release_file(json_dir, related_id)
				ror_mr = ror_mr = fuzz.ratio(related_name, ror_name)
				with open(outfile, 'a') as f_out:
					writer = csv.writer(f_out)
					writer.writerow([record_id, name, json_name, json_mr, related_id, related_name, ror_name, ror_mr])

if __name__ == '__main__':
	check_relationships_file(sys.argv[1])
