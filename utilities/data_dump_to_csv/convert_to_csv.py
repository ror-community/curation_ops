import os
import re
import csv
import sys
import json


def get_all_data(f):
	outfile = f.split('.json')[0]+ '.csv'
	with open(outfile, 'w') as f_out:
		writer = csv.writer(f_out)
		writer.writerow(['id', 'name', 'types', 'status', 'links', 'aliases', 'labels', 'acronyms', 'wikipedia_url', 'established',
						 'addresses[0].lat', 'addresses[0].lng', 'addresses[0].geonames_city.name', 'addresses[0].geonames_city.id',
						 'addresses[0].geonames_city.geonames_admin1.name','addresses[0].geonames_city.geonames_admin1.code',
						 'addresses[0].geonames_city.geonames_admin2.name','addresses[0].geonames_city.geonames_admin2.code',
						 'country.country_code', 'country.country_name', 'external_ids.GRID.preferred', 'external_ids.GRID.all',
						 'external_ids.ISNI.preferred', 'external_ids.ISNI.all', 'external_ids.FundRef.preferred', 'external_ids.FundRef.all',
						 'external_ids.Wikidata.preferred', 'external_ids.Wikidata.all', 'relationships'])
	with open(f, 'r+', encoding='utf8') as f_in:
		json_file = json.load(f_in)
	for record in json_file:
		ror_id = record['id']
		primary_name = record['name']
		status = record['status']
		links = record['links'][0] if record['links'] != [] else None
		types, aliases, acronyms = record['types'], record['aliases'], record['acronyms']
		types = '; '.join(types) if types != [] else None
		aliases = '; '.join(aliases) if aliases != [] else None
		labels = record['labels']
		labels_dict = {}
		if len(labels) > 0:
			for label in labels:
				code = None
				if label['iso639']:
					code = label['iso639']
				else:
					code = 'no_lang_code'
				if code in labels_dict:
					labels_dict[code].append(label['label'])
				else:
					labels_dict[code] = [label['label']]
		labels_str = str()
		for code in labels_dict:
			labels_str += code + ": " + ", ".join(labels_dict[code]) + "; "
		labels_str = labels_str.rstrip('; ')
		acronyms = '; '.join(acronyms) if acronyms != [] else None
		country_code = record['country']['country_code']
		country_name = record['country']['country_name']
		wikipedia_url = record['wikipedia_url']
		established = record['established']
		relationships = record['relationships']
		relationships_dict = {}
		if len(relationships) > 0:
			rel_types = [rel['type'] for rel in relationships]
			for rel_type in rel_types:
				relationships_dict[rel_type] = []
				for rel in relationships:
					if rel['type'] == rel_type:
						relationships_dict[rel_type].append(rel['id'])
		rels_str = str()
		for rel_type in relationships_dict:
			rels_str += rel_type + ": " + ", ".join(relationships_dict[rel_type]) + "; "
		rels_str = rels_str.rstrip('; ')
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
			writer.writerow([ror_id, primary_name, types, status, links, aliases, labels_str, acronyms, wikipedia_url, established, lat,
							 lng, city, city_id, admin1, admin1_id, admin2, admin2_id, country_code, country_name, grid_id_preferred,
							 grid_id_all, isni_id_preferred, isni_id_all, funder_id_preferred, funder_id_all, wikidata_id_preferred,
							 wikidata_id_all, rels_str])


if __name__ == '__main__':
	get_all_data(sys.argv[1])
