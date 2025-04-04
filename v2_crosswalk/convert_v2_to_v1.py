import copy
import json
import logging
import os

import v1_fields
import v1_enums
import v2_enums

ERROR_LOG = "errors.log"
V1_TEMPLATE = os.path.join(os.path.dirname(__file__), 'v1_template.json')

logging.basicConfig(filename=ERROR_LOG,level=logging.ERROR, filemode='w')

# relationships
def format_v1_relationships(v2_relationships):
    for v2_rel in v2_relationships:
        v2_rel['type'] = v2_rel['type'].title()
    return v2_relationships

# external_ids
def get_v1_ext_id_type(v2_ext_id_type):
    type_key = "".join([k for k in v1_enums.EXTERNAL_ID_TYPES if \
                        v1_enums.EXTERNAL_ID_TYPES[k].lower()==v2_ext_id_type])
    if type_key:
        return v1_enums.EXTERNAL_ID_TYPES[type_key]
    else:
        return None

def format_v1_external_ids(v2_external_ids):
    v1_external_ids = {}
    for v2_external_id in v2_external_ids:
        v1_ext_id_type = get_v1_ext_id_type(v2_external_id['type'])
        if v1_ext_id_type:
            v1_external_id = copy.deepcopy(v1_fields.v1_external_id_template)
            if isinstance(v2_external_id['all'], list) and len(v2_external_id['all']) > 0:
                if v1_ext_id_type == v1_enums.EXTERNAL_ID_TYPES['GRID']:
                    v1_external_id['all'] = v2_external_id['all'][0]
                else:
                    v1_external_id['all'] = v2_external_id['all']
            if isinstance(v2_external_id['all'], str) and len(v2_external_id['all']) > 0:
                v1_external_id['all'].append(v2_external_id['all'])
            if v2_external_id['preferred']:
                v1_external_id['preferred'] = v2_external_id['preferred']
            if v1_external_id['preferred'] or v1_external_id['all']:
                v1_external_ids[v1_ext_id_type] = v1_external_id
    return v1_external_ids

# links
def format_v1_links(v2_links):
    v1_links = []
    v2_links = filter(None, v2_links)
    for link in v2_links:
        if link['type'] == v2_enums.LINK_TYPES['WEBSITE']:
            v1_links.append(link['value'])
    return v1_links

# wikipedia_url
def format_v1_wikipedia_url(v2_links):
    v2_links = filter(None, v2_links)
    for link in v2_links:
        if link['type'] == v2_enums.LINK_TYPES['WIKIPEDIA']:
            return link['value']
    return None

# addresses
def format_v1_addresses(v2_locations):
    v1_addresses = []
    v2_location = v2_locations[0]
    v1_address = copy.deepcopy(v1_fields.v1_address_template)
    if v2_location['geonames_id']:
        v1_address['geonames_city']['id'] = v2_location['geonames_id']
    if v2_location['geonames_details']:
        if v2_location['geonames_details']['country_subdivision_code']:
            v1_address['geonames_city']['geonames_admin1']['code'] = f"{v2_location['geonames_details']['country_code']}.{v2_location['geonames_details']['country_subdivision_code']}"
        if v2_location['geonames_details']['country_subdivision_name']:
            v1_address['geonames_city']['geonames_admin1']['name'] = v2_location['geonames_details']['country_subdivision_name']
        if v2_location['geonames_details']['lat']:
            v1_address['lat'] = v2_location['geonames_details']['lat']
        if v2_location['geonames_details']['lng']:
            v1_address['lng'] = v2_location['geonames_details']['lng']
        if v2_location['geonames_details']['name']:
            v1_address['city'] = v2_location['geonames_details']['name']
            v1_address['geonames_city']['city'] = v2_location['geonames_details']['name']
    v1_addresses.append(v1_address)
    return v1_addresses


# country
def format_v1_country(v2_locations):
    v2_location = v2_locations[0]
    v1_country = copy.deepcopy(v1_fields.v1_country_template)
    if v2_location['geonames_details']:
        if v2_location['geonames_details']['country_code']:
            v1_country['country_code'] = v2_location['geonames_details']['country_code']
        if v2_location['geonames_details']['country_name']:
            v1_country['country_name'] = v2_location['geonames_details']['country_name']
    return v1_country

# name
def format_v1_name(v2_names):
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ROR_DISPLAY'] in v2_name['types']:
            return v2_name['value']
    return None

# acronyms
def format_v1_acronyms(v2_names):
    v1_acronyms = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ACRONYM'] in v2_name['types']:
            v1_acronyms.append(v2_name['value'])
    return v1_acronyms

# aliases
def format_v1_aliases(v2_names):
    v1_aliases = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['ALIAS'] in v2_name['types']:
            v1_aliases.append(v2_name['value'])
    return v1_aliases

# labels
def format_v1_labels(v2_names):
    v1_labels = []
    for v2_name in v2_names:
        if v2_enums.NAME_TYPES['LABEL'] in v2_name['types'] and v2_enums.NAME_TYPES['ROR_DISPLAY'] not in v2_name['types']:
            v1_label = copy.deepcopy(v1_fields.v1_label_template)
            v1_label['label'] = v2_name['value']
            v1_label['iso639'] = v2_name['lang']
            v1_labels.append(v1_label)
    return v1_labels

def convert_v2_to_v1(v2_data):
    try:
        with open(V1_TEMPLATE) as template_file:
            v1_data = json.load(template_file)
            # these fields don't change
            v1_data['id'] = v2_data['id']
            v1_data['types'] = [type.title() for type in v2_data['types'] if type.title() in v1_enums.ORG_TYPES.values()]
            v1_data['status'] = v2_data['status']
            v1_data['established'] = v2_data['established']
            v1_data['email_address'] = None
            v1_data['ip_addresses'] = []
            # these fields DO change
            v1_data['relationships'] = format_v1_relationships(v2_data['relationships'])
            v1_data['external_ids'] = format_v1_external_ids(v2_data['external_ids'])
            v1_data['links'] = format_v1_links(v2_data['links'])
            v1_data['wikipedia_url'] = format_v1_wikipedia_url(v2_data['links'])
            v1_data['addresses'] = format_v1_addresses(v2_data['locations'])
            v1_data['country'] = format_v1_country(v2_data['locations'])
            v1_data['name'] = format_v1_name(v2_data['names'])
            v1_data['acronyms'] = format_v1_acronyms(v2_data['names'])
            v1_data['aliases'] = format_v1_aliases(v2_data['names'])
            v1_data['labels'] = format_v1_labels(v2_data['names'])
            return v1_data
    except Exception as e:
        logging.error(f"Error converting v1 data to v2: {e}")
