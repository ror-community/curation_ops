import os
import csv
import sys
import json
import glob
import requests
import jsondiff

def get_diffs():
	curr_dir =  os.getcwd()
	outfile = curr_dir + '/diff_report.csv'
	header = ['ror_id', 'field', 'change']
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for file in glob.glob("*.json"):
		with open(file, 'r+') as f_in:
			json_file = json.load(f_in)
		ror_id = json_file['id']
		api_url  = 'http://localhost:9292/organizations/' + ror_id
		api_json = requests.get(api_url).json()
		file_api_diffs = jsondiff.diff(api_json, json_file, syntax='symmetric')
		if type(file_api_diffs) == list:
			for diff in file_api_diffs:
				for key, value in diff.items():
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([ror_id, key, value])
		else:
			for key, value in file_api_diffs.items():
				with open(outfile, 'a') as f_out:
					writer = csv.writer(f_out)
					writer.writerow([ror_id, key, value])

if __name__ == '__main__':
	get_diffs()

