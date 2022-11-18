import os
import re
import csv
import sys
import json


def get_all_data(f):
	outfile = f.split('.json')[0]+ '.csv'
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(['ror_id', 'name', 'type', 'status', 'links', 'aliases', 'labels', 'acronyms', 'wikipedia_url', 'established',
						 'lat', 'lng', 'city', 'city_id', 'admin1','admin1_id', 'admin2','admin2_id', 'country_code',
						 'country_name', 'grid_id_preferred', 'grid_id_all', 'isni_id_preferred', 'isni_id_preferred',
						 'funder_id_preferred','funder_id_all', 'wikidata_id_preferred', 'wikidata_id_all', 'related_ror_ids'])
	with open(f, 'r+', encoding='utf8') as f_in:
		json_file = json.load(f_in)
	for record in json_file:
		ror_id = record['id']
		primary_name = record['name']
		org_type = record['types'][0] if record['types'] != [] else None
		status = record['status']
		links = record['links'][0] if record['links'] != [] else None
		aliases, labels, acronyms = record['aliases'], record['labels'], record['acronyms']
		aliases = '; '.join(aliases) if aliases != [] else None
		labels = '; '.join([label['label'] for label in labels]) if labels != [] else None
		acronyms = '; '.join(acronyms) if acronyms != [] else None
		country_code = record['country']['country_code']
		country_name = record['country']['country_name']
		wikipedia_url = record['wikipedia_url']
		established = record['established']
		relationships = record['relationships']
		related_ids = '; '.join([relationship['id'] for relationship in relationships]) if relationships != [] else None
		address = record['addresses'][0]
		lat = address['lat'] if 'lat' in address.keys() else None
		lng = address['lng'] if 'lng' in address.keys() else None
		try:
			city = address['geonames_city']['city'] if 'geonames_city' in address.keys() else None
			city_id = address['geonames_city']['id']
		except KeyError:
			city = address['city'] if 'city' in address.keys() and address['city'] != None else None
			city_id = address['geonames_city']['id'] if 'id' in address['geonames_city'].keys() else None
		admin1 = address['geonames_city']['geonames_admin1']['name'] if 'geonames_admin1' in address['geonames_city'].keys() else None
		admin1_id = address['geonames_city']['geonames_admin1']['id'] if 'geonames_admin1' in address['geonames_city'].keys() else None
		admin2 = address['geonames_city']['geonames_admin1']['name'] if 'geonames_admin2' in address['geonames_city'].keys() else None
		admin2_id = address['geonames_city']['geonames_admin1']['id'] if 'geonames_admin2' in address['geonames_city'].keys() else None
		grid_id_preferred, isni_id_preferred, funder_id_preferred, wikidata_id_preferred = None, None, None, None
		grid_id_all, isni_id_all, funder_id_all, wikidata_id_all = None, None, None, None
		external_ids = record['external_ids']
		if 'GRID' in external_ids.keys() and external_ids['GRID'] != {'preferred':'null', all:[]}:
			if external_ids['GRID']['preferred'] != None:
				grid_id_preferred = external_ids['GRID']['preferred']
				grid_id_all = external_ids['GRID']['all']
		if 'ISNI' in external_ids.keys() and external_ids['ISNI'] != {'preferred':'null', all:[]}:
			if external_ids['ISNI']['preferred'] != None:
				isni_id_preferred = external_ids['ISNI']['preferred']
			if len(external_ids['ISNI']['all']) == 1:
				isni_id_all = external_ids['ISNI']['all'][0]
			else:
				isni_id_all = ';'.join(external_ids['ISNI']['all'])
		if 'FundRef' in external_ids.keys() and external_ids['FundRef'] != {'preferred':'null', all:[]}:
			if external_ids['FundRef']['preferred'] != None:
				funder_id_preferred = external_ids['FundRef']['preferred']
			if len(external_ids['FundRef']['all']) == 1:
				funder_id_all = external_ids['FundRef']['all'][0]
			else:
				funder_id_all = ';'.join(external_ids['FundRef']['all'])
		if 'Wikidata' in external_ids.keys() and external_ids['Wikidata'] != {'preferred':'null', all:[]}:
			if external_ids['Wikidata']['preferred'] != None:
				wikidata_id_preferred = external_ids['Wikidata']['preferred']
			if len(external_ids['Wikidata']['all']) == 1:
				wikidata_id_all = external_ids['Wikidata']['all'][0]
			else:
				wikidata_id_all = ';'.join(external_ids['Wikidata']['all'])
		with open(outfile, 'a') as f_out:
			writer = csv.writer(f_out)
			writer.writerow([ror_id, primary_name, org_type, status, links, aliases, labels, acronyms, wikipedia_url, established, lat,
							 lng, city, city_id, admin1, admin1_id, admin2, admin2_id, country_code, country_name, grid_id_preferred, 
							 grid_id_all, isni_id_preferred, isni_id_all, funder_id_preferred, funder_id_all, wikidata_id_preferred, 
							 wikidata_id_all, related_ids])


if __name__ == '__main__':
	get_all_data(sys.argv[1])
