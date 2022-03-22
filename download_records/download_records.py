import re
import os
import sys
import csv
import json
import requests
from datetime import datetime



def download_record(ror_id, json_file_path):
	api_url = 'https://api.ror.org/organizations/' + ror_id
	ror_data = requests.get(api_url).json()
	with open(json_file_path, 'w', encoding='utf8') as f_out:
		json.dump(ror_data, f_out, indent=4)

def parse_and_download(f):
	now = datetime.now()
	json_dir = os.getcwd() + '/' + now.strftime("%Y%m%d_%H%M%S") + '/'
	os.makedirs(json_dir)
	with open(f, encoding='utf-8-sig') as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			ror_id = row['ror_id']
			print('Downloading', ror_id, '...')
			ror_id = ror_id.split('.org/')[1]
			json_file_path = ror_id + '.json'
			json_file_path = json_dir + json_file_path
			download_record(ror_id, json_file_path)

if __name__ == '__main__':
	parse_and_download(sys.argv[1])

