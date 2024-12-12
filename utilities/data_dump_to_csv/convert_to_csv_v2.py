import os
import re
import csv
import sys
import json

EXT_ID_TYPES = ['fundref', 'grid', 'isni', 'wikidata']

def format_names(names_list):
    names_dict = {}
    lang_codes = []
    if len(names_list) > 0:
        #for code in lang_codes:
        #    names_dict[code] = []
        for name in names_list:
            code = None
            if name['lang']:
                code = name['lang']
            else:
                code = 'no_lang_code'
            if code in names_dict:
                names_dict[code].append(name['value'])
            else:
                names_dict[code] = [name['value']]
    names_str = str()
    for code in names_dict:
        names_str += code + ": " + ", ".join(names_dict[code]) + "; "
    names_str = names_str.rstrip('; ')
    return names_str

def get_all_ext_ids(ext_ids):
    all_ext_ids = {}
    for ext_id_type in EXT_ID_TYPES:
        all = "".join([";".join(id['all']) for id in ext_ids if id['type']==ext_id_type])
        if all:
            all_ext_ids[ext_id_type] = all
        else:
            all_ext_ids[ext_id_type] = None
    return all_ext_ids

def get_preferred_ext_ids(ext_ids):
    preferred_ids = {}
    for ext_id_type in EXT_ID_TYPES:
        preferred = [id['preferred'] for id in ext_ids if id['type']==ext_id_type]
        if len(preferred) > 0:
            preferred_ids[ext_id_type] = preferred[0]
        else:
            preferred_ids[ext_id_type] = None
    return preferred_ids

def get_all_data(f):
    outfile = f.split('.json')[0]+ '.csv'
    with open(outfile, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['id', 'admin.created.date', 'admin.created.schema_version', 'admin.last_modified.date', 'admin.last_modified.schema_version',
                        'domains', 'established', 'external_ids.type.fundref.all', 'external_ids.type.fundref.preferred',
                        'external_ids.type.grid.all', 'external_ids.type.grid.preferred', 'external_ids.type.isni.all', 'external_ids.type.isni.preferred',
                        'external_ids.type.wikidata.all', 'external_ids.type.wikidata.preferred', 'links.type.website', 'links.type.wikipedia',
                        'locations.geonames_id', 'locations.geonames_details.continent_code', 'locations.geonames_details.continent_name',
                        'locations.geonames_details.country_code', 'locations.geonames_details.country_name',
                        'locations.geonames_details.country_subdivision_code', 'locations.geonames_details.country_subdivision_name',
                        'locations.geonames_details.lat', 'locations.geonames_details.lng', 'locations.geonames_details.name',
                        'names.types.acronym', 'names.types.alias', 'names.types.label', 'names.types.ror_display', 'ror_display_lang', 'relationships', 'status', 'types'])
    with open(f, 'r+', encoding='utf8') as f_in:
        json_file = json.load(f_in)
    for record in json_file:
        ror_id = record['id']
        created_date = record['admin']['created']['date']
        created_schema = record['admin']['created']['schema_version']
        last_mod_date = record['admin']['last_modified']['date']
        last_mod_schema = record['admin']['last_modified']['schema_version']
        domains = ";".join(record['domains']) if record['domains'] != [] else None
        established = record['established']
        # external IDs
        ext_ids = record['external_ids']
        preferred_ids = get_preferred_ext_ids(ext_ids)
        all_ids = get_all_ext_ids(ext_ids)
        # links
        links = record['links']
        links_website = ";".join([link['value'] for link in links if link['type']=='website'])
        links_wikipedia = ";".join([link['value'] for link in links if link['type']=='wikipedia'])
        #locations
        geonames_id = record['locations'][0]['geonames_id']
        geonames_name = record['locations'][0]['geonames_details']['name']
        geonames_continent_code = record['locations'][0]['geonames_details']['continent_code']
        geonames_continent_name = record['locations'][0]['geonames_details']['continent_name']
        geonames_country_code = record['locations'][0]['geonames_details']['country_code']
        geonames_country_name = record['locations'][0]['geonames_details']['country_name']
        geonames_country_subdivision_code = record['locations'][0]['geonames_details']['country_subdivision_code']
        geonames_country_subdivision_name = record['locations'][0]['geonames_details']['country_subdivision_name']
        geonames_lat = record['locations'][0]['geonames_details']['lat']
        geonames_lng = record['locations'][0]['geonames_details']['lng']
        # names
        names = record['names']
        acronyms_list = [name for name in names if 'acronym' in name['types']]
        aliases_list = [name for name in names if 'alias' in name['types']]
        labels_list = [name for name in names if 'label' in name['types']]
        ror_display_list = [name for name in names if 'ror_display' in name['types']]
        acronyms_str = format_names(acronyms_list)
        aliases_str = format_names(aliases_list)
        labels_str = format_names(labels_list)
        ror_display_str = ror_display_list[0]['value']
        ror_display_lang = ror_display_list[0]['lang']
        if not ror_display_lang:
            ror_display_lang = 'no_lang_code'
        #relationships
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
        #status
        status = record['status']
        #types
        types = '; '.join(record['types']) if record['types'] != [] else None

        with open(outfile, 'a') as f_out:
            writer = csv.writer(f_out)
            writer.writerow([ror_id, created_date, created_schema, last_mod_date, last_mod_schema, domains, established,
                            all_ids['fundref'], preferred_ids['fundref'], all_ids['grid'], preferred_ids['grid'],
                            all_ids['isni'], preferred_ids['isni'], all_ids['wikidata'], preferred_ids['wikidata'],
                            links_website, links_wikipedia, geonames_id, geonames_continent_code, geonames_continent_name,
                            geonames_country_code, geonames_country_name, geonames_country_subdivision_code, geonames_country_subdivision_name,
                            geonames_lat, geonames_lng, geonames_name, acronyms_str, aliases_str, labels_str, ror_display_str,
                            ror_display_lang, rels_str, status, types])


if __name__ == '__main__':
	get_all_data(sys.argv[1])
