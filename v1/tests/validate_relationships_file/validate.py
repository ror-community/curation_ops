import os
import csv
import sys
import json
import requests


def write_errors(f, entry, error):
	with open(f, 'a') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(entry + [error])

def get_ror_name(ror_id):
    url = 'https://api.ror.org/organizations/' + ror_id
    print(ror_id, url)
    ror_data = requests.get(url).json()
    return ror_data['name']

def validate_relationships_file(f1, f2):
	release_records = {}
	with open(f1) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			release_records[row['ror_id']] = row['name']
	outfile = os.getcwd() + '/relationships_file_errors.csv'
	with open(f2) as f_in:
		reader = csv.DictReader(f_in)
		for row in reader:
			if row['Record ID'] in release_records.keys():
				release_record_name = release_records[row['Record ID']]
				if release_record_name != row['Name of org in Record ID']:
					error_text = 'Record name does not match release file - Release file: ' +  release_record_name + ", Related Name: " + row['Name of org in Record ID']
					write_errors(outfile, list(row.values()), error_text)
				if row['Related ID'] in release_records.keys() and row['Current location of Related ID'] != 'Release':
					write_errors(outfile, list(row.values()), 'both files in release, but related ID is listed as on production')
				if row['Related ID'] not in release_records.keys() and row['Current location of Related ID'] == 'Release':
					write_errors(outfile, list(row.values()), 'related file is on production, but related ID is listed as in the release')
				if row['Related ID'] in release_records.keys():
					release_related_name = release_records[row['Related ID']]
					if release_related_name != row['Name of org in Related ID']:
						error_text = 'related name does not match release file - Release file: ' +  release_related_name + ", Related Name: " + row['Name of org in Related ID']
						write_errors(outfile, list(row.values()), error_text)
			if row['Name of org in Record ID'] == row['Name of org in Related ID']:
				write_errors(outfile, list(row.values()), 'same name in record and related record' )
			if row['Record ID'] == row['Related ID']:
				write_errors(outfile, list(row.values()), 'same ROR ID in record and related record')
			if row['Related ID'] not in release_records.keys():
				prod_related_name = get_ror_name(row['Related ID'])
				if prod_related_name != row['Name of org in Related ID']:
					error_text = 'related name does not match production - Production: ' +  prod_related_name + ", Related Name: " + row['Name of org in Related ID']
					write_errors(outfile, list(row.values()), error_text)

if __name__ == '__main__':
	validate_relationships_file(sys.argv[1], sys.argv[2])