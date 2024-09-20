import csv
import re
import argparse
from thefuzz import fuzz
from furl import furl


def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text


def normalize_url_furl(url, context=None):
    if url is None:
        return None
    try:
        f = furl(url)
        f.path.normalize()
        f.path = ''
        f.remove(args=True, fragment=True)
        if f.host.startswith('www.'):
            f.host = f.host[4:]
        f.scheme = None
        return f.url.lower()
    except Exception as e:
        print(f"Error normalizing URL: {url}, Context: {context}, Error: {e}")
        return None


def parse_csv_row(row):
    return {
        'id': row['id'],
        'names': [
            row['names.types.ror_display'],
            *row['names.types.alias'].split('; '),
            *row['names.types.label'].split('; ')
        ],
        'urls': [row['links.type.website']] if row['links.type.website'] else []
    }


def check_url_matches(urls1, urls2):
    for url1 in urls1:
        for url2 in urls2:
            if normalize_url_furl(url1) == normalize_url_furl(url2):
                return True, url1, url2
    return False, None, None


def check_name_matches(names1, names2):
    matches = []
    for name1 in names1:
        for name2 in names2:
            cleaned_name1 = name1.split('*')[0].strip()
            cleaned_name2 = name2.split('*')[0].strip()
            if not cleaned_name1 or not cleaned_name2:
                continue
            name_match_ratio = fuzz.ratio(normalize_text(cleaned_name1), normalize_text(cleaned_name2))
            if name_match_ratio >= 85:
                matches.append((name1, name2, name_match_ratio))
    return matches


def check_duplicates(input_file, output_file):
    all_records = {}
    with open(input_file, 'r', newline='') as f_in:
        reader = csv.DictReader(f_in)
        for row in reader:
            parsed_row = parse_csv_row(row)
            all_records[parsed_row['id']] = parsed_row
    header = ['ror_id', 'name', 'url', 'duplicate_ror_id',
              'duplicate_name', 'duplicate_url', 'match_type', 'match_ratio']
    unique_matches = {}
    unique_name_pairs = set()
    for record_id, record in all_records.items():
        for copied_id, copied_record in all_records.items():
            if record_id == copied_id:
                continue
            match_key = tuple(sorted([record_id, copied_id]))
            if match_key in unique_matches:
                continue
            unique_matches[match_key] = []
            url_match, match_url1, match_url2 = check_url_matches(
                record['urls'], copied_record['urls'])
            if url_match:
                unique_matches[match_key].append({
                    'ror_id': record_id,
                    'name': record['names'][0],
                    'url': match_url1,
                    'duplicate_ror_id': copied_id,
                    'duplicate_name': copied_record['names'][0],
                    'duplicate_url': match_url2,
                    'match_type': 'url',
                    'match_ratio': 100
                })

            name_matches = check_name_matches(
                record['names'], copied_record['names'])
            for name1, name2, match_ratio in name_matches:
                name_pair = tuple(sorted([name1, name2]))
                if name_pair not in unique_name_pairs:
                    unique_name_pairs.add(name_pair)
                    unique_matches[match_key].append({
                        'ror_id': record_id,
                        'name': name1,
                        'url': record['urls'][0] if record['urls'] else '',
                        'duplicate_ror_id': copied_id,
                        'duplicate_name': name2,
                        'duplicate_url': copied_record['urls'][0] if copied_record['urls'] else '',
                        'match_type': 'name',
                        'match_ratio': match_ratio
                    })

    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)
        for matches in unique_matches.values():
            for match in matches:
                writer.writerow([match[field] for field in header])


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Check for duplicate name and URL metadata in a CSV file containing ROR records")
    parser.add_argument("-i", "--input_file", required=True,
                        help="Input CSV file path.")
    parser.add_argument("-o", "--output_file",
                        default="csv_duplicates.csv", help="Output CSV file path.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    check_duplicates(args.input_file, args.output_file)


if __name__ == '__main__':
    main()
