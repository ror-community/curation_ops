import re
import csv
import json
import glob
import string
import urllib
import argparse
import itertools
import requests
from thefuzz import fuzz


def normalize_text(org_name):
	org_name = org_name.lower()
	org_name = re.sub(r'[^\w\s]', '', org_name)
	exclude = set(string.punctuation)
	org_name = ''.join(ch for ch in org_name if ch not in exclude)
	return org_name


def get_all_names(j):
	all_names = []
	name_types = ['ror_display', 'alias', 'label']
	for name_type in name_types:
		all_names += [name['value']
					  for name in j.get('names', []) if name_type in name.get('types', [])]
	return all_names


def ror_search(org_name):
	base_url = 'https://api.ror.org/v2/organizations'
	params_query = {'query': org_name}
	params_affiliation = {'affiliation': org_name}
	all_params = [params_query, params_affiliation]
	ror_matches = []
	for params in all_params:
		api_response = requests.get(base_url, params=params).json()
		if api_response['number_of_results'] != 0:
			results = api_response['items']
			for result in results:
				if 'organization' in result:
					result = result['organization']
				ror_id = result['id']
				result_names = get_all_names(result)
				for result_name in result_names:
					name_mr = fuzz.ratio(normalize_text(
						org_name), normalize_text(result_name))
					if name_mr >= 90:
						ror_matches.append([ror_id, result_name, name_mr])
	ror_matches = list(ror_matches for ror_matches,
					   _ in itertools.groupby(ror_matches))
	return ror_matches


def check_duplicates(input_dir, output_file):
	header = ["ror_id", "name", "matched_ror_id",
			  "matched_name", "match_ratio"]
	with open(output_file, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for file in glob.glob(f"{input_dir}/*.json"):
		with open(file, 'r+') as f_in:
			json_file = json.load(f_in)
		ror_id = json_file['id']
		record_names = get_all_names(json_file)
		for record_name in record_names:
			print("Searching", ror_id, "-", record_name, "...")
			ror_matches = ror_search(record_name)
			if ror_matches:
				for match in ror_matches:
					with open(output_file, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow([ror_id, record_name] + match)


def parse_arguments():
	parser = argparse.ArgumentParser(
		description="Check for duplicate name records on production from a directory containing ROR records")
	parser.add_argument("-i", "--input_dir", required=True,
						help="Input directory path.")
	parser.add_argument("-o", "--output_file",
						default="on_production_duplicates.csv", help="Output CSV file path.")
	return parser.parse_args()


def main():
	args = parse_arguments()
	check_duplicates(args.input_dir, args.output_file)


if __name__ == '__main__':
	main()
