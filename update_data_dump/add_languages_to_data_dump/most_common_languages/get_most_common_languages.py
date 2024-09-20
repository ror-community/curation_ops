import json
import argparse
from collections import defaultdict
import csv


def parse_args():
    parser = argparse.ArgumentParser(
        description='Count unique languages per country from a JSON file and remove outliers.')
    parser.add_argument('-i', '--input_file', type=str, required=True,
                        help='Path to the input JSON file.')
    parser.add_argument('-o', '--output_file', type=str, default='most_common_lanaguages.csv',
                        help='Path to the output CSV file (optional).')
    parser.add_argument('-t', '--threshold', type=float, default=0.1,
                        help='Threshold for removing outlier languages (optional).')
    return parser.parse_args()


def load_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def count_languages_by_country(data):
    language_counts = defaultdict(lambda: defaultdict(int))
    for org in data:
        country = org['locations'][0]['geonames_details']['country_code']
        for name in org['names']:
            lang = name.get('lang')
            if lang:
                language_counts[country][lang] += 1
    return language_counts


def remove_outlier_languages(language_counts, threshold=0.1):
    common_languages = {}
    for country, lang_counts in language_counts.items():
        total_count = sum(lang_counts.values())
        common_langs = [lang for lang, count in lang_counts.items()
                        if count >= threshold * total_count]
        if 'en' not in common_langs:
            common_langs.append('en')
        common_languages[country] = common_langs
    return common_languages


def save_results_to_csv(results, output_path):
    with open(output_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Country', 'Most Common Languages'])
        for country, languages in results.items():
            writer.writerow([country, '; '.join(languages)])
    print(f"Results saved to {output_path}")


def main():
    args = parse_args()
    input_file = args.input_file
    output_file = args.output_file
    threshold = args.threshold

    data = load_json(input_file)
    language_counts = count_languages_by_country(data)
    common_languages = remove_outlier_languages(language_counts, threshold)
    save_results_to_csv(common_languages, output_file)


if __name__ == '__main__':
    main()
