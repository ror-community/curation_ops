import os
import sys
import json
import re
import requests
import update_address
from datetime import datetime


def download_record(ror_id, json_dir):
	api_url = 'https://api.ror.org/organizations/' + ror_id
	ror_data = requests.get(api_url).json()
	ror_data = update_address.update_geonames(ror_data)
	json_file_path = json_dir + ror_id + '.json'
	with open(json_file_path, 'w', encoding='utf8') as f_out:
		json.dump(ror_data, f_out, ensure_ascii=False, indent=4)


def update_address_only(f):
	with open(f) as f_in:
		ror_ids = [line.strip() for line in f_in]
	ror_ids = [re.sub('https://ror.org/', '', ror_id) for ror_id in ror_ids]
	now = datetime.now()
	json_dir = os.getcwd() + '/' + now.strftime("%Y%m%d_%H%M%S") + '/'
	os.makedirs(json_dir)
	for ror_id in ror_ids:
		download_record(ror_id, json_dir)


if __name__ == '__main__':
	update_address_only(sys.argv[1])
