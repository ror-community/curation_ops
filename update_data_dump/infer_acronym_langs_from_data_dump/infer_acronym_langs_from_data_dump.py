import re
import csv
import json
import argparse
from unidecode import unidecode


def parse_args():
    parser = argparse.ArgumentParser(
        description='Infer acronym languages from JSON data')
    parser.add_argument('-i', '--input', type=str,
                        required=True, help='Path to the input JSON file')
    parser.add_argument('-o', '--output', type=str,
                        default='inferred_acronyms_w_langs.csv', help='Path to the output CSV file')
    parser.add_argument('-u', '--unmatched', type=str, default='unmatched_acronyms.csv',
                        help='Path to the unmatched acronyms CSV file')
    return parser.parse_args()


def load_json(input_file):
    with open(input_file, 'r') as file:
        return json.load(file)


def extract_prefixes(name, max_prefix_length):
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split(' ')
    prefixes = []
    direct_acronym = ''.join(word[0].upper() for word in words)
    prefixes.append(direct_acronym)
    for prefix_length in range(1, max_prefix_length + 1):
        for word in words:
            prefix = ''.join(word[:prefix_length].upper() for word in words)
            prefixes.append(prefix)
    decoded = [unidecode(p) for p in prefixes]
    prefixes += decoded
    return list(set(prefixes))


def extract_prefixes(name, max_prefix_length):
    name = re.sub(r'\s+', ' ', name).strip()
    words = name.split(' ')
    prefixes = []
    direct_acronym = ''.join(word[0].upper() for word in words)
    title_case_acronym = ''.join(word[0].upper() for word in words if word[0].isupper())
    prefixes += [direct_acronym, title_case_acronym]
    for prefix_length in range(1, max_prefix_length + 1):
        prefix = ''.join(word[:prefix_length].upper() for word in words)
        prefixes.append(prefix)
    decoded_prefixes = [unidecode(prefix) for prefix in prefixes]
    prefixes.extend(decoded_prefixes)
    return list(set(prefixes))


def generate_pseudo_acronyms(name, max_prefix_length):
    pseudo_acronyms = []
    prefixes = extract_prefixes(name, max_prefix_length)
    for prefix in prefixes:
        pseudo_acronyms.append(prefix)
    return pseudo_acronyms


def is_sequential_match(acronym, name):
    iter_name = iter(name)
    return all(char in iter_name for char in acronym)


def infer_acronym_language(records, max_prefix_length):
    results = []
    unmatched = []
    for record in records:
        if 'company' not in record['types']:
            acronyms = [name for name in record['names']
                        if 'acronym' in name['types'] and not name['lang']]
            count_acronyms += len(acronyms)
            names_with_lang = [name for name in record['names'] if name['lang'] and any(
                t in ['alias', 'label'] for t in name['types'])]
            for acronym in acronyms:
                matched_name = None
                matched_lang = None
                for name in names_with_lang:
                    pseudo_acronyms = generate_pseudo_acronyms(
                        name['value'], max_prefix_length)
                    for pseudo_acronym in pseudo_acronyms:
                        if acronym['value'].upper() in pseudo_acronym or acronym['value'].upper() == pseudo_acronym:
                            matched_name = name['value']
                            matched_lang = name['lang']
                            break
                if matched_name:
                    country_code = record['locations'][0]['geonames_details']['country_code'] if record.get(
                        'locations') else ''
                    results.append({
                        'id': record['id'],
                        'name': matched_name,
                        'acronym': acronym['value'],
                        'type': ';'.join(record['types']) if len(record['types']) > 1 else record['types'][0],
                        'lang': matched_lang,
                        'country_code': country_code
                    })
                else:
                    unmatched.append({
                        'id': record['id'],
                        'acronym': acronym['value'],
                        'names': ';'.join([name['value'] for name in record['names'] if 'acronym' not in name['types']])
                    })
    return results, unmatched


def write_csv(output_file, results):
    fieldnames = ['id', 'name', 'acronym', 'type', 'lang', 'country_code']
    with open(output_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


def write_unmatched_csv(unmatched_file, unmatched):
    fieldnames = ['id', 'acronym', 'names']
    with open(unmatched_file, 'w') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unmatched)


def main():
    args = parse_args()
    records = load_json(args.input)
    max_prefix_length = 3
    results, unmatched = infer_acronym_language(records, max_prefix_length)
    write_csv(args.output, results)
    write_unmatched_csv(args.unmatched, unmatched)


if __name__ == '__main__':
    main()
