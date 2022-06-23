import os
import sys
import json
import re
import glob
import update_address


def export_json(json_data, json_file):
	json_file.seek(0)
	json.dump(json_data, json_file, ensure_ascii=False, indent=2)
	json_file.truncate()


def update_address_in_file(json_file):
	with open(json_file, 'r+') as json_in:
		json_data = json.load(json_in)
		json_data = update_address.update_geonames(json_data)
		export_json(json_data, json_in)


def update_addresses():
	for json_file in glob.glob('*.json'):
		update_address_in_file(json_file)


if __name__ == '__main__':
	update_addresses()
