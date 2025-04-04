import copy
import json
import logging
import os

import v2_fields
import v2_enums

ERROR_LOG = "errors.log"
V2_TEMPLATE = os.path.join(os.path.dirname(__file__), 'v2_template.json')

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

def sort_list_fields(v2_data):
    for field in v2_data:
        if field in v2_enums.SORT_KEYS:
            if v2_enums.SORT_KEYS[field] is not None:
                sort_key = v2_enums.SORT_KEYS[field]
                sorted_vals = sorted(v2_data[field], key=lambda x: x[sort_key])
            else:
                sorted_vals = sorted(v2_data[field])
            v2_data[field] = sorted_vals
    return v2_data

# admin
def format_v2_admin(file_date):
    v2_admin = v2_fields.v2_admin_template
    v2_admin['created']['date'] = file_date
    v2_admin['created']['schema_version'] = copy.copy(v2_enums.SCHEMA_VERSIONS['1'])
    v2_admin['last_modified']['date'] = file_date
    v2_admin['last_modified']['schema_version'] = copy.copy(v2_enums.SCHEMA_VERSIONS['2'])
    return v2_admin

# relationships
def format_v2_relationships(v1_relationships):
    for v1_rel in v1_relationships:
        v1_rel['type'] = v1_rel['type'].lower()
    return v1_relationships

# external_ids
def get_v2_ext_id_type(v1_ext_id_type):
    type_key = "".join([k for k in v2_enums.EXTERNAL_ID_TYPES if v2_enums.EXTERNAL_ID_TYPES[k]==v1_ext_id_type.lower()])
    if type_key:
        return v2_enums.EXTERNAL_ID_TYPES[type_key]
    else:
        return None

def format_v2_external_ids(v1_external_ids):
    v2_external_ids = []
    for k in v1_external_ids:
        v2_ext_id_type = get_v2_ext_id_type(k)
        if v2_ext_id_type:
            v2_external_id = copy.deepcopy(v2_fields.v2_external_id_template)
            v2_external_id['type'] = v2_ext_id_type
            if isinstance(v1_external_ids[k]['all'], list) and len(v1_external_ids[k]['all']) > 0:
                v2_external_id['all'] = v1_external_ids[k]['all']
            if isinstance(v1_external_ids[k]['all'], str) and len(v1_external_ids[k]['all']) > 0:
                v2_external_id['all'].append(v1_external_ids[k]['all'])
            if v1_external_ids[k]['preferred']:
                v2_external_id['preferred'] = v1_external_ids[k]['preferred']
            if v2_external_id['preferred'] or v2_external_id['all']:
                v2_external_ids.append(v2_external_id)
    return v2_external_ids

# links
def format_v2_links(v1_links, v1_wikipedia_url):
    v2_links = []
    v1_links = filter(None, v1_links)
    for link in v1_links:
        v2_link = copy.deepcopy(v2_fields.v2_link_template)
        v2_link['value'] = link
        v2_link['type'] = copy.copy(v2_enums.LINK_TYPES['WEBSITE'])
        v2_links.append(v2_link)
    if v1_wikipedia_url:
        v2_link = copy.deepcopy(v2_fields.v2_link_template)
        v2_link['value'] = v1_wikipedia_url
        v2_link['type'] = copy.copy(v2_enums.LINK_TYPES['WIKIPEDIA'])
        v2_links.append(v2_link)
    return v2_links

# locations
def format_v2_locations(v1_data):
    v2_locations = []
    for address in v1_data['addresses']:
        v2_location = copy.deepcopy(v2_fields.v2_location_template)
        # temp until missing geonames IDs/names are fixed
        if address['geonames_city']:
            if address['geonames_city']['id']:
                v2_location['geonames_id'] = address['geonames_city']['id']
            if address['geonames_city']['city']:
                v2_location['geonames_details']['name'] = address['geonames_city']['city']
            if address['geonames_city']['geonames_admin1']:
                if address['geonames_city']['geonames_admin1']['code']:
                    if '.' in address['geonames_city']['geonames_admin1']['code']:
                        code = address['geonames_city']['geonames_admin1']['code'].split('.')[1]
                    else:
                        code = address['geonames_city']['geonames_admin1']['code']
                    v2_location['geonames_details']['country_subdivision_code'] = code
                if address['geonames_city']['geonames_admin1']['name']:
                    v2_location['geonames_details']['country_subdivision_name'] = address['geonames_city']['geonames_admin1']['name']
        if v1_data['country']['country_code']:
            v2_location['geonames_details']['country_code'] = v1_data['country']['country_code']
        if v1_data['country']['country_name']:
            v2_location['geonames_details']['country_name'] = v1_data['country']['country_name']
        if address['lat']:
            v2_location['geonames_details']['lat'] = address['lat']
        if address['lng']:
            v2_location['geonames_details']['lng'] = address['lng']
        v2_locations.append(v2_location)
    return v2_locations

# names
def format_v2_names(v1_data):
    v2_names = []

    if v1_data['name']:
        v2_name = copy.deepcopy(v2_fields.v2_name_template)
        v2_name['value'] = v1_data['name']
        v2_name['types'].extend([v2_enums.NAME_TYPES['ROR_DISPLAY'], v2_enums.NAME_TYPES['LABEL']])
        v2_names.append(v2_name)

    if len(v1_data['aliases']) > 0:
        for alias in v1_data['aliases']:
            v2_alias = copy.deepcopy(v2_fields.v2_name_template)
            v2_alias['value'] = alias
            v2_alias['types'].append(v2_enums.NAME_TYPES['ALIAS'])
            v2_names.append(v2_alias)

    if len(v1_data['labels']) > 0:
        for label in v1_data['labels']:
            v2_label = copy.deepcopy(v2_fields.v2_name_template)
            v2_label['value'] = label['label']
            v2_label['lang'] = label['iso639']
            v2_label['types'].append(v2_enums.NAME_TYPES['LABEL'])
            v2_names.append(v2_label)

    if len(v1_data['acronyms']) > 0:
        for acronym in v1_data['acronyms']:
            v2_acronym = copy.deepcopy(v2_fields.v2_name_template)
            v2_acronym['value'] = acronym
            v2_acronym['types'].append(v2_enums.NAME_TYPES['ACRONYM'])
            v2_names.append(v2_acronym)

    return v2_names

def convert_v1_to_v2(v1_data, file_date):
    try:
        with open(V2_TEMPLATE) as template_file:
            v2_data = json.load(template_file)
            # these fields don't change
            v2_data['id'] = v1_data['id']
            v2_data['types'] = [type.lower() for type in v1_data['types']]
            v2_data['status'] = v1_data['status']
            v2_data['established'] = v1_data['established']
            v2_data['domains'] = []
            # these fields DO change
            v2_data['relationships'] = format_v2_relationships(v1_data['relationships'])
            v2_data['external_ids'] = format_v2_external_ids(v1_data['external_ids'])
            v2_data['links'] = format_v2_links(v1_data['links'], v1_data['wikipedia_url'])
            v2_data['locations'] = format_v2_locations(v1_data)
            v2_data['names'] = format_v2_names(v1_data)
            v2_data['admin'] = format_v2_admin(file_date)
            return sort_list_fields(v2_data)
    except Exception as e:
        logging.error(f"Error converting v1 data to v2: {e}")
