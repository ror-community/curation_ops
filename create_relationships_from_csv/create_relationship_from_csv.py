import os
import re
import sys
import csv
import json
import requests

def get_related_name_from_api(ror_id):
	api_url = 'https://api.ror.org/organizations/' + ror_id
	r = requests.get(api_url)
	try:
		record = r.json()
		org_name = record['name']
		return org_name
	except KeyError:
		return None

def get_related_name_from_file(ror_id):
	related_file_name = re.sub('https://ror.org/', '', ror_id) + '.json'
	related_file_path =  os.getcwd() + '/' + related_file_name
	with open(related_file_path, 'r+', encoding='utf8') as json_in:
	    json_data = json.load(json_in)
	    related_org_name = json_data['name']
	    return related_org_name

def parse_csv(f):
	relationships = {}
	with open(f, encoding='utf-8-sig') as f_in:
		reader = csv.DictReader(f_in)
		fieldnames = reader.fieldnames
		for row in reader:
			entry = {'Parent':[], 'Child':[], 'Related':[]}
			ror_id = row['ror_id']
			org_name = row['name']
			for fieldname in fieldnames:
				if "Parent" in fieldname and row[fieldname] != '':
					entry['Parent'].append(row[fieldname])
				elif "Child" in fieldname and row[fieldname] != '':
					entry['Child'].append(row[fieldname])
				elif "Related" in fieldname and row[fieldname] != '':
					entry['Related'].append(row[fieldname])
			relationships[ror_id] = {'name':org_name, 'relationships': entry}
	return relationships

def create_relationships_file(relationships):
	header = ['Issue # from Github', 'Issue URL', 'Issue title from Github', 'Name of org in Record ID', 'Record ID',
			  'Related ID', 'Name of org in Related ID', 'Relationship of Related ID to Record ID', 'Current location of Related ID']              
	outfile = os.getcwd() + '/relationships.csv'
	inverted_relationships = {'Parent':'Child', 'Child':'Parent', 'Related':'Related'}
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(header)
	for key, value in relationships.items():
		ror_id = key
		org_name = value['name']
		org_relationships = value['relationships']
		for relationship_type, related_ror_ids in org_relationships.items():
			for related_ror_id in related_ror_ids:
				related_org_name = get_related_name_from_api(related_ror_id)
				if related_org_name == None:
					related_org_name = get_related_name_from_file(related_ror_id)
					csv_entry  = ['','','', org_name, ror_id, related_ror_id, related_org_name, relationship_type, 'Release']
					inverted_csv_entry = ['','','', related_org_name,related_ror_id, ror_id, org_name, inverted_relationships[relationship_type], 'Release']
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow(csv_entry)
						writer.writerow(inverted_csv_entry)
				else:
					csv_entry  = ['','','', org_name, ror_id, related_ror_id, related_org_name, relationship_type, 'Production']
					inverted_csv_entry = ['','','', related_org_name,related_ror_id, ror_id, org_name, inverted_relationships[relationship_type], 'Release']
					with open(outfile, 'a') as f_out:
						writer = csv.writer(f_out)
						writer.writerow(csv_entry)
						writer.writerow(inverted_csv_entry)



if __name__ == '__main__':
	relationships = parse_csv(sys.argv[1])
	create_relationships_file(relationships)


