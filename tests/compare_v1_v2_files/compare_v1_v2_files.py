import argparse
import csv
import json
import os


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Compare JSON files in two directories.')
    parser.add_argument('-v1', '--v1_dir', help='v1 input directory path')
    parser.add_argument('-v2', '--v2_dir', help='v2 input directory path')
    parser.add_argument(
        '-o', '--output_csv', default='compare_v1_v2_report.csv', help='Output CSV file path')
    return parser.parse_args()


def flatten_list(nested_list):
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list


def v1_simplify_json(j):
    simplified = {}
    link_types = ['links', 'wikipedia_url']
    external_id_types = ['ISNI', 'FundRef', 'Wikidata']
    simplified['status'] = j.get('status', None)
    simplified['types'] = j.get('types', [])
    if simplified['types']:
        simplified['types'] = [t.lower() for t in simplified['types']]
    simplified['established'] = j.get('established', None)
    simplified['locations.geonames_id'] = [address.get(
        'geonames_city', {}).get('id') for address in j.get('addresses', [])]
    simplified['names.types.ror_display'] = [j.get('name')]
    simplified['names.types.alias'] = j.get('aliases', [])
    simplified['names.types.acronym'] = j.get('acronyms', [])
    simplified['names.types.label'] = j.get('labels', [])
    if simplified['names.types.label']:
        simplified['names.types.label'] = [label['label']
                                           for label in simplified['names.types.label']]
    simplified['names.types.label'].append(j.get('name'))
    for link_type in link_types:
        if link_type == 'wikipedia_url':
            simplified[f'links.type.wikipedia'] = [j.get('wikipedia_url')] if j.get('wikipedia_url') else []
        else:
            simplified[f'links.type.website'] = j.get('links', [])
    for id_type in external_id_types:
        lowercase_id_type = id_type.lower()
        if lowercase_id_type:
            preferred = j.get('external_ids', {}).get(
                id_type, {}).get('preferred')
            simplified[f'external_ids.type.{lowercase_id_type}.preferred'] = [] if preferred is None else [preferred]
            simplified[f'external_ids.type.{lowercase_id_type}.all'] = j.get('external_ids', {}).get(id_type, {}).get('all', [])
    all_values = []
    for value in simplified.values():
        if isinstance(value, list):
            all_values.extend(flatten_list(value))
        else:
            all_values.append(value)
    all_values = [value for value in all_values if value]
    simplified['all'] = all_values
    print(simplified)
    return simplified


def v2_simplify_json(j):
    simplified = {}
    name_types = ['ror_display', 'alias', 'label', 'acronym']
    link_types = ['wikipedia', 'website']
    external_id_types = ['isni', 'fundref', 'wikidata']

    simplified['status'] = j.get('status', None)
    simplified['types'] = j.get('types', [])
    simplified['established'] = j.get('established', None)
    simplified['locations.geonames_id'] = [location['geonames_id']
                                           for location in j.get('locations', [])]
    for name_type in name_types:
        simplified[f'names.types.{name_type}'] = [name['value'] for name in j.get('names', []) if name_type in name.get('types', [])]
    for link_type in link_types:
        simplified[f'links.type.{link_type}'] = [link['value'] for link in j.get('links', []) if link.get('type') == link_type]
    for id_type in external_id_types:
        ids_of_type = [ext_id for ext_id in j.get(
            'external_ids', []) if ext_id.get('type') == id_type]
        preferred = [ext_id['preferred'] for ext_id in ids_of_type]
        simplified[f'external_ids.type.{id_type}.preferred'] = [] if preferred == [None] else preferred
        all_id_values = [ext_id.get('all', []) for ext_id in ids_of_type]
        simplified[f'external_ids.type.{id_type}.all'] = sum(all_id_values, []) if all(isinstance(v, list) for v in all_id_values) else []
    all_values = []
    for value in simplified.values():
        if isinstance(value, list):
            all_values.extend(flatten_list(value))
        else:
            all_values.append(value)
    all_values = [value for value in all_values if value]
    simplified['all'] = all_values
    print(simplified)
    return simplified


def process_directories(v1_dir, v2_dir, output_csv):
    json_data1 = {}
    json_data2 = {}
    for file_name in os.listdir(v1_dir):
        if file_name.endswith('.json'):
            file_path = os.path.join(v1_dir, file_name)
            with open(file_path, 'r') as file:
                json_content = json.load(file)
                simplified_json = v1_simplify_json(json_content)
                json_data1[json_content['id']] = simplified_json
    for file_name in os.listdir(v2_dir):
        if file_name.endswith('.json'):
            file_path = os.path.join(v2_dir, file_name)
            with open(file_path, 'r') as file:
                json_content = json.load(file)
                simplified_json = v2_simplify_json(json_content)
                json_data2[json_content['id']] = simplified_json
    compare_json_data(json_data1, json_data2, output_csv)


def compare_json_data(json_data1, json_data2, output_csv):
    with open(output_csv, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['ID', 'Matched ID Found', 'Key-Value Pairs Matched',
                         'All Values Matched', 'Mismatched Keys'])
        for id1, data1 in json_data1.items():
            if id1 in json_data2:
                data2 = json_data2[id1]
                key_value_match = all(set(value) == set(data2.get(key, [])) if isinstance(value, list) else value == data2.get(key) for key, value in data1.items() if key != 'all')
                all_values_match = set(str(value) for value in data1['all']) == set(str(value) for value in data2['all'])
                mismatched_keys = [key for key in data1 if key !=
                                   'all' and data1[key] != data2.get(key)]
                writer.writerow([id1, 'True', 'True' if key_value_match else 'False',
                                 'True' if all_values_match else 'False', '; '.join(mismatched_keys)])
            else:
                writer.writerow([id1, 'False', '', '', ''])
        for id2 in json_data2:
            if id2 not in json_data1:
                writer.writerow([id2, 'False', '', '', ''])


def main():
    args = parse_arguments()
    process_directories(args.v1_dir, args.v2_dir, args.output_csv)


if __name__ == '__main__':
    main()
