import csv
import argparse
from collections import defaultdict


def parse_arguments():
    parser = argparse.ArgumentParser(description='Language Outlier Detection')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Path to the input CSV file')
    parser.add_argument('-l', '--languages_file', required=True,
                        help='Path to the CSV file containing the most common languages for each country')
    parser.add_argument('-o', '--output_file',
                        default='detected_outliers.csv', help='Path to the output CSV file')
    return parser.parse_args()


def read_csv_file(file_path):
    data = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data


def write_csv_file(file_path, data):
    fieldnames = data[0].keys()
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def calculate_language_distribution(data):
    distribution = defaultdict(lambda: defaultdict(int))
    for row in data:
        country_code = row['country_code']
        lang = row['lang']
        distribution[country_code][lang] += 1
    return distribution


def load_common_languages(file_path):
    common_languages = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            country_code = row['Country']
            languages = [lang.strip()
                         for lang in row['Most Common Languages'].split(';')]
            common_languages[country_code] = languages
    return common_languages


def identify_common_languages(distribution):
    common_languages = {}
    for country_code, lang_counts in distribution.items():
        max_count = max(lang_counts.values())
        threshold = 0.1 * max_count
        common_langs = [lang for lang,
                        count in lang_counts.items() if count >= threshold]
        common_languages[country_code] = common_langs
    return common_languages


def detect_outliers(data, common_languages, most_common_languages):
    for row in data:
        country_code = row['country_code']
        lang = row['lang']
        fasttext_langs = row['fasttext_langs'].split(';')
        lingua_langs = row['lingua_langs'].split(';')
        if lang == 'en':
            if 'en' not in fasttext_langs or 'en' not in lingua_langs:
                row['outlier'] = 'TRUE'
            else:
                row['outlier'] = 'FALSE'
        elif lang in most_common_languages.get(country_code, []):
            row['outlier'] = 'FALSE'
        elif lang in common_languages[country_code]:
            row['outlier'] = 'FALSE'
        else:
            row['outlier'] = 'TRUE'
    return data


def main():
    args = parse_arguments()
    input_data = read_csv_file(args.input_file)
    language_distribution = calculate_language_distribution(input_data)
    common_languages = identify_common_languages(language_distribution)
    most_common_languages = load_common_languages(args.languages_file)
    output_data = detect_outliers(
        input_data, common_languages, most_common_languages)
    write_csv_file(args.output_file, output_data)
    print(f"Outlier detection completed. Output file: {args.output_file}")


if __name__ == '__main__':
    main()
